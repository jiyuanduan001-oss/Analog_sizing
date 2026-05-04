# LUT Parameter Derivation Template

## Purpose

Standard procedure to derive all small-signal parameters for a single
device from the gm/ID LUT. Called by the design flow once per role
during initial sizing.

---

## Inputs

| Input | Description |
|-------|-------------|
| `device_type` | `'nfet'` or `'pfet'` |
| `gm_id` | Target gm/ID operating point (S/A) |
| `L` | Channel length (µm) |
| `ID` | Drain current (A) — total current the device carries |
| `corner` | Process corner (e.g. `'tt'`) |
| `temp` | Temperature string (e.g. `'27C'`) |

---

## Procedure

Given (device_type, gm_id, L, ID, corner, temp), derive all parameters:

```
gm     = gm_id × ID

id_w   = lut_query(device_type, 'id_w',  L, corner=corner, temp=temp, gm_id_val=gm_id)   # A/m
W      = ID / id_w                                                                         # m (display as W×1e6 for µm)

gds    = gm / lut_query(device_type, 'gm_gds', L, corner=corner, temp=temp, gm_id_val=gm_id)
ft     = lut_query(device_type, 'ft',     L, corner=corner, temp=temp, gm_id_val=gm_id)    # Hz
vdsat  = lut_query(device_type, 'vdsat',  L, corner=corner, temp=temp, gm_id_val=gm_id)    # V

Cgs    = lut_query(device_type, 'cgs_w', L, corner=corner, temp=temp, gm_id_val=gm_id) × W  # F
Cgd    = lut_query(device_type, 'cgd_w', L, corner=corner, temp=temp, gm_id_val=gm_id) × W  # F
Cdb    = lut_query(device_type, 'cdb_w', L, corner=corner, temp=temp, gm_id_val=gm_id) × W  # F
```

## Units

- `id_w` is in A/m; `W = ID / id_w` gives meters (not µm)
- `cgs_w`, `cgd_w`, `cdb_w` are in F/m; multiply by W (in meters) directly — no extra 1e-6 factor
- `vdsat` is the BSIM4 |Vds|_sat (positive magnitude)

## Usage in Design Flow

Call this template for each device being sized. Example:

> Derive all parameters for **M3** (DIFF_PAIR, nfet) from LUT using
> `general/knowledge/lut-parameter-derivation.md` with:
> device_type='nfet', gm_id=(gm/ID)_3, L=L3, ID=ID3

For mirror devices (e.g. TAIL mirrors BIAS_GEN), derive per-finger
parameters using the unit-cell current `ID_finger = I_bias`, then
scale total quantities by the finger count M:
```
gm_total  = gm_finger × M
gds_total = gds_finger × M
Cgs_total = Cgs_finger × M
...
```
