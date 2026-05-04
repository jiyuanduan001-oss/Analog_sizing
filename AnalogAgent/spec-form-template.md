# Design Spec Form — 5T OTA (SKY130)

## Required (sizing will not proceed without these)
VDD          : 1.8         # Supply voltage (V)
CL           : 2e-12       # Load capacitance (F)
Gain         : 46.5          # DC gain target (dB)
GBW          : 1.1e7        # Gain-bandwidth product (Hz)
PM           : 72          # Phase margin (degrees)

## Environment (recommended — defaults applied if blank)
Temperature  : 27          # C  (default: 27)
Corner       : tt          # tt, ff, ss, fs, sf  (default: tt)

## Optional (leave blank to skip — will not be optimized)
Power        : 40e-6      # Max power (W)
SR+          : 8.5e6         # Positive slew rate (V/s)
SR-          : 7e6         # Negative slew rate (V/s)
CMRR         : 65          # (dB)
PSRR+        : 45          # Positive PSRR (dB)
PSRR-        : 75          # Negative PSRR (dB)
IRN          :             # Integrated input-referred noise (V rms)
ORN          :             # Integrated output-referred noise (V rms)
Output_swing :             # (V)
I_bias       : 2e-6        # External bias current (A)

## Mismatch (leave blank to skip — saves significant runtime)
#
# Mismatch simulation uses Monte Carlo (50 runs) and is much slower than
# other specs. When blank, mismatch is completely skipped: no Monte Carlo
# simulation is run, no mismatch data is reported, and mismatch is excluded
# from the iteration loop and optimization constraints.
#
# When a number is provided, mismatch becomes an active design target.
# The sizing flow will run Monte Carlo each iteration, check the 3-sigma offset
# against the target, and include it in root-cause diagnosis if it fails.
# Diagnosis focuses on two fixes: (1) increase WxL (transistor area),
# (2) reduce |Vdsat| (push toward weaker inversion).
#
Mismatch     :             # 3-sigma mismatch offset (V) — Monte Carlo, 50 runs
                            #   Leave BLANK to skip mismatch entirely

## Post-Sizing Options
Extreme_PVT  : no          # yes/no — run additional sims at extreme corners
                            #   after sizing converges (SS/85C + FF/-40C)
Optimize     : no          # yes/no — run numerical optimization after sizing
                            #   converges. After the LLM sizing stage, the system
                            #   will ask which metric to prioritize: Power, Gain,
                            #   or GBW. The selected metric receives a higher
                            #   weight; the other two are still improved but with
                            #   lower priority. All other specs are kept above
                            #   user targets as constraints.
