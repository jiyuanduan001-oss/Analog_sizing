# AnalogAgent — Agent Instructions

> This file is for OpenAI Codex and compatible agents.
> For Claude Code, see `CLAUDE.md`. Both files point to the same
> skill stack — the source of truth is `skills/analog-amplifier/`.

When asked to size or design an analog circuit, follow the procedural
skill stack defined in `skills/analog-amplifier/SKILL.md`.

Read that file first, then read each referenced sub-file on-demand as
you reach each stage. Do not read all files upfront.

Key points:
- All calculations must be done in Python, not mentally.
- The design review (Stage 6) has a strict format defined in
  `skills/analog-amplifier/general/flow/design-review.md` — follow
  it verbatim.
- Use root-cause diagnosis files for fixing failures, do not improvise.
- CircuitCollector must be running on localhost:8001 for simulations.
- See README.md for environment setup.
