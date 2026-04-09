"""
Build USD and AUD discount curves from market_data.

Both curves are bootstrapped in three steps:
  1. Deposits  → short end (3M, 6M, 1Y)
  2. Swaps     → long end  (2Y, 3Y, 4Y, 5Y) using semi-annual frequency

Log-linear interpolation (DiscountCurve default) fills in between pillars.
"""

from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import market_data as md
from .discount_curve import DiscountCurve


def build_usd_curve() -> DiscountCurve:
    """Bootstrap USD discount curve from SOFR deposits and swap rates."""
    curve = DiscountCurve()
    curve.bootstrap_deposits(md.usd_deposits)
    for T, rate in md.usd_swaps:
        curve.bootstrap_swap(T, rate, freq=2)
    return curve


def build_aud_curve() -> DiscountCurve:
    """Bootstrap AUD discount curve from AONIA deposits and BBSW swap rates."""
    curve = DiscountCurve()
    curve.bootstrap_deposits(md.aud_deposits)
    for T, rate in md.aud_swaps:
        curve.bootstrap_swap(T, rate, freq=2)
    return curve
