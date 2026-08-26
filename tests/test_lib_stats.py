"""Tests for lib_stats.py — validated against ANALYTIC IDENTITIES, not tables.

A remembered table value can be wrong in the same direction as the code that
produced it, and nothing catches that. Every distribution function here has a
closed form at some parameter value; those closed forms are the oracle. The
round-trip tests then pin the inverses against the forward functions, so an
inverse cannot drift away from the CDF the rest of the kit uses.
"""
import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from lib_stats import (betai, chi2_sf, gamma_sf, norm_cdf, norm_ppf, norm_sf,  # noqa: E402
                       t_cdf, t_ppf, t_sf)


# ---------- normal ----------

def test_norm_cdf_is_symmetric_about_zero():
    assert norm_cdf(0.0) == pytest.approx(0.5, abs=1e-15)
    for x in (0.1, 0.7, 1.5, 2.6, 4.0):
        assert norm_cdf(-x) == pytest.approx(1.0 - norm_cdf(x), abs=1e-14)


def test_norm_sf_is_the_complement_of_the_cdf():
    for x in (-3.0, -0.4, 0.0, 1.1, 5.0):
        assert norm_sf(x) == pytest.approx(1.0 - norm_cdf(x), abs=1e-14)


def test_norm_ppf_round_trips_through_the_cdf():
    # The inverse must agree with the CDF the rest of the kit uses, to full
    # double precision — Acklam alone is only ~1e-9, hence the Halley step.
    for p in (1e-8, 0.001, 0.025, 0.1, 0.5, 0.9, 0.975, 0.999, 1 - 1e-8):
        assert norm_cdf(norm_ppf(p)) == pytest.approx(p, rel=1e-12, abs=1e-15)


def test_norm_ppf_is_antisymmetric():
    for p in (0.01, 0.2, 0.44):
        assert norm_ppf(p) == pytest.approx(-norm_ppf(1 - p), abs=1e-12)


def test_norm_ppf_rejects_probabilities_outside_the_open_unit_interval():
    for bad in (0.0, 1.0, -0.1, 1.5):
        with pytest.raises(ValueError):
            norm_ppf(bad)


def test_norm_ppf_survives_the_subnormal_tail_instead_of_overflowing():
    # The Halley step divides by the density, spelled exp(x²/2), which overflows
    # a double past |x| ≈ 37.7. A *refinement* step used to raise OverflowError
    # on inputs Acklam's approximation handles fine, so the far tail returned no
    # answer at all rather than a slightly less refined one.
    for p in (1e-300, 1e-308, 1e-310, 5e-324):
        z = norm_ppf(p)
        assert math.isfinite(z) and z < 0
    # Monotone across the guard boundary — the skip must not introduce a step.
    assert norm_ppf(5e-324) < norm_ppf(1e-310) < norm_ppf(1e-308) < norm_ppf(1e-300)


def test_norm_ppf_still_refines_everywhere_the_step_is_computable():
    # The bound is derived from log(DBL_MAX), not rounded down to a tidy 37: at
    # p = 1e-300 (|x| ≈ 37.03) the step computes perfectly well, and a lazy
    # threshold would have silently dropped that case to Acklam's ~1e-9.
    assert norm_cdf(norm_ppf(1e-300)) == pytest.approx(1e-300, rel=1e-9)


def test_the_conventional_95_percent_z_value():
    # Not an identity, but the single most consequential constant in the whole
    # meta-analysis path: every CI in the output is built from it.
    assert norm_ppf(0.975) == pytest.approx(1.959963984540054, abs=1e-12)


# ---------- chi-square ----------

def test_chi2_with_two_df_matches_its_closed_form():
    # A chi-square with 2 df is Exponential(1/2): P(X > x) = exp(-x/2) exactly.
    for x in (0.01, 0.5, 1.0, 3.0, 7.5, 20.0, 60.0):
        assert chi2_sf(x, 2) == pytest.approx(math.exp(-x / 2.0), rel=1e-12)


def test_chi2_with_one_df_matches_the_squared_normal():
    # X ~ chi2(1) is Z², so P(X > x) = 2 * P(Z > sqrt(x)) exactly.
    for x in (0.001, 0.25, 1.0, 3.841459, 10.0, 30.0):
        assert chi2_sf(x, 1) == pytest.approx(2.0 * norm_sf(math.sqrt(x)), rel=1e-11)


def test_chi2_with_four_df_matches_its_closed_form():
    # df = 4: P(X > x) = exp(-x/2) * (1 + x/2).
    for x in (0.1, 2.0, 9.488, 25.0):
        assert chi2_sf(x, 4) == pytest.approx(math.exp(-x / 2.0) * (1 + x / 2.0), rel=1e-12)


def test_chi2_sf_is_monotone_decreasing_and_bounded():
    prev = 1.0
    for x in (0.0, 0.5, 1.0, 2.0, 5.0, 12.0, 40.0):
        cur = chi2_sf(x, 6)
        assert 0.0 <= cur <= 1.0
        assert cur <= prev + 1e-15
        prev = cur


def test_chi2_sf_at_zero_is_one():
    for df in (1, 2, 5, 17):
        assert chi2_sf(0.0, df) == 1.0


def test_chi2_sf_rejects_a_nonpositive_df():
    with pytest.raises(ValueError):
        chi2_sf(1.0, 0)


def test_gamma_sf_matches_the_exponential_closed_form():
    # Q(1, x) = exp(-x) exactly.
    for x in (0.0, 0.3, 2.0, 11.0):
        assert gamma_sf(1.0, x) == pytest.approx(math.exp(-x), rel=1e-12, abs=1e-300)


def test_gamma_sf_agrees_across_its_two_branches():
    # The series and continued-fraction branches switch at x = a + 1; they must
    # meet without a step. A discontinuity here is invisible in normal use and
    # shows up as a wrong p-value only for particular Q values.
    a = 4.0
    left, right = gamma_sf(a, a + 1.0 - 1e-9), gamma_sf(a, a + 1.0 + 1e-9)
    # 1e-8 relative, not 1e-15: the two branches converge by different routes and
    # agree to ~1e-9, which is nine orders of magnitude finer than any p-value
    # this feeds. The test exists to catch a STEP, not to pin the last bit.
    assert left == pytest.approx(right, rel=1e-8)


# ---------- Student's t ----------

def test_t_with_one_df_matches_the_cauchy_closed_form():
    # t(1) is Cauchy: F(x) = 0.5 + atan(x)/pi exactly.
    for x in (-9.0, -1.0, 0.0, 0.5, 3.0, 40.0):
        assert t_cdf(x, 1) == pytest.approx(0.5 + math.atan(x) / math.pi, rel=1e-11,
                                            abs=1e-13)


def test_t_with_two_df_matches_its_closed_form():
    # F(x) = 0.5 * (1 + x / sqrt(x^2 + 2)).
    for x in (-5.0, -0.2, 0.0, 1.0, 6.0):
        assert t_cdf(x, 2) == pytest.approx(0.5 * (1 + x / math.sqrt(x * x + 2)),
                                            rel=1e-11, abs=1e-13)


def test_t_converges_to_the_normal_as_df_grows():
    for x in (-2.0, -0.5, 1.3, 2.8):
        assert t_cdf(x, 2_000_000) == pytest.approx(norm_cdf(x), abs=1e-6)


def test_t_cdf_is_symmetric():
    for x, df in ((0.4, 3), (2.0, 9), (5.0, 30)):
        assert t_cdf(-x, df) == pytest.approx(1.0 - t_cdf(x, df), abs=1e-13)


def test_t_sf_is_the_complement_of_the_cdf():
    for x, df in ((-1.0, 4), (0.0, 7), (2.5, 12)):
        assert t_sf(x, df) == pytest.approx(1.0 - t_cdf(x, df), abs=1e-13)


def test_t_ppf_round_trips_through_the_cdf():
    # The prediction interval lives in this tail; an inverse that disagrees with
    # its own CDF would widen or narrow it silently.
    for df in (1, 2, 3, 10, 47):
        for p in (0.005, 0.025, 0.25, 0.5, 0.9, 0.975, 0.995):
            assert t_cdf(t_ppf(p, df), df) == pytest.approx(p, abs=1e-11)


def test_t_ppf_is_antisymmetric():
    for df in (2, 8, 25):
        assert t_ppf(0.025, df) == pytest.approx(-t_ppf(0.975, df), abs=1e-9)


def test_t_ppf_rejects_probabilities_outside_the_open_unit_interval():
    for bad in (0.0, 1.0, 2.0):
        with pytest.raises(ValueError):
            t_ppf(bad, 5)


def test_t_quantiles_widen_as_df_shrinks():
    # The whole reason a prediction interval uses t rather than z.
    q = [t_ppf(0.975, df) for df in (2, 5, 10, 50, 1000, 10**7)]
    assert q == sorted(q, reverse=True)
    # t(1000) still sits ~2.4e-3 above z — a real difference, not error — so the
    # normal limit is checked at a df where the gap is genuinely negligible.
    assert q[-1] == pytest.approx(norm_ppf(0.975), abs=1e-5)


# ---------- incomplete beta ----------

def test_betai_is_the_identity_for_a_equals_b_equals_one():
    # I_x(1, 1) = x exactly (uniform distribution).
    for x in (0.0, 0.13, 0.5, 0.91, 1.0):
        assert betai(1.0, 1.0, x) == pytest.approx(x, abs=1e-13)


def test_betai_satisfies_the_symmetry_relation():
    # I_x(a, b) = 1 - I_{1-x}(b, a) exactly.
    for a, b, x in ((2.0, 3.0, 0.4), (0.5, 7.0, 0.15), (9.0, 1.5, 0.83)):
        assert betai(a, b, x) == pytest.approx(1.0 - betai(b, a, 1.0 - x), rel=1e-12)


def test_betai_is_bounded_at_the_endpoints():
    assert betai(3.0, 4.0, 0.0) == 0.0
    assert betai(3.0, 4.0, 1.0) == 1.0
