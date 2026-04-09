"""
Cashflow generation for both legs of the cross-currency swap.

USD leg  — fixed rate (receive):
  CF(ti) = N_USD × coupon × dt    for coupon periods
  CF(T)  += N_USD                  principal returned at maturity

AUD leg  — floating BBSW + basis (pay):
  CF(ti) = N_AUD × (BBSW_fwd(t_{i-1}, ti) + basis) × dt
  CF(T)  += N_AUD                  principal returned at maturity

The BBSW forward rate is extracted from the AUD discount curve:
  BBSW_fwd_simple = (exp(f_cont × dt) − 1) / dt
  where f_cont = aud_curve.forward_rate(t_{i-1}, ti)

Using simple-rate conversion is more accurate than using the continuously
compounded rate directly, especially for longer accrual periods.
"""

from __future__ import annotations

import numpy as np
from .discount_curve import DiscountCurve


def generate_schedule(tenor: float, freq: int) -> list[float]:
    """
    Payment schedule as a list of year fractions.

    Parameters
    ----------
    tenor : swap tenor in years (e.g. 5.0)
    freq  : payments per year (e.g. 2 for semi-annual)

    Returns
    -------
    list[float] : [dt, 2*dt, ..., tenor]  where dt = 1/freq
    """
    dt = 1.0 / freq
    n  = int(round(tenor * freq))
    return [round(dt * i, 10) for i in range(1, n + 1)]


def usd_cashflows(
    schedule: list[float],
    notional: float,
    coupon:   float,
) -> list[tuple[float, float]]:
    """
    USD fixed-leg cashflows (received by Australia).

    Parameters
    ----------
    schedule : list of payment dates (year fractions)
    notional : USD notional (e.g. 5e9)
    coupon   : annual coupon rate (e.g. 0.045 for 4.50%)

    Returns
    -------
    list of (t, cashflow) pairs; principal included at maturity
    """
    dt  = schedule[0]         # constant time step
    cfs = []
    for i, t in enumerate(schedule):
        cf = notional * coupon * dt
        if i == len(schedule) - 1:
            cf += notional    # principal repayment at maturity
        cfs.append((t, cf))
    return cfs


def aud_cashflows(
    schedule:  list[float],
    notional:  float,
    aud_curve: DiscountCurve,
    basis:     float,
) -> list[tuple[float, float]]:
    """
    AUD floating-leg cashflows (paid by Australia).

    Floating rate = BBSW forward + cross-currency basis.

    Parameters
    ----------
    schedule  : list of payment dates (year fractions)
    notional  : AUD notional (e.g. 7.75e9)
    aud_curve : bootstrapped AUD discount curve
    basis     : cross-currency basis spread (e.g. -0.0025 for −25bp)

    Returns
    -------
    list of (t, cashflow) pairs; principal included at maturity
    """
    cfs    = []
    prev_t = 0.0
    for i, t in enumerate(schedule):
        dt = t - prev_t
        # Continuously compounded forward rate over [prev_t, t]
        f_cont = aud_curve.forward_rate(prev_t, t)
        # Convert to simple interest rate (used in money market conventions)
        bbsw_simple = (np.exp(f_cont * dt) - 1.0) / dt
        # Floating coupon = (BBSW + basis) × dt × notional
        cf = notional * (bbsw_simple + basis) * dt
        if i == len(schedule) - 1:
            cf += notional    # principal repayment at maturity
        cfs.append((t, cf))
        prev_t = t
    return cfs
