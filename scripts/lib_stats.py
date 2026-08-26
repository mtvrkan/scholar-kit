#!/usr/bin/env python3
"""lib_stats.py — the distribution functions meta_analysis.py needs, in pure Python.

Imported by siblings, never invoked directly.

The kit's runtime dependencies are `requests openpyxl rapidfuzz python-docx
pymupdf4llm`. Adding SciPy — a ~90 MB compiled scientific stack — so that one
script can call three CDFs would be a poor trade for users who mostly do not run
meta-analyses, and would make the kit fail to install wherever a wheel is
missing. These are the standard algorithms (Acklam's normal inverse, Numerical
Recipes' incomplete gamma and beta), which is exactly why they are safe to write
out: they are textbook, fixed, and — the reason this file is testable at all —
checkable against *analytic identities* rather than against remembered table
values:

    chi2_sf(x, df=2)  == exp(-x/2)                exactly
    chi2_sf(x, df=1)  == 2 * (1 - norm_cdf(√x))   exactly
    t_cdf(x, df=1)    == 0.5 + atan(x)/π          exactly (Cauchy)
    norm_cdf(norm_ppf(p)) == p                    round trip

`tests/test_lib_stats.py` asserts each of those. A remembered table value can be
wrong in the same direction as the code; an identity cannot.
"""
from __future__ import annotations

import math
import random
import sys

_MAXIT = 300
_EPS = 3.0e-16
_FPMIN = 1e-300


# ---------- normal ----------

def norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def norm_sf(x: float) -> float:
    return 0.5 * math.erfc(x / math.sqrt(2.0))


# Acklam's rational approximation, refined by one Halley step against erfc so the
# result is accurate to full double precision rather than Acklam's ~1.15e-9.
_A = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
      1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
_B = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
      6.680131188771972e+01, -1.328068155288572e+01]
_C = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
      -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
_D = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
      3.754408661907416e+00]
_P_LOW = 0.02425
# log of the largest finite double: the exact point past which math.exp() raises.
_LOG_DBL_MAX = math.log(sys.float_info.max)


def norm_ppf(p: float) -> float:
    """Inverse standard normal CDF."""
    if not 0.0 < p < 1.0:
        raise ValueError(f"norm_ppf needs 0 < p < 1, got {p}")
    if p < _P_LOW:
        q = math.sqrt(-2 * math.log(p))
        x = (((((_C[0] * q + _C[1]) * q + _C[2]) * q + _C[3]) * q + _C[4]) * q + _C[5]) / \
            ((((_D[0] * q + _D[1]) * q + _D[2]) * q + _D[3]) * q + 1)
    elif p <= 1 - _P_LOW:
        q = p - 0.5
        r = q * q
        x = (((((_A[0] * r + _A[1]) * r + _A[2]) * r + _A[3]) * r + _A[4]) * r + _A[5]) * q / \
            (((((_B[0] * r + _B[1]) * r + _B[2]) * r + _B[3]) * r + _B[4]) * r + 1)
    else:
        q = math.sqrt(-2 * math.log(1 - p))
        x = -(((((_C[0] * q + _C[1]) * q + _C[2]) * q + _C[3]) * q + _C[4]) * q + _C[5]) / \
            ((((_D[0] * q + _D[1]) * q + _D[2]) * q + _D[3]) * q + 1)
    # One Halley refinement step, skipped where it cannot be computed. The step
    # divides the CDF error by the density and spells that as `exp(x²/2)`, which
    # overflows a double once x²/2 passes log(DBL_MAX) ≈ 709.78 — so p below
    # ~1e-308 used to raise OverflowError out of a *refinement* step, on inputs
    # Acklam's approximation itself handles fine. The bound is derived rather
    # than rounded off to a tidy 37, because 37 would also skip the refinement
    # for p = 1e-300 (|x| ≈ 37.03), which computes perfectly well and is inside
    # the range a small Egger p-value can reach. Beyond the bound the raw
    # approximation stands at its ~1e-9 relative accuracy, which is the answer
    # that exists out there.
    if x * x / 2.0 > _LOG_DBL_MAX:
        return x
    e = norm_cdf(x) - p
    u = e * math.sqrt(2 * math.pi) * math.exp(x * x / 2)
    return x - u / (1 + x * u / 2)


# ---------- incomplete gamma -> chi-square ----------

def _gser(a: float, x: float) -> float:
    """Regularized lower incomplete gamma P(a, x) by series expansion."""
    ap, total, delta = a, 1.0 / a, 1.0 / a
    for _ in range(_MAXIT):
        ap += 1
        delta *= x / ap
        total += delta
        if abs(delta) < abs(total) * _EPS:
            break
    return total * math.exp(-x + a * math.log(x) - math.lgamma(a))


def _gcf(a: float, x: float) -> float:
    """Regularized upper incomplete gamma Q(a, x) by continued fraction."""
    b, c = x + 1.0 - a, 1.0 / _FPMIN
    d = 1.0 / b
    h = d
    for i in range(1, _MAXIT + 1):
        an = -i * (i - a)
        b += 2.0
        d = an * d + b
        if abs(d) < _FPMIN:
            d = _FPMIN
        c = b + an / c
        if abs(c) < _FPMIN:
            c = _FPMIN
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < _EPS:
            break
    return math.exp(-x + a * math.log(x) - math.lgamma(a)) * h


def gamma_sf(a: float, x: float) -> float:
    """Regularized upper incomplete gamma Q(a, x) = 1 - P(a, x)."""
    if x < 0 or a <= 0:
        raise ValueError("gamma_sf needs x >= 0 and a > 0")
    if x == 0:
        return 1.0
    return 1.0 - _gser(a, x) if x < a + 1.0 else _gcf(a, x)


def chi2_sf(x: float, df: int) -> float:
    """P(X > x) for a chi-square with `df` degrees of freedom."""
    if df <= 0:
        raise ValueError("chi2_sf needs df >= 1")
    if x <= 0:
        return 1.0
    return gamma_sf(df / 2.0, x / 2.0)


# ---------- incomplete beta -> Student's t ----------

def _betacf(a: float, b: float, x: float) -> float:
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < _FPMIN:
        d = _FPMIN
    d = 1.0 / d
    h = d
    for m in range(1, _MAXIT + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < _FPMIN:
            d = _FPMIN
        c = 1.0 + aa / c
        if abs(c) < _FPMIN:
            c = _FPMIN
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < _FPMIN:
            d = _FPMIN
        c = 1.0 + aa / c
        if abs(c) < _FPMIN:
            c = _FPMIN
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < _EPS:
            break
    return h


def betai(a: float, b: float, x: float) -> float:
    """Regularized incomplete beta I_x(a, b)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    front = math.exp(math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
                     + a * math.log(x) + b * math.log(1.0 - x))
    if x < (a + 1.0) / (a + b + 2.0):
        return front * _betacf(a, b, x) / a
    return 1.0 - front * _betacf(b, a, 1.0 - x) / b


def t_cdf(x: float, df: float) -> float:
    """P(T <= x) for Student's t with `df` degrees of freedom."""
    if df <= 0:
        raise ValueError("t_cdf needs df > 0")
    p = 0.5 * betai(df / 2.0, 0.5, df / (df + x * x))
    return 1.0 - p if x > 0 else p


def t_sf(x: float, df: float) -> float:
    return 1.0 - t_cdf(x, df)


def bootstrap_ci(items: list, metric, resamples: int = 1000,
                 seed: int = 20260812) -> tuple | None:
    """Percentile 95% CI for `metric` over a resampled list of observations.

    Lives here rather than in either caller because two scripts now report
    bootstrap intervals — `calibration_score.py` over (gold, predicted) verdict
    pairs and `screening_score.py` over screening decisions — and a CI that is
    computed two slightly different ways in two places is two different claims
    wearing one name.

    `seed` is fixed by default so a reported interval is reproducible rather
    than redrawn on every run: a CI that moves when nothing changed teaches the
    reader to discount it.

    Returns None when the metric is undefined in more than half the resamples —
    an interval built mostly from the draws where the quantity existed is not an
    interval for the quantity, and printing one would be worse than printing
    nothing.
    """
    if not items:
        return None
    rng = random.Random(seed)
    draws = []
    for _ in range(resamples):
        sample = [items[rng.randrange(len(items))] for _ in range(len(items))]
        val = metric(sample)
        if val is not None:
            draws.append(val)
    if len(draws) < resamples // 2:
        return None
    draws.sort()
    lo = draws[int(0.025 * (len(draws) - 1))]
    hi = draws[int(0.975 * (len(draws) - 1))]
    return round(lo, 4), round(hi, 4)


def cohen_kappa(pairs: list[tuple[bool, bool]]) -> float | None:
    """Cohen's κ for two binary raters over (rater_a, rater_b) observations.

    The agreement statistic a systematic review is expected to report for its
    screening step, and the reason it is κ rather than raw agreement: at a 5%
    inclusion rate a screener that excludes everything agrees with the human on
    95% of records while finding nothing. κ subtracts the agreement expected by
    chance, so that screener scores 0.

    Returns None when either rater's marginal is degenerate (one rater used a
    single class). κ's chance-agreement term is then 1, the definition divides
    by zero, and the convention of reporting 0 would be indistinguishable from a
    measured, genuine disagreement.
    """
    n = len(pairs)
    if not n:
        return None
    a_pos = sum(1 for a, _ in pairs if a)
    b_pos = sum(1 for _, b in pairs if b)
    if a_pos in (0, n) or b_pos in (0, n):
        return None
    observed = sum(1 for a, b in pairs if a == b) / n
    expected = (a_pos / n) * (b_pos / n) + ((n - a_pos) / n) * ((n - b_pos) / n)
    if expected >= 1.0:
        return None
    return (observed - expected) / (1.0 - expected)


def t_ppf(p: float, df: float) -> float:
    """Inverse Student's t CDF, by bisection on t_cdf.

    Bisection rather than a closed form: t_cdf is monotone and cheap, 200
    iterations bracket the answer to well under 1e-12, and the result is
    guaranteed consistent with the CDF used everywhere else in this file — an
    approximation formula could disagree with it in the tail, which is precisely
    where prediction intervals live.
    """
    if not 0.0 < p < 1.0:
        raise ValueError(f"t_ppf needs 0 < p < 1, got {p}")
    lo, hi = -1e4, 1e4
    for _ in range(200):
        mid = (lo + hi) / 2.0
        if t_cdf(mid, df) < p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0
