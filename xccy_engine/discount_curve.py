"""
Discount curve: bootstrap from deposits, FRAs, and swap rates.

The curve maps time → discount factor D(t), the present value of $1 at time t.
All other quantities (zero rates, forward rates, derivative prices) are derived
from the discount curve.

Bootstrap order mirrors a real rates desk:
  1. Deposits  → short end  (direct formula, no iteration needed)
  2. FRAs      → medium end (D(t2) solved from D(t1) already on curve)
  3. Swaps     → long end   (D(T) solved sequentially from inner pillars)
"""
from __future__ import annotations

import numpy as np


class DiscountCurve:
    """
    Piecewise log-linear discount curve.

    Log-linear interpolation on discount factors is the market standard:
    discount factors are strictly positive and decay roughly exponentially,
    so interpolating log(D) linearly in time avoids the negative discount
    factors that naive linear interpolation can produce.
    """

    def __init__(self) -> None:
        # D(0) = 1 by definition — the value today of $1 received today is $1
        self._times:     list[float] = [0.0]
        self._discounts: list[float] = [1.0]

    # ── Curve building ────────────────────────────────────────────────────────

    def add_point(self, t: float, D: float) -> None:
        """Insert a (maturity, discount factor) pillar, keeping the list sorted."""
        self._times.append(t)
        self._discounts.append(D)
        order = list(np.argsort(self._times))
        self._times     = [self._times[i]     for i in order]
        self._discounts = [self._discounts[i] for i in order]

    # ── Queries ───────────────────────────────────────────────────────────────

    def discount(self, t: float) -> float:
        """
        Discount factor D(t) via log-linear interpolation.

        ln D(t) is interpolated linearly in t between the bracketing pillars,
        then exponentiated.  Between t=0 (ln D = 0) and the first pillar the
        curve is also log-linear, giving smooth behaviour.
        """
        log_d = np.interp(t, self._times, np.log(self._discounts))
        return float(np.exp(log_d))

    def zero_rate(self, t: float) -> float:
        """
        Continuously compounded zero rate r(t) defined by D(t) = e^{-r(t) * t}.

          r(t) = -ln D(t) / t
        """
        if t <= 0.0:
            return 0.0
        return float(-np.log(self.discount(t)) / t)

    def forward_rate(self, t1: float, t2: float) -> float:
        """
        Continuously compounded instantaneous forward rate for [t1, t2].

        No-arbitrage requires:
          D(t1) / D(t2) = e^{f(t1,t2) * (t2 - t1)}

        So:
          f(t1, t2) = ln(D(t1) / D(t2)) / (t2 - t1)

        This is the rate a bank would offer today to lock in borrowing
        for the period [t1, t2].
        """
        if not (t2 > t1 >= 0):
            raise ValueError(f"Need 0 <= t1 < t2, got t1={t1}, t2={t2}")
        D1 = self.discount(t1)
        D2 = self.discount(t2)
        return float(np.log(D1 / D2) / (t2 - t1))

    # ── Bootstrap from market instruments ────────────────────────────────────

    def bootstrap_deposits(self, rates: list[tuple[float, float]]) -> None:
        """
        Bootstrap the short end of the curve from deposit rates.

        Deposits have one cashflow (principal + interest at maturity), so
        the discount factor follows directly from simple-interest pricing:

          D(T) = 1 / (1 + r * T)

        Parameters
        ----------
        rates : list of (maturity_in_years, annualised_rate)
                e.g. [(0.25, 0.052), (0.5, 0.053), (1.0, 0.055)]
        """
        for T, r in rates:
            D = 1.0 / (1.0 + r * T)
            self.add_point(T, D)

    def bootstrap_fra(self, t1: float, t2: float, fra_rate: float) -> None:
        """
        Bootstrap D(t2) from D(t1) and an FRA rate.

        An FRA fixes the simple interest rate for [t1, t2].  No-arbitrage
        ties the FRA rate to the forward rate implied by the curve:

          D(t1) / D(t2) = 1 + fra_rate * (t2 - t1)

        Rearranging:
          D(t2) = D(t1) / (1 + fra_rate * tau)

        D(t1) must already be on the curve (bootstrapped from a shorter instrument).

        Parameters
        ----------
        t1, t2   : FRA period boundaries in years (e.g. 1.0, 1.5 for a 1x18 FRA)
        fra_rate : agreed forward rate (simple interest, e.g. 0.056)
        """
        D1  = self.discount(t1)
        tau = t2 - t1
        D2  = D1 / (1.0 + fra_rate * tau)
        self.add_point(t2, D2)

    def bootstrap_swap(self, T: float, swap_rate: float, freq: int = 1) -> None:
        """
        Bootstrap D(T) from a par swap rate (the real quant step).

        A par swap pays a fixed coupon c on notional N at each payment date,
        and receives floating.  At inception (fair value = 0):

          c * sum_{i=1}^{n} D(t_i) * dt  +  D(T)  =  1

        All D(t_i) for i < n must already be on the curve.  Solving for D(T):

          D(T) = (1  -  c * sum_{i<n} D(t_i) * dt) / (1 + c * dt)

        This is called sequential bootstrapping: the long-end discount factors
        are peeled off one maturity at a time from the swap curve.

        Parameters
        ----------
        T         : swap maturity in years
        swap_rate : par swap rate (e.g. 0.048 for 4.8%)
        freq      : coupon frequency (1=annual, 2=semi-annual)
        """
        c  = swap_rate
        dt = 1.0 / freq
        # all payment dates before T
        inner_times = np.arange(dt, T - 1e-9, dt)
        annuity_sum = sum(self.discount(t) * dt for t in inner_times)
        D_T = (1.0 - c * annuity_sum) / (1.0 + c * dt)
        self.add_point(T, D_T)

    # ── Curve output ──────────────────────────────────────────────────────────

    def sample(self, times: np.ndarray) -> dict:
        """
        Sample the curve at a grid of maturities.

        Returns dict with keys: 'times', 'discounts', 'zero_rates'.
        """
        discounts  = np.array([self.discount(t)  for t in times])
        zero_rates = np.array([self.zero_rate(t) for t in times])
        return {"times": times, "discounts": discounts, "zero_rates": zero_rates}
