* TSM OTA — LOW-VOLTAGE (wide-swing, Sooch-style) cascode PMOS active load
*   on first stage.
*
*   Stage 1:  NMOS diff pair (M3/M4) + wide-swing cascode PMOS mirror load
*             (M1/M2 main, M9/M10 cascode).
*   Stage 2:  PMOS CS amp (M7) + NMOS current source (M8).
*   Bias:     M5 (diode ref) mirrors to M6 (tail) and M8 (2nd-stage bias).
*   Comp:     Miller Rc + C1 from first-stage output to vout.
*
*   LOAD sub-block main:    M1 (mirror side), M2 (output side).  PFETs with
*                           source at VDD.  BOTH main gates are tied to net1
*                           (= M9.drain on the reference side) — this is the
*                           Sooch wide-swing wiring.  net1 is the only
*                           "diode" feedback node in the structure.
*   LOAD_CAS sub-block:     M9 (mirror side), M10 (output side), stacked on
*                           the main row.  Both cascode gates are driven by
*                           the EXTERNAL bias port Vbias_cas_p, supplied
*                           by the testbench at
*                               Vbias_cas_p = VDD - (vdsat_main + vdsat_cas + |Vth_cas|).
*
*   Headroom: output_max approx VDD - (vdsat_M2 + vdsat_M10)
*             (approx 2*vdsat — much better than the regular cascode's |Vgs| + vdsat).
*   Netlist signature: main.gate is wired to cas.drain on the reference side
*             (M1.gate = M2.gate = M9.drain = net1).
*
*   Matched pairs:  M1 == M2, M9 == M10, M3 == M4, M5 == [M6, M8].
*
.subckt tsm_lv_cascode gnda vdda vinn vinp vout Ib Vbias_cas_p
* PMOS cascode mirror — main row: source=VDD, both gates tied to mirror-side
*   cas-drain (net1 = M9.drain) — correct Sooch wide-swing mirror
XM1 net_int_ref  net1        vdda         vdda sky130_fd_pr__pfet_01v8
XM2 net_int_out  net1        vdda         vdda sky130_fd_pr__pfet_01v8
* PMOS cascode mirror — cascode row: gates = external Vbias_cas_p
XM9  net1  Vbias_cas_p net_int_ref  vdda sky130_fd_pr__pfet_01v8
XM10 net5  Vbias_cas_p net_int_out  vdda sky130_fd_pr__pfet_01v8
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
.ends tsm_lv_cascode
