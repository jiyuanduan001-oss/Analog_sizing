from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field


class SimRequest(BaseModel):
    params: Dict[str, Any] = Field(
        ...,
        description="Sizing parameters",
    )

    # Optional parameters
    base_config_path: Optional[str] = Field(None, description="Base config file path")
    output_dir: Optional[str] = Field(None, description="Output directory path")
    spec_list: Optional[List[str]] = Field(None, description="List of specs to extract")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "params": {"M1_L": 0.15, "M1_WL_ratio": 3.7, "M1_M": 350},
                "base_config_path": "config/skywater/opamp/5tota_single.toml",
                "output_dir": "output/opamp/tsm",
                "spec_list": ["dcgain_", "gain_bandwidth_product_", "phase_margin"]
            }
        }
    }


class RegisterCircuitRequest(BaseModel):
    raw_netlist: str = Field(
        ...,
        description="Raw .subckt netlist text (SPICE format or Jinja2-parameterized)",
    )
    topology_name: str = Field(
        ...,
        description="Filesystem-safe topology identifier (e.g. 'tco', 'fc_ota')",
    )
    circuit_type: str = Field(
        "opamp",
        description="Circuit type category",
    )
    extra_ports: Optional[Dict[str, float]] = Field(
        None,
        description=(
            "Optional DC bias ports beyond (gnda, vdda, vinn, vinp, vout, Ib). "
            "Mapping of port_name -> default DC voltage (V). Used for LV cascode "
            "bias. The netlist.j2 subckt header and testbench will be extended "
            "to declare and drive these ports."
        ),
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "raw_netlist": ".subckt tco gnda vdda vinn vinp vout Ib\n...\n.ends tco",
                "topology_name": "tco",
                "circuit_type": "opamp",
                "extra_ports": {"Vbias_cas_p": 0.6, "Vbias_cas_n": 1.2},
            }
        }
    }


class RegisterCircuitResponse(BaseModel):
    status: str = Field(..., description="'created', 'already_exists', or 'error'")
    config_path: str = Field(..., description="Relative TOML config path")
    netlist_j2_path: str = Field(..., description="Relative netlist.j2 path")
    message: Optional[str] = Field(None, description="Additional info")


class SimResponse(BaseModel):
    specs: Dict[str, Any]
    op_region: Dict[str, Any]
    logs: Optional[str] = Field(None, description="Optional, log or result file path")
