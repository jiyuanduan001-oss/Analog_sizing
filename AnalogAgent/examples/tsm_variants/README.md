# TSM OTA — First-Stage Active-Load Variants

Three bare SPICE netlists for the two-stage Miller (TSM) OTA, differing only
in how the PMOS current-mirror **active load** on the **first stage** is
implemented. The sub-block abstraction in
`.claude/skills/analog-amplifier/general/knowledge/mirror-load-structures.md`
defines these three variants.

The second stage (M7 CS amp, M8 current source), bias generation (M5 ref,
M6 tail, M8 mirror), and Miller compensation (Rc + C1) are **identical**
across all three variants.

All netlists use NMOS diff pair M3/M4, NMOS tail M6, NMOS bias reference M5,
and a SKY130 PDK.

| File | Load structure | Headroom (VDD − V\_out\_max, 1st stage) | Extra bias port |
|------|----------------|------------------------------------------|-----------------|
| `tsm_single.sp`      | Single PFET mirror (M1/M2)                       | `vdsat_M2`                          | — |
| `tsm_cascode.sp`     | Self-biased cascode (M1/M2 + M9/M10)              | `\|Vgs_M2\| + vdsat_M10`           | — |
| `tsm_lv_cascode.sp`  | Wide-swing (Sooch) cascode (M1/M2 + M9/M10)       | `vdsat_M2 + vdsat_M10`             | `Vbias_cas_p` |

## Device roles (common to all variants)

| Device(s) | Role | Type |
|-----------|------|------|
| M1 / M2 | 1st-stage PMOS mirror load (main row) | PFET |
| M9 / M10 | 1st-stage PMOS cascode load (cascode and lv\_cascode only) | PFET |
| M3 / M4 | 1st-stage NMOS differential pair | NFET |
| M5 | Bias reference (diode-connected) | NFET |
| M6 | Tail current source (mirrors M5) | NFET |
| M7 | 2nd-stage CS amplifier | PFET |
| M8 | 2nd-stage current source (mirrors M5) | NFET |
| Rc + C1 | Miller compensation (series R-C from net5 to vout) | passive |

## Matched pairs

```
M1  == M2          (1st-stage load mirror)
M9  == M10         (1st-stage cascode — when present)
M3  == M4          (diff pair)
M5  == [M6, M8]    (bias mirrors)
```

## Circuit-understanding expectations

When these netlists are fed through `general/flow/circuit-understanding.md`,
the system should detect:

- **single**:     `LOAD` role -> `sub_block_type = "single"` (no `LOAD_CAS`).
- **cascode**:    `LOAD` role -> `sub_block_type = "cascode"`, plus `LOAD_CAS` role for M9/M10. No extra ports.
- **lv_cascode**: `LOAD` role -> `sub_block_type = "lv_cascode"`, plus `LOAD_CAS` role. `extra_ports = {"Vbias_cas_p": <value>}`.

## Key nodes

```
net1     — mirror-side 1st-stage output (M3.drain, M1 chain)
net5     — output-side 1st-stage output (M4.drain, M2/M10 chain, M7.gate, comp tap)
net2     — diff pair tail node (M3.source = M4.source = M6.drain)
net3     — bias reference (M5.drain = M5.gate)
net_rc   — mid-point of series Rc-C1 Miller compensation
vout     — final output (M7.drain = M8.drain = C1 bottom plate)
```

For cascode / lv\_cascode variants only:
```
net_int_ref — internal node between M1 (main) and M9 (cas) on mirror side
net_int_out — internal node between M2 (main) and M10 (cas) on output side
```

## Port convention

All subcircuits use the standard CircuitCollector testbench port order:
```
gnda vdda vinn vinp vout Ib [Vbias_cas_p]
```
The LV cascode variant adds `Vbias_cas_p` as a 7th port, supplied by the
testbench as a DC voltage:
`Vbias_cas_p = VDD - (vdsat_M2 + vdsat_M10 + |Vth_cas|)`. This value
should be re-derived per sizing iteration from the current LUT-derived
`vdsat`/`vth` and passed to `simulate_circuit(..., extra_ports={...})`
rather than relying on the seed value baked into the TOML at
`ensure_topology_registered` time.
