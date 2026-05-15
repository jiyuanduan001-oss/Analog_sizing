"""
Waveform copy and plot utilities for AnalogAgent.

Copies simulation waveform files from CircuitCollector output to
the AnalogAgent simulation_waveform/ directory, organized into
subfolders by category.  Also provides plot generation from
ngspice wrdata files.

Subfolder structure:
  simulation_waveform/
    nominal/          — final sizing result waveforms
    pvt_ss_85C/       — extreme PVT slow corner
    pvt_ff_m40C/      — extreme PVT fast corner
    optimized/        — post-optimization result waveforms
    optimized_pvt_ss/ — optimized + PVT slow corner
    optimized_pvt_ff/ — optimized + PVT fast corner
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Optional

import numpy as np

# CircuitCollector output root
_CC_ROOT = Path(__file__).resolve().parent.parent.parent / "CircuitCollector" / "CircuitCollector" / "output" / "opamp"

# AnalogAgent waveform root
_WAVE_ROOT = Path(__file__).resolve().parent.parent / "simulation_waveform"


def collect_waveforms(
    topology_name: str,
    category: str = "nominal",
    cc_output_dir: str | Path | None = None,
) -> list[str]:
    """
    Copy waveform files from CircuitCollector output to AnalogAgent.

    Looks for files matching *_waveform_*.txt in the CircuitCollector
    output directory for the given topology.

    Args:
        topology_name: Name of the topology (e.g. 'tsm_single', '5tota_single').
        category:      Subfolder name — one of:
                         'nominal', 'pvt_ss_85C', 'pvt_ff_m40C',
                         'optimized', 'optimized_pvt_ss', 'optimized_pvt_ff'
        cc_output_dir: Override for the CircuitCollector output directory.
                       If None, uses the default path based on topology_name.

    Returns:
        List of destination file paths that were copied.
    """
    if cc_output_dir is not None:
        src_dir = Path(cc_output_dir)
    else:
        src_dir = _CC_ROOT / topology_name

    dst_dir = _WAVE_ROOT / category
    dst_dir.mkdir(parents=True, exist_ok=True)

    copied = []
    patterns = [
        f"{topology_name}_waveform_*.txt",
        f"{topology_name}_waveform_*.txt.*",
    ]

    for pattern in patterns:
        for src_file in src_dir.glob(pattern):
            dst_file = dst_dir / src_file.name
            shutil.copy2(src_file, dst_file)
            copied.append(str(dst_file))

    return copied


# ---------------------------------------------------------------------------
# ngspice wrdata parser
# ---------------------------------------------------------------------------

def _parse_wrdata(filepath: str | Path, n_vars: int) -> tuple[np.ndarray, list[np.ndarray]]:
    """
    Parse an ngspice ``wrdata`` output file.

    wrdata format: each row has ``n_vars`` interleaved (x, y) pairs::

        x1 y1  x2 y2  x3 y3 ...

    All x columns are identical (the sweep variable).  This function
    returns the shared x-axis and a list of y arrays.

    Args:
        filepath: Path to the wrdata .txt file.
        n_vars:   Number of output variables (= number of (x,y) pairs per row).

    Returns:
        (x, [y1, y2, ...]) where x and each yi are 1-D numpy arrays.
    """
    data = np.loadtxt(filepath)
    if data.ndim == 1:
        data = data.reshape(1, -1)
    x = data[:, 0]
    ys = [data[:, 2 * i + 1] for i in range(n_vars)]
    return x, ys


# ---------------------------------------------------------------------------
# Plot generators
# ---------------------------------------------------------------------------

def plot_ac_bode(
    filepath: str | Path,
    output_png: str | Path,
    title: str = "Open-Loop AC Response",
    specs: Optional[dict] = None,
) -> str:
    """
    Generate a Bode plot (gain + phase) from the AC waveform file.

    The AC waveform file contains 5 variables from the template::

        wrdata ... vdb(opout) vp(opout) vdb(cm3) vdb(ppsr1) vdb(npsr1)

    Args:
        filepath:   Path to ``*_waveform_AC.txt``.
        output_png: Destination PNG path.
        specs:      Optional dict with 'dcgain_', 'gain_bandwidth_product_',
                    'phase_margin' to annotate the plot.

    Returns:
        The output PNG path (as string).
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    freq, ys = _parse_wrdata(filepath, n_vars=5)
    gain_db   = ys[0]    # vdb(opout)  — open-loop gain
    phase_deg = ys[1]    # vp(opout)   — open-loop phase
    cmrr_db   = ys[2]    # vdb(cm3)    — CMRR
    psrrp_db  = ys[3]    # vdb(ppsr1)  — PSRR+
    psrrn_db  = ys[4]    # vdb(npsr1)  — PSRR-

    fig, (ax_gain, ax_phase, ax_rej) = plt.subplots(
        3, 1, figsize=(10, 10), sharex=True,
        gridspec_kw={"height_ratios": [3, 2, 2]},
    )

    # -- Gain --
    ax_gain.semilogx(freq, gain_db, "b-", linewidth=1.5, label="Gain")
    ax_gain.axhline(0, color="gray", linewidth=0.5, linestyle="--")
    ax_gain.set_ylabel("Gain (dB)")
    ax_gain.set_title(title)
    ax_gain.grid(True, which="both", alpha=0.3)

    if specs:
        dc = specs.get("dcgain_")
        gbw = specs.get("gain_bandwidth_product_")
        if dc is not None:
            ax_gain.axhline(dc, color="green", linewidth=0.8, linestyle=":")
            # Annotate DC gain value on the curve at low frequency
            ax_gain.annotate(
                f"DC gain = {dc:.1f} dB",
                xy=(freq[0], dc), xytext=(freq[0] * 5, dc - 8),
                fontsize=9, fontweight="bold", color="green",
                arrowprops=dict(arrowstyle="->", color="green", lw=1.2),
            )
        if gbw is not None:
            ax_gain.axvline(gbw, color="red", linewidth=0.8, linestyle=":")
            # Place a marker at the 0-dB crossing and annotate GBW
            ax_gain.plot(gbw, 0, "ro", markersize=6, zorder=5)
            ax_gain.annotate(
                f"GBW = {gbw/1e6:.1f} MHz",
                xy=(gbw, 0), xytext=(gbw * 3, 12),
                fontsize=9, fontweight="bold", color="red",
                arrowprops=dict(arrowstyle="->", color="red", lw=1.2),
            )
        ax_gain.legend(fontsize=8, loc="upper right")

    # -- Phase --
    ax_phase.semilogx(freq, phase_deg, "r-", linewidth=1.5, label="Phase")
    ax_phase.axhline(0, color="gray", linewidth=0.5, linestyle="--")
    ax_phase.axhline(-180, color="gray", linewidth=0.5, linestyle="--")
    ax_phase.set_ylabel("Phase (deg)")
    ax_phase.grid(True, which="both", alpha=0.3)

    if specs:
        pm = specs.get("phase_margin")
        gbw = specs.get("gain_bandwidth_product_")
        if pm is not None:
            phase_at_pm = -180 + pm
            ax_phase.axhline(phase_at_pm, color="green", linewidth=0.8,
                             linestyle=":")
            # Place marker at the GBW frequency on the phase curve
            if gbw is not None and len(freq) > 1:
                # Interpolate phase at GBW frequency
                phase_at_gbw = np.interp(gbw, freq, phase_deg)
                ax_phase.plot(gbw, phase_at_gbw, "go", markersize=6, zorder=5)
                # Draw a double-headed arrow showing PM
                ax_phase.annotate(
                    "", xy=(gbw, -180), xytext=(gbw, phase_at_gbw),
                    arrowprops=dict(arrowstyle="<->", color="green", lw=1.5),
                )
                ax_phase.annotate(
                    f"PM = {pm:.1f}\u00b0",
                    xy=(gbw, phase_at_gbw),
                    xytext=(gbw * 3, phase_at_gbw + 15),
                    fontsize=9, fontweight="bold", color="green",
                    arrowprops=dict(arrowstyle="->", color="green", lw=1.2),
                )
            else:
                ax_phase.text(
                    0.02, 0.15, f"PM = {pm:.1f}\u00b0",
                    transform=ax_phase.transAxes,
                    fontsize=9, fontweight="bold", color="green",
                    bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="green", alpha=0.8),
                )

    # -- CMRR / PSRR --
    # The testbench stores rejection ratios as negative dB (e.g. -62 dB).
    # Plot absolute values so higher = better rejection.
    ax_rej.semilogx(freq, np.abs(cmrr_db), "g-", linewidth=1.2, label="CMRR")
    ax_rej.semilogx(freq, np.abs(psrrp_db), "m-", linewidth=1.2, label="PSRR+")
    ax_rej.semilogx(freq, np.abs(psrrn_db), "c-", linewidth=1.2, label="PSRR\u2212")
    ax_rej.set_ylabel("|Rejection| (dB)")
    ax_rej.set_xlabel("Frequency (Hz)")
    ax_rej.grid(True, which="both", alpha=0.3)

    if specs:
        cmrr_dc = specs.get("cmrr")
        psrrp_dc = specs.get("dcpsrp")
        psrrn_dc = specs.get("dcpsrn")
        # Annotate DC values directly on the curves at low frequency
        f_annot = freq[0] * 3
        if cmrr_dc is not None:
            ax_rej.annotate(
                f"{abs(cmrr_dc):.1f} dB",
                xy=(freq[0], abs(cmrr_dc)), xytext=(f_annot * 10, abs(cmrr_dc) + 3),
                fontsize=8, fontweight="bold", color="green",
                arrowprops=dict(arrowstyle="->", color="green", lw=0.8),
            )
        if psrrp_dc is not None:
            ax_rej.annotate(
                f"{abs(psrrp_dc):.1f} dB",
                xy=(freq[0], abs(psrrp_dc)), xytext=(f_annot * 10, abs(psrrp_dc) + 3),
                fontsize=8, fontweight="bold", color="m",
                arrowprops=dict(arrowstyle="->", color="m", lw=0.8),
            )
        if psrrn_dc is not None:
            ax_rej.annotate(
                f"{abs(psrrn_dc):.1f} dB",
                xy=(freq[0], abs(psrrn_dc)), xytext=(f_annot * 10, abs(psrrn_dc) - 6),
                fontsize=8, fontweight="bold", color="c",
                arrowprops=dict(arrowstyle="->", color="c", lw=0.8),
            )

    ax_rej.legend(fontsize=8, loc="lower left")

    plt.tight_layout()
    Path(output_png).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(str(output_png), dpi=150, bbox_inches="tight")
    plt.close(fig)
    return str(output_png)


def plot_transient(
    filepath: str | Path,
    output_png: str | Path,
    title: str = "Transient (Slew Rate)",
    specs: Optional[dict] = None,
) -> str:
    """
    Generate a transient plot from the slew-rate waveform file.

    The TRAN waveform file contains 2 variables::

        wrdata ... v(srout) v(srin)

    where ``srout`` is the OTA output and ``srin`` is the pulse input.

    Args:
        filepath:   Path to ``*_waveform_TRAN.txt``.
        output_png: Destination PNG path.
        specs:      Optional dict with 'slew_rate_pos', 'slew_rate_neg'
                    for on-plot annotation.

    Returns:
        The output PNG path.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    time, ys = _parse_wrdata(filepath, n_vars=2)
    v_out = ys[0]   # v(srout) — OTA output
    v_in = ys[1]    # v(srin)  — pulse input

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(time * 1e6, v_in, "b-", linewidth=1, alpha=0.6, label="Input")
    ax.plot(time * 1e6, v_out, "r-", linewidth=1.5, label="Output")
    ax.set_xlabel("Time (\u00b5s)")
    ax.set_ylabel("Voltage (V)")
    ax.set_title(title)
    ax.grid(True, alpha=0.3)

    if specs:
        sr_pos = specs.get("slew_rate_pos")
        sr_neg = specs.get("slew_rate_neg")
        # Find the rising and falling edges to annotate
        dv = np.diff(v_out)
        dt = np.diff(time)
        slope = dv / dt  # V/s

        if sr_pos is not None:
            # Find the steepest positive slope region
            pos_idx = np.argmax(slope)
            t_rise = time[pos_idx] * 1e6  # µs
            v_rise = v_out[pos_idx]
            ax.annotate(
                f"SR+ = {sr_pos/1e6:.1f} MV/s",
                xy=(t_rise, v_rise),
                xytext=(t_rise + (time[-1] - time[0]) * 1e6 * 0.05, v_rise + 0.15),
                fontsize=9, fontweight="bold", color="darkgreen",
                arrowprops=dict(arrowstyle="->", color="darkgreen", lw=1.2),
                bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="darkgreen", alpha=0.85),
            )

        if sr_neg is not None:
            # Find the steepest negative slope region
            neg_idx = np.argmin(slope)
            t_fall = time[neg_idx] * 1e6  # µs
            v_fall = v_out[neg_idx]
            ax.annotate(
                f"SR\u2212 = {abs(sr_neg)/1e6:.1f} MV/s",
                xy=(t_fall, v_fall),
                xytext=(t_fall + (time[-1] - time[0]) * 1e6 * 0.05, v_fall - 0.15),
                fontsize=9, fontweight="bold", color="darkred",
                arrowprops=dict(arrowstyle="->", color="darkred", lw=1.2),
                bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="darkred", alpha=0.85),
            )

    ax.legend(fontsize=8)

    plt.tight_layout()
    Path(output_png).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(str(output_png), dpi=150, bbox_inches="tight")
    plt.close(fig)
    return str(output_png)


def plot_output_swing(
    filepath: str | Path,
    output_png: str | Path,
    title: str = "Output Swing (DC Sweep)",
    specs: Optional[dict] = None,
) -> str:
    """
    Generate an output-swing plot from the DC sweep waveform file.

    The SWING waveform file contains 2 variables::

        wrdata ... v(swout) v(swin)

    Args:
        filepath:   Path to ``*_waveform_SWING.txt``.
        output_png: Destination PNG path.
        specs:      Optional dict with 'vout_high', 'vout_low',
                    'output_swing' for on-plot annotation.

    Returns:
        The output PNG path.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    vin, ys = _parse_wrdata(filepath, n_vars=2)
    v_out = ys[0]   # V(swout) — DUT output
    v_inp = ys[1]   # V(swin)  — DUT input (= sweep variable)

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.plot(vin, v_out, "b-", linewidth=1.5, label="Vout vs Vin")
    ax.plot(vin, vin, "k--", linewidth=0.8, alpha=0.4, label="Vout = Vin (ideal)")
    ax.set_xlabel("Input Voltage (V)")
    ax.set_ylabel("Output Voltage (V)")
    ax.set_title(title)
    ax.grid(True, alpha=0.3)

    if specs:
        v_high = specs.get("vout_high")
        v_low = specs.get("vout_low")
        swing = specs.get("output_swing")
        if v_high is not None:
            ax.axhline(v_high, color="green", linewidth=0.8, linestyle=":")
            ax.annotate(
                f"Vout,max = {v_high:.3f} V",
                xy=(vin[0], v_high),
                xytext=(vin[0] + (vin[-1] - vin[0]) * 0.05, v_high + 0.06),
                fontsize=9, fontweight="bold", color="green",
                bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="green", alpha=0.85),
            )
        if v_low is not None:
            ax.axhline(v_low, color="red", linewidth=0.8, linestyle=":")
            ax.annotate(
                f"Vout,min = {v_low:.3f} V",
                xy=(vin[-1], v_low),
                xytext=(vin[0] + (vin[-1] - vin[0]) * 0.05, v_low - 0.08),
                fontsize=9, fontweight="bold", color="red",
                bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="red", alpha=0.85),
            )
        if swing is not None:
            ax.text(
                0.98, 0.5,
                f"Output Swing = {swing:.3f} V",
                transform=ax.transAxes, fontsize=10, fontweight="bold",
                color="purple", ha="right", va="center",
                bbox=dict(boxstyle="round,pad=0.4", fc="white", ec="purple", alpha=0.85),
            )

    ax.legend(fontsize=8)

    plt.tight_layout()
    Path(output_png).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(str(output_png), dpi=150, bbox_inches="tight")
    plt.close(fig)
    return str(output_png)


def plot_noise(
    filepath: str | Path,
    output_png: str | Path,
    title: str = "Input-Referred Noise Spectral Density",
    specs: Optional[dict] = None,
) -> str:
    """
    Generate an input-referred noise density plot from the noise waveform.

    The NOISE waveform file contains 1 variable::

        wrdata ... irn_spectrum

    The x-axis is frequency (Hz) and the y-axis is V/sqrt(Hz).

    Args:
        filepath:   Path to ``*_waveform_NOISE.txt``.
        output_png: Destination PNG path.
        specs:      Optional dict with 'integrated_input_noise',
                    'input_noise_density_spot' for annotation.

    Returns:
        The output PNG path.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    freq, ys = _parse_wrdata(filepath, n_vars=1)
    irn = ys[0]  # V/sqrt(Hz)

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.loglog(freq, irn, "b-", linewidth=1.5)
    ax.set_xlabel("Frequency (Hz)")
    ax.set_ylabel("Input-Referred Noise (V/\u221aHz)")
    ax.set_title(title)
    ax.grid(True, which="both", alpha=0.3)

    if specs:
        irn_int = specs.get("integrated_input_noise")
        irn_spot = specs.get("input_noise_density_spot")
        irn_1hz = specs.get("input_noise_density_1hz")

        # Annotate spot noise at 10 kHz with marker on curve
        if irn_spot is not None and len(freq) > 1:
            f_spot = 1e4  # 10 kHz
            irn_at_spot = np.interp(f_spot, freq, irn)
            ax.plot(f_spot, irn_at_spot, "ro", markersize=6, zorder=5)
            ax.annotate(
                f"Spot @10kHz = {irn_spot*1e9:.1f} nV/\u221aHz",
                xy=(f_spot, irn_at_spot),
                xytext=(f_spot * 10, irn_at_spot * 2),
                fontsize=9, fontweight="bold", color="red",
                arrowprops=dict(arrowstyle="->", color="red", lw=1.2),
                bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="red", alpha=0.85),
            )

        # Annotate 1/f noise at 1 Hz
        if irn_1hz is not None and len(freq) > 1:
            irn_at_1 = np.interp(1.0, freq, irn) if freq[0] <= 1.0 else irn[0]
            f_1hz = max(freq[0], 1.0)
            ax.plot(f_1hz, irn_at_1, "gs", markersize=6, zorder=5)
            ax.annotate(
                f"@1Hz = {irn_1hz*1e6:.1f} \u00b5V/\u221aHz",
                xy=(f_1hz, irn_at_1),
                xytext=(f_1hz * 30, irn_at_1 * 0.5),
                fontsize=9, fontweight="bold", color="green",
                arrowprops=dict(arrowstyle="->", color="green", lw=1.2),
                bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="green", alpha=0.85),
            )

        # Integrated noise as a text box
        if irn_int is not None:
            ax.text(
                0.98, 0.95,
                f"IRN(integrated) = {irn_int*1e6:.1f} \u00b5V rms",
                transform=ax.transAxes, fontsize=10, fontweight="bold",
                color="purple", ha="right", va="top",
                bbox=dict(boxstyle="round,pad=0.4", fc="white", ec="purple", alpha=0.85),
            )

    plt.tight_layout()
    Path(output_png).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(str(output_png), dpi=150, bbox_inches="tight")
    plt.close(fig)
    return str(output_png)


def _check_waveform_freshness(
    ac_filepath: Path, specs: dict, tol_dB: float = 1.0,
) -> None:
    """
    Verify that waveform AC data matches the scalar spec values.

    Compares the DC gain from the waveform file (first data point)
    against ``specs['dcgain_']``.  If they differ by more than *tol_dB*,
    the waveform file is stale (left over from a previous simulation)
    and the plots would be misleading.

    Raises:
        RuntimeError with instructions if stale data is detected.
    """
    dc_gain_spec = specs.get("dcgain_")
    if dc_gain_spec is None:
        return  # no reference value to check against

    try:
        data = np.loadtxt(ac_filepath, max_rows=1)
        dc_gain_waveform = data[1]  # second column = gain (dB) at lowest freq
    except Exception:
        return  # can't read — proceed without validation

    delta = abs(dc_gain_waveform - dc_gain_spec)
    if delta > tol_dB:
        raise RuntimeError(
            f"Stale waveform data detected: AC waveform DC gain = "
            f"{dc_gain_waveform:.1f} dB but specs report "
            f"{dc_gain_spec:.1f} dB (delta = {delta:.1f} dB > "
            f"{tol_dB:.0f} dB tolerance). The waveform file "
            f"'{ac_filepath.name}' is from a previous simulation run. "
            f"Re-run simulate_circuit(..., save_waveforms=True) before "
            f"calling generate_all_plots()."
        )


def generate_all_plots(
    topology_name: str,
    category: str = "nominal",
    specs: Optional[dict] = None,
    cc_output_dir: str | Path | None = None,
) -> list[str]:
    """
    Generate all available plots for a simulation run.

    Looks for waveform files in the CircuitCollector output directory,
    generates PNG plots, and saves them to ``simulation_waveform/<category>/``.
    Also copies the raw waveform text files so that text and PNG stay in sync.

    When *specs* is provided, the AC waveform is checked for freshness
    before plotting.  If the waveform DC gain disagrees with
    ``specs['dcgain_']`` by more than 1 dB, a ``RuntimeError`` is raised
    instructing the caller to re-run the simulation with
    ``save_waveforms=True``.

    Args:
        topology_name: e.g. 'tsm_single'
        category:      Subfolder (e.g. 'nominal', 'pvt_ss_85C')
        specs:         Simulation specs dict for annotation (from sim['specs'])
        cc_output_dir: Override source directory

    Returns:
        List of generated PNG file paths.
    """
    src_dir = Path(cc_output_dir) if cc_output_dir else _CC_ROOT / topology_name
    dst_dir = _WAVE_ROOT / category
    dst_dir.mkdir(parents=True, exist_ok=True)

    generated = []

    ac_file = src_dir / f"{topology_name}_waveform_AC.txt"
    if ac_file.exists():
        # Guard: reject stale waveforms before generating plots
        if specs:
            _check_waveform_freshness(ac_file, specs)
        png = plot_ac_bode(ac_file, dst_dir / f"{topology_name}_bode.png",
                           specs=specs)
        generated.append(png)

    tran_file = src_dir / f"{topology_name}_waveform_TRAN.txt"
    if tran_file.exists():
        png = plot_transient(tran_file, dst_dir / f"{topology_name}_transient.png",
                             specs=specs)
        generated.append(png)

    swing_file = src_dir / f"{topology_name}_waveform_SWING.txt"
    if swing_file.exists():
        png = plot_output_swing(swing_file, dst_dir / f"{topology_name}_swing.png",
                                specs=specs)
        generated.append(png)

    noise_file = src_dir / f"{topology_name}_waveform_NOISE.txt"
    if noise_file.exists():
        png = plot_noise(noise_file, dst_dir / f"{topology_name}_noise.png",
                         specs=specs)
        generated.append(png)

    # Copy raw waveform text files alongside the PNGs so they stay in sync
    for src_txt in src_dir.glob(f"{topology_name}_waveform_*.txt"):
        shutil.copy2(src_txt, dst_dir / src_txt.name)

    return generated
