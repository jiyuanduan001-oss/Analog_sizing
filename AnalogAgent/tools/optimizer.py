"""
Derivative-free numerical optimizer for analog circuit sizing.

Provides CMA-ES with coordinate-descent warmup for post-sizing optimization.
Called from the LLM via the numerical-optimization skill.

Usage:
    from tools.optimizer import coordinate_warmup, cma_es, make_batch_evaluator, compute_penalty
"""

import numpy as np
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Callable


# ---------------------------------------------------------------------------
# Penalty computation
# ---------------------------------------------------------------------------

def compute_penalty(
    specs: dict,
    targets: dict[str, tuple[str, float]],
    baseline_specs: Optional[dict] = None,
    objective_cost: float = 1.0,
    transistors: Optional[dict] = None,
) -> float:
    """
    Compute constraint penalty with dynamic scaling and asymmetric weighting.

    Specs that were PASSING in the baseline design receive 5x higher penalty
    weight if violated, preventing the optimizer from trading them away.

    Args:
        specs:          Current simulation results dict.
        targets:        {spec_name: (direction, value)} where direction is
                        '>=', '<=', or 'abs>=' (take abs before comparing).
        baseline_specs: Specs from the LLM-converged design. If provided,
                        enables asymmetric penalty for already-passing specs.
        objective_cost: Current objective value (for relative scaling).
        transistors:    Transistor OP dict from simulation. If provided,
                        adds saturation penalty for non-saturated devices.

    Returns:
        Total penalty value.
    """
    base_k = max(10.0, 10.0 * abs(objective_cost))
    total = 0.0

    for spec_name, (direction, target_val) in targets.items():
        achieved = specs.get(spec_name)
        if achieved is None:
            continue

        actual_dir = direction
        if direction == 'abs>=':
            achieved = abs(achieved)
            actual_dir = '>='

        # Compute normalized violation
        if actual_dir == '>=' and achieved < target_val:
            violation = (target_val - achieved) / abs(target_val)
        elif actual_dir == '<=' and achieved > target_val:
            violation = (achieved - target_val) / abs(target_val)
        else:
            continue  # constraint satisfied

        # Asymmetric multiplier: protect already-passing specs
        mult = 1.0
        if baseline_specs is not None:
            baseline_val = baseline_specs.get(spec_name)
            if baseline_val is not None:
                if direction == 'abs>=':
                    baseline_val = abs(baseline_val)
                was_passing = (
                    (actual_dir == '>=' and baseline_val >= target_val) or
                    (actual_dir == '<=' and baseline_val <= target_val)
                )
                if was_passing:
                    mult = 5.0

        total += base_k * mult * violation ** 2

    # Gain-plateau penalty (always active)
    gp = specs.get('gain_peaking_db', 0) or 0
    if gp > 0:
        total += 1e4 * gp ** 2

    # Saturation penalty
    if transistors is not None:
        for name, t in transistors.items():
            if abs(t.id) < 1e-12:
                continue
            margin = abs(t.vds) - abs(t.vgs - t.vth)
            if margin < 0:
                total += 1e6

    return total


# ---------------------------------------------------------------------------
# Coordinate-descent warmup
# ---------------------------------------------------------------------------

def coordinate_warmup(
    f_single: Callable,
    x0: np.ndarray,
    bounds_list: list[tuple[float, float]],
    int_indices: set[int],
    param_names: list[str],
    mirror_groups: dict[int, list[int]],
    n_workers: int = 16,
) -> dict:
    """
    Sweep each variable ±10% while keeping others at x0.

    Identifies which dimensions can be improved without breaking constraints,
    providing two inputs for CMA-ES:
      1. Feasible improving points to inject into generation 1
      2. Diagonal covariance prior (active dims = 1.0, sensitive = 0.01)

    Args:
        f_single:      Objective function (same signature as CMA-ES).
        x0:            Initial point (original scale).
        bounds_list:   [(lo, hi)] per dimension.
        int_indices:   Set of integer-variable indices.
        param_names:   Variable names (for logging).
        mirror_groups: {primary_idx: [mirror_idx, ...]} mapping integer
                       indices within ``param_names`` / ``x0``.  Use this
                       only when mirror variables are **included** in the
                       optimization variable list but should track their
                       primary during the sweep and inherit its
                       ``diag_scale``.  When mirror variables are already
                       **excluded** from the variable list (and enforced
                       inside the objective function instead), pass ``{}``.
        n_workers:     Parallel workers for ThreadPoolExecutor.

    Returns:
        dict with 'improving', 'diag_scale', 'f0'.
    """
    n = len(x0)
    lo = np.array([b[0] for b in bounds_list])
    hi = np.array([b[1] for b in bounds_list])
    delta = 0.10 * (hi - lo)

    # Validate mirror_groups: keys and values must be int indices into x0.
    for primary, mirrors in mirror_groups.items():
        if not isinstance(primary, int):
            raise TypeError(
                f"mirror_groups keys must be int indices into the variable "
                f"list, got {type(primary).__name__} ({primary!r}).  If "
                f"mirror variables are excluded from the optimization "
                f"variable list, pass mirror_groups={{}}."
            )
        for m in mirrors:
            if not isinstance(m, int):
                raise TypeError(
                    f"mirror_groups values must be lists of int indices, "
                    f"got {type(m).__name__} ({m!r}) under primary {primary}."
                )
            if m >= n:
                raise IndexError(
                    f"mirror index {m} is out of bounds for variable list "
                    f"of length {n}."
                )

    # Skip mirror target dims (they track their primary)
    mirror_targets = set()
    for mirrors in mirror_groups.values():
        mirror_targets.update(mirrors)

    candidates = []
    candidate_info = []
    for i in range(n):
        if i in mirror_targets:
            continue
        for sign in [+1, -1]:
            x_new = x0.copy()
            x_new[i] = np.clip(x0[i] + sign * delta[i], lo[i], hi[i])
            if i in int_indices:
                x_new[i] = max(lo[i], round(x_new[i]))
            if x_new[i] == x0[i]:
                continue
            candidates.append(x_new)
            candidate_info.append((i, sign))

    f0 = f_single(x0)
    print(f"  Warmup: x0 cost = {f0:.4f}", flush=True)

    print(f"  Evaluating {len(candidates)} warmup probes...", flush=True)
    with ThreadPoolExecutor(max_workers=n_workers) as pool:
        f_vals = list(pool.map(f_single, candidates))

    improving = []
    diag_scale = np.full(n, 0.01)

    for x_c, f_c, (dim_i, direction) in zip(candidates, f_vals, candidate_info):
        if f_c < f0:
            improving.append((x_c, f_c))
            diag_scale[dim_i] = 1.0
            print(f"  Warmup: {param_names[dim_i]:>16} "
                  f"{'+'if direction > 0 else '-'}10% → cost={f_c:.4f} "
                  f"(Δ={f_c - f0:+.4f}) ✅", flush=True)
        elif f_c < 1e8:
            diag_scale[dim_i] = max(diag_scale[dim_i], 0.3)

    for primary, mirrors in mirror_groups.items():
        for m in mirrors:
            diag_scale[m] = diag_scale[primary]

    print(f"  Warmup: {len(improving)} improving directions out of "
          f"{len(candidates)} probes", flush=True)

    return {'improving': improving, 'diag_scale': diag_scale, 'f0': f0}


# ---------------------------------------------------------------------------
# CMA-ES
# ---------------------------------------------------------------------------

def cma_es(
    f_batch: Callable,
    x0: np.ndarray,
    bounds: list[tuple[float, float]],
    int_params: set[int],
    sigma0: Optional[float] = None,
    max_gen: int = 20,
    lam: int = 16,
    n_workers: int = 16,
    warmup: Optional[dict] = None,
) -> dict:
    """
    CMA-ES with bound handling, warmup injection, and parallel batch eval.

    Args:
        f_batch:    function(list[array]) -> list[float].
        x0:         Initial mean (original scale).
        bounds:     [(lo, hi)] per dimension (original scale).
        int_params: Set of integer-variable indices.
        sigma0:     Initial step size. Default: 0.3/sqrt(n).
        max_gen:    Maximum generations.
        lam:        Population size.
        n_workers:  Concurrent workers (informational; parallelism is
                    handled by f_batch).
        warmup:     Dict from coordinate_warmup() with 'improving',
                    'diag_scale'. If provided, shapes C0 and injects
                    improving points into generation 1.

    Returns:
        dict with 'x' (best params), 'fun', 'nfev', 'ngen'.
    """
    n = len(x0)
    lo = np.array([b[0] for b in bounds], dtype=float)
    hi = np.array([b[1] for b in bounds], dtype=float)

    if sigma0 is None:
        sigma0 = 0.3 / np.sqrt(n)
        print(f"  σ₀ = 0.3/√{n} = {sigma0:.4f}", flush=True)

    def to_unit(x):
        return (x - lo) / (hi - lo)

    def from_unit(u):
        x = lo + u * (hi - lo)
        for i in int_params:
            x[i] = max(lo[i], round(x[i]))
        return np.clip(x, lo, hi)

    # CMA-ES hyperparameters
    mu = lam // 2
    weights = np.log(mu + 0.5) - np.log(np.arange(1, mu + 1))
    weights /= weights.sum()
    mu_eff = 1.0 / (weights ** 2).sum()

    c_sigma = (mu_eff + 2) / (n + mu_eff + 5)
    d_sigma = 1 + 2 * max(0, np.sqrt((mu_eff - 1) / (n + 1)) - 1) + c_sigma
    c_c = (4 + mu_eff / n) / (n + 4 + 2 * mu_eff / n)
    c_1 = 2 / ((n + 1.3) ** 2 + mu_eff)
    c_mu = min(1 - c_1, 2 * (mu_eff - 2 + 1 / mu_eff) / ((n + 2) ** 2 + mu_eff))
    chi_n = np.sqrt(n) * (1 - 1 / (4 * n) + 1 / (21 * n ** 2))

    # State
    mean = to_unit(x0)
    sigma = sigma0
    p_sigma = np.zeros(n)
    p_c = np.zeros(n)
    best_x = x0.copy()
    best_f = float('inf')
    n_evals = 0
    stagnation = 0

    # Covariance: shaped by warmup or identity
    if warmup is not None and 'diag_scale' in warmup:
        ds = warmup['diag_scale']
        C = np.diag(ds ** 2)
        print(f"  C₀ shaped: {int(np.sum(ds > 0.5))}/{n} active dims", flush=True)
    else:
        C = np.eye(n)

    for gen in range(max_gen):
        try:
            A = np.linalg.cholesky(C)
        except np.linalg.LinAlgError:
            C = np.eye(n)
            A = np.eye(n)

        z = np.random.randn(lam, n)
        y = z @ A.T
        pop_unit = mean + sigma * y

        # Gen 1: inject x0 and warmup improving points
        if gen == 0:
            pop_unit[0] = to_unit(x0)
            y[0] = (pop_unit[0] - mean) / max(sigma, 1e-12)
            if warmup is not None:
                for j, (x_imp, _) in enumerate(warmup.get('improving', [])):
                    slot = j + 1
                    if slot >= lam:
                        break
                    pop_unit[slot] = to_unit(x_imp)
                    y[slot] = (pop_unit[slot] - mean) / max(sigma, 1e-12)

        population = np.array([from_unit(np.clip(u, 0, 1)) for u in pop_unit])

        f_vals = f_batch(population)
        n_evals += lam

        order = np.argsort(f_vals)
        f_sorted = np.array(f_vals)[order]

        if f_sorted[0] < best_f:
            best_f = f_sorted[0]
            best_x = population[order[0]].copy()
            stagnation = 0
        else:
            stagnation += 1

        # Recombination
        y_sel = y[order[:mu]]
        y_w = weights @ y_sel
        mean = np.clip(mean + sigma * y_w, 0, 1)

        # Evolution paths
        try:
            C_inv_sqrt = np.linalg.inv(A)
        except np.linalg.LinAlgError:
            C_inv_sqrt = np.eye(n)

        p_sigma = ((1 - c_sigma) * p_sigma +
                   np.sqrt(c_sigma * (2 - c_sigma) * mu_eff) * (C_inv_sqrt @ y_w))
        h_sigma = (np.linalg.norm(p_sigma) /
                   np.sqrt(1 - (1 - c_sigma) ** (2 * (gen + 1))) <
                   (1.4 + 2 / (n + 1)) * chi_n)
        p_c = ((1 - c_c) * p_c +
               h_sigma * np.sqrt(c_c * (2 - c_c) * mu_eff) * y_w)

        # Covariance update
        rank_one = np.outer(p_c, p_c)
        rank_mu_mat = sum(w * np.outer(y_sel[i], y_sel[i])
                         for i, w in enumerate(weights))
        C = (1 - c_1 - c_mu) * C + c_1 * rank_one + c_mu * rank_mu_mat

        # Step-size adaptation
        sigma *= np.exp((c_sigma / d_sigma) *
                        (np.linalg.norm(p_sigma) / chi_n - 1))
        sigma = min(sigma, 0.5)

        print(f"  Gen {gen+1}/{max_gen}: best={best_f:.4f}, "
              f"gen_best={f_sorted[0]:.4f}, σ={sigma:.4f}, "
              f"evals={n_evals}, stag={stagnation}", flush=True)

        if sigma < 1e-6:
            break
        if stagnation >= 5:
            print(f"  Early stop: {stagnation} stagnant generations", flush=True)
            break

    return {'x': best_x, 'fun': best_f, 'nfev': n_evals, 'ngen': gen + 1}


# ---------------------------------------------------------------------------
# Batch evaluation helper
# ---------------------------------------------------------------------------

def make_batch_evaluator(f_single: Callable, n_workers: int = 16) -> Callable:
    """Wrap a single-point objective into a parallel batch evaluator."""
    def f_batch(population):
        with ThreadPoolExecutor(max_workers=n_workers) as pool:
            return list(pool.map(f_single, population))
    return f_batch
