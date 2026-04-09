"""
FX utilities: forward rates and spot bumps.

Covered Interest Rate Parity (CIP):
  F(t) = S × DF_AUD(t) / DF_USD(t)

No-arbitrage requires that the FX forward be consistent with the interest rate
differential between the two currencies. A deviation from CIP is the
cross-currency basis.
"""
from __future__ import annotations


def fx_forward(t: float, spot: float, df_aud: float, df_usd: float) -> float:
    """
    FX forward rate at time t via covered interest rate parity.

      F(t) = spot × DF_AUD(t) / DF_USD(t)

    Parameters
    ----------
    t       : maturity in years (informational only)
    spot    : FX spot rate (AUD per USD, e.g. 1.55)
    df_aud  : AUD discount factor at t
    df_usd  : USD discount factor at t

    Returns
    -------
    float : forward AUD/USD at maturity t
    """
    return spot * df_aud / df_usd


def fx_spot_bump(spot: float, pct: float) -> float:
    """
    Bump the FX spot rate by a percentage.

    Parameters
    ----------
    spot : current spot rate (AUD per USD)
    pct  : percentage move, e.g. -0.10 for AUD depreciates 10% vs USD

    Returns
    -------
    float : bumped spot rate
    """
    return spot * (1.0 + pct)
