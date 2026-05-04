* 5T OTA — SELF-BIASED cascode PMOS active load
*   (regular cascode mirror — NOT wide-swing; see 5tota_lv_cascode.sp for
*   the wide-swing / Sooch variant).
*
*   LOAD sub-block main:    M5 (output side), M6 (mirror side).  Both are
*                           common-source PFETs with source at VDD, gate at net1.
*   LOAD_CAS sub-block:     M7 (output side), M8 (mirror side).  Stacked on the
*                           main devices.  Both cascode gates are tied to net1
*                           (the mirror diode node) — SELF-BIASED, no extra port.
*
*   The mirror reference stack (M6 + M8) is diode-connected: M8 drain = its gate
*   = net1, which also gates M6 and the output-side cascode/main pair (M5/M7).
*
*   Headroom penalty (one |Vgs| above the wide-swing variant):
*     output_max ≈ VDD − |Vgs_M5| − vdsat_M7
*
.subckt 5tota_cascode gnda vdda vinn vinp vout Ib
* PMOS cascode mirror — main row (source at VDD, gate at net1)
XM5 net_out5 net1 vdda     vdda sky130_fd_pr__pfet_01v8
XM6 net_int_m net1 vdda     vdda sky130_fd_pr__pfet_01v8
* PMOS cascode mirror — cascode row (self-biased: gate = net1 for both)
XM7 vout     net1 net_out5  vdda sky130_fd_pr__pfet_01v8
XM8 net1     net1 net_int_m vdda sky130_fd_pr__pfet_01v8
* NMOS diff pair
XM1 vout  vinn net2 gnda sky130_fd_pr__nfet_01v8
XM2 net1  vinp net2 gnda sky130_fd_pr__nfet_01v8
* Tail current source + bias reference
XM3 net2  net3 gnda gnda sky130_fd_pr__nfet_01v8
XM4 net3  net3 gnda gnda sky130_fd_pr__nfet_01v8
I0  vdda  net3 Ib
.ends 5tota_cascode
