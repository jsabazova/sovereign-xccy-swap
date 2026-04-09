"""
Market data for the sovereign cross-currency swap demo.

USD rates: fetched live from FRED (St. Louis Fed) using stdlib urllib.
           Falls back to hardcoded April 2025 values if the request fails.

AUD rates: hardcoded April 2025 values (RBA cash rate 4.10% post-Feb 2025 cut).

No external packages required for the live fetch — only Python stdlib urllib.

Trade scenario:
  Australia issues USD 5bn fixed bond, 4.00% coupon, 5Y semi-annual.
  Hedges via CCS: receive USD fixed 4.00% / pay AUD floating (BBSW + basis).
  FX spot: 1 USD = 1.55 AUD → AUD notional = 7.75bn AUD.
"""

from __future__ import annotations

import urllib.request
from typing import Optional


# ── Live data fetch from FRED ─────────────────────────────────────────────────

def _fred(series_id: str) -> Optional[float]:
    """Fetch the most recent value for a FRED series (no API key required)."""
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            lines = resp.read().decode().strip().split("\n")
        for line in reversed(lines[1:]):          # walk backwards to find latest
            parts = line.split(",")
            if len(parts) == 2 and parts[1].strip() not in ("", "."):
                return float(parts[1]) / 100.0    # FRED values are in percent
    except Exception:
        pass
    return None


def _fetch_usd_live():
    """
    Build USD deposit and swap rate tables from FRED.

    Short end  : Treasury bills as SOFR-deposit proxies (DTB3, DTB6, DGS1).
    Long end   : Treasury constant-maturity yields + 10bp swap spread
                 (DGS2, DGS3, DGS5 — no DSWP series needed).

    Returns (deposits, swaps) or None if data is unavailable.
    """
    bill_3m  = _fred("DTB3")
    bill_6m  = _fred("DTB6")
    yield_1y = _fred("DGS1")
    yield_2y = _fred("DGS2")
    yield_3y = _fred("DGS3")
    yield_5y = _fred("DGS5")

    if any(v is None for v in [bill_3m, bill_6m, yield_1y, yield_2y, yield_5y]):
        return None

    swap_spread = 0.001                           # +10bp swap spread over UST
    deposits = [
        (0.25, bill_3m),
        (0.50, bill_6m),
        (1.00, yield_1y),
    ]
    swaps = [
        (2.0, yield_2y + swap_spread),
        (3.0, (yield_3y or (yield_2y + yield_5y) / 2) + swap_spread),
        (4.0, ((yield_3y + yield_5y) / 2 if yield_3y else yield_5y) + swap_spread),
        (5.0, yield_5y + swap_spread),
    ]
    return deposits, swaps


# ── USD rates ─────────────────────────────────────────────────────────────────

_live = _fetch_usd_live()

if _live is not None:
    usd_deposits, usd_swaps = _live
    _usd_source = "FRED (live)"
else:
    # Fallback: April 2025 — Fed funds 4.25–4.50%, two cuts since mid-2024
    usd_deposits = [
        (0.25, 0.043),   # 3M  4.30%
        (0.50, 0.042),   # 6M  4.20%
        (1.00, 0.040),   # 1Y  4.00%
    ]
    usd_swaps = [
        (2.0, 0.0395),   # 2Y  3.95%
        (3.0, 0.0395),   # 3Y  3.95%
        (4.0, 0.0398),   # 4Y  3.98%
        (5.0, 0.0400),   # 5Y  4.00%
    ]
    _usd_source = "hardcoded (April 2025 fallback)"

# ── AUD rates ─────────────────────────────────────────────────────────────────
# April 2025: RBA cash rate 4.10% (cut from 4.35% in Feb 2025)

aud_deposits = [
    (0.25, 0.0415),  # 3M  4.15%
    (0.50, 0.0400),  # 6M  4.00%
    (1.00, 0.0385),  # 1Y  3.85%
]

aud_swaps = [
    (2.0, 0.0375),   # 2Y  3.75%
    (3.0, 0.0378),   # 3Y  3.78%
    (4.0, 0.0382),   # 4Y  3.82%
    (5.0, 0.0385),   # 5Y  3.85%
]

_aud_source = "hardcoded (April 2025)"

# ── FX and basis ──────────────────────────────────────────────────────────────

fx_spot = 1.55      # 1 USD = 1.55 AUD  (trade inception rate, ~2024/2025)
basis   = -0.0025   # −25bp AUD/USD cross-currency basis (typical 2024/2025)

# ── Trade parameters ──────────────────────────────────────────────────────────

N_USD  = 5_000_000_000.0   # USD 5bn notional
coupon = 0.040              # 4.00% USD fixed coupon (semi-annual, at-market Apr 2025)
tenor  = 5.0                # 5 years
freq   = 2                  # semi-annual

N_AUD  = N_USD * fx_spot   # AUD 7.75bn (principal exchanged at spot)
