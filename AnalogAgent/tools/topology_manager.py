"""
Dynamic topology registration and management.

Orchestrates the flow:
  1. Check if topology exists in TOPOLOGY_REGISTRY (in-memory)
  2. If not, check for a persisted .meta.json on disk (cross-process cache)
  3. If not, call CircuitCollector /register_circuit/ to create netlist.j2 + TOML
  4. Register the topology in TOPOLOGY_REGISTRY + persist .meta.json

Usage from the LLM:
    from tools.topology_manager import ensure_topology_registered

    result = ensure_topology_registered(
        topology_name="tco",
        raw_netlist="...",
        role_device_map={...},
    )
    # result["config_path"] can now be used with convert_sizing()
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from tools.api_client import register_circuit
from tools.param_converter import TOPOLOGY_REGISTRY

logger = logging.getLogger(__name__)

# CircuitCollector config directory — resolved once at import time.
_CC_CONFIG_DIR: Path | None = None
_agent_root = Path(__file__).resolve().parent.parent
_candidate = _agent_root.parent / "CircuitCollector" / "CircuitCollector" / "config" / "skywater" / "opamp"
if _candidate.is_dir():
    _CC_CONFIG_DIR = _candidate


def _meta_path(topology_name: str) -> Path | None:
    """Return the .meta.json path for a topology, or None if CC dir unknown."""
    if _CC_CONFIG_DIR is None:
        return None
    return _CC_CONFIG_DIR / f"{topology_name}.meta.json"


def _persist_meta(topology_name: str, info: dict) -> None:
    """Write topology metadata to a .meta.json file next to the TOML."""
    path = _meta_path(topology_name)
    if path is None:
        return
    # Only persist JSON-serialisable fields.
    serialisable = {
        "config_path": info["config_path"],
        "requires_Cc": info.get("requires_Cc", False),
        "roles": info.get("roles", []),
        "role_device_map": info.get("role_device_map", {}),
        "passive_params": info.get("passive_params", []),
        "extra_ports": info.get("extra_ports", {}),
    }
    try:
        path.write_text(json.dumps(serialisable, indent=2) + "\n")
    except OSError as exc:
        logger.warning("Failed to persist topology meta for %s: %s", topology_name, exc)


def _load_meta(topology_name: str) -> dict | None:
    """Load a previously persisted .meta.json, or return None."""
    path = _meta_path(topology_name)
    if path is None or not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        # Minimal validation: must have config_path and role_device_map.
        if "config_path" not in data or "role_device_map" not in data:
            return None
        return data
    except (OSError, json.JSONDecodeError, KeyError) as exc:
        logger.warning("Failed to load topology meta for %s: %s", topology_name, exc)
        return None


def ensure_topology_registered(
    topology_name: str,
    raw_netlist: str,
    role_device_map: dict[str, dict],
    roles: Optional[list[str]] = None,
    requires_Cc: bool = False,
    passive_params: Optional[list[str]] = None,
    circuit_type: str = "opamp",
    extra_ports: Optional[dict] = None,
) -> dict:
    """
    Ensure a topology is registered and ready for simulation.

    If the topology already exists in TOPOLOGY_REGISTRY, returns its config_path.
    Otherwise, registers it with CircuitCollector and adds it to the registry.

    Args:
        topology_name:   Filesystem-safe identifier (e.g. 'tco', 'fc_ota')
        raw_netlist:     Full .subckt text (Jinja2-parameterized)
        role_device_map: Dict of role -> {"primary": "M3", "device_type": "nfet",
                         "mirrors": ["M4"], "mirror_of": "BIAS_GEN" (optional)}
        roles:           List of role names (derived from role_device_map if None)
        requires_Cc:     Whether the topology needs a compensation capacitor
        passive_params:  List of passive param names (e.g. ["C1_value", "Rc_value"])
        circuit_type:    Circuit category (default: "opamp")
        extra_ports:     Optional mapping of port_name -> DC voltage (V) for
                         LV cascode bias (e.g. {"Vbias_cas_p": 0.6}). When
                         provided, CircuitCollector extends the .subckt header
                         and testbench to declare and drive each port.

    Returns:
        {"status": "ok", "config_path": "config/skywater/opamp/<name>.toml",
         "registered": True/False}
    """
    # Validate extra_ports: must be a dict of {port_name: DC_voltage}.
    # A bare list of port names is a common mistake; catch it early so the
    # TOML doesn't end up with empty/malformed [testbench.extra_ports].
    if extra_ports is not None:
        if not isinstance(extra_ports, dict):
            return {
                "status": "error",
                "message": (
                    f"extra_ports must be a dict mapping port_name -> DC voltage "
                    f"(e.g. {{'Vbias_cas_p': 0.6, 'Vbias_cas_n': 0.6}}); "
                    f"got {type(extra_ports).__name__}."
                ),
            }
        bad = [k for k, v in extra_ports.items() if not isinstance(v, (int, float))]
        if bad:
            return {
                "status": "error",
                "message": (
                    f"extra_ports values must be numeric (V). "
                    f"Non-numeric entries: {bad}"
                ),
            }

    # 1. Already in in-memory registry?
    if topology_name in TOPOLOGY_REGISTRY:
        info = TOPOLOGY_REGISTRY[topology_name]
        return {
            "status": "ok",
            "config_path": info["config_path"],
            "registered": False,
        }

    # 2. Check for a persisted .meta.json on disk (cross-process cache).
    cached = _load_meta(topology_name)
    if cached is not None:
        TOPOLOGY_REGISTRY[topology_name] = {
            "bridge_module":  "tools.bridge_generic",
            **cached,
        }
        return {
            "status": "ok",
            "config_path": cached["config_path"],
            "registered": False,
        }

    # 3. Register with CircuitCollector (creates netlist.j2 + TOML)
    try:
        resp = register_circuit(
            raw_netlist=raw_netlist,
            topology_name=topology_name,
            circuit_type=circuit_type,
            extra_ports=extra_ports,
        )
    except Exception as e:
        return {"status": "error", "message": f"CircuitCollector registration failed: {e}"}

    if not resp.get("config_path"):
        return {
            "status": "error",
            "message": f"CircuitCollector returned no config_path: {resp}",
        }

    config_path = resp["config_path"]

    # 4. Add to runtime registry AND persist to disk.
    if roles is None:
        roles = list(role_device_map.keys())

    info = {
        "bridge_module":  "tools.bridge_generic",
        "config_path":    config_path,
        "requires_Cc":    requires_Cc,
        "roles":          roles,
        "role_device_map": role_device_map,
        "passive_params": passive_params or [],
        "extra_ports":    extra_ports or {},
    }
    TOPOLOGY_REGISTRY[topology_name] = info
    _persist_meta(topology_name, info)

    return {
        "status": "ok",
        "config_path": config_path,
        "registered": True,
    }
