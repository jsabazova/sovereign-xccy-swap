"""
Generate LinkedIn-ready visual for the sovereign CCS post.
Produces: linkedin_heatmap.png

Layout:
  Left (70%)  : Scenario heatmap with USD-dominance callout
  Right (30%) : Trade stats + DV01 asymmetry + key insight
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from matplotlib.patches import FancyBboxPatch

import market_data as md
from xccy_engine import build_usd_curve, build_aud_curve, mtm_ccs, shift_curve

# ── Palette ────────────────────────────────────────────────────────────────
BG       = '#0f1923'
CARD     = '#131f2e'
C_WHITE  = '#e8f0f7'
C_MID    = '#8a9ab4'
C_DIM    = '#2e4055'
C_USD    = '#e63946'
C_AUD    = '#f4a261'
C_GREEN  = '#2dc653'
C_ACCENT = '#ffd166'

# ── Market data + curves ────────────────────────────────────────────────────
usd_curve = build_usd_curve()
aud_curve = build_aud_curve()
common    = dict(N_USD=md.N_USD, coupon=md.coupon,
                 tenor=md.tenor, freq=md.freq, basis=md.basis)
base_mtm  = mtm_ccs(usd_curve, aud_curve, md.fx_spot, **common)

# ── Scenario grid ──────────────────────────────────────────────────────────
usd_shifts = [-200, -100, 0, 100, 200]
aud_shifts = [-200, -100, 0, 100, 200]

grid = np.zeros((len(usd_shifts), len(aud_shifts)))
for i, u in enumerate(usd_shifts):
    for j, a in enumerate(aud_shifts):
        mtm = mtm_ccs(
            shift_curve(usd_curve, u),
            shift_curve(aud_curve, a),
            md.fx_spot,
            **common
        )
        grid[i, j] = (mtm - base_mtm) / 1e6  # AUD millions

row_labels = [f'USD {u:+d}bp' for u in usd_shifts]
col_labels = [f'AUD {a:+d}bp' for a in aud_shifts]

# ── Figure ────────────────────────────────────────────────────────────────
fig = plt.figure(figsize=(14, 8.5), facecolor=BG)
gs = GridSpec(1, 2, figure=fig, width_ratios=[2.9, 1],
              wspace=0.03, left=0.04, right=0.97,
              top=0.89, bottom=0.10)

ax_heat  = fig.add_subplot(gs[0])
ax_panel = fig.add_subplot(gs[1])
for ax in [ax_heat, ax_panel]:
    ax.set_facecolor(BG)
    for sp in ax.spines.values():
        sp.set_visible(False)

# ═══════════════════
# HEATMAP
# ═══════════════════
vmax = max(abs(grid.min()), abs(grid.max()))
im = ax_heat.imshow(grid, cmap='RdYlGn', vmin=-vmax, vmax=vmax, aspect='auto')

# Annotate cells
for i in range(len(usd_shifts)):
    for j in range(len(aud_shifts)):
        v = grid[i, j]
        norm = (v + vmax) / (2*vmax)
        tc = 'white' if norm < 0.27 or norm > 0.73 else '#111111'
        ax_heat.text(j, i, f'{v:+.0f}', ha='center', va='center',
                     fontsize=13.5, fontweight='bold', color=tc)

ax_heat.set_xticks(range(len(aud_shifts)))
ax_heat.set_xticklabels(col_labels, color=C_MID, fontsize=10.5)
ax_heat.set_yticks(range(len(usd_shifts)))
ax_heat.set_yticklabels(row_labels, color=C_MID, fontsize=10.5)
ax_heat.tick_params(length=0)
ax_heat.set_xlabel('AUD Rate Shift', color=C_MID, fontsize=11, labelpad=10)
ax_heat.set_ylabel('USD Rate Shift', color=C_MID, fontsize=11, labelpad=10)

# Colorbar
cbar = fig.colorbar(im, ax=ax_heat, fraction=0.025, pad=0.02,
                    orientation='horizontal', shrink=0.65, aspect=32)
cbar.set_label('ΔMtM  (AUD million)', color=C_MID, fontsize=10, labelpad=7)
cbar.ax.xaxis.set_tick_params(color=C_MID, labelcolor=C_MID, labelsize=9)
cbar.outline.set_visible(False)

# ═══════════════════
# USD DOMINANCE CALLOUT
# ═══════════════════
callout_text = (
    'USD DV01  = −AUD 3,539K / bp\n'
    'AUD DV01  = −AUD    23K / bp\n'
    '────────────────────────\n'
    'USD is 150× more sensitive'
)
ax_heat.text(0.68, 0.97, callout_text, transform=ax_heat.transAxes,
             ha='left', va='top', fontsize=9.5, fontfamily='monospace',
             color=C_ACCENT, bbox=dict(boxstyle='round,pad=0.55',
                                       facecolor='#0d1e30', edgecolor=C_ACCENT,
                                       linewidth=1.4, alpha=0.95))

# Bracket arrow showing USD dominates rows
ax_heat.annotate('', xy=(-0.18, 0.03), xytext=(-0.18, 0.97),
                 xycoords='axes fraction', textcoords='axes fraction',
                 arrowprops=dict(arrowstyle='<->', color=C_USD,
                                 lw=2.0, mutation_scale=14))
ax_heat.text(-0.215, 0.50, 'USD rates\ndrive P&L', transform=ax_heat.transAxes,
             ha='center', va='center', rotation=90, color=C_USD,
             fontsize=9, fontweight='bold')

# ═══════════════════
# RIGHT PANEL
# ═══════════════════
ax_panel.set_xlim(0, 1)
ax_panel.set_ylim(0, 1)
ax_panel.axis('off')
t = ax_panel.transAxes

def card(y0, h, edge=C_DIM, face=CARD):
    ax_panel.add_patch(FancyBboxPatch((0.04, y0), 0.92, h,
                                      boxstyle='round,pad=0.025',
                                      facecolor=face, edgecolor=edge,
                                      linewidth=1.0, transform=t, clip_on=False))
def lbl(x, y, s, **kw):
    kw.setdefault('color', C_MID)
    kw.setdefault('fontsize', 8.5)
    kw.setdefault('ha', 'left')
    kw.setdefault('va', 'top')
    ax_panel.text(x, y, s, transform=t, **kw)
def val(x, y, s, **kw):
    kw.setdefault('color', C_WHITE)
    kw.setdefault('fontsize', 11)
    kw.setdefault('fontweight', 'bold')
    kw.setdefault('ha', 'left')
    kw.setdefault('va', 'top')
    ax_panel.text(x, y, s, transform=t, **kw)

# Card positions — bottom up, no overlaps
# Card 3 (insight):  y0=0.015  h=0.24  top=0.255
# Card 2 (DV01):     y0=0.275  h=0.38  top=0.655
# Card 1 (trade):    y0=0.675  h=0.30  top=0.975

# ── Trade card ────────────────────────────────────────────────────────────────
card(0.675, 0.30)
lbl(0.10, 0.962, 'SOVEREIGN CCS  ·  AUSTRALIA', fontsize=8.5, fontweight='bold', color=C_MID)
y = 0.928
for l, v in [('Notional',   'USD 5bn  /  AUD 7.75bn'),
             ('USD Coupon', '4.00%  fixed  semi-annual'),
             ('AUD Float',  'BBSW  −  25bp  basis'),
             ('FX Spot',    '1.5500 AUD/USD  ·  5 years')]:
    lbl(0.10, y, l);               y -= 0.027
    val(0.10, y, v, fontsize=9.5); y -= 0.040

# ── DV01 asymmetry card ───────────────────────────────────────────────────────
card(0.275, 0.38, edge=C_ACCENT, face='#0f1a0d')
lbl(0.10, 0.638, 'RATE SENSITIVITY  —  DV01',
    fontsize=8.5, fontweight='bold', color=C_ACCENT)

bar_left, bar_right, bar_h = 0.10, 0.88, 0.020
y = 0.600
for label_s, value_s, color, frac in [
    ('USD curve  (+1bp)', '−AUD 3,539K', C_USD, 1.000),
    ('AUD curve  (+1bp)', '−AUD    23K', C_AUD, 0.007),
]:
    lbl(bar_left, y, label_s, fontsize=9);              y -= 0.028
    val(bar_left, y, value_s, color=color, fontsize=11); y -= 0.028
    # track
    ax_panel.add_patch(FancyBboxPatch(
        (bar_left, y - 0.009), bar_right - bar_left, bar_h,
        boxstyle='round,pad=0.002', facecolor='#1a3050',
        edgecolor='none', transform=t, clip_on=False))
    # fill
    ax_panel.add_patch(FancyBboxPatch(
        (bar_left, y - 0.009), max((bar_right - bar_left) * frac, 0.014), bar_h,
        boxstyle='round,pad=0.002', facecolor=color, alpha=0.85,
        edgecolor='none', transform=t, clip_on=False))
    y -= 0.050

ax_panel.text(0.50, y + 0.012, '150×  asymmetry',
              ha='center', va='top', color=C_ACCENT,
              fontsize=10.5, fontweight='bold', transform=t)
y -= 0.042
lbl(bar_left, y, 'FX Delta  (+1% USD appreciation)', fontsize=9)
y -= 0.028
val(bar_left, y, '+AUD 672K', color='#06d6a0')

# ── Key insight card ──────────────────────────────────────────────────────────
card(0.015, 0.24, edge=C_GREEN, face='#0a1a0d')
lbl(0.10, 0.240, 'KEY INSIGHT', fontsize=8.5, fontweight='bold', color=C_GREEN)
ax_panel.text(0.10, 0.207,
    'AUD floating leg reprices every 6 months\n'
    '→ near-zero duration.\n'
    'USD fixed leg carries ~4.5Y duration.\n\n'
    'That asymmetry is the whole point of the hedge.',
    color=C_WHITE, fontsize=9.5, va='top', ha='left',
    linespacing=1.5, transform=t)

# ═══════════════════
# TITLE
# ═══════════════════

fig.text(0.04, 0.965,
         'Sovereign Cross-Currency Swap — Scenario P&L (ΔMtM, AUD millions)',
         color=C_WHITE, fontsize=14.5, fontweight='bold', va='top')
fig.text(0.04, 0.940,
         f'USD × AUD rate shifts · base = current market · USD data: {md._usd_source}',
         color=C_MID, fontsize=9, va='top')

# ── Watermark + Author ───────────────────────────────────────────────────────
fig.text(0.97, 0.012,
         'github.com/jsabazova/sovereign-xccy-swap',
         color=C_DIM, fontsize=9, ha='right', va='bottom')

fig.text(0.97, 0.035,
         'By Jamila Sabazova',
         color=C_DIM, fontsize=9, ha='right', va='bottom')

plt.savefig('linkedin_heatmap.png', dpi=220, bbox_inches='tight', facecolor=BG)
print('Saved: linkedin_heatmap.png')

