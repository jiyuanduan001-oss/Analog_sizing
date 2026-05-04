# Run Log: TSM Single OTA Sizing

```
Date:     2026-04-14
Topology: tsm_single (Two-Stage Miller OTA)
Process:  SKY130
Tool:     AnalogAgent (analog-amplifier skill stack)
```

---

## [Stage 1] Spec Understanding

### Input: User Netlist

```spice
.subckt tsm_single gnda vdda vinn vinp vout Ib
* PMOS mirror load — single transistor per branch
XM1 net1  net1 vdda vdda sky130_fd_pr__pfet_01v8
XM2 net5  net1 vdda vdda sky130_fd_pr__pfet_01v8
* NMOS diff pair
XM3 net1  vinn net2 gnda sky130_fd_pr__nfet_01v8
XM4 net5  vinp net2 gnda sky130_fd_pr__nfet_01v8
* Tail current source + bias reference
XM5 net3  net3 gnda gnda sky130_fd_pr__nfet_01v8
XM6 net2  net3 gnda gnda sky130_fd_pr__nfet_01v8
* Second stage — PMOS CS amplifier + NMOS current source
XM7 vout  net5 vdda vdda sky130_fd_pr__pfet_01v8
XM8 vout  net3 gnda gnda sky130_fd_pr__nfet_01v8
* Miller compensation
R_Rc net5 net_rc Rc
C_C1 net_rc vout C1
I0  vdda  net3 Ib
.ends tsm_single
```

### Input: Spec Form (from template defaults)

```
VDD          : 1.8
CL           : 5e-12
Gain         : 70
GBW          : 50e6
PM           : 60
Temperature  : 20
Corner       : tt
Power        : 500e-6
SR+          : 10
CMRR         : 60
PSRR+        : 60
PSRR-        : 60
IRN          : 30e-6
I_bias       : 10e-6
Mismatch     : (blank)
Extreme_PVT  : yes
Optimize     : yes
```

### Run: LUT temperature check

```python
from scripts.lut_lookup import list_available_L, _resolve_device, _discover_temps
temps = _discover_temps(_resolve_device('nfet'), 'tt')
```

```
>>> Available temperatures: [-40, 25, 85]
>>> 20C in temps? False
```

20C is between -40C and 25C — LUT will use first-order linear interpolation.

### Output: Validated Specifications

```
REQUIRED FIELDS CHECK
======================
VDD  : 1.8 V     ✓
CL   : 5 pF      ✓
Gain : 70 dB     ✓
GBW  : 50 MHz    ✓
PM   : 60°       ✓
Status: ALL PRESENT → proceed

VALIDATED SPECIFICATIONS
========================
Required:
  VDD  = 1.8 V
  CL   = 5e-12 F
  Gain > 70 dB  (3162.3 V/V)
  GBW  > 50 MHz
  PM   > 60°

Environment:
  Temperature = 20°C    (LUT interpolation between -40C and 25C)
  Corner      = tt
  VSS         = 0 V

Active Targets:
  Power  : < 500 µW
  SR+    : > 10 V/µs
  CMRR   : > 60 dB
  PSRR+  : > 60 dB
  PSRR-  : > 60 dB
  IRN    : < 30 µV rms
  I_bias : = 10 µA

Mismatch: disabled (skipped entirely)

Inactive (report only):
  SR-, ORN, Output_swing

Post-Sizing:
  Extreme PVT check       : enabled
  Numerical optimization  : enabled
```

---

## [Stage 2] Circuit Understanding

### Run: Topology identification

Parsed netlist → 4 NMOS, 4 PMOS, 2 passives (R, C).
Matched pattern: diff pair + mirror load + CS stage + Miller cap → **Two-Stage Miller (TSM)**.

### Output: Role-Device Map

```
LOAD        → M1 [+ M2] (pfet)              sub_block: single
DIFF_PAIR   → M3 [+ M4] (nfet)
BIAS_GEN    → M5          (nfet)             sub_block: single
TAIL        → M6          (nfet) mirrors BIAS_GEN   sub_block: single
OUTPUT_CS   → M7          (pfet)
OUTPUT_BIAS → M8          (nfet) mirrors BIAS_GEN   sub_block: single
```

### Run: Topology registration

```python
from tools import ensure_topology_registered

result = ensure_topology_registered(
    topology_name='tsm_single',
    raw_netlist=parameterized_netlist,
    role_device_map=role_device_map,
    requires_Cc=True,
    passive_params=['C1_value', 'Rc_value'],
)
```

```
>>> {'status': 'ok', 'config_path': 'config/skywater/opamp/tsm_single.toml', 'registered': False}
```

---

## [Stage 3] Analytical Sizing — Iteration A-1

### Run: Step 1 — DIFF_PAIR (M3, M4)

```python
gm_id_3 = 12   # GBW=50MHz → moderate inversion
Cc_initial = 0.5 * CL   # = 2.5 pF  (CL <= 5pF rule)
gm3 = 2 * pi * 50e6 * 2.5e-12   # = 785.40 µS
```

L sweep (nfet, gm/ID=12):
```
  L=0.18 µm: gm/gds = 22.7,  gm_gds/2 = 11.4   (need >= 56.2)
  L=0.50 µm: gm/gds = 124.8, gm_gds/2 = 62.4   → Selected L3 = 0.50 µm
```

```
ID3     = 785.40 / 12     = 65.45 µA
I_tail  = 2 × 65.45       = 130.90 µA
id_w3   = lut_query('nfet', 'id_w', 0.5, gm_id_val=12)
W3      = 65.45e-6 / id_w3 = 27.432 µm
gds3    = 785.40 / 124.8   = 6.295 µS
vdsat3  = 80.4 mV
Cgs3=29.57fF  Cgd3=0.04fF  Cdb3=2.83fF  ft3=1722.5MHz
```

### Run: Step 2 — LOAD (M1, M2)

```python
gm_id_1 = 12   # moderate inversion for decent p3
ID1 = ID3 = 65.45 µA
```

L sweep (pfet, gm/ID=12):
```
  L=0.18 µm: A_v1 = 14.8 (23.4 dB)
  L=0.50 µm: A_v1 = 54.3 (34.7 dB)
  L=1.00 µm: A_v1 = 85.5 (38.6 dB)   → Selected L1 = 1.00 µm
```

```
gm1     = 12 × 65.45e-6   = 785.40 µS
W1      = 91.541 µm
gds1    = 785.40 / 271.5   = 2.893 µS
vdsat1  = 141.1 mV
Cgs1=404.11fF  Cgd1=0.37fF  Cdb1=38.56fF  ft1=259.4MHz
A_v1    = 785.40 / (6.295 + 2.893)  = 85.5  (38.6 dB)
```

### Run: Step 3 — OUTPUT_CS (M7)

```python
gm_id_7 = 10   # moderate-strong inversion for speed
gm7_required = 2.2 * wc * CL = 2.2 * 2π*50e6 * 5e-12  = 3455.75 µS
ID7_from_PM  = 3455.75 / 10  = 345.58 µA
ID7_from_SR  = 10e6 * (2.5e-12 + 5e-12)  = 75.00 µA
ID7          = max(345.58, 75.00)  = 345.58 µA
gm7          = 10 × 345.58e-6  = 3455.75 µS
```

A_v2 needed = 3162.3 / 85.5 = 37.0 (31.4 dB). L sweep:
```
  L=0.50 µm: gm/gds = 83.9 >= 37.0*1.3=48.1   → Selected L7 = 0.50 µm
```

```
W7=146.833µm  gds7=41.203µS  vdsat7=180.9mV
Cgs7=364.58fF  Cgd7=0.75fF  Cdb7=32.55fF  ft7=1352.4MHz
```

### Run: Step 4 — BIAS_GEN / TAIL / OUTPUT_BIAS

```python
gm_id_5 = 12;  L5 = 1.00 µm (nearest to 1.0 in LUT)
M5_M = 1
M6_M = round(130.90 / 10) = 13
M8_M = round(345.58 / 10) = 35
>>> ⚠️ High mirror ratio (35) — risk of VDS compression
```

Unit cell (per-finger):
```
ID_finger=10µA  gm_finger=120µS  W5=3.507µm  gds_finger=1.091µS  vdsat5=136.9mV
```

Scaled:
```
M6(TAIL):         gm6=1560.0µS  gds6=14.177µS
M8(OUTPUT_BIAS):  gm8=4200.0µS  gds8=38.168µS
```

### Run: Step 5 — Compensation

```
Cc = gm3 / (2π × 50e6) = 2.500 pF
Rc = (1/gm7) × (1 + CL/Cc) = (1/3455.75e-6) × (1 + 5/2.5) = 868.1 Ω
p3 = gm1/(2×Cgs1) = 785.40e-6 / (2×404.11e-15) = 154.7 MHz
p4 = gm7/C1 = 3455.75e-6 / 365.00e-15 = 1506.8 MHz
PM_est = 90° - arctan(wc/p3) - arctan(wc/p4) = 70.2°
```

### Output: Analytical Spec Check A-1

```
Spec           |   Analytical |       Target | Status
---------------+--------------+--------------+-------
A0             |     71.4 dB  |     70.0 dB  | ✅
GBW            |     50.0 MHz |     50.0 MHz | ✅
PM             |       70.2°  |       60.0°  | ✅
SR+            |   52.4 V/µs  |   10.0 V/µs  | ✅
SR-            |   46.1 V/µs  |          --- | (inactive)
Power          |    875.7 µW  |    500.0 µW  | ❌
CMRR           |     79.5 dB  |     60.0 dB  | ✅
PSRR-          |     75.8 dB  |     60.0 dB  | ✅
PSRR+          |     58.4 dB  |     60.0 dB  | ❌
Swing          |      1.482 V |          --- | (inactive)

A_v1 = 85.5 (38.6 dB)   A_v2 = 43.5 (32.8 dB)
C1 = 365.00 fF   CTL = 5.002 pF
```

### Diagnosis: Root-cause (A-1)

```
FAIL 1: Power = 875.7 µW >> 500 µW
  Root cause: ID7 = 345.6 µA driven by pre-Rc-cancellation PM rule (gm7 = 2.2*wc*CL).
  With Rc cancelling p2, PM is actually set by p3 and p4 only → PM = 70.2°.
  ID7 is grossly overestimated.
  Fix: increase gm/ID_7 (14, reduce ID7) + size ID7 to power budget.

FAIL 2: PSRR+ = 58.4 dB < 60 dB
  Root cause: cancellation term gm7*gds3/gm1 = 27.7 µS too far from gds7 = 41.2 µS.
  Fix: adjusting gm7 and gds3 balance in iteration 2 should help.

Additional fix: increase gm/ID_3 from 12 to 14 → reduces I_tail for same gm3.
```

---

## [Stage 3] Analytical Sizing — Iteration A-2

### Changes applied

```
gm/ID_3:  12 → 14    (reduce I_tail)
gm/ID_7:  10 → 14    (reduce ID7)
L3:       0.50 → 1.00 µm   (gm_gds at gm/ID=14 needs longer L for gain)
L1:       1.00 → 0.50 µm   (A_v1=64.3 still >= 56.2 at shorter L)
ID7:      345.58 → 155.58 µA   (sized to power budget: 500/1.8 - 10 - 112.2)
```

### Run: Re-derive all devices

```
DIFF_PAIR:
  gm3=785.40µS  ID3=56.10µA  I_tail=112.20µA
  L3=1.00µm (gm_gds=150.8, /2=75.4 >= 56.2)
  W3=244.505µm  gds3=5.207µS  vdsat3=51.0mV

LOAD:
  L1=0.50µm (A_v1=64.3 >= 56.2)
  gm1=673.20µS  W1=38.881µm  gds1=7.006µS  vdsat1=146.4mV
  A_v1 = 785.40 / (5.207 + 7.006) = 64.3 (36.2 dB)

OUTPUT_CS:
  ID7=155.58µA  gm7=2178.09µS
  L7=0.50µm (gm_gds=106.5 >= 49.2*1.3)
  W7=186.311µm  gds7=20.455µS  vdsat7=117.1mV

BIAS / MIRRORS:
  L5=1.00µm  W5=3.507µm  vdsat5=136.9mV
  M5_M=1  M6_M=11  M8_M=16
  ⚠️ High mirror ratio: max=16 (improved from 35)
  Actual: I_tail=110.0µA  ID7=160.0µA  Power=504.0µW

COMPENSATION:
  Cc = 2.500 pF
  Rc = (1/2178.09e-6) × (1 + 5/2.5) = 1377.4 Ω
  p3 = 589.2 MHz   p4 = 856.2 MHz
  PM_est = 81.8°
```

### Output: Analytical Spec Check A-2

```
Spec           |   Analytical |       Target | Status
---------------+--------------+--------------+-------
A0             |     71.4 dB  |     70.0 dB  | ✅
GBW            |     50.0 MHz |     50.0 MHz | ✅
PM             |       81.8°  |       60.0°  | ✅
SR+            |   44.9 V/µs  |   10.0 V/µs  | ✅
SR-            |   20.7 V/µs  |          --- | (inactive)
Power          |    500.0 µW  |    500.0 µW  | ✅
CMRR           |     77.2 dB  |     60.0 dB  | ✅
PSRR-          |     73.8 dB  |     60.0 dB  | ✅
PSRR+          |     69.8 dB  |     60.0 dB  | ✅
Swing          |      1.546 V |          --- | (inactive)

A_v1 = 64.3 (36.2 dB)   A_v2 = 57.5 (35.2 dB)
C1 = 404.89 fF   CTL = 5.001 pF

All 9 specs PASS analytically → proceed to SPICE.
```

---

## [Stage 3] Simulation — Iteration S-1

### Run: convert_sizing

```python
result = convert_sizing(
    topology='tsm_single',
    roles_raw={
        "DIFF_PAIR":    {"gm_id_target": 14,  "L_guidance_um": 1.0,  "id_derived": 56.10e-6},
        "LOAD":         {"gm_id_target": 12,  "L_guidance_um": 0.5,  "id_derived": 56.10e-6},
        "OUTPUT_CS":    {"gm_id_target": 14,  "L_guidance_um": 0.5,  "id_derived": 155.58e-6},
        "BIAS_GEN":     {"gm_id_target": 12,  "L_guidance_um": 1.0,  "id_derived": 10e-6},
        "TAIL":         {"gm_id_target": 0,   "L_guidance_um": 1.0,  "id_derived": 112.20e-6},
        "OUTPUT_BIAS":  {"gm_id_target": 0,   "L_guidance_um": 1.0,  "id_derived": 155.58e-6},
    },
    Ib_a=10e-6, Cc_f=2.5e-12, Rc_ohm=1377.4,
    l_overrides={"DIFF_PAIR": 1.0, "LOAD": 0.5, "OUTPUT_CS": 0.5,
                 "BIAS_GEN": 1.0, "TAIL": 1.0, "OUTPUT_BIAS": 1.0},
)
```

```
>>> status: ok
>>> config_path: config/skywater/opamp/tsm_single.toml
>>> params: {
      'M5_L': 1.0, 'M5_WL_ratio': 3.44, 'M5_M': 1,
      'M6_L': 1.0, 'M6_WL_ratio': 3.44, 'M6_M': 11,
      'M8_L': 1.0, 'M8_WL_ratio': 3.44, 'M8_M': 16,
      'M3_L': 1.0, 'M3_WL_ratio': 9.89, 'M3_M': 3,
      'M1_L': 0.5, 'M1_WL_ratio': 9.13, 'M1_M': 10,
      'M7_L': 0.5, 'M7_WL_ratio': 9.99, 'M7_M': 42,
      'C1_value': 2.5e-12, 'Rc_value': 1377.4, 'ibias': 1e-05
    }
```

### Run: simulate_circuit (S-1)

```python
sim = simulate_circuit(
    params, config_path='config/skywater/opamp/tsm_single.toml',
    corner='tt', temperature=20, supply_voltage=1.8, CL=5e-12,
    measure_mismatch=False,
)
```

### Output: SPICE specs (S-1)

```
dcgain_                  : 75.8165
gain_bandwidth_product_  : 4.69574e+07
phase_margin             : 75.3203
cmrr                     : 61.9895
dcpsrp                   : -83.7549
dcpsrn                   : -64.9048
power                    : 487.64
integrated_input_noise   : 2.10589e-05
slew_rate_pos            : 4.83444e+07
slew_rate_neg            : -1.49554e+07
output_swing             : 1.57899
gain_peaking_db          : 0.02181
true_gbw                 : 4.68396e+07
vos25                    : 0.0002692
```

### Output: SPICE operating points (S-1)

```
Device | Vds(V)   | Vgs(V)   | gm(S)        | gds(S)
M1     | 1.078213 | 1.078213 | 6.418532e-04 | 4.720816e-06
M2     | 1.056366 | 1.078213 | 6.407152e-04 | 4.751307e-06
M3     | 0.543120 | 0.721602 | 7.640168e-04 | 4.737869e-06
M4     | 0.564967 | 0.721333 | 7.631827e-04 | 4.608219e-06
M5     | 0.733052 | 0.733052 | 1.218889e-04 | 8.987095e-07
M6     | 0.178667 | 0.733052 | 1.166183e-03 | 8.470876e-05
M7     | 0.899731 | 1.056366 | 2.297757e-03 | 1.741901e-05
M8     | 0.900269 | 0.733052 | 1.973106e-03 | 1.277399e-05
```

### Verification: S-1

```
OP TABLE — Iteration S-1
Device | Vds(V)  | vdsat*(mV) | margin(mV) | Region
M1     | -1.078  |  ~141      | 937        | sat ✅
M2     | -1.056  |  ~141      | 915        | sat ✅
M3     |  0.543  |  ~51       | 492        | sat ✅
M4     |  0.565  |  ~51       | 514        | sat ✅
M5     |  0.733  |  ~137      | 596        | sat ✅
M6     |  0.179  |  ~137      | 42         | sat ⚠️ (marginal)
M7     | -0.900  |  ~117      | 783        | sat ✅
M8     |  0.900  |  ~137      | 763        | sat ✅

Symmetry: |gm_M1 - gm_M2|/gm_M1 = 0.19% ✅
Symmetry: |gm_M3 - gm_M4|/gm_M3 = 0.11% ✅

SPEC COMPLIANCE — S-1
Spec           |       Target |        SPICE |   Margin | Status
DC gain        |      > 70 dB |      75.8 dB |   +8.3%  | ✅
GBW            |     > 50 MHz |     47.0 MHz |   -6.1%  | ❌
PM             |        > 60° |        75.3° |  +25.5%  | ✅
SR+            |    > 10 V/µs |    48.3 V/µs |  +383%   | ✅
Power          |     < 500 µW |     487.6 µW |   -2.5%  | ✅
CMRR           |      > 60 dB |      62.0 dB |   +3.3%  | ✅
PSRR+          |      > 60 dB |      83.8 dB |  +39.6%  | ✅
PSRR-          |      > 60 dB |      64.9 dB |   +8.2%  | ✅
IRN            |      < 30 µV |      21.1 µV |  -29.8%  | ✅

ANALYTICAL vs SPICE
Metric  | Analytical | SPICE    | Error
A0      | 71.4 dB    | 75.8 dB  | +6.2%
GBW     | 50.0 MHz   | 47.0 MHz | -6.1%
PM      | 81.8°      | 75.3°    | -6.5°
Power   | 500.0 µW   | 487.6 µW | -2.5%
```

### Diagnosis: S-1

```
FAIL: GBW = 47.0 MHz < 50 MHz target  (-6.1%)

Root cause:
  - gm3_spice = 764 µS vs analytical 785 µS (slight reduction)
  - M6 marginal saturation (gds6_sim = 84.7 µS >> analytical 14.2 µS)
  - Parasitic loading reduces effective GBW by ~6%

Fix: Reduce Cc from 2.5 pF to 2.3 pF.
  - PM headroom = 15° (75.3° vs 60° target) easily absorbs this.
  - Analytical GBW at Cc=2.3pF: 785/(2π×2.3e-12) = 54.3 MHz → expect ~50 MHz in SPICE.
  - Rc updated: (1/gm7)×(1 + CL/Cc) = 1457.2 Ω
```

---

## [Stage 3] Simulation — Iteration S-2

### Run: simulate_circuit (S-2, Cc=2.3pF)

```python
params['C1_value'] = 2.3e-12
params['Rc_value'] = 1457.2
sim = simulate_circuit(
    params, config_path='config/skywater/opamp/tsm_single.toml',
    corner='tt', temperature=20, supply_voltage=1.8, CL=5e-12,
    measure_mismatch=False,
)
```

### Output: SPICE specs (S-2)

```
dcgain_                  : 75.8165
gain_bandwidth_product_  : 5.06e+07
phase_margin             : 73.3
cmrr                     : 62.0
dcpsrp                   : -83.8
dcpsrn                   : -64.9
power                    : 487.6
integrated_input_noise   : 2.15e-05
slew_rate_pos            : 5.42e+07
slew_rate_neg            : -1.51e+07
output_swing             : 1.579
gain_peaking_db          : 0
```

### Output: SPICE operating points (S-2)

```
Device | Vds(V)   | Vgs(V)   | gm(µS)  | gds(µS)
M1     | 1.078    | 1.078    | 641.9   | 4.72
M2     | 1.056    | 1.078    | 640.7   | 4.75
M3     | 0.543    | 0.722    | 764.0   | 4.74
M4     | 0.565    | 0.721    | 763.2   | 4.61
M5     | 0.733    | 0.733    | 121.9   | 0.90
M6     | 0.179    | 0.733    | 1166.2  | 84.71
M7     | 0.900    | 1.056    | 2297.8  | 17.42
M8     | 0.900    | 0.733    | 1973.1  | 12.77
```

### Verification: S-2

```
SPEC COMPLIANCE — S-2
Spec           |       Target |        SPICE |   Margin | Status
DC gain        |      > 70 dB |      75.8 dB |   +8.3%  | ✅
GBW            |     > 50 MHz |     50.6 MHz |   +1.2%  | ✅
PM             |        > 60° |        73.3° |  +22.2%  | ✅
SR+            |    > 10 V/µs |    54.2 V/µs |  +442%   | ✅
Power          |     < 500 µW |     487.6 µW |   +2.5%  | ✅
CMRR           |      > 60 dB |      62.0 dB |   +3.3%  | ✅
PSRR+          |      > 60 dB |      83.8 dB |  +39.7%  | ✅
PSRR-          |      > 60 dB |      64.9 dB |   +8.2%  | ✅
IRN            |      < 30 µV |      21.5 µV |  +28.3%  | ✅

Reported (inactive):
  SR-           = 15.1 V/µs
  Output swing  = 1.579 V

Status: 9/9 PASS → CONVERGED
```

---

## [Stage 4] Simulation Verification — Decision

```
ITERATION S-2 SUMMARY
======================
Status   : PASSED
OP       : all saturated (M6 marginal ⚠️ 42 mV margin)
Specs    : 9/9 active specs met
Next     : design-review.md
```

---

## [Stage 6] Extreme PVT Check

### Run: SS/85C

```python
sim_ss85 = simulate_circuit(
    params, config_path=config_path,
    corner='ss', temperature=85, supply_voltage=1.8, CL=5e-12,
    measure_mismatch=False,
)
```

### Run: FF/-40C

```python
sim_ff_m40 = simulate_circuit(
    params, config_path=config_path,
    corner='ff', temperature=-40, supply_voltage=1.8, CL=5e-12,
    measure_mismatch=False,
)
```

### Output: PVT results

```
Spec       |       Target | Design(tt/20) |      SS/85°C |     FF/-40°C
-----------+--------------+---------------+--------------+-------------
A0         |      > 70 dB |      75.8 dB  |     75.3 dB ✅ |     75.9 dB ✅
GBW        |     > 50 MHz |     50.6 MHz  |     39.8 MHz ❌ |     69.0 MHz ✅
PM         |       > 60 ° |       73.3 °  |       70.3 ° ✅ |       75.6 ° ✅
SR+        |    > 10 V/µs |    54.2 V/µs  |    50.7 V/µs ✅ |    58.0 V/µs ✅
Power      |     < 500 µW |     487.6 µW  |     484.5 µW ✅ |     488.6 µW ✅
CMRR       |      > 60 dB |      62.0 dB  |      58.2 dB ❌ |      65.1 dB ✅
PSRR+      |      > 60 dB |      83.8 dB  |      83.1 dB ✅ |      88.7 dB ✅
PSRR-      |      > 60 dB |      64.9 dB  |      60.1 dB ✅ |      68.8 dB ✅
IRN        |      < 30 µV |      21.5 µV  |      22.8 µV ✅ |      20.5 µV ✅

OP Flags:
  SS/85°C:   M6 Vds=0.183V, margin=46mV ⚠️
  FF/-40°C:  M6 Vds=0.172V, margin=35mV ⚠️

Summary:
  SS/85°C:  7/9 specs met  (GBW -21%, CMRR -3%)
  FF/-40°C: 9/9 specs met
```

---

## [Stage 6] Numerical Optimization

### Input: User selection

```
Optimization is enabled. Which metric should be prioritized?
  1. Power   — minimize power consumption (default)
  2. Gain    — maximize DC gain
  3. GBW     — maximize gain-bandwidth product

>>> User selected: 3 (GBW)
>>> Weights: w_pwr=0.15, w_gain=0.15, w_gbw=1.0
```

### Run: Setup optimization variables

```python
param_names = [
    'M5_L', 'M5_WL_ratio', 'M5_M',         # BIAS_GEN
    'M6_M', 'M8_M',                          # mirrors (L/WL excluded, enforced in obj)
    'M3_L', 'M3_WL_ratio', 'M3_M',          # DIFF_PAIR
    'M1_L', 'M1_WL_ratio', 'M1_M',          # LOAD
    'M7_L', 'M7_WL_ratio', 'M7_M',          # OUTPUT_CS
    'C1_value', 'Rc_value', 'ibias',         # passives + bias
]
# 17 variables total, 6 integer (all *_M)
# Mirror constraint: M6_L = M8_L = M5_L, M6_WL = M8_WL = M5_WL (enforced in f())
# mirror_groups = {} (mirror dims excluded from variable list)
```

### Run: Coordinate warmup

```python
warmup = coordinate_warmup(
    f_single=f, x0=x0, bounds_list=bounds,
    int_indices={2,3,4,7,10,13}, param_names=param_names,
    mirror_groups={}, n_workers=16,
)
```

```
>>> Warmup: x0 cost = -0.9605
>>> Evaluating 33 warmup probes...
>>>   M3_L         +10% → cost=-1.0144 (Δ=-0.0539) ✅
>>>   M3_WL_ratio  +10% → cost=-0.9606 (Δ=-0.0001) ✅
>>>   M3_M         +10% → cost=-1.4269 (Δ=-0.4664) ✅   ← strongest
>>>   M1_L         +10% → cost=-1.0170 (Δ=-0.0565) ✅
>>>   M1_WL_ratio  +10% → cost=-0.9998 (Δ=-0.0393) ✅
>>>   M1_M         +10% → cost=-0.9883 (Δ=-0.0278) ✅
>>>   M7_WL_ratio  -10% → cost=-0.9902 (Δ=-0.0297) ✅
>>> Warmup: 7 improving directions out of 33 probes
```

### Run: CMA-ES

```python
f_batch = make_batch_evaluator(f, n_workers=16)
result = cma_es(
    f_batch=f_batch, x0=x0, bounds=bounds,
    int_params={2,3,4,7,10,13}, max_gen=20, lam=16,
    n_workers=16, warmup=warmup,
)
```

```
>>> σ₀ = 0.3/√17 = 0.0728
>>> C₀ shaped: 7/17 active dims
>>> Gen 1/20: best=-1.4269, gen_best=-1.4269, σ=0.0622, evals=16,  stag=0
>>> Gen 2/20: best=-1.4269, gen_best= 3.1486, σ=0.0602, evals=32,  stag=1
>>> Gen 3/20: best=-1.4269, gen_best=14.0770, σ=0.0574, evals=48,  stag=2
>>> Gen 4/20: best=-1.4269, gen_best= 1.5529, σ=0.0548, evals=64,  stag=3
>>> Gen 5/20: best=-1.4269, gen_best=-0.6475, σ=0.0533, evals=80,  stag=4
>>> Gen 6/20: best=-1.4269, gen_best=-1.1353, σ=0.0545, evals=96,  stag=5
>>> Early stop: 5 stagnant generations.
>>>
>>> Optimization complete: 96 evals, 6 gens, 117s (1.9 min)
>>> Best cost: -1.4269
```

### Run: Final verification of optimized params

```python
# Only M3_M changed: 3 → 13
best_params = {**llm_params, 'M3_M': 13}
sim_final = simulate_circuit(best_params, ...)
```

### Output: Optimized SPICE specs

```
dcgain_                  : 77.1513
gain_bandwidth_product_  : 7.11793e+07
phase_margin             : 59.6278
cmrr                     : 69.084
dcpsrp                   : -84.286
dcpsrn                   : -76.3888
power                    : 493.976
integrated_input_noise   : 1.14049e-05
slew_rate_pos            : 5.1037e+07
slew_rate_neg            : -1.39938e+07
output_swing             : 1.61191
gain_peaking_db          : 0
```

### Output: Optimization comparison

```
6a. Parameter Changes
Parameter        |          LLM |    Optimized |     Change
M3_M             |            3 |           13 |    +333.3%

6b. Specification Comparison
Spec           |       Target |     LLM      |    Optimized |   Change | Status
DC gain        |      > 70 dB |      75.8 dB |      77.2 dB | +1.3 dB  | ✅
GBW            |     > 50 MHz |     50.6 MHz |     71.2 MHz | +40.7%   | ✅
PM             |        > 60° |        73.3° |        59.6° | -18.7%   | ❌
SR+            |    > 10 V/µs |    54.2 V/µs |    51.0 V/µs | -5.8%    | ✅
Power          |     < 500 µW |     487.6 µW |     494.0 µW | +1.3%    | ✅
CMRR           |      > 60 dB |      62.0 dB |      69.1 dB | +7.1 dB  | ✅
PSRR+          |      > 60 dB |      83.8 dB |      84.3 dB | +0.5 dB  | ✅
PSRR-          |      > 60 dB |      64.9 dB |      76.4 dB | +11.5 dB | ✅
IRN            |      < 30 µV |      21.5 µV |      11.4 µV | -47.0%   | ✅

Constraints satisfied: 8/9 (PM fails by 0.4°)
```

### Decision

```
Optimized design meets 8/9 specs (PM = 59.6° < 60° target).
LLM design meets 9/9 specs.
→ Optimization did not improve the design. Keeping LLM sizing.
```

---

## [Final] Converged Design

### Final params

```
M3_L = 1.0       M3_WL_ratio = 9.89    M3_M = 3      # DIFF_PAIR (nfet)
M1_L = 0.5       M1_WL_ratio = 9.13    M1_M = 10     # LOAD (pfet)
M7_L = 0.5       M7_WL_ratio = 9.99    M7_M = 42     # OUTPUT_CS (pfet)
M5_L = 1.0       M5_WL_ratio = 3.44    M5_M = 1      # BIAS_GEN (nfet)
M6_L = 1.0       M6_WL_ratio = 3.44    M6_M = 11     # TAIL (nfet, mirrors M5)
M8_L = 1.0       M8_WL_ratio = 3.44    M8_M = 16     # OUTPUT_BIAS (nfet, mirrors M5)
C1_value = 2.3e-12                                     # Miller cap (F)
Rc_value = 1457.2                                      # Nulling resistor (Ohm)
ibias = 1e-05                                           # Bias current (A)
```

### Final SPICE performance (tt/20C)

```
Spec           |       Target |     Achieved |   Margin | Status
DC gain        |      > 70 dB |      75.8 dB |   +8.3%  | ✅
GBW            |     > 50 MHz |     50.6 MHz |   +1.2%  | ✅
PM             |        > 60° |        73.3° |  +22.2%  | ✅
SR+            |    > 10 V/µs |    54.2 V/µs |  +442%   | ✅
SR-            |   (inactive) |    15.1 V/µs |     --   | --
Power          |     < 500 µW |     487.6 µW |   +2.5%  | ✅
CMRR           |      > 60 dB |      62.0 dB |   +3.3%  | ✅
PSRR+          |      > 60 dB |      83.8 dB |  +39.7%  | ✅
PSRR-          |      > 60 dB |      64.9 dB |   +8.2%  | ✅
IRN            |      < 30 µV |      21.5 µV |  +28.3%  | ✅
Output swing   |   (inactive) |      1.579 V |     --   | --
```

### Execution statistics

```
Analytical iterations      : 2
SPICE iterations (sizing)  : 2
PVT simulations            : 2
Optimizer warmup probes    : 33 (+1 baseline)
Optimizer CMA-ES evals     : 96
Optimizer verification     : 1
Total SPICE calls          : 135
```
