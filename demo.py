"""
demo.py — Terminal output for the Sovereign Cross-Currency Swap demo.

Run:
    python demo.py

Prints:
  1. Market data source (live FRED or hardcoded fallback)
  2. Trade terms
  3. Cashflow schedule — both legs side by side
  4. MTM at inception
  5. Rate and FX scenarios
  6. Risk sensitivities (DV01 USD, DV01 AUD, FX delta)
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import market_data as md
from xccy_engine import (
    build_usd_curve, build_aud_curve,
    generate_schedule, usd_cashflows, aud_cashflows,
    pv_leg, mtm_ccs,
    shift_curve, dv01_usd, dv01_aud, fx_delta, scenario_grid,
)

# ── Helpers ───────────────────────────────────────────────────────────────────

W = 72

def hr(char="─"):
    print(char * W)

def section(title: str):
    print()
    hr("═")
    print(f"  {title}")
    hr("═")

def fmt_ccy(n: float, symbol: str = "") -> str:
    return f"{symbol}{n:>20,.0f}"

# ── Build curves ──────────────────────────────────────────────────────────────

usd_curve = build_usd_curve()
aud_curve = build_aud_curve()

# ── Header ────────────────────────────────────────────────────────────────────

print()
hr("═")
print(f"{'SOVEREIGN CROSS-CURRENCY SWAP VALUATION ENGINE':^{W}}")
print(f"{'Australia: USD 5bn Fixed Bond → AUD CCS Hedge':^{W}}")
hr("═")

print(f"\n  USD market data : {md._usd_source}")
print(f"  AUD market data : {md._aud_source}")

# ── Trade terms ───────────────────────────────────────────────────────────────

section("TRADE TERMS")
print(f"  {'Notional (USD)':<26} USD {md.N_USD:>20,.0f}")
print(f"  {'Notional (AUD)':<26} AUD {md.N_AUD:>20,.0f}")
print(f"  {'USD Fixed Coupon':<26} {md.coupon:.3%}")
basis_bp = int(round(md.basis * 10_000))
print(f"  {'AUD Floating Rate':<26} BBSW + ({basis_bp:+d}bp cross-currency basis)")
print(f"  {'FX Spot (USD/AUD)':<26} {md.fx_spot:.4f}")
print(f"  {'Tenor / Frequency':<26} {md.tenor:.0f}Y, {'semi-annual' if md.freq==2 else 'annual'}")

# ── Cashflow schedule ─────────────────────────────────────────────────────────

section("CASHFLOW SCHEDULE")

schedule = generate_schedule(md.tenor, md.freq)
usd_cfs  = usd_cashflows(schedule, md.N_USD, md.coupon)
aud_cfs  = aud_cashflows(schedule, md.N_AUD, aud_curve, md.basis)

# Compute BBSW forward rates for display
bbsw_fwds = []
import numpy as np
prev = 0.0
for t in schedule:
    dt = t - prev
    f  = aud_curve.forward_rate(prev, t)
    bbsw_fwds.append((np.exp(f * dt) - 1.0) / dt)
    prev = t

print(f"  {'Date':>6}  {'USD Fixed CF':>22}  {'BBSW Fwd':>10}  {'AUD Float CF':>22}")
hr()
for i, t in enumerate(schedule):
    t_usd, usd_cf = usd_cfs[i]
    t_aud, aud_cf = aud_cfs[i]
    bbsw = bbsw_fwds[i]
    print(f"  {t:>6.2f}  {usd_cf:>22,.0f}  {bbsw:>9.4%}  {aud_cf:>22,.0f}")
hr()

# ── Valuation at inception ────────────────────────────────────────────────────

section("VALUATION AT INCEPTION")

pv_usd  = pv_leg(usd_cfs, usd_curve)
pv_aud  = pv_leg(aud_cfs, aud_curve)
mtm_base = pv_usd * md.fx_spot - pv_aud

print(f"  {'PV (USD leg)':<30} USD {pv_usd:>20,.0f}")
print(f"  {'PV (AUD leg)':<30} AUD {pv_aud:>20,.0f}")
print(f"  {'PV_USD × FX_spot':<30} AUD {pv_usd * md.fx_spot:>20,.0f}")
print()
print(f"  {'MTM (AUD)  ← at-market ≈ 0':<30} AUD {mtm_base:>20,.0f}")

# ── Scenario analysis ─────────────────────────────────────────────────────────

section("RATE AND FX SCENARIOS")

common = dict(
    N_USD=md.N_USD, coupon=md.coupon,
    tenor=md.tenor, freq=md.freq, basis=md.basis,
)

scenarios = [
    ("Base",                    usd_curve, aud_curve, md.fx_spot),
    ("+100bp USD rates",        shift_curve(usd_curve, +100), aud_curve,  md.fx_spot),
    ("+100bp AUD rates",        usd_curve, shift_curve(aud_curve, +100),  md.fx_spot),
    ("AUD depreciates  −10%",   usd_curve, aud_curve, md.fx_spot * 0.90),
    ("AUD appreciates  +10%",   usd_curve, aud_curve, md.fx_spot * 1.10),
    ("+100bp USD / AUD −10%",   shift_curve(usd_curve, +100), aud_curve, md.fx_spot * 0.90),
]

print(f"  {'Scenario':<30}  {'MTM (AUD)':>20}  {'Δ MTM (AUD)':>20}")
hr()
for label, uc, ac, fx in scenarios:
    mtm = mtm_ccs(usd_curve=uc, aud_curve=ac, fx_spot=fx, **common)
    delta = mtm - mtm_base
    delta_str = f"{delta:>+20,.0f}" if label != "Base" else f"{'—':>20}"
    print(f"  {label:<30}  {mtm:>20,.0f}  {delta_str}")
hr()

# ── Risk sensitivities ────────────────────────────────────────────────────────

section("RISK SENSITIVITIES")

dv01_u = dv01_usd(usd_curve, aud_curve, md.fx_spot, **common)
dv01_a = dv01_aud(usd_curve, aud_curve, md.fx_spot, **common)
fxd    = fx_delta(usd_curve, aud_curve, md.fx_spot, **common)

print(f"  {'DV01 USD':<30} AUD {dv01_u:>+20,.0f}  per +1bp USD rates")
print(f"  {'DV01 AUD':<30} AUD {dv01_a:>+20,.0f}  per +1bp AUD rates")
print(f"  {'FX Delta':<30} AUD {fxd:>+20,.0f}  per +1% USD appreciation")

print()
print(f"  Approx DV01_USD × 100bp = AUD {dv01_u * 100:>+20,.0f}")
print(f"  Matches '+100bp USD' scenario above ✓")

# ── Scenario grid ─────────────────────────────────────────────────────────────

section("SCENARIO GRID  (ΔMtM in AUD millions)")

grids = scenario_grid(
    usd_curve=usd_curve, aud_curve=aud_curve, fx_spot=md.fx_spot,
    usd_shifts=[-100, 0, 100],
    aud_shifts=[-100, 0, 100],
    fx_moves=[-0.10, 0.0, 0.10],
    **common,
)

for fx_label, df in grids.items():
    print(f"\n  {fx_label}")
    print(f"  {df.round(1).to_string()}")

print()
hr("═")
print(f"{'END':^{W}}")
hr("═")
print()
