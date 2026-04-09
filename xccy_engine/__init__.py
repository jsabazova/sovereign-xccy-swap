"""
xccy_engine — Sovereign Cross-Currency Swap Valuation Engine.

Public API:
  DiscountCurve               curve building and querying
  build_usd_curve()           bootstrap USD SOFR/swap curve
  build_aud_curve()           bootstrap AUD BBSW/swap curve
  fx_forward()                covered IRP forward rate
  fx_spot_bump()              percentage bump of FX spot
  generate_schedule()         semi-annual/annual payment dates
  usd_cashflows()             USD fixed leg cashflows
  aud_cashflows()             AUD floating leg cashflows
  pv_leg()                    PV of a cashflow leg
  mtm_ccs()                   full CCS mark-to-market in AUD
  shift_curve()               parallel zero-rate shift
  dv01_usd()                  DV01 w.r.t. USD curve
  dv01_aud()                  DV01 w.r.t. AUD curve
  fx_delta()                  MTM change per 1% FX move
  scenario_grid()             3D scenario P&L grid
"""

from .discount_curve import DiscountCurve
from .curves        import build_usd_curve, build_aud_curve
from .fx            import fx_forward, fx_spot_bump
from .cashflows     import generate_schedule, usd_cashflows, aud_cashflows
from .valuation     import pv_leg, mtm_ccs
from .risk          import shift_curve, dv01_usd, dv01_aud, fx_delta, scenario_grid

__all__ = [
    "DiscountCurve",
    "build_usd_curve", "build_aud_curve",
    "fx_forward", "fx_spot_bump",
    "generate_schedule", "usd_cashflows", "aud_cashflows",
    "pv_leg", "mtm_ccs",
    "shift_curve", "dv01_usd", "dv01_aud", "fx_delta", "scenario_grid",
]
