* TSM OTA — single-transistor PMOS current-mirror load on first stage.
*
*   Stage 1:  NMOS diff pair (M3/M4) + single PMOS mirror load (M1/M2).
*   Stage 2:  PMOS CS amp (M7) + NMOS current source (M8).
*   Bias:     M5 (diode ref) mirrors to M6 (tail) and M8 (2nd-stage bias).
*   Comp:     Miller Rc + C1 from first-stage output to vout.
*
*   LOAD sub-block:  { M2 (mirror-driven), M1 (diode-connected) }.
*   Matched pairs:   M1 == M2 (load mirror), M3 == M4 (diff pair),
*                    M5 == [M6, M8] (bias mirrors).
*   Headroom (1st stage):  output_max approx VDD - vdsat_M2 (one vdsat penalty).
*
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
