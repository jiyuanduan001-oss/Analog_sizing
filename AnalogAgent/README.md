# AnalogAgent

LLM-driven analog IC sizing agent. Operates as a set of structured skills that guide any LLM through gm/ID-based sizing, SPICE verification, and iterative root-cause diagnosis.

## How it works

AnalogAgent is **not** a standalone program you run. It is a workspace that an LLM agent (Claude Code, Codex, Cursor, etc.) opens and operates in. The agent reads the skill stack, executes Python, calls the CircuitCollector simulation server over HTTP, and iterates until all specs are met.

```
LLM agent
  reads  skills/analog-amplifier/SKILL.md        (design flow)
  calls  scripts/lut_lookup.py                    (gm/ID LUT queries)
  calls  tools/bridge_generic.py                  (simulation bridge)
  calls  tools/optimizer.py                       (post-sizing optimizer)
  writes simulation_waveform/nominal/*.png        (Bode, transient, swing, noise plots)
```

## Directory structure

```
AnalogAgent/
  skills/analog-amplifier/          Procedural skill stack (markdown, agent-agnostic)
    SKILL.md                          Master flow definition (6 stages)
    general/flow/                     Shared: spec validation, circuit ID, sim verification, design review
    general/knowledge/                Shared: LUT derivation, mirror structures, optimizer, PM regression
    circuit-specific/5TOTA/           5T OTA: equations, design flow, root-cause diagnosis
    circuit-specific/tsm/             Two-Stage Miller: equations, design flow, root-cause diagnosis

  tools/                            Python integration layer
    api_client.py                     HTTP client for CircuitCollector (/simulate, /register_circuit, /health)
    bridge_generic.py                 Topology-agnostic simulation bridge (role targets -> params -> simulate)
    param_converter.py                Converts gm/ID sizing targets to CircuitCollector parameter dicts
    topology_manager.py               Dynamic topology registration (in-memory -> disk cache -> server)
    optimizer.py                      CMA-ES + coordinate descent post-sizing optimizer
    waveform_utils.py                 Waveform parsing, annotated Bode/transient/swing/noise plots

  scripts/
    lut_lookup.py                     gm/ID LUT query API (lut_query, list_available_L, extrinsic_caps)

  asset_new/                        Pre-computed transistor characterization data
    nfet_01v8/                        NMOS 1.8V: 5 corners x 3 temps x 13 channel lengths
    pfet_01v8/                        PMOS 1.8V: same coverage

  examples/                         Reference netlists
    5tota_variants/                   5tota_single.sp, 5tota_cascode.sp, 5tota_lv_cascode.sp
    tsm_variants/                     tsm_single.sp, tsm_cascode.sp, tsm_lv_cascode.sp

  spec-form-template.md             User-facing spec form (fill in VDD, CL, Gain, GBW, PM, etc.)
  CLAUDE.md                         Auto-loaded instructions for Claude Code
  AGENTS.md                         Auto-loaded instructions for Codex
  environment.yml                   Conda environment definition
```

## Skill stack

The design flow is encoded as markdown procedures in `skills/analog-amplifier/`. The LLM reads and executes them step by step.

| Stage | Skill file | What it does |
|-------|-----------|-------------|
| [1] Spec Understanding | `general/flow/spec-understanding.md` | Validate 5 required fields, check LUT temperature, parse optional specs |
| [2] Circuit Understanding | `general/flow/circuit-understanding.md` | Parse netlist, match topology, generate Jinja2 template, register with server |
| [3] Design Flow | `circuit-specific/<topo>/*-design-flow.md` | gm/ID-based sizing: diff pair, load, output stage, bias mirrors, compensation |
| [4] Simulation Verification | `general/flow/simulation-verification.md` | Run SPICE, check OP saturation, compare analytical vs SPICE |
| [5] Root-Cause Diagnosis | `circuit-specific/<topo>/*-root-cause-diagnosis.md` | Fault trees: gain, GBW, PM, SR, CMRR, PSRR, noise, swing, mismatch |
| [6] Design Review | `general/flow/design-review.md` | Final report with analytical / regression / OP-based / SPICE columns |

Supporting knowledge files:
- `general/knowledge/lut-parameter-derivation.md` — How to derive all device params from a single LUT query
- `general/knowledge/mirror-load-structures.md` — Single / cascode / wide-swing cascode sub-block formulas
- `general/knowledge/numerical-optimization.md` — CMA-ES optimizer procedure and penalty functions
- `general/knowledge/self-evolving-corrections.md` — Regression-based PM correction that improves over runs

## gm/ID look-up tables

Pre-computed characterization data for SKY130 1.8V devices:

| Parameter | Unit | Description |
|-----------|------|-------------|
| `gm_gds` | V/V | Intrinsic gain |
| `id_w` | A/m | Current density |
| `ft` | Hz | Transit frequency |
| `cgs_w`, `cgd_w`, `cdb_w` | F/m | Capacitance densities |
| `vdsat` | V | Saturation voltage |
| `vth` | V | Threshold voltage |

**Coverage:** 5 corners (tt, ff, ss, fs, sf) x 3 temperatures (-40, 25, 85 C) x 13 channel lengths (0.18 -- 6.0 um). Intermediate temperatures are interpolated automatically.

**API:**
```python
from scripts.lut_lookup import lut_query, list_available_L, extrinsic_caps

gm_gds = lut_query('nfet', 'gm_gds', L=0.5, corner='tt', temp='27C', gm_id_val=12)
L_vals = list_available_L('nfet', corner='tt', temp='27C')
ex = extrinsic_caps('nfet', W=10e-6, M=1)  # gate-drain overlap, junction sidewall
```

## Simulation bridge

The bridge converts role-based sizing targets into flat parameter dicts and calls CircuitCollector:

```python
from tools import convert_sizing, simulate_circuit

result = convert_sizing(
    topology='tsm_single',
    roles_raw={
        "DIFF_PAIR": {"gm_id_target": 15, "L_guidance_um": 1.0, "id_derived": 75e-6},
        "LOAD":      {"gm_id_target": 12, "L_guidance_um": 1.0, "id_derived": 75e-6},
        ...
    },
    Ib_a=10e-6, Cc_f=4e-12, Rc_ohm=2700,
)

sim = simulate_circuit(
    result["params"],
    config_path=result["config_path"],
    corner='tt', temperature=27, supply_voltage=1.8, CL=5e-12,
)

print(sim['specs']['dcgain_'])       # 76.8 dB
print(sim['specs']['phase_margin'])  # 64.1 deg
```

## Optimizer

Post-sizing numerical optimization that minimizes power / maximizes gain or GBW while keeping all specs above user targets:

```python
from tools import cma_es, make_batch_evaluator, compute_penalty

best_params, best_specs = cma_es(
    initial_params, config_path, targets, weights,
    corner='tt', temperature=27, supply_voltage=1.8, CL=5e-12,
)
```

## Prerequisites

- **CircuitCollector** running on `localhost:8001` (see `setup_and_run.ipynb`)
- **ngspice 46** on PATH (required by CircuitCollector)
- **Python 3.11** in the `Agent` conda environment

## License

MIT
