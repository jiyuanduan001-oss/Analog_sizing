# Numerical Optimization Skill

## Purpose

After the LLM-driven sizing flow converges (design review complete),
this skill further optimizes the design using a derivative-free
numerical optimizer. It treats the simulator as a black-box function
and searches the design space to minimize power while maximizing gain
and GBW, subject to all user-specified constraints.

## When to Invoke

Only when `Optimize = yes` in the validated spec form. Invoked **after**
the design review (Stage [6]), including Extreme PVT if enabled.

## Prerequisites

The following must be available from the completed design flow:
- `params` dict and `config_path` from the final converged simulation
- `corner` and `temperature` from the validated spec form
- All user targets from the validated spec form
- The converged simulation specs (`baseline_specs`) for asymmetric
  penalty computation
- **Optimization weights** (`w_pwr`, `w_gain`, `w_gbw`) from user
  priority selection (see `design-review.md` Step 4a)

---

## Procedure

### Step 1 — Identify Optimization Variables

Extract all tunable parameters from the `params` dict:

| Suffix / Key  | Type       | Bounds                        |
|---------------|------------|-------------------------------|
| `*_L`         | continuous | [0.15, 5.0] um                |
| `*_WL_ratio`  | continuous | device-dependent min to 10.0  |
| `*_M`         | integer    | [1, 100]                      |
| `C1_value`    | continuous | [0.1pF, 20pF]                 |
| `Rc_value`    | continuous | [100, 100k] ohm               |
| `ibias`       | continuous | [1uA, 100uA]                  |

`*_L` and `*_WL_ratio` MUST be included — gain is primarily controlled
by device lengths (intrinsic gain gm/gds scales with L).

Integer variables (`*_M`) are rounded after each optimizer step.

The LLM-converged `params` dict provides the initial point `x0`.

**Mirror constraints:** Devices sharing W/L (e.g., M5/M6/M8 in TSM)
must be enforced inside the objective function by copying the primary's
L and WL_ratio to its mirrors. **Exclude** mirror L and WL_ratio from
`param_names` (only the primary's L/WL_ratio appear as opt variables;
each mirror's `_M` is still an independent variable). Because mirror
dimensions are excluded, pass `mirror_groups={}` to the warmup and
optimizer — there are no in-list mirrors to track. The `mirror_groups`
argument accepts `{primary_idx: [mirror_idx, ...]}` with **integer
indices** into the variable list; passing string keys will raise
`TypeError`.

**Initial step size:** `sigma0 = 0.3 / sqrt(n)` where n = number of
variables. Scales with dimensionality for consistent perturbation.

**Population and generations:** lambda=16 (parallel capacity), max_gen=20,
early stop after 5 stagnant generations.

### Step 2 — Define Objective and Constraints

**Objective (minimize):**

```
cost = w_pwr  * (Power / Power_ref)
     - w_gain * (Gain_linear / Gain_ref_linear)
     - w_gbw  * (GBW / GBW_ref)
```

**IMPORTANT:** Gain MUST be in linear scale (V/V), not dB.
`Gain_linear = 10^(Gain_dB / 20)`.

Where `*_ref` are the values from the LLM-converged simulation.

Weights are set by user priority:

| Priority | w_pwr | w_gain | w_gbw |
|----------|-------|--------|-------|
| Power    | 1.0   | 0.15   | 0.15  |
| Gain     | 0.15  | 1.0    | 0.15  |
| GBW      | 0.15  | 0.15   | 1.0   |

**Constraints (asymmetric penalty via `tools.optimizer.compute_penalty`):**

Every user-specified active target is an inequality constraint. The
penalty function uses two key improvements over a naive fixed-k approach:

1. **Dynamic scaling:** `k = 10 * max(|objective_cost|, 1.0)` ensures
   penalties dominate the objective when constraints are violated,
   regardless of the design's absolute power/gain/GBW levels.

2. **Asymmetric protection:** Specs that were PASSING in the LLM
   baseline (`baseline_specs`) receive a 5x penalty multiplier if
   violated. This prevents the optimizer from trading away already-met
   specs to improve one metric.

Additional mandatory penalties:
- Gain-plateau: `1e4 * max(0, gain_peaking_dB)^2`
- Saturation: `+1e6` per non-saturated device

### Step 3 — Build the Objective Function

```python
from tools.optimizer import compute_penalty
import tempfile

def f(x):
    params = dict(zip(param_names, x))
    for k in params:
        if k.endswith('_M'):
            params[k] = max(1, round(params[k]))

    # Enforce mirror constraints (topology-specific)
    # e.g., params['M6_L'] = params['M5_L']

    sim = simulate_circuit(
        params, config_path=config_path,
        corner=corner, temperature=temperature,
        supply_voltage=VDD, CL=CL,
        output_dir=tempfile.mkdtemp(),
    )
    specs = sim['specs']

    gain_linear = 10 ** (specs['dcgain_'] / 20)
    cost = (w_pwr * specs['power'] / power_ref
            - w_gain * gain_linear / gain_ref_linear
            - w_gbw * specs['gain_bandwidth_product_'] / gbw_ref)

    penalty = compute_penalty(
        specs=specs,
        targets=targets,
        baseline_specs=baseline_specs,
        objective_cost=cost,
        transistors=sim['transistors'],
    )
    return cost + penalty
```

Each `simulate_circuit` call uses a unique `output_dir` (tempfile)
to enable parallel evaluation without file-path conflicts.

**IMPORTANT:** `corner`, `temperature`, `supply_voltage` (VDD), and `CL` MUST
come from the validated spec form (Stage [1]). These are the same values used
for LUT queries and analytical sizing. Omitting them causes the simulator to
fall back to TOML defaults (typically tt/27°C/1.8V/5pF), creating a mismatch
between the LUT-based sizing and the SPICE verification. The `CL` parameter
accepts **Farads** (SI); the bridge converts to picoFarads internally for
CircuitCollector.

### Step 3b — Coordinate-Descent Warmup (mandatory)

Before CMA-ES, sweep each variable +/-10% to identify improvable
dimensions. This provides a shaped covariance prior for CMA-ES.

```python
from tools.optimizer import coordinate_warmup

warmup = coordinate_warmup(
    f_single=f,
    x0=x0,
    bounds_list=bounds,
    int_indices=int_indices,
    param_names=param_names,
    mirror_groups=mirror_groups,
    n_workers=16,
)
```

Returns:
- `improving`: list of (x, cost) better than x0
- `diag_scale`: per-dim scale for C0 (1.0 = active, 0.01 = suppress)
- `f0`: baseline cost

### Step 4 — Run the Optimizer

```python
from tools.optimizer import cma_es, make_batch_evaluator

f_batch = make_batch_evaluator(f, n_workers=16)
result = cma_es(
    f_batch=f_batch,
    x0=x0,
    bounds=bounds,
    int_params=int_indices,
    max_gen=20,
    lam=16,
    n_workers=16,
    warmup=warmup,
)
best_params = dict(zip(param_names, result['x']))
```

**Why CMA-ES:**

| Method | Evals (N=10) | Coupling | Parallelism |
|--------|-------------|----------|-------------|
| Coordinate search | 50-80 | No | No |
| Nelder-Mead | 100-200 | Partial | No |
| CMA-ES | 80-160 | **Yes** (covariance) | **Yes** (population) |
| Bayesian Opt | 30-50 | Yes (GP) | Limited |

CMA-ES learns correlated directions (e.g., Rc-Cc-gm7 coupling) and
evaluates each generation in parallel. With lambda=16 and ~10 gen,
total ~160 sims. At 16-way parallelism: ~2 min wall-clock.

**Runtime estimate:** ~34 warmup probes + 20 generations x 16 = 354
total sims. With 16-way parallelism and ~12s/batch, wall-clock ~13 min
(less with early stopping).

### Step 5 — Post-Optimization Verification

After convergence:

1. Run `simulate_circuit` with the optimized `params` one final time.
2. Verify ALL constraints are satisfied.
3. If any constraint is violated by more than 1%:
   - Increase penalty weight (`k *= 10`)
   - Re-run for 5 more generations from the current best.

### Step 6 — Return Results

**MANDATORY: Always print the full optimization results table** (Section
6 of the design review) before returning, regardless of whether the
optimizer improved the design. This includes: the spec comparison table
(LLM vs optimized), parameter changes, and the pass/fail count. This
lets the user see exactly what the optimizer tried and why it did or
did not help.

Return to `design-review.md` Step 4:

- `optimized_params`: the optimized `params` dict
- `optimized_specs`: simulation specs from final verification
- `llm_specs` / `baseline_specs`: reference specs from LLM design
- `n_evals`: total simulation calls (`result['nfev']`)
- `n_gen`: generations run (`result['ngen']`)
- `best_cost`: final cost (`result['fun']`)
- `runtime_s`: elapsed time in seconds
- `improved`: boolean — whether optimized cost < LLM cost AND
  optimized design meets at least as many specs as LLM

**CMA-ES return dict keys** (from `tools.optimizer.cma_es`):
- `result['x']` — best parameter vector
- `result['fun']` — best objective value
- `result['nfev']` — total function evaluations
- `result['ngen']` — number of generations run

If the optimized design meets **fewer** specs than the LLM sizing, set
`improved = False` and keep the LLM sizing as the final design.

---

## Notes

- **Simulation budget**: ~354 calls (34 warmup + 320 CMA-ES). With
  16-way parallelism, wall-clock ~13 min (less with early stopping).
- **Topology agnostic**: works at the `params` dict level. Does not
  need gm/ID methodology or circuit equations.
- **Variable coupling**: CMA-ES adapts a covariance matrix that learns
  which variables move together. No explicit coupling equations needed.
- **Local optimization**: the LLM starting point is already a good
  solution; CMA-ES explores a neighborhood (sigma = 0.3/sqrt(n)).
- **Implementation**: all optimizer code is in `tools/optimizer.py`.
  Functions: `coordinate_warmup`, `cma_es`, `make_batch_evaluator`,
  `compute_penalty`.
