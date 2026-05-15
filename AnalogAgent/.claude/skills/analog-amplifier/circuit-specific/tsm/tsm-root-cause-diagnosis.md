# TSM Root-Cause Diagnosis

## Purpose

When a TSM design fails to meet specs (analytically or in simulation),
this skill maps each failure to its root cause and recommends a fix.

## Rules

1. Follow the priority order: fix saturation issues before spec failures.

---

## Priority Order

1. **CRITICAL**: Any device not in saturation → fix OP first
2. **NORMAL**: Spec failures → fix per fault tree below

---

## ⚠️ Power Utilization — Read Before Any Fault Tree

Before diving into individual fault trees, check whether the design is
using its power budget. If power is well below target while specs are
failing, consider increasing I_tail first — it improves GBW, noise, SR,
and CMRR simultaneously. Allocate remaining margin to ID7 if SR⁻ fails.

---

## Fault Tree: Device Not Saturated

### M6 (TAIL) in linear region

Most common failure. VDS_M6 = V_cm - VGS_M3 - VSS must exceed Vdsat_M6.

```
Root cause: VDS_M6 < Vdsat_M6
  Mechanism: I_tail/I_bias mirror ratio too high → VGS_M6 large → VDS compressed
  OR: V_cm too low for the stack height

Fix priority:
  1. Reduce VGS(DIFF_PAIR) by increasing gm/ID of DIFF_PAIR (M3, M4)
     ⚠️ Side effect: larger input pair, more parasitic cap
  2. Increase gm/ID of TAIL → reduces Vdsat_M6
     ⚠️ Side effect: larger device area
  3. Increase I_bias to reduce mirror ratio (target ratio ≤ 8:1)
  4. If all fail: topology may not support these specs at this VDD
```

### M7 (OUTPUT_CS) in linear region

```
Root cause: VDD - V_out < Vdsat_M7
  Mechanism: V_out,max spec too close to VDD for M7's Vdsat

Fix:
  1. Increase W7 (reduces Vdsat at same ID7)
     ⚠️ Side effect: larger Cgs7, slower p4
  2. Increase gm/ID of OUTPUT_CS (weaker inversion, lower Vdsat)
  3. Reduce ID7 (but check PM — lower gm7 → lower p2)
```

### M8 (OUTPUT_BIAS) in linear region

```
Root cause: V_out < Vdsat_M8
  Mechanism: V_out,min spec too aggressive for M8's Vdsat

Fix:
  1. Increase W8 (reduces Vdsat at same ID8)
     This means increasing W5 (shared unit-cell W/L)
  2. Reduce ID7 (= ID8)
  3. Relax V_out,min spec
```

### M3/M4 (DIFF_PAIR) in linear region

```
Root cause: V_cm too low, or first-stage output node voltage wrong
  Mechanism: systematic offset condition not met → drain voltages of M3/M4 unequal

Fix:
  1. Check V_cm range vs bias constraints
  2. Verify systematic offset condition:
     (W1/L1)/(W7/L7) = (1/2)·(W6/L6)/(W8/L8)
     Adjust mirror ratios to satisfy offset condition
```

---

## Fault Tree: Tail Current Source Headroom

The TAIL (M6) saturation margin is a cross-cutting concern: when M6
operates near the saturation boundary, its effective gds rises steeply,
degrading **multiple specs simultaneously** — CMRR, PSRR⁻, GBW (via
mirror current loss), and indirectly noise and SR. If more than one of
these specs fails at the same time, check M6 headroom first.

```
M6 saturation margin too low  (margin < 100 mV, or multiple specs degraded)
    │
    ├── Reduce Vdsat of BIAS_GEN / TAIL
    │   Push gm/ID of BIAS_GEN (M5) toward weaker inversion.
    │   Since M5, M6, M8 share the same per-instance W/L, lowering
    │   Vdsat on M5 lowers Vdsat on M6 and M8 simultaneously.
    │   This is the most direct fix — it does not change VGS_M3 or
    │   the voltage stack above M6.
    │
    ├── Reduce VGS of DIFF_PAIR
    │   Push gm/ID of DIFF_PAIR toward weaker inversion.
    │   VDS_M6 = V_cm − VGS_M3, so any reduction in VGS_M3 adds
    │   directly to M6 headroom.
    │   ⚠️ Side effect: wider input pair, more parasitic cap, lower ft.
    │
    ├── Increase L5 (= L6) for higher intrinsic ro per device
    │   Higher ro improves small-signal tail impedance even at the
    │   same saturation margin.
    │   ⚠️ Side effect: W5 shrinks, may force M5_M > 1
    │   (discretization can double the effective mirror ratio).
    │
    └── Increase I_bias to reduce mirror ratio
        Lower M6_M means less VDS compression from finite ro.
        Only if the spec form allows it (I_bias is often constrained).

Cross-references:
  CMRR depends on 1/gds_eq_TAIL — see "CMRR Too Low"
  PSRR⁻ TAIL path scales with gds_eq_TAIL — see "PSRR Too Low"
  GBW shortfall from mirror current loss — see "GBW Too Low"
```

⚠️ **Analytical overestimate warning:** The small-signal CMRR and
PSRR⁻ formulas use gds6 as a constant, but near the saturation
boundary gds changes steeply with VDS. The analytical prediction can
overestimate CMRR by 15–20 dB when M6 margin is below 100 mV. Always
verify with SPICE, and if the analytical model predicts comfortable
CMRR margin but SPICE fails, check M6 headroom.

---

## Fault Tree: Gain Too Low

```
A0 < A0_target
    │
    ├── First-stage gain too low (A_v1 = gm3/(gds3+gds_eq_LOAD))
    │   ├── gds3 too large → increase L3
    │   │   ⚠️ Side effect: larger Cgs3, Cgd3 → may affect GBW
    │   ├── gds_eq_LOAD too large → increase L1 (or L_cas for cascode)
    │   │   ⚠️ Side effect: larger Cgs1 → lower mirror pole p3 → PM may degrade
    │   └── Check from OP: intrinsic gain of M3 vs M1
    │       → If one device has much lower gm_gds → that's the bottleneck
    │
    └── Second-stage gain too low (A_v2 = gm7/(gds7+gds_eq_OBIAS))
        ├── gm7 too low → increase W7 or ID7
        ├── gds7 + gds8 too high → increase L7 and/or L8 (L8 = L5)
        │   ⚠️ Side effect: longer L7 → slower p2, p4
        └── OP check: verify gm7, gds7, gds8 from simulation

Side effects of fixing gain:
  Increasing L → larger parasitics → GBW may decrease
  Increasing ID → more power (almost no gain benefit, since gds also rises)
  These tradeoffs must be reported to the user.
```

---

## Fault Tree: GBW Too Low

```
GBW < GBW_target   (GBW = gm3/(2π·Cc))
    │
    ├── gm3 too low
    │   → Increase I_tail to get larger gm3 (Especially when there is power margin available. )
    │
    ├── Cc too large
    │   → Reduce Cc (but verify PM still meets target)
    │
    └── Non-dominant pole pulling effective BW down
        ├── p2 too low → increase gm7
        ├── p3 too low → reduce C2 (smaller W1/W2 or shorter L1)
        └── Check: is SPICE GBW much lower than gm3/(2π·Cc)?
            → If yes: parasitic pole separation assumption is violated
```

---

## Fault Tree: Phase Margin Too Low

```
PM < PM_target
    │
    ├── Output pole p2 too close to ω_c
    │   → Increase gm7 (increase W7 or ID7)
    │   → Or increase Cc (moves ω_c down, but reduces GBW)
    │
    ├── Mirror pole p3 too close to ω_c
    │   → Reduce capacitance at mirror node:
    │     - Reduce W1, W2 (reduces Cgs1, Cgs2)
    │     - Reduce W4 (reduces Cdb4, Cgd4)
    │   → Or increase gm1 (move p3 up — but W1 must also increase → tradeoff)
    │
    ├── Compensation pole p4 too close to ω_c
    │   → Increase gm7 (raises p4 — recompute via KCL cubic)
    │   → Or reduce C1 parasitic (shorter L7 or smaller W1/W2)
    │
    ├── RHP zero not cancelled / p2 not fully cancelled
    │   → Recompute Rc = 1/gm7 + 1/(p2_kcl × Cc) after any parameter change
    │
    └── PM estimation was optimistic
        → Check: was arctan(x)≈x used with x > 0.47?
        → Switch to exact arctan computation
        → Or just trust SPICE PM and adjust accordingly
```

---

## Fault Tree: Slew Rate Too Low

SR+ and SR- are separate specs:
```
SR+ = I_tail / Cc
SR- = min(I_tail / Cc, ID7 / CTL_eff)    where CTL_eff = CTL + Cgd7 × A_v2
```

```
SR+ < SR+_target
    │
    └── I_tail/Cc too low
        → Increase I_tail
        → Or reduce Cc (but check PM)
        ⚠️ Side effect: more power

SR- < SR-_target   (identify which term limits min())
    │
    ├── Limited by I_tail/Cc (1st stage too slow)
    │   → Increase I_tail
    │   → Or reduce Cc (but check PM)
    │   ⚠️ Side effect: more power
    │
    └── Limited by ID7/CTL (2nd stage too slow)
        → Increase ID7
        → Or reduce CL (usually fixed)
        ⚠️ Side effect: more power
```

---

## Fault Tree: Output Swing Too Low

```
V_swing = VDD - Vdsat_M7 - Vdsat_M8 < Swing_target
    │
    ├── Vdsat_M7 too large → increase gm/ID of OUTPUT_CS (weaker inversion)
    │   ⚠️ Side effect: lower ft, larger W7
    │
    └── Vdsat_M8 too large → increase gm/ID of bias mirrors (weaker inversion)
        This means increasing W5 (shared unit-cell), which increases W8
        ⚠️ Side effect: larger device area
```

---

## Fault Tree: CMRR Too Low

```
CMRR = 2·gm3·gm1/[(gds3+gds_eq_LOAD)·gds_eq_TAIL] < CMRR_target
    │
    ├── gds_eq_TAIL too high (most common root cause)
    │   → First check M6 saturation margin.
    │     If margin < 100 mV or multiple specs (CMRR + PSRR⁻ + GBW)
    │     fail together → see "Tail Current Source Headroom" fault tree.
    │   → If M6 is well saturated: increase L5 (= L6) or add cascode to TAIL.
    │     TAIL is not speed-critical.
    │
    └── A0 too low → fix gain first (see gain fault tree)
```

---

## Fault Tree: PSRR Too Low

```
PSRR⁻ — use the two-path formula (see tsm-equation.md):
  A_VSS_M8 = gds_eq_OBIAS / (gds7 + gds_eq_OBIAS)                      [M8 direct]
  A_VSS_TAIL = gds_eq_TAIL·gds_eq_LOAD·gm7 / [2·gm1·(gds3+gds_eq_LOAD)·(gds7+gds_eq_OBIAS)]  [TAIL]
  PSRR⁻    = A0 / (A_VSS_M8 + A_VSS_TAIL)

  PSRR⁻ too low:
    │
    ├── A_VSS_TAIL dominates (check: A_VSS_TAIL > A_VSS_M8)
    │   Root cause: gds_eq_TAIL too high (M6 near triode)
    │   → If M6 margin < 100 mV or CMRR also fails
    │     → see "Tail Current Source Headroom" fault tree
    │   → If M6 well saturated: increase L5 (= L6) for higher ro_eq_TAIL
    │
    ├── A_VSS_M8 dominates (check: A_VSS_M8 > A_VSS_TAIL)
    │   Root cause: gds_eq_OBIAS too high
    │   → Increase L5 (= L8) for higher ro_eq_OBIAS
    │
    └── Both paths comparable
        → Increase L5 (benefits both ro_eq_TAIL and ro_eq_OBIAS)
        → Or improve first-stage gain (increase L3 or L1)

PSRR⁺ — use the 4-node formula (see tsm-equation.md):
  Solve the 4-node DC system (net1, net5, vout, net2) for δVout/δVDD,
  then PSRR⁺ ≈ (1+A0) / |δVout/δVDD|.

  The dominant coupling path is M7's gds7 pushing vout toward VDD.
  The mirror's VDD tracking partially cancels this, but the tail node
  shift limits the cancellation.

  PSRR⁺ too low:
    │
    ├── A0 too low → fix gain first (see gain fault tree)
    │
    ├── gds7 too high → increase L7 (improves ro7)
    │
    └── TAIL gds too high → increase L5 (= L6) or improve M6 headroom
        (reduces tail node shift, improves VDD tracking cancellation)
```

---

## Fault Tree: Power Too High

```
P = VDD × (I_bias + I_tail + ID7) > P_target
    │
    ├── I_tail too high
    │   → Driven by GBW or SR requirement
    │   → Increase gm/ID of DIFF_PAIR (get same gm with less current)
    │   → Or relax GBW/SR spec
    │
    ├── ID7 (second stage) too high
    │   → Driven by PM constraint (need large gm7 for p2)
    │   → Increase gm/ID of OUTPUT_CS (but check fT constraint)
    │   → Or relax PM spec
    │
    └── Bias overhead
        → Optimize I_bias (reduce if mirror ratios allow)
```

## Fault Tree: Power Under-Utilized

See **"⚠️ Power Utilization"** at the top of this file.

---

## Fault Tree: Noise Too High

Noise parameters (Kf, Cox) are not in the LUT. Noise is best evaluated
by the simulator. For pre-simulation guidance:

```
Integrated noise too high
    │
    ├── Thermal noise dominated
    │   → Increase gm3 (more current or larger gm/ID)
    │   → gm1/gm3 ratio also matters — minimize gm1 relative to gm3
    │
    └── 1/f noise dominated
        → Increase W3 × L3 (more input pair area)
        → Check load contribution: if (Kf_p·µn·W3·L3)/(Kf_n·µp·W1·L1) > 0.5,
          load noise is significant → increase L1
```

---

## Fault Tree: Cascode / LV Cascode Sub-Block Issues

Applies only when LOAD or OUTPUT_BIAS uses `sub_block_type = "cascode"` or
`"lv_cascode"` (see `general/knowledge/mirror-load-structures.md`).

### Internal pole too low → degrades PM

```
p_int_LOAD  = gm_loadcas / C_int_LOAD  < 3·ω_c
p_int_OBIAS = gm_obcas   / C_int_OBIAS < 3·ω_c
    │
    ├── Reduce L_cas (already at L_min? skip)
    │     → smaller C_int → higher p_int
    │
    └── Increase gm_cas
        → Lower (gm/ID)_cas to 8 S/A
        ⚠️ Bigger Vdsat_cas → more headroom consumed
```

### 1st- or 2nd-stage gain low despite cascode

```
A_v1 = gm3 / (gds3 + gds_eq_LOAD)  below target
  OR
A_v2 = gm7 / (gds7 + gds_eq_OBIAS) below target
    │
    ├── gds_eq too high because main gds (gds1 or gds8) dominant
    │     → Increase L1 (or L5 for OUTPUT_BIAS) to reduce main gds
    │
    ├── gds_eq too high because cascode gm_gds low
    │     → Increase L_cas (longer cascode → higher gm_gds_cas)
    │     ⚠️ Verify p_int still > 3·ω_c
    │
    └── gds3 or gds7 (input-side) dominant
        → Standard gain fix: increase L3 or L7
```

### PM degraded by cascode internal pole

```
arctan(ω_c / p_int_*) eats > 15° of PM
    │
    └── Same fixes as "internal pole too low" above.
        If already at gm/ID = 8 and L_min, can't fix further:
          → Increase Cc (moves ω_c down, recovers PM)
          → Or accept the PM loss if still above target
```

### Headroom violation → consider lv_cascode

```
If output stage hits saturation limit at either end:
  Regular cascode headroom = vdsat_main + Vgs_cas (≈ Vth + 2·vdsat)
  LV cascode headroom      ≈ 2·vdsat (better)

Fix: rewire the netlist to the LV cascode pattern and add external bias.
Requires netlist change — may need user intervention.
```

---

## Fault Tree: Mismatch Too High

Only applies when Mismatch is an active target (user provided a number).

Mismatch is dominated by Pelgrom threshold mismatch: `σ(ΔVth) = A_VT / √(W × L)`.
Both the input pair and load pair contribute.

**Two fixes only — do not overcomplicate:**

```
Mismatch_3sigma > Mismatch_target
    │
    ├── Fix 1: Increase W and L (increase transistor area)
    │   Identify the pair with the smaller W×L product (diff pair or load).
    │   Increase both W and L for the bottleneck pair.
    │
    └── Fix 2: Reduce |Vdsat| (push toward weaker inversion)
        Higher gm/ID → lower id_w → wider W at same current → more area.
        Also reduces VGS, improving headroom for stacked devices.
```

---

## Output

After consulting the fault trees, apply the fix and output the **new adjusted
sizes** for the affected role(s). Re-derive all LUT parameters for the changed
role(s), then return to design-flow Step 6 for re-evaluation.
