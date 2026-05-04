# AnalogAgent

LLM-guided analog amplifier sizing agent using gm/ID methodology, SPICE
verification, and iterative root-cause diagnosis. Works with
[Claude Code](https://docs.anthropic.com/en/docs/claude-code) as the
interactive front-end.

---

## Prerequisites

| Dependency | Version | Notes |
|---|---|---|
| [Conda](https://docs.conda.io/) (or Mamba) | any | Environment management |
| [ngspice](https://ngspice.sourceforge.io/) | 42+ recommended | SPICE simulator |
| [Claude Code](https://docs.anthropic.com/en/docs/claude-code) | latest | CLI / VS Code / JetBrains |
| Anthropic API key | — | For Claude Code |

**Optional:** Redis (for simulation result caching). The system works
without it — caching is silently disabled.

---

## 1. Directory Layout

Place both repositories side by side under the **same parent directory**:

```
parent/
├── AnalogAgent/          # This repo — LLM agent + LUT data + skills
└── CircuitCollector/     # Simulation server — testbench gen + ngspice runner
```

This is required because `AnalogAgent/environment.yml` installs
CircuitCollector as an editable package via `pip install -e ../CircuitCollector`.

---

## 2. Install ngspice

ngspice must be accessible as `ngspice` on your `PATH` when the
CircuitCollector server runs.

**Option A — System package manager:**

```bash
# Ubuntu / Debian
sudo apt install ngspice

# Fedora / RHEL
sudo dnf install ngspice

# macOS (Homebrew)
brew install ngspice
```

**Option B — Custom install location:**

If ngspice is installed elsewhere (e.g. `/opt/ngspice/bin/ngspice`),
add it to `PATH` before starting the server:

```bash
export PATH=/opt/ngspice/bin:$PATH
```

**Verify:**

```bash
ngspice --version
# Should print: ngspice-42 (or similar)
```

---

## 3. Create Conda Environments

Two separate environments are needed.

### 3a. CircuitCollector environment

```bash
cd CircuitCollector
conda env create -f CircuitCollector/environment.yml
conda activate CircuitCollector
pip install -e .
conda deactivate
```

### 3b. AnalogAgent environment

```bash
cd ../AnalogAgent
conda env create -f environment.yml
conda activate Agent
```

> The `Agent` environment installs CircuitCollector in editable mode
> automatically (via `pip install -e ../CircuitCollector` in
> `environment.yml`). If this step fails, run it manually:
> ```bash
> pip install -e ../CircuitCollector
> ```

---

## 4. Configure API Key

Create a `.env` file in `AnalogAgent/` with your Anthropic API key:

```bash
cd AnalogAgent
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env
```

> `.env` is listed in `.gitignore` and will not be committed.

---

## 5. Start the CircuitCollector Server

The server must be running before any simulation can execute.

```bash
# Terminal 1 — keep this running
conda activate CircuitCollector
export PATH=/path/to/ngspice/bin:$PATH    # skip if ngspice is already on PATH
cd CircuitCollector
uvicorn CircuitCollector.api.main:app --host 0.0.0.0 --port 8001
```

Or run in the background:

```bash
conda activate CircuitCollector
export PATH=/path/to/ngspice/bin:$PATH
cd CircuitCollector
nohup uvicorn CircuitCollector.api.main:app --host 0.0.0.0 --port 8001 \
  > CircuitCollector/logs/nohup.out 2>&1 &
```

**Verify the server is up:**

```bash
curl http://localhost:8001/health
# {"status":"ok"}
```

---

## 6. Run AnalogAgent with Claude Code

```bash
# Terminal 2
conda activate Agent
cd AnalogAgent
claude                    # starts Claude Code CLI
```

Or open `AnalogAgent/` in VS Code / JetBrains with the Claude Code
extension installed.

### Quick Start — Size a 5T OTA

Paste a netlist and specs directly into Claude Code. For example:

```
.subckt 5tota gnda vdda vinn vinp vout Ib
XM1 vout  vinn net2 gnda sky130_fd_pr__nfet_01v8
XM2 net1  vinp net2 gnda sky130_fd_pr__nfet_01v8
XM5 vout  net1 vdda vdda sky130_fd_pr__pfet_01v8
XM6 net1  net1 vdda vdda sky130_fd_pr__pfet_01v8
XM3 net2  net3 gnda gnda sky130_fd_pr__nfet_01v8
XM4 net3  net3 gnda gnda sky130_fd_pr__nfet_01v8
I0  vdda  net3 Ib
.ends 5tota

Use the analog-amplifier skill to size this.
Specs: VDD=1.8V, CL=2pF, Gain>40dB, GBW>20MHz, PM>60deg, Ib=5uA
```

The agent will:
1. Identify the topology (5T OTA)
2. Register it with CircuitCollector
3. Size devices using gm/ID + LUT
4. Run SPICE simulation and verify
5. Diagnose and fix any spec failures
6. Produce a full design review

### Supported Topologies

| Topology | Description |
|---|---|
| 5T OTA | Diff pair + mirror load (single / cascode / LV-cascode variants) |
| Two-Stage Miller (TSM) | 1st stage + CS output + Miller compensation |
| Folded-Cascode OTA | Diff pair folded into opposite-type cascode |
| Telescopic OTA | Same-type cascode stack |
| Rail-to-Rail Opamp | Complementary N+P inputs + class-AB output |

---

## Project Structure

```
AnalogAgent/
├── environment.yml              # Conda env (Python 3.11)
├── .env                         # ANTHROPIC_API_KEY (git-ignored)
├── agent/                       # LLM agent orchestration
├── tools/                       # CircuitCollector API client + sizing bridges
│   ├── api_client.py            #   HTTP client (localhost:8001)
│   ├── bridge_generic.py        #   Generic topology sizing → params
│   ├── param_converter.py       #   Topology dispatcher
│   ├── topology_manager.py      #   Dynamic registration
│   └── optimizer.py             #   CMA-ES numerical optimization
├── scripts/
│   └── lut_lookup.py            # gm/ID LUT query API
├── asset_new/                   # Pre-generated LUT data (SKY130)
│   ├── nfet_01v8/               #   5 corners x 3 temps x 12 lengths
│   └── pfet_01v8/
├── .claude/
│   ├── skills/analog-amplifier/ # Hierarchical skill stack (design flows,
│   │                            #   equations, root-cause diagnosis)
│   └── settings.local.json      # Claude Code permissions
└── examples/                    # Example netlists
```

```
CircuitCollector/
├── setup.py                     # pip install -e .
├── CircuitCollector/
│   ├── api/                     # FastAPI server (port 8001)
│   ├── runner/                  # Testbench generation + ngspice execution
│   ├── spec_lib/                # Measurement templates (Jinja2)
│   ├── config/skywater/opamp/   # TOML configs per topology
│   ├── circuits/opamp/          # Netlist templates (Jinja2)
│   ├── PDK/sky130_pdk/          # Skywater 130nm PDK (bundled)
│   ├── output/                  # Simulation outputs (git-ignored)
│   ├── cache/                   # Redis + SQLite cache (optional)
│   └── environment.yml          # Conda env
└── scripts/                     # Netlist conversion utilities
```

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `Connection refused` on simulate | CircuitCollector server not running | Start the server (Step 5) |
| `ngspice: command not found` in sim logs | ngspice not on PATH in server's shell | `export PATH=/path/to/ngspice/bin:$PATH` before starting server |
| GBW / PM return `null` | ngspice failed silently | Check `CircuitCollector/output/opamp/<topo>/<topo>.log` for errors |
| `Unknown topology` from `convert_sizing` | Topology not registered in this session | The agent auto-registers; if running manually, call `ensure_topology_registered()` first |
| Redis warning on server start | Redis not installed | Safe to ignore — caching is disabled, simulations still run |
| `pip install -e ../CircuitCollector` fails | Repos not side by side | Ensure directory layout matches Step 1 |

---

## LUT Data

Pre-generated gm/ID lookup tables for SKY130 are in `asset_new/`.

- **Devices:** `nfet_01v8`, `pfet_01v8`
- **Corners:** `tt`, `ff`, `ss`, `fs`, `sf`
- **Temperatures:** `-40C`, `25C`, `85C` (linear interpolation between these)
- **Channel lengths:** 0.18, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0 um

Each file contains 11 columns:
`gm/id  gm/gds  id/W  ft  Cgg/W  Cgd/W  Cgs/W  Cdb/W  vgs  vth  vdsat`

Query API:

```python
from scripts.lut_lookup import lut_query, list_available_L

# Get intrinsic gain at L=1um, gm/ID=12
gain = lut_query('nfet', 'gm_gds', 1.0, gm_id_val=12, temp='27C', corner='tt')

# List available channel lengths
lengths = list_available_L('nfet', 'tt', '27C')
```

---

## License

See individual repository license files.
