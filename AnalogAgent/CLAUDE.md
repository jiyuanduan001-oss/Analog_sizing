# AnalogAgent — Project Instructions

This repository contains an LLM-driven analog circuit sizing agent.
These instructions apply to any LLM agent working in this codebase
(Claude Code, Codex, Cursor, API-based agents, etc.).

## Skill Stack

The sizing flow is defined as a **procedural skill stack** in:

    skills/analog-amplifier/SKILL.md

This file is the master entry point. It defines the design flow stages,
rules, and references to sub-files that contain detailed procedures.

## How to Use the Skill Stack

When asked to size a circuit (any task involving "size", "design",
"optimize", or working with amplifier specs):

1. **Read `skills/analog-amplifier/SKILL.md` first.** It defines the
   flow stages (1-6) and the rules you must follow.

2. **Read each sub-file on-demand, not upfront.** The SKILL.md
   references files like `general/flow/spec-understanding.md` and
   `circuit-specific/tsm/tsm-design-flow.md`. Read each one only
   when you reach that stage in the flow. This keeps your context
   focused on the current task.

3. **Follow each sub-file as a procedure to execute**, not as
   reference material to absorb. Execute the steps in order,
   print the required outputs, and respect the gates.

4. **The design-review format is strict.** When you reach Stage [6],
   read `general/flow/design-review.md` and follow its template
   verbatim. Do NOT invent your own report format.

## Key Rules (from the skill stack)

- All calculations MUST be done in Python. Never do mental arithmetic.
- During the optimization loop, use the circuit-specific
  root-cause-diagnosis skill. Do NOT improvise fixes.
- Always report SR+ and SR- as separate specs, never min().
- Always print the full spec comparison table after optimization,
  even if results did not improve.
- Use `generate_all_plots()` (not `collect_waveforms()`) so PNGs
  always match the latest simulation data.
- Must run `simulate_circuit(..., save_waveforms=True)` before
  calling `generate_all_plots()`.

## Environment

- **Python**: Use the conda environment defined in `environment.yml`.
- **Working directory**: All imports assume CWD is the repo root.
  Use `sys.path.insert(0, '.')` when running standalone scripts.
- **CircuitCollector**: Must be running on `localhost:8001` before
  simulation. See README.md for setup.
- **LUT data**: Lives in `asset_new/`. Temperature interpolation is
  automatic. Use string format for temp (e.g. `'27C'`, `'20C'`).
- **ngspice**: Must be on PATH when CircuitCollector server starts.
