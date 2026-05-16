# CircuitCollector

FastAPI server that bridges LLM agents to ngspice. Generates testbenches, runs simulations, parses results, and caches everything.

## What it does

CircuitCollector turns a parameter dict into a complete simulation result:

```
{"M1_L": 1.0, "M1_WL_ratio": 9.36, "M1_M": 12, ...}
  --> Jinja2 template rendering (netlist + testbench)
  --> ngspice batch simulation
  --> Result parsing (gain, GBW, PM, SR, noise, swing, mismatch, OP data)
  --> {"specs": {"dcgain_": 76.8, "phase_margin": 64.1, ...}, "op_region": {...}}
```

## API endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Server health check |
| `/simulate/` | POST | Run simulation, return specs + operating points |
| `/register_circuit/` | POST | Register a new topology from a Jinja2 netlist template |
| `/simulate/cache_stats` | GET | Redis + SQLite cache statistics |

### Example: run a simulation

```python
import requests

r = requests.post("http://localhost:8001/simulate/", json={
    "params": {
        "M1_L": 1.0, "M1_WL_ratio": 9.36, "M1_M": 12,
        "M3_L": 1.0, "M3_WL_ratio": 9.38, "M3_M": 11,
        "M5_L": 1.0, "M5_WL_ratio": 6.88, "M5_M": 2,
        "M6_M": 30, "M7_L": 0.5, "M7_WL_ratio": 9.33, "M7_M": 11,
        "M8_M": 22, "C1_value": 4.167e-12, "Rc_value": 2722,
        "ibias": 1e-5,
    },
    "base_config_path": "config/skywater/opamp/tsm_single.toml",
})

specs = r.json()["specs"]
print(f"Gain: {specs['dcgain_']:.1f} dB")
print(f"GBW:  {specs['gain_bandwidth_product_']/1e6:.1f} MHz")
print(f"PM:   {specs['phase_margin']:.1f} deg")
```

### Example: register a new topology

```python
requests.post("http://localhost:8001/register_circuit/", json={
    "raw_netlist": ".subckt {{netlist_name}} gnda vdda vinn vinp vout Ib\n...",
    "topology_name": "my_ota",
    "circuit_type": "opamp",
})
```

## Measurements

Each `/simulate/` call can produce any combination of these analyses:

| Analysis | What it measures | Key outputs |
|----------|-----------------|-------------|
| DC sweep | Power, systematic offset, temp coefficient | `power`, `vos25`, `tc` |
| AC sweep | Open-loop gain, CMRR, PSRR+, PSRR- | `dcgain_`, `cmrr`, `dcpsrp`, `dcpsrn` |
| GBW/PM | Unity-gain bandwidth, phase margin, peaking | `gain_bandwidth_product_`, `phase_margin`, `gain_peaking_db` |
| Noise | Input/output noise density, integrated noise | `integrated_input_noise`, `input_noise_density_1hz` |
| Slew rate | Rising/falling transient slope | `slew_rate_pos`, `slew_rate_neg` |
| Output swing | Linear output range (Vout tracks Vin) | `vout_low`, `vout_high`, `output_swing` |
| Mismatch MC | Monte Carlo offset (50 runs) | `vos_mismatch_3sigma` |
| Operating point | Per-device gm, gds, Vds, Vgs, Vdsat, Cgs, Cgd, region | `op_region` dict |

Measurements are controlled by TOML config flags (`measure_noise`, `measure_slew_rate`, etc.) and can be overridden per-call via the `params` dict.

## Directory structure

```
CircuitCollector/
  CircuitCollector/                 Main Python package
    api/                              FastAPI web service
      main.py                           App factory, CORS, health endpoint
      routes/simulate.py                POST /simulate/
      routes/register_circuit.py        POST /register_circuit/
      schemas.py                        Pydantic request/response models
      deps.py                           Dependency injection (SimulationAPI, cache)

    runner/                           Simulation execution pipeline
      simulation_runner.py              Orchestrator: config -> netlist -> ngspice -> results
      simulator.py                      ngspice subprocess invocation
      result_parser.py                  Parse ngspice measurement output files
      render.py                         Jinja2 template rendering
      parameter_controller.py           Parameter range management
      testbench_generator/
        testbench_generator.py            Generate stimulus and measurement SPICE code
        circuit_params_generator.py       Render circuit netlist with parameter values
        circuit_op_region_generator.py    Extract operating-point data

    cache/                            Two-tier result caching
      cache_manager.py                  Redis (hot) + SQLite (cold) with distributed locking

    circuits/opamp/                   Jinja2 netlist templates (one dir per topology)
    config/skywater/opamp/            TOML simulation configs (one file per topology)
    spec_lib/                         Testbench Jinja2 templates
      base/header.j2                    SPICE header (.PARAM, sources, stimuli)
      opamp/main.j2                     Master template (includes circuit + tech + sim)
      opamp/simulation.j2              .control block with all measurements
      tech_lib/skywater/pdk.j2          SKY130 model includes
    PDK/sky130_pdk/                   SKY130 process design kit (models, corners)
    utils/                            Helpers (path, toml, enums, log_checker)

  setup.py                          pip install -e .
```

## Testbench generation

CircuitCollector uses a layered Jinja2 template system:

```
spec_lib/opamp/main.j2              master template
  includes header.j2                  .PARAM declarations, voltage sources, input stimulus
  includes circuit.j2                 .include of the rendered subcircuit
  includes pdk.j2                     SKY130 model library includes (corner-aware)
  includes simulation.j2              .control block: DC, AC, noise, transient, swing, MC
```

The circuit netlist itself is a Jinja2 template in `circuits/opamp/<name>/netlist.j2`:

```spice
.subckt {{netlist_name}} gnda vdda vinn vinp vout Ib
XM1 net1 net1 vdda vdda sky130_fd_pr__pfet_01v8 l={{ M1_L }} w={{ M1_W }} m={{ M1_M }}
...
```

Parameters like `M1_W` are computed from `M1_WL_ratio * M1_L` at render time.

## TOML configuration

Each topology has a TOML file (e.g., `config/skywater/opamp/tsm_single.toml`) that controls:

| Section | What it configures |
|---------|-------------------|
| `[tech_lib]` | PDK path, process corner |
| `[testbench.dc]` | Supply voltage, VCM, temperature |
| `[testbench.ac]` | AC sweep range, load capacitance |
| `[testbench.ibias]` | External bias current |
| `[testbench.noise]` | Noise frequency range, spot frequency |
| `[testbench.slew_rate]` | Step size, simulation time |
| `[testbench.output_swing]` | DC sweep step size |
| `[testbench.mismatch]` | Monte Carlo run count |
| `[circuit.params]` | Default parameter values |
| `[circuit.params_range]` | Min/max bounds for each parameter |
| `[circuit.mosfet_pairs]` | Matched device pairs (M1=M2, M3=M4) |
| `[circuit.op_region]` | Operating-point extraction config |

## Cache architecture

Two-tier caching with automatic fallback:

```
Request --> Redis GET (hot cache, in-memory)
              |
              hit --> return cached result
              |
              miss --> SQLite SELECT (cold storage, persistent)
                         |
                         hit --> re-warm Redis, return
                         |
                         miss --> run ngspice simulation
                                    |
                                    write to Redis + SQLite
                                    return result
```

- **Key generation:** SHA256 of circuit path + canonicalized parameter JSON
- **Distributed locking:** Redis locks prevent duplicate simulations under concurrent requests
- **Graceful degradation:** If Redis is unavailable, falls back to SQLite-only (1s timeout)

## Quick start

```bash
# Install
conda create -n CircuitCollector python=3.11 pip -y
conda run -n CircuitCollector pip install -e .

# Start (ngspice must be on PATH)
export PATH="$HOME/ngspice46/bin:$PATH"
conda run -n CircuitCollector uvicorn CircuitCollector.api.main:app --port 8001

# Verify
curl http://localhost:8001/health
```

## Prerequisites

- **Python 3.11+**
- **ngspice 46** on PATH
- **Redis** (optional, for hot caching -- falls back to SQLite without it)

## License

MIT
