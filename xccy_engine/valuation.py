"""
Mark-to-market valuation for the cross-currency swap.

    MTM_AUD = PV_USD × FX_spot − PV_AUD

where:
  PV_USD = Σ CF_USD(t_i) × DF_USD(t_i)   [USD fixed leg discounted on USD curve]
  PV_AUD = Σ CF_AUD(t_i) × DF_AUD(t_i)   [AUD float leg discounted on AUD curve]

At inception with at-market rates, MTM ≈ 0 (the swap has zero fair value on day one).
"""

from __future__ import annotations

from .discount_curve import DiscountCurve
from .cashflows import generate_schedule, usd_cashflows, aud_cashflows


def pv_leg(cashflows: list[tuple[float, float]], curve: DiscountCurve) -> float:
    """
    Present value of a cashflow leg.

    Parameters
    ----------
    cashflows : list of (t, CF) — maturity in years and cashflow amount
    curve     : discount curve matching the cashflow currency

    Returns
    -------
    float : PV = Σ CF × DF(t)
    """
    return sum(cf * curve.discount(t) for t, cf in cashflows)


def mtm_ccs(
    usd_curve: DiscountCurve,
    aud_curve: DiscountCurve,
    fx_spot:   float,
    N_USD:     float,
    coupon:    float,
    tenor:     float,
    freq:      int,
    basis:     float,
) -> float:
    """
    Full mark-to-market of the cross-currency swap in AUD.

    Australia's perspective: receive USD fixed, pay AUD floating BBSW + basis.

    Parameters
    ----------
    usd_curve : USD discount curve
    aud_curve : AUD discount curve
    fx_spot   : AUD per USD (e.g. 1.55)
    N_USD     : USD notional
    coupon    : USD fixed coupon (annual rate, e.g. 0.045)
    tenor     : swap tenor in years
    freq      : coupon frequency (2 = semi-annual)
    basis     : cross-currency basis (e.g. -0.0025 for −25bp)

    Returns
    -------
    float : MTM in AUD (positive = gain for Australia)
    """
    N_AUD    = N_USD * fx_spot
    schedule = generate_schedule(tenor, freq)

    usd_cfs = usd_cashflows(schedule, N_USD, coupon)
    aud_cfs = aud_cashflows(schedule, N_AUD, aud_curve, basis)

    pv_usd = pv_leg(usd_cfs, usd_curve)
    pv_aud = pv_leg(aud_cfs, aud_curve)

    return pv_usd * fx_spot - pv_aud
