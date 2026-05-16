# TSM — Small-Signal Transfer Function

## Purpose

Derive the exact open-loop voltage gain H(s) = Vout/Vd for the
Two-Stage Miller compensated OTA from KCL at every node, including
ALL parasitic capacitances and the Rc–Cc compensation network.

---

## Circuit and Nodes

```
         VDD (AC ground)
          |     |              |
        [M1]  [M2]           [M7]       M1/M2: PMOS LOAD, M7: PMOS OUTPUT_CS
          |     |              |
   V3 (net1)  V2 (net5)──Rc──Cc──V1 (vout) ── CL ── GND
          |     |              |
  vinn──[M3]  [M4]──vinp    [M8]       M3/M4: NMOS DIFF_PAIR, M8: NMOS OUTPUT_BIAS
          └──┬──┘              |
          V4 (net2)           GND
             |
           [M6]                          NMOS TAIL (gate = AC gnd, gm6 = 0)
             |
            GND
```

| Device | Type | Gate | Drain | Source | Bulk | Role |
|--------|------|------|-------|--------|------|------|
| M1 | PMOS | V3 | V3 (diode) | GND(ac) | GND(ac) | LOAD (diode ref) |
| M2 | PMOS | V3 | V2 | GND(ac) | GND(ac) | LOAD (mirror) |
| M3 | NMOS | vinn | V3 | V4 | GND | DIFF_PAIR |
| M4 | NMOS | vinp | V2 | V4 | GND | DIFF_PAIR |
| M6 | NMOS | GND | V4 | GND | GND | TAIL (gm6=0) |
| M7 | PMOS | V2 | V1 | GND(ac) | GND(ac) | OUTPUT_CS |
| M8 | NMOS | GND | V1 | GND | GND | OUTPUT_BIAS (gm8=0) |

M5 (BIAS_GEN, diode at net3) sets the gate bias for M6 and M8. Net3 is
approximately AC ground through M5's diode impedance 1/gm5.
Therefore M6 and M8 have vgs ≈ 0 and contribute only gds (no gm).
M1 is diode-connected (gate = drain = V3).

---

## Capacitance Inventory

### Grounded capacitances

```
C1g = CL + Cdb7 + Cdb8 + Cgd8           (at V1: load + M7/M8 drain-bulk + M8 gate-drain to gnd)
C2g = Cdb2 + Cdb4 + Cgs7                (at V2: M2/M4 drain-bulk + M7 gate-source to gnd)
C3g = Cdb1 + Cdb3 + Cgs1 + Cgs2         (at V3: M1/M3 drain-bulk + M1/M2 gate-source to gnd)
C4g = Csb3 + Csb4 + Cdb6 + Cgd6         (at V4: M3/M4 source-bulk + M6 drain-bulk + gate-drain to gnd)
```

### Coupling capacitances

```
Between V1 and V2:  Cgd7                 (M7 gate-drain — in parallel with Rc+Cc)
Between V2 and V3:  Cgd2                 (M2 gate-drain)
Between V2 and vinp: Cgd4               (M4 gate-drain)
Between V3 and vinn: Cgd3               (M3 gate-drain)
Between V3 and V4:  (via gds3 only, no direct cap)
Between V2 and V4:  (via gds4 only, no direct cap)
```

### Compensation network

Rc in series with Cc, connecting V2 to V1:

```
Y_cc(s) = s·Cc / (1 + s·Rc·Cc)          (admittance of series Rc–Cc)
```

Note: Cgd1 has both terminals at V3 (M1 diode) → shorted, ignored.
Cgd6 has gate at gnd, drain at V4 → grounded cap at V4.
Cgd8 has gate at gnd, drain at V1 → grounded cap at V1.

---

## Differential-Mode Reduction

With matched diff pair (M3 = M4) and differential input vinp = +vd/2,
vinn = −vd/2: the tail node V4 = 0 (AC ground).

The system reduces to **3 nodes**: V1 (vout), V2 (net5), V3 (net1).

---

## KCL Equations (V4 = 0)

### Node V1 (vout)

Currents leaving V1:
- M7 drain: id7 = gm7·V2 + gds7·V1
- M8 drain: id8 = gds8·V1
- Grounded caps: s·C1g·V1
- Cgd7 to V2: s·Cgd7·(V1 − V2)
- Rc+Cc to V2: Y_cc·(V1 − V2)

```
V1·[gds7 + gds8 + s·C1g + s·Cgd7 + Y_cc]
+ V2·[gm7 − s·Cgd7 − Y_cc]
+ V3·[0]
= 0                                                     ... (1)
```

### Node V2 (net5, 1st-stage output)

Currents leaving V2:
- M2 drain: id2 = gm2·V3 + gds2·V2
- M4 drain: id4 = gm4·vinp + gds4·V2
- Grounded caps: s·C2g·V2
- Cgd2 to V3: s·Cgd2·(V2 − V3)
- Cgd4 to vinp: s·Cgd4·(V2 − vinp)
- Cgd7 to V1: s·Cgd7·(V2 − V1)
- Rc+Cc to V1: Y_cc·(V2 − V1)

```
V1·[−s·Cgd7 − Y_cc]
+ V2·[gds2 + gds4 + s·(C2g + Cgd2 + Cgd4 + Cgd7) + Y_cc]
+ V3·[gm2 − s·Cgd2]
= −(gm4 − s·Cgd4)·vinp                                 ... (2)
```

### Node V3 (net1, mirror node)

Currents leaving V3:
- M1 drain (diode): id1 = (gm1 + gds1)·V3
- M3 drain: id3 = gm3·vinn + gds3·V3
- Grounded caps: s·C3g·V3
- Cgd2 to V2: s·Cgd2·(V3 − V2)
- Cgd3 to vinn: s·Cgd3·(V3 − vinn)

```
V1·[0]
+ V2·[−s·Cgd2]
+ V3·[gm1 + gds1 + gds3 + s·(C3g + Cgd2 + Cgd3)]
= −(gm3 − s·Cgd3)·vinn                                 ... (3)
```

---

## Matrix Form

### Differential input: vinp = +vd/2, vinn = −vd/2

With matched M3 = M4 (gm3 = gm4 ≡ gm_dp, Cgd3 = Cgd4 ≡ Cgd_dp):

```
Y · [V1, V2, V3]ᵀ = (gm_dp − s·Cgd_dp)·(vd/2) · [0, −1, +1]ᵀ
```

### Y-matrix elements

Define Y_cc = s·Cc / (1 + s·Rc·Cc).

```
Y11 = gds7 + gds8 + s·(C1g + Cgd7) + Y_cc
Y12 = gm7 − s·Cgd7 − Y_cc
Y13 = 0

Y21 = −s·Cgd7 − Y_cc
Y22 = gds2 + gds4 + s·(C2g + Cgd2 + Cgd4 + Cgd7) + Y_cc
Y23 = gm2 − s·Cgd2

Y31 = 0
Y32 = −s·Cgd2
Y33 = gm1 + gds1 + gds3 + s·(C3g + Cgd2 + Cgd3)
```

---

## Transfer Function H(s) = V1 / vd

By Cramer's rule: `V1 = det(Y₁) / det(Y)` where Y₁ replaces column 1
of Y with the source vector.

### Denominator D(s)

```
D(s) = det(Y) = Y11·(Y22·Y33 − Y23·Y32) − Y12·(Y21·Y33 − Y23·Y31) + Y13·(...)

Since Y13 = 0 and Y31 = 0:

D(s) = Y11·(Y22·Y33 − Y23·Y32) − Y12·Y21·Y33
```

Substituting and multiplying through by (1 + s·Rc·Cc) to clear Y_cc:

D(s) is a **4th-order polynomial** in s (3 nodes + 1 from Cc). This
gives **4 poles**.

### Numerator N(s)

```
N(s) = B · [−1·(Y21·Y33 − Y23·0) − (−1)·(Y11·Y33 − Y13·0) + ... ]

where B = (gm_dp − s·Cgd_dp) / 2.

Simplifying (Y13 = Y31 = 0):
N(s) = B · [−Y21·Y33 + Y11·Y33 + Y23·0 − ...]
     = B · Y33 · (Y11 − Y21)    (after expansion)
     ... (not this simple — need full cofactor expansion)
```

The numerator is best computed numerically. After clearing
(1 + s·Rc·Cc), N(s) is a **3rd-order polynomial** → up to **3 zeros**.

### Key Poles and Zeros (approximate locations)

**Poles:**

| Pole | Approximate location | Physical origin |
|------|---------------------|-----------------|
| p1 | `(gds1·gds7) / (gm7·Cc)` | Dominant pole — Miller-multiplied Cc at output |
| p2 | `gm7 / CTL` | Output pole (cancelled by Rc zero in compensated design) |
| p3 | `gm1 / C_net1` | Mirror pole at net1 |
| p4 | `gm7 / C_net5` | Compensation pole at net5 (from Rc–C1 interaction) |

where:
```
CTL    = CL + Cdb7 + Cdb8 + Cgd7 + Cgd8       (total output cap)
C_net1 = Cdb1 + Cdb3 + Cgs1 + Cgs2 + Cgd2 + Cgd3  (total cap at mirror node)
C_net5 = Cdb2 + Cdb4 + Cgs7 + Cgd2 + Cgd4 + Cgd7   (total cap at 1st-stage output)
```

**Zeros:**

| Zero | Approximate location | Physical origin |
|------|---------------------|-----------------|
| z_RHP | `gm7/Cc − 1/(Rc·Cc)` | Cc feedforward; becomes LHP when Rc > 1/gm7 |
| z_LHP | Placed at p2 when `Rc = (1/gm7)·(Cc+C1)(Cc+CTL)/Cc²` | Rc nulling — cancels output pole |
| z_mirror | `≈ 2·p3` | Mirror pole-zero doublet (same as 5T OTA) |

When Rc is chosen to cancel p2, the effective loop gain has:
```
PM ≈ 90° − arctan(ω_c/p3) − arctan(ω_c/p4)
```
plus any cascode internal pole penalties.

---

## Python Implementation

```python
import numpy as np

def h_tsm(f,
    gm1, gds1, Cgs1, Cgd1_ignored, Cdb1,           # M1 LOAD (diode, Cgd1 shorted)
    gm2, gds2, Cgs2, Cgd2, Cdb2,                    # M2 LOAD mirror
    gm3, gds3, Cgs3_ignored, Cgd3, Cdb3, Csb3,      # M3 DIFF_PAIR
    gm4, gds4, Cgs4_ignored, Cgd4, Cdb4, Csb4,      # M4 DIFF_PAIR
    gds6, Cdb6, Cgd6,                                # M6 TAIL (gm6=0)
    gm7, gds7, Cgs7, Cgd7, Cdb7,                    # M7 OUTPUT_CS
    gds8, Cgd8, Cdb8,                                # M8 OUTPUT_BIAS (gm8=0)
    CL, Cc, Rc):
    """Evaluate H(s) at frequency array f (Hz). Returns complex array."""

    # Grounded caps
    C1g = CL + Cdb7 + Cdb8 + Cgd8
    C2g = Cdb2 + Cdb4 + Cgs7
    C3g = Cdb1 + Cdb3 + Cgs1 + Cgs2

    s = 1j * 2 * np.pi * np.asarray(f, dtype=float)

    H = np.empty_like(s)
    for k, sk in enumerate(s):
        Y_cc = sk * Cc / (1 + sk * Rc * Cc)

        Y = np.array([
            [gds7+gds8 + sk*(C1g+Cgd7) + Y_cc,
             gm7 - sk*Cgd7 - Y_cc,
             0],
            [-sk*Cgd7 - Y_cc,
             gds2+gds4 + sk*(C2g+Cgd2+Cgd4+Cgd7) + Y_cc,
             gm2 - sk*Cgd2],
            [0,
             -sk*Cgd2,
             gm1+gds1+gds3 + sk*(C3g+Cgd2+Cgd3)],
        ])

        # Differential input (matched M3=M4):
        # I = (gm_dp - s·Cgd_dp)·(vd/2) · [0, -1, +1]
        gm_dp = (gm3 + gm4) / 2
        Cgd_dp = (Cgd3 + Cgd4) / 2
        B = (gm_dp - sk * Cgd_dp) / 2
        I_vec = B * np.array([0, -1, +1])

        V = np.linalg.solve(Y, I_vec)
        H[k] = V[0]

    return H


def analyze_tsm(f, **device_params):
    """Compute gain, GBW, PM from full transfer function."""
    H = h_tsm(f, **device_params)

    gain_dB = 20 * np.log10(np.abs(H))
    phase = np.degrees(np.unwrap(np.angle(H)))

    dc_gain_dB = gain_dB[0]

    # 0-dB crossing
    crossings = np.where(np.diff(np.sign(gain_dB)))[0]
    if len(crossings) > 0:
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

## Verification

After sizing, the agent should:

1. Query all parasitic caps from LUT (or from SPICE OP data)
2. Build H(s) using the functions above
3. Compare the analytical Bode plot against SPICE AC simulation
4. Extract DC gain, GBW, PM — these should closely match SPICE

The residual error vs SPICE comes from:
- NQS (non-quasi-static) effects in long-channel devices
- Voltage-dependent junction caps (linearized at OP in our model)
- Distributed gate resistance (not modeled)
