* 5T OTA — single-transistor PMOS current-mirror load (classic).
*   LOAD sub-block: { M5 (mirror-driven), M6 (diode-connected) }.
*   Matched pairs:    M1 == M2 (diff pair), M5 == M6 (load mirror).
*   Mirror group:     M3 (TAIL) mirrors M4 (BIAS_GEN).
*   Headroom:         output_max ≈ VDD − vdsat_M5 (one vdsat penalty).
.subckt 5tota_single gnda vdda vinn vinp vout Ib
* NMOS diff pair
XM1 vout  vinn net2 gnda sky130_fd_pr__nfet_01v8
XM2 net1  vinp net2 gnda sky130_fd_pr__nfet_01v8
* PMOS mirror load — single transistor per branch
XM5 vout  net1 vdda vdda sky130_fd_pr__pfet_01v8
XM6 net1  net1 vdda vdda sky130_fd_pr__pfet_01v8
* Tail current source + bias reference
XM3 net2  net3 gnda gnda sky130_fd_pr__nfet_01v8
XM4 net3  net3 gnda gnda sky130_fd_pr__nfet_01v8
I0  vdda  net3 Ib
.ends 5tota_single
