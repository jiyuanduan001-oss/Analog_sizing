* 5T OTA — LOW-VOLTAGE (wide-swing, Sooch-style) cascode PMOS active load.
*
*   LOAD sub-block main:    M5 (output side), M6 (mirror side). PFETs with
*                           source at VDD. BOTH main gates are tied to net1
*                           (= M8.drain on the reference side) — this is the
*                           Sooch wide-swing wiring.  net1 is the only
*                           "diode" feedback node in the structure.
*   LOAD_CAS sub-block:     M7 (output side), M8 (mirror side), stacked on
*                           the main row.  Both cascode gates are driven by
*                           the EXTERNAL bias port Vbias_cas_p, supplied
*                           by the testbench at
*                               Vbias_cas_p = VDD − (vdsat_main + vdsat_cas + |Vth_cas|).
*
*   Headroom: output_max ≈ VDD − (vdsat_main + vdsat_cas)
*             (≈2·vdsat — much better than the regular cascode's |Vgs| + vdsat).
*   Netlist signature: main.gate is wired to cas.drain on the reference side
*             (M5.gate = M6.gate = M8.drain = net1).
*
.subckt 5tota_lv_cascode gnda vdda vinn vinp vout Ib Vbias_cas_p
* PMOS cascode mirror — main row: source=VDD, both gates tied to mirror-side
*   cas-drain (net1 = M8.drain) — correct Sooch wide-swing mirror
XM5 net_out5 net1  vdda        vdda sky130_fd_pr__pfet_01v8
XM6 net_int_m net1  vdda        vdda sky130_fd_pr__pfet_01v8
* PMOS cascode mirror — cascode row: gates = external Vbias_cas_p
XM7 vout     Vbias_cas_p net_out5  vdda sky130_fd_pr__pfet_01v8
XM8 net1     Vbias_cas_p net_int_m vdda sky130_fd_pr__pfet_01v8
* NMOS diff pair
XM1 vout  vinn net2 gnda sky130_fd_pr__nfet_01v8
XM2 net1  vinp net2 gnda sky130_fd_pr__nfet_01v8
* Tail current source + bias reference
XM3 net2  net3 gnda gnda sky130_fd_pr__nfet_01v8
XM4 net3  net3 gnda gnda sky130_fd_pr__nfet_01v8
I0  vdda  net3 Ib
.ends 5tota_lv_cascode
