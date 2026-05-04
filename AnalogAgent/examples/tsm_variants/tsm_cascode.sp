* TSM OTA — SELF-BIASED cascode PMOS active load on first stage
*   (regular cascode mirror — NOT wide-swing; see tsm_lv_cascode.sp for
*   the wide-swing / Sooch variant).
*
*   Stage 1:  NMOS diff pair (M3/M4) + cascode PMOS mirror load (M1/M2 main,
*             M9/M10 cascode).
*   Stage 2:  PMOS CS amp (M7) + NMOS current source (M8).
*   Bias:     M5 (diode ref) mirrors to M6 (tail) and M8 (2nd-stage bias).
*   Comp:     Miller Rc + C1 from first-stage output to vout.
*
*   LOAD sub-block main:    M1 (mirror side), M2 (output side).  Both are
*                           common-source PFETs with source at VDD, gate at net1.
*   LOAD_CAS sub-block:     M9 (mirror side), M10 (output side).  Stacked on
*                           the main devices.  Both cascode gates are tied to net1
*                           (the mirror diode node) — SELF-BIASED, no extra port.
*
*   The mirror reference stack (M1 + M9) is diode-connected: M9 drain = its gate
*   = net1, which also gates M1, M2, and the output-side cascode M10.
*
*   Headroom penalty (one |Vgs| above the wide-swing variant):
*     output_max approx VDD - |Vgs_M2| - vdsat_M10
*
*   Matched pairs:  M1 == M2, M9 == M10, M3 == M4, M5 == [M6, M8].
*
.subckt tsm_cascode gnda vdda vinn vinp vout Ib
* PMOS cascode mirror — main row (source at VDD, gate at net1)
XM1 net_int_ref  net1 vdda        vdda sky130_fd_pr__pfet_01v8
XM2 net_int_out  net1 vdda        vdda sky130_fd_pr__pfet_01v8
* PMOS cascode mirror — cascode row (self-biased: gate = net1 for both)
XM9  net1  net1 net_int_ref  vdda sky130_fd_pr__pfet_01v8
XM10 net5  net1 net_int_out  vdda sky130_fd_pr__pfet_01v8
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
.ends tsm_cascode
