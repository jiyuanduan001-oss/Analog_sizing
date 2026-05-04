# Mirror/Load Sub-Block Structures

## Purpose

Current mirrors and active loads in amplifier topologies (5T OTA, TSM) can
be implemented with three different transistor-level structures. This file
defines those structures as **sub-blocks** and specifies the effective
small-signal quantities that the surrounding circuit equations must use.

Any role that is a current mirror or active load — `LOAD`, `TAIL`,
`OUTPUT_BIAS`, `BIAS_GEN` — can in principle be realized as any of the
three sub-block types. The detection is done from the netlist (see
`general/flow/circuit-understanding.md`). Once detected, the equations in
the circuit-specific files use the sub-block outputs `gds_eq`, `C_eq`,
`p_int` uniformly.

---

## Section A — The Sub-Block Abstraction

A mirror/load sub-block is a two-terminal network between an output node
and a supply rail. Looking into the output node, the external equations
need only five quantities:

| Quantity | Meaning | Used in |
|----------|---------|---------|
| `gds_eq` | Small-signal conductance looking into output node | DC gain denominator: `A0 = gm_in / (gds_in + gds_eq)` |
| `C_eq` | Capacitance at the output node contributed by the sub-block | Total output cap: `C_out = CL + C_eq + ...` |
| `p_int` | Internal pole introduced by the sub-block (if any) | Non-dominant pole for PM |
| `V_headroom` | Minimum voltage drop from rail to output node | Output swing constraint and OP check |
| `Vbias_ext` | External bias voltage required (if any) | Testbench port declaration |

If `p_int` is `None`, the sub-block has no internal node and contributes
no extra pole. If `Vbias_ext` is `None`, the sub-block is self-biased and
does not require an additional port on the subcircuit.

---

## Section B — Sub-Block Type 1: `single`

One transistor between output and rail. The formulas below are
polarity-agnostic — apply identically to an NMOS stack (rail = VSS,
typical for TAIL / OUTPUT_BIAS) and a PMOS stack (rail = VDD, typical
for LOAD). "output node" is the abstract external net that the
sub-block drives: for LOAD / OUTPUT_BIAS it is the amplifier output,
for TAIL it is the diff-pair source node.

```
      rail (VDD or VSS)
        |
       [M_main]          ← gate driven by mirror/diode
        |
      output node
```

**Effective quantities:**

```
gds_eq    = gds_main                     [from LUT: gm_main / gm_gds_main]
C_eq      = Cgd_main + Cdb_main          [at output node]
p_int     = None                          [no internal node]
V_headroom = vdsat_main                    [at saturation edge]
Vbias_ext = None                          [self-biased]
```

This is the default behavior that matches the current 5T OTA / TSM flow.

---

## Section C — Sub-Block Type 2: `cascode` (self-biased)

Two transistors of the same type stacked in series. Both gates are driven
from the existing mirror/diode chain of the surrounding circuit — no
extra bias supply is needed. Formulas are polarity-agnostic (NMOS with
rail=VSS and PMOS with rail=VDD use the same `gds_eq`, `C_eq`, `p_int`,
and `V_headroom` expressions).

```
      rail (VDD or VSS)
        |
      [M_main]           ← closer to supply rail; gate on mirror chain
        |
      internal node
        |
      [M_cas]            ← farther from rail; gate on mirror chain
        |
      output node
```

The cascode device (M_cas) is always **farther from the supply rail**,
with its drain at the output node. The main device (M_main) is always
**adjacent to the rail**. For an NMOS stack (rail = VSS), M_main is at
the bottom and M_cas is on top; for a PMOS stack (rail = VDD), M_main
is at the top and M_cas is below. The connections are:

- `M_main` and `M_cas` are the **same type** (both NMOS or both PMOS)
- `M_main.source` = rail
- `M_main.drain` = `M_cas.source` = internal node
- `M_cas.drain` = output node
- `M_cas.gate` and `M_main.gate` are both driven by the mirror/diode chain
  (not external bias, not at the output node)

**Effective quantities** (compute in Python):

```
# Looking into output node from outside (full expression):
Rout       = ro_cas + ro_main + gm_cas × ro_cas × ro_main
gds_eq     = 1 / Rout
           = (gds_main × gds_cas) / (gm_cas + gds_main + gds_cas)
           ≈ (gds_main × gds_cas) / gm_cas    [since gm_cas >> gds]

# Capacitance at output node:
C_eq       = Cgd_cas + Cdb_cas

# Capacitance at internal node:
C_int      = Cgs_cas + Cdb_main + Cgd_main

# Internal pole from internal node (rad/s):
p_int      = (gm_cas + gmb_cas) / C_int
           ≈ gm_cas / C_int             [gmb_cas not in LUT; ~10-20% underestimate]

# Headroom (self-biased cascode):
#   M_main sits at Vds = Vgs (from the diode reference chain),
#   M_cas needs only Vds ≥ vdsat_cas to stay saturated.
V_headroom = Vgs_main + vdsat_cas              (one Vgs penalty)

Vbias_ext  = None
```

The cascode boosts output impedance by a factor of `gm_cas × ro_cas`
(the intrinsic gain of the cascode device).

---

## Section D — Sub-Block Type 3: `lv_cascode` (low-voltage / wide-swing / Sooch)

Two transistors of the same type. The small-signal equivalents are
identical to `cascode`, but the DC biasing is different so the headroom
shrinks to `vdsat_main + vdsat_cas`. This requires a different netlist AND an external
bias supply.

**NMOS lv_cascode wiring (rail = VSS):**

```
      output node
        |   drain
      [M_cas]            ← farther from rail; gate = Vbias_ext (external)
        |   source
      internal node
        |   drain
      [M_main]           ← closer to rail; gate = M_cas.drain (= output node)
        |   source
      VSS (rail)
```

The main transistor's **gate is connected to the output node** (the
cascode device's drain), and the cascode's **gate is at an external bias**.
PMOS lv_cascode is the mirror image with rail = VDD.

**Netlist pattern (how to recognize from the netlist):**
1. Two same-type devices stacked in series between a rail and the output
2. `M_main.gate == M_cas.drain` (this is the signature)
3. `M_cas.gate` is connected to a top-level port (external bias)

**Effective quantities** — small-signal formulas are **identical** to the
regular cascode:

```
Rout    = ro_cas + ro_main + gm_cas × ro_cas × ro_main
gds_eq  = (gds_main × gds_cas) / (gm_cas + gds_main + gds_cas)
        ≈ (gds_main × gds_cas) / gm_cas
C_eq    = Cgd_cas + Cdb_cas
C_int   = Cgs_cas + Cdb_main + Cgd_main
p_int   = (gm_cas + gmb_cas) / C_int  ≈  gm_cas / C_int
```

**Headroom (the key difference):**

```
V_headroom = vdsat_main + vdsat_cas        (much better than cascode)
```

The main device sits at its saturation edge (Vds_main = vdsat_main), and the
cascode is stacked above it with its own vdsat_cas. The output can swing
down to (vdsat_main + vdsat_cas) above the rail.

**External bias value (NMOS):**

```
Vbias_ext = Vbias_cas = vdsat_main + vdsat_cas + Vth_cas

Derivation:
  V_internal = vdsat_main          (main at saturation edge)
  Vgs_cas   = Vth_cas + vdsat_cas  (cas saturated)
  Vbias_cas = V_internal + Vgs_cas
            = vdsat_main + Vth_cas + vdsat_cas
```

**External bias value (PMOS):**

```
Vbias_ext = VDD − (vdsat_main + vdsat_cas + |Vth_cas|)
```

This bias must be provided by the testbench via an additional subcircuit
port (e.g. `Vbias_cas_n`, `Vbias_cas_p`).

---

## Section E — Detection Rules from Netlist

Given a candidate main device `M_main` for a role (e.g. the LOAD primary
transistor identified by basic role assignment), check for a cascode
companion:

```
Look for a device M_cas such that:
  - M_cas is the same type (both NMOS or both PMOS) as M_main
  - M_cas.source == M_main.drain    (stacked in series)
  - M_cas.drain  == the external output/signal node

If no such device exists:
  → sub_block_type = "single"
  → no _CAS role created

If found, inspect the gate wiring:
  if M_main.gate is in the mirror/diode chain of the circuit AND
     M_cas.gate  is in the mirror/diode chain of the circuit:
       → sub_block_type = "cascode"        (self-biased)
  elif M_main.gate == M_cas.drain (== output node) AND
       M_cas.gate  is a top-level subcircuit port (external bias):
       → sub_block_type = "lv_cascode"     (Sooch wiring)
  else:
       → report ambiguous; ask the user
```

Assign the cascode device a role derived by suffix: `<MAIN_ROLE>_CAS`.
Examples: `LOAD_CAS`, `TAIL_CAS`, `OUTPUT_BIAS_CAS`.

Record in the role_device_map:
```python
"<MAIN_ROLE>": {
    ...
    "sub_block_type": "single" | "cascode" | "lv_cascode",
},
"<MAIN_ROLE>_CAS": {
    "primary": "<Mx>",
    "mirrors": [...],
    "device_type": "nfet"|"pfet",
    "parent_role": "<MAIN_ROLE>",
},
```

For `lv_cascode`, also record the required bias port name in a
topology-level field (e.g. `extra_ports: ["Vbias_cas_n"]`) so the
registration pipeline adds it to the `.subckt` header.

---

## Section F — Sizing the Cascode Device

The cascode device carries the same DC current as its main companion
(they are in series), so `ID_cas = ID_main` is fixed.

The designer still has two free parameters: `gm/ID_cas` and `L_cas`.

**Guidelines:**

| Parameter | Recommended | Reason |
|-----------|-------------|--------|
| gm/ID_cas | 8–12 S/A (strong-to-moderate inversion) | Higher gm_cas → higher `p_int = gm_cas / C_int` |
| L_cas | L_min or 2·L_min | The cascode device multiplies ro; its own intrinsic gain matters much less. Short L keeps C_int small. |

**Constraint**: the internal pole must not degrade phase margin. For a
60° PM design with dominant pole at `ω_c`, require:

```
p_int ≈ gm_cas / C_int  >  3 × ω_c
```

If `p_int < 3·ω_c`, either:
- Increase gm_cas (raise current or lower gm/ID — but current is fixed)
- Reduce L_cas (shorter → smaller C_int)
- Switch to a weaker gm/ID on the main to free current for the cascode
  (only if main's gain contribution allows it)

**For lv_cascode**, also compute the required external bias:
```python
# NMOS
Vbias_cas_n = vdsat_main + vdsat_cas + Vth_cas_from_LUT
# PMOS
Vbias_cas_p = VDD - (vdsat_main + vdsat_cas + abs(Vth_cas_from_LUT))
```
and emit this into the testbench configuration.

---

## Section G — Using the Sub-Block in Circuit Equations

When the circuit-specific equation file writes a gain expression, it
should use the sub-block's `gds_eq` rather than a raw device `gds`:

**Before (single only):**
```
A0 = gm_in / (gds_in + gds_LOAD)
```

**After (any sub-block type):**
```
A0 = gm_in / (gds_in + gds_eq_LOAD)
```

where `gds_eq_LOAD` is computed from the LOAD sub-block's type using
Section B / C / D formulas. The same substitution applies for output
capacitance (`C_eq_LOAD` replaces single-device `Cgd_LOAD + Cdb_LOAD`)
and for non-dominant pole lists (add `p_int_LOAD` if the sub-block is
cascode or lv_cascode).

---

## Section H — Quick Reference Table

| Property | single | cascode | lv_cascode |
|----------|--------|---------|------------|
| # of devices | 1 | 2 | 2 |
| `Rout` | `ro` | `ro_c + ro_m + gm_c·ro_c·ro_m` | same as cascode |
| `gds_eq` | `gds` | `gds_m·gds_c / (gm_c+gds_m+gds_c)` | same as cascode |
| `C_eq` at output | `Cgd + Cdb` | `Cgd_c + Cdb_c` | same as cascode |
| Internal pole | none | `(gm_c+gmb_c) / C_int` | same as cascode |
| Headroom | `vdsat` | `Vgs_main + vdsat_cas` | `vdsat_main + vdsat_cas` |
| External bias | No | No | Yes (`vdsat_main + vdsat_cas + Vth`) |
| Netlist wiring | — | Both gates in mirror chain | Main.gate = Cas.drain; Cas.gate = port |
| Gain scaling | `gm·ro` | `(gm·ro)²` | `(gm·ro)²` |

---

## References

- `general/flow/circuit-understanding.md` — sub-block detection workflow
- `circuit-specific/5TOTA/5t-ota-equation.md` — 5T OTA equations using gds_eq
- `circuit-specific/tsm/tsm-equation.md` — TSM equations using gds_eq
