"""
Risk sensitivities for the cross-currency swap.

DV01 (Dollar Value of a Basis Point)
--------------------------------------
Change in MTM (AUD) for a +1bp parallel shift of one yield curve.

  DV01_USD = MTM(usd_curve + 1bp, aud_curve) − MTM(base)
  DV01_AUD = MTM(usd_curve, aud_curve + 1bp) − MTM(base)

FX Delta
---------
Change in MTM (AUD) per 1% appreciation of the USD vs AUD.

  FX_delta = MTM(spot × 1.01) − MTM(spot)

Scenario Grid
-------------
3D PnL surface: USD curve shift × AUD curve shift, repeated for each FX move.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .discount_curve import DiscountCurve
from .valuation import mtm_ccs


def shift_curve(curve: DiscountCurve, bps: float) -> DiscountCurve:
    """
    Return a new DiscountCurve with all zero rates shifted by `bps` basis points.

    D_shifted(t) = exp(−(r(t) + shift) × t)

    Parameters
    ----------
    curve : original discount curve
    bps   : parallel shift in basis points (positive = rates rise)
    """
    shift   = bps / 10_000.0
    shifted = DiscountCurve()
    for t, D in zip(curve._times[1:], curve._discounts[1:]):
        r = -np.log(D) / t
        shifted.add_point(t, float(np.exp(-(r + shift) * t)))
    return shifted


def dv01_usd(
    usd_curve: DiscountCurve,
    aud_curve: DiscountCurve,
    fx_spot:   float,
    N_USD:     float,
    coupon:    float,
    tenor:     float,
    freq:      int,
    basis:     float,
) -> float:
    """DV01 with respect to the USD curve (MTM change per +1bp USD rates)."""
    kwargs = dict(aud_curve=aud_curve, fx_spot=fx_spot, N_USD=N_USD,
                  coupon=coupon, tenor=tenor, freq=freq, basis=basis)
    base   = mtm_ccs(usd_curve,              **kwargs)
    bumped = mtm_ccs(shift_curve(usd_curve, 1), **kwargs)
    return bumped - base


def dv01_aud(
    usd_curve: DiscountCurve,
    aud_curve: DiscountCurve,
    fx_spot:   float,
    N_USD:     float,
    coupon:    float,
    tenor:     float,
    freq:      int,
    basis:     float,
) -> float:
    """DV01 with respect to the AUD curve (MTM change per +1bp AUD rates)."""
    kwargs = dict(usd_curve=usd_curve, fx_spot=fx_spot, N_USD=N_USD,
                  coupon=coupon, tenor=tenor, freq=freq, basis=basis)
    base   = mtm_ccs(aud_curve=aud_curve,              **kwargs)
    bumped = mtm_ccs(aud_curve=shift_curve(aud_curve, 1), **kwargs)
    return bumped - base


def fx_delta(
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
    FX delta: MTM change (AUD) per 1% USD appreciation vs AUD.

    A 1% rise in fx_spot (more AUD per USD) increases the AUD value
    of the USD fixed leg Australia receives.
    """
    kwargs = dict(usd_curve=usd_curve, aud_curve=aud_curve,
                  N_USD=N_USD, coupon=coupon, tenor=tenor, freq=freq, basis=basis)
    base   = mtm_ccs(fx_spot=fx_spot,        **kwargs)
    bumped = mtm_ccs(fx_spot=fx_spot * 1.01, **kwargs)
    return bumped - base


def scenario_grid(
    usd_curve:  DiscountCurve,
    aud_curve:  DiscountCurve,
    fx_spot:    float,
    N_USD:      float,
    coupon:     float,
    tenor:      float,
    freq:       int,
    basis:      float,
    usd_shifts: list[float],
    aud_shifts: list[float],
    fx_moves:   list[float],
) -> dict[str, pd.DataFrame]:
    """
    MTM scenario grid: USD rate shift × AUD rate shift for each FX move.

    Parameters
    ----------
    usd_shifts : list of USD curve shifts in bps   e.g. [-100, 0, 100]
    aud_shifts : list of AUD curve shifts in bps   e.g. [-100, 0, 100]
    fx_moves   : list of FX spot multipliers       e.g. [-0.10, 0.0, 0.10]

    Returns
    -------
    dict mapping fx_move label → DataFrame (rows=USD shift, cols=AUD shift)
    Each cell contains the MTM change vs base in AUD millions.
    """
    base_kwargs = dict(N_USD=N_USD, coupon=coupon, tenor=tenor,
                       freq=freq, basis=basis)
    base_mtm = mtm_ccs(usd_curve=usd_curve, aud_curve=aud_curve,
                       fx_spot=fx_spot, **base_kwargs)

    results = {}
    for pct in fx_moves:
        spot_s = fx_spot * (1.0 + pct)
        label  = f"FX {'+' if pct >= 0 else ''}{pct*100:.0f}%"
        grid   = {}
        for u_bp in usd_shifts:
            row = {}
            for a_bp in aud_shifts:
                mtm = mtm_ccs(
                    usd_curve=shift_curve(usd_curve, u_bp),
                    aud_curve=shift_curve(aud_curve, a_bp),
                    fx_spot=spot_s,
                    **base_kwargs,
                )
                row[f"AUD {'+' if a_bp >= 0 else ''}{int(a_bp)}bp"] = (
                    (mtm - base_mtm) / 1e6
                )
            grid[f"USD {'+' if u_bp >= 0 else ''}{int(u_bp)}bp"] = row
        results[label] = pd.DataFrame(grid).T   # rows=USD, cols=AUD
    return results
