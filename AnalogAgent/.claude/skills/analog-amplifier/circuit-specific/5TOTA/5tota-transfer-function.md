# 5T OTA — Small-Signal Transfer Function

## Purpose

Derive the exact open-loop voltage gain H(s) = Vout/Vd from KCL at every
node, including ALL parasitic capacitances. This gives poles and zeros
that closely match SPICE AC analysis.

---

## Circuit and Nodes

```
         VDD (AC ground)
          |          |
        [M6]       [M5]          PMOS LOAD (source = VDD = AC gnd)
          |          |
   V2 (net1)      V1 (vout) ── CL ── GND
          |          |
   vinp──[M2]  [M1]──vinn       NMOS DIFF_PAIR
          └────┬────┘
            V3 (net2)
               |
             [M3]                NMOS TAIL (gate = AC gnd, gm3 = 0)
               |
             GND
```

M1 (gate=vinn) has drain at V1 (vout); M2 (gate=vinp) has drain at V2 (net1).
vinp ↑ → M2 current ↑ → net1 rises → M5 mirror increases → vout rises (non-inverting).

| Device | Type | Gate | Drain | Source | Bulk |
|--------|------|------|-------|--------|------|
| M1 | NMOS | vinn | V1 | V3 | GND |
| M2 | NMOS | vinp | V2 | V3 | GND |
| M5 | PMOS | V2 | V1 | GND(ac) | GND(ac) |
| M6 | PMOS | V2 | V2 | GND(ac) | GND(ac) |
| M3 | NMOS | GND | V3 | GND | GND |

---

## Capacitance Inventory

### Grounded capacitances

```
C1g = CL + Cdb1 + Cdb5                 (at V1)
C2g = Cdb2 + Cdb6 + Cgs5 + Cgs6       (at V2)
C3g = Csb1 + Csb2 + Cdb3 + Cgd3       (at V3)
```

### Coupling capacitances

```
Between V1 and V2:    Cgd5
Between V1 and vinn:  Cgd1
Between V2 and vinp:  Cgd2
Between V3 and vinn:  Cgs1
Between V3 and vinp:  Cgs2
```

Note: Cgd6 has both terminals at V2 (diode) → zero current, ignored.

---

## KCL Equations

Convention: sum of currents **leaving** each node = 0.
MOSFET drain current `id = gm·vgs + gds·vds` flows into the drain
terminal, i.e., current leaves the drain node through the device.

### Node V1 (vout)

```
V1·[gds1 + gds5 + s(C1g + Cgd1 + Cgd5)]
+ V2·[gm5 − s·Cgd5]
+ V3·[−gm1 − gds1]
= −(gm1 − s·Cgd1)·vinn                                 ... (1)
```

### Node V2 (net1)

```
V1·[−s·Cgd5]
+ V2·[gds2 + gm6 + gds6 + s(C2g + Cgd2 + Cgd5)]
+ V3·[−gm2 − gds2]
= −(gm2 − s·Cgd2)·vinp                                 ... (2)
```

### Node V3 (net2)

```
V1·[−gds1]
+ V2·[−gds2]
+ V3·[gm1 + gds1 + gm2 + gds2 + gds3 + s(C3g + Cgs1 + Cgs2)]
= (gm1 + s·Cgs1)·vinn + (gm2 + s·Cgs2)·vinp            ... (3)
```

---

## Differential-Mode Reduction (matched M1 = M2)

Set vinp = +vd/2, vinn = −vd/2. With matched diff pair (gm1=gm2≡gm,
Cgs1=Cgs2, Cgd1=Cgd2≡Cgd_dp), equation (3) gives V3 = 0.

The system reduces to **2×2** with V3 = 0:

```
Y·V = I·vd

┌                  ┐ ┌    ┐       ┌     ┐
│ Y11    Y12       │ │ V1 │       │ +1  │
│                  │ │    │ = B · │     │ · vd
│ Y21    Y22       │ │ V2 │       │ −1  │
└                  ┘ └    ┘       └     ┘
```

where `B = (gm − s·Cgd_dp) / 2` and:

```
Y11 = G1 + s·C1        G1 = gds1 + gds5
Y12 = gm5 − s·Cgd5     C1 = CL + Cdb1 + Cdb5 + Cgd1 + Cgd5
Y21 = −s·Cgd5
Y22 = G2 + s·C2        G2 = gds2 + gm6 + gds6
                        C2 = Cdb2 + Cdb6 + Cgs5 + Cgs6 + Cgd2 + Cgd5
```

---

## Transfer Function H(s) = V1 / vd

By Cramer's rule:

```
         B · [(Y22 + Y12)]
H(s) = ─────────────────────
         Y11·Y22 − Y12·Y21
```

### Numerator N(s)

```
N(s) = B · (Y22 + Y12)

     = (gm − s·Cgd_dp) / 2  ×  (G2 + gm5 + s·C_mir)

where  C_mir = C2 − Cgd5 = Cdb2 + Cdb6 + Cgs5 + Cgs6 + Cgd2
```

Expanding:

```
N(s) = [a0 + a1·s + a2·s²] / 2

a0 = gm · (G2 + gm5)
a1 = gm·C_mir − Cgd_dp·(G2 + gm5)
a2 = −Cgd_dp · C_mir
```

**Zeros** (roots of N(s) = 0):

```
z1:  s = −(G2 + gm5) / C_mir ≈ −(gm5 + gm6) / C_mir     [LHP — mirror zero]
z2:  s = +gm / Cgd_dp                                      [RHP — very high freq, ≈ ft]
```

The mirror zero z1 is at approximately **twice the mirror pole frequency**
(same as the traditional `fz = 2·fp2`). The RHP zero z2 is near the
transit frequency and negligible for practical designs.

### Denominator D(s)

```
D(s) = Y11·Y22 − Y12·Y21

     = (G1 + sC1)(G2 + sC2) − (gm5 − sCgd5)(−sCgd5)

     = b0 + b1·s + b2·s²

b0 = G1·G2
b1 = G1·C2 + G2·C1 + gm5·Cgd5
b2 = C1·C2 − Cgd5²
```

**Poles** (roots of D(s) = 0):

Exact: use the quadratic formula on `b2·s² + b1·s + b0 = 0`.

Approximate (widely separated poles, G2 ≈ gm6 >> G1):

```
p1 ≈ −b0/b1 = −G1·G2 / (G1·C2 + G2·C1 + gm5·Cgd5)      [dominant pole]
p2 ≈ −b1/b2 = −(G1·C2 + G2·C1 + gm5·Cgd5) / (C1·C2 − Cgd5²)  [mirror pole]
```

Further simplification (G2·C1 dominates b1):

```
p1 ≈ −G1 / C1 = −(gds1 + gds5) / (CL + Cdb1 + Cdb5 + Cgd1 + Cgd5)
p2 ≈ −G2 / C2 = −(gm6 + gds6 + gds2) / (Cdb2 + Cdb6 + Cgs5 + Cgs6 + Cgd2 + Cgd5)
```

### DC Gain

```
H(0) = a0 / (2·b0) = gm·(G2 + gm5) / (2·G1·G2)

Since G2 ≈ gm6 and gm5 ≈ gm6:
H(0) ≈ gm·(2·gm6) / (2·G1·gm6) = gm / G1 = gm / (gds1 + gds5)
```

### GBW and Phase Margin

```
GBW = |H(0)| × |p1| / (2π) = gm / (2π·C1)

PM = 180° + ∠H(j·2π·GBW)
```

Compute PM numerically from the full H(s) — this automatically includes
the mirror pole-zero doublet and the Cgd5 feedforward path.

---

## Python Implementation

```python
import numpy as np

def h_5tota(f,
    gm1, gds1, Cgs1, Cgd1, Cdb1, Csb1,
    gm2, gds2, Cgs2, Cgd2, Cdb2, Csb2,
    gm5, gds5, Cgs5, Cgd5, Cdb5,
    gm6, gds6, Cgs6, Cdb6,
    gds3, Cdb3, Cgd3,
    CL):
    """Evaluate H(s) at frequency array f (Hz). Returns complex array."""

    # Grounded caps
    C1g = CL + Cdb1 + Cdb5
    C2g = Cdb2 + Cdb6 + Cgs5 + Cgs6
    C3g = Csb1 + Csb2 + Cdb3 + Cgd3

    s = 1j * 2 * np.pi * np.asarray(f, dtype=float)

    # --- Full 3-node solution (no matched-pair assumption) ---
    H = np.empty_like(s)
    for k, sk in enumerate(s):
        Y = np.array([
            [gds1+gds5 + sk*(C1g+Cgd1+Cgd5),   gm5 - sk*Cgd5,                   -(gm1+gds1)],
            [-sk*Cgd5,                           gds2+gm6+gds6 + sk*(C2g+Cgd2+Cgd5), -(gm2+gds2)],
            [-gds1,                              -gds2,                             gm1+gds1+gm2+gds2+gds3 + sk*(C3g+Cgs1+Cgs2)],
        ])
        # Differential input: vinp = vd/2, vinn = -vd/2
        # RHS per unit vd:
        I = np.array([
            (gm1 - sk*Cgd1) / 2,
            -(gm2 - sk*Cgd2) / 2,
            (-(gm1+sk*Cgs1) + (gm2+sk*Cgs2)) / 2,
        ])
        V = np.linalg.solve(Y, I)
        H[k] = V[0]

    return H


def analyze_5tota(f, **device_params):
    """Compute gain, GBW, PM from full transfer function."""
    H = h_5tota(f, **device_params)

    gain_dB = 20 * np.log10(np.abs(H))
    phase = np.degrees(np.unwrap(np.angle(H)))

    dc_gain_dB = gain_dB[0]

    # 0-dB crossing
    crossings = np.where(np.diff(np.sign(gain_dB)))[0]
    if len(crossings) > 0:
        # Linear interpolation for precision
        i = crossings[0]
        frac = -gain_dB[i] / (gain_dB[i+1] - gain_dB[i])
        gbw = f[i] + frac * (f[i+1] - f[i])
        pm = 180 + (phase[i] + frac * (phase[i+1] - phase[i]))
    else:
        gbw, pm = None, None

    return {"dc_gain_dB": dc_gain_dB, "GBW_Hz": gbw, "PM_deg": pm,
            "gain_dB": gain_dB, "phase_deg": phase}
```

---

## Cascode Load Extension

When the LOAD is `cascode` or `lv_cascode`, add node **V_int**
(M_main drain = M_cas source) and expand to a 4×3 system
(3×3 in differential mode becomes 3×3 with 4 internal nodes minus
tail = 3). The cascode internal pole emerges naturally as a 3rd
eigenvalue of the expanded Y-matrix.
