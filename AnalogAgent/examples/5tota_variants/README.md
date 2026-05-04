# 5T OTA — Active-Load Variants

Three bare SPICE netlists for the classic 5-transistor OTA, differing only
in how the PMOS current-mirror **active load** is implemented. The
sub-block abstraction in
`.claude/skills/analog-amplifier/general/knowledge/mirror-load-structures.md`
defines these three variants.

All netlists use NMOS diff pair M1/M2, NMOS tail M3, NMOS bias reference M4,
and a SKY130 PDK.

| File | Load structure | Headroom (VDD − V_out_max) | Extra bias port |
|------|----------------|----------------------------|-----------------|
| `5tota_single.sp`      | Single PFET mirror (M5/M6)                   | `vdsat_M5`                          | — |
| `5tota_cascode.sp`     | Self-biased cascode (M5/M6 + M7/M8)          | `\|Vgs_M5\| + vdsat_M7`             | — |
| `5tota_lv_cascode.sp`  | Wide-swing (Sooch) cascode (M5/M6 + M7/M8)   | `vdsat_M5 + vdsat_M7`               | `Vbias_cas_p` |

## Circuit-understanding expectations

When these netlists are fed through `general/flow/circuit-understanding.md`,
the system should detect:

- **single**:     `LOAD` role → `sub_block_type = "single"` (no `LOAD_CAS`).
- **cascode**:    `LOAD` role → `sub_block_type = "cascode"`, plus `LOAD_CAS` role for M7/M8. No extra ports.
- **lv_cascode**: `LOAD` role → `sub_block_type = "lv_cascode"`, plus `LOAD_CAS` role. `extra_ports = {"Vbias_cas_p": <value>}`.

## Port convention

All subcircuits use the standard CircuitCollector testbench port order:
```
gnda vdda vinn vinp vout Ib [Vbias_cas_p]
```
The LV cascode variant adds `Vbias_cas_p` as a 7th port, supplied by the
testbench as a DC voltage:
`Vbias_cas_p = VDD − (vdsat_M5 + vdsat_M7 + |Vth_cas|)`. This value
should be re-derived per sizing iteration from the current LUT-derived
`vdsat`/`vth` and passed to `simulate_circuit(..., extra_ports={...})`
rather than relying on the seed value baked into the TOML at
`ensure_topology_registered` time.
