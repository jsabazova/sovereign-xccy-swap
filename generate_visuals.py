"""
Generate LinkedIn-ready visuals for the sovereign CCS post.
Produces: linkedin_heatmap.png
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.gridspec import GridSpec
import matplotlib.patches as mpatches

import market_data as md
from xccy_engine import (
    build_usd_curve, build_aud_curve,
    mtm_ccs, shift_curve,
)

usd_curve = build_usd_curve()
aud_curve = build_aud_curve()

common = dict(N_USD=md.N_USD, coupon=md.coupon,
              tenor=md.tenor, freq=md.freq, basis=md.basis)

# ── Scenario grid data ────────────────────────────────────────────────────────

usd_shifts = [-200, -100, 0, +100, +200]
aud_shifts = [-200, -100, 0, +100, +200]

base_mtm = mtm_ccs(usd_curve, aud_curve, md.fx_spot, **common)

grid = np.zeros((len(usd_shifts), len(aud_shifts)))
for i, u in enumerate(usd_shifts):
    for j, a in enumerate(aud_shifts):
        mtm = mtm_ccs(
            usd_curve=shift_curve(usd_curve, u),
            aud_curve=shift_curve(aud_curve, a),
            fx_spot=md.fx_spot,
            **common,
        )
        grid[i, j] = (mtm - base_mtm) / 1e6   # AUD millions

row_labels = [f"USD {u:+d}bp" for u in usd_shifts]
col_labels = [f"AUD {a:+d}bp" for a in aud_shifts]

# ── Figure ────────────────────────────────────────────────────────────────────

fig = plt.figure(figsize=(13, 7.5), facecolor='#0f1923')
gs  = GridSpec(1, 2, figure=fig, width_ratios=[2.8, 1], wspace=0.22,
               left=0.06, right=0.97, top=0.87, bottom=0.10)

ax_heat  = fig.add_subplot(gs[0])
ax_panel = fig.add_subplot(gs[1])

for ax in [ax_heat, ax_panel]:
    ax.set_facecolor('#0f1923')

# ── Heatmap ───────────────────────────────────────────────────────────────────

vmax = max(abs(grid.min()), abs(grid.max()))
cmap = plt.cm.RdYlGn

im = ax_heat.imshow(grid, cmap=cmap, vmin=-vmax, vmax=vmax, aspect='auto')

# Cell annotations
for i in range(len(usd_shifts)):
    for j in range(len(aud_shifts)):
        val = grid[i, j]
        # choose white or dark text based on cell intensity
        norm_val = (val + vmax) / (2 * vmax)
        text_col = 'white' if (norm_val < 0.25 or norm_val > 0.75) else '#1a1a1a'
        sign = '+' if val >= 0 else ''
        ax_heat.text(j, i, f'{sign}{val:.0f}',
                     ha='center', va='center',
                     fontsize=13, fontweight='bold', color=text_col)

ax_heat.set_xticks(range(len(aud_shifts)))
ax_heat.set_xticklabels(col_labels, color='#aab4be', fontsize=10)
ax_heat.set_yticks(range(len(usd_shifts)))
ax_heat.set_yticklabels(row_labels, color='#aab4be', fontsize=10)
ax_heat.tick_params(colors='#aab4be', length=0)

ax_heat.set_xlabel('AUD Rate Shift', color='#aab4be', fontsize=11, labelpad=10)
ax_heat.set_ylabel('USD Rate Shift', color='#aab4be', fontsize=11, labelpad=10)

for spine in ax_heat.spines.values():
    spine.set_visible(False)

# Colorbar — placed below the heatmap to avoid overlap
cbar = fig.colorbar(im, ax=ax_heat, fraction=0.030, pad=0.02,
                    orientation='horizontal', shrink=0.75, aspect=30)
cbar.set_label('ΔMtM  (AUD million)', color='#aab4be', fontsize=10, labelpad=8)
cbar.ax.xaxis.set_tick_params(color='#aab4be', labelcolor='#aab4be')
plt.setp(cbar.ax.xaxis.get_ticklines(), color='#aab4be')
cbar.outline.set_visible(False)

# ── Right panel: key stats ────────────────────────────────────────────────────

ax_panel.set_xlim(0, 1)
ax_panel.set_ylim(0, 1)
ax_panel.axis('off')

title_kw  = dict(color='white',    fontsize=13, fontweight='bold', ha='left', va='top')
value_kw  = dict(color='#00e5ff',  fontsize=20, fontweight='bold', ha='left', va='top')
sub_kw    = dict(color='#7a8a96',  fontsize=9,  ha='left', va='top')
label_kw  = dict(color='#aab4be',  fontsize=10, ha='left', va='top')
accent_kw = dict(color='#ff6b6b',  fontsize=10, ha='left', va='top')

# Trade summary block
y = 0.96
ax_panel.text(0.05, y, 'SOVEREIGN CCS', **title_kw)

y -= 0.06
ax_panel.text(0.05, y, 'Australia · USD 5bn', color='#7a8a96', fontsize=10, ha='left', va='top')

y -= 0.10
stats = [
    ('NOTIONAL',    'USD 5bn',         'AUD 7.75bn at spot'),
    ('USD COUPON',  '4.00% fixed',     'semi-annual'),
    ('AUD FLOAT',   'BBSW − 25bp',     'cross-currency basis'),
    ('TENOR',       '5 years',         'semi-annual payments'),
]
for label, val, sub in stats:
    ax_panel.text(0.05, y, label, **sub_kw)
    y -= 0.045
    ax_panel.text(0.05, y, val, color='#e0e8f0', fontsize=11, fontweight='bold', ha='left', va='top')
    y -= 0.040
    ax_panel.text(0.05, y, sub, **sub_kw)
    y -= 0.055

# Divider
ax_panel.axhline(y + 0.02, xmin=0.05, xmax=0.95, color='#2a3a4a', linewidth=0.8)
y -= 0.04

ax_panel.text(0.05, y, 'RISK SENSITIVITIES', **title_kw)
y -= 0.07

risks = [
    ('DV01 USD',  '−AUD 3.5M / bp',   '#ff6b6b'),
    ('DV01 AUD',  '−AUD 23K / bp',    '#ffd166'),
    ('FX Delta',  '+AUD 672K / 1%',   '#06d6a0'),
]
for label, val, col in risks:
    ax_panel.text(0.05, y, label, color='#7a8a96', fontsize=9, ha='left', va='top')
    y -= 0.042
    ax_panel.text(0.05, y, val, color=col, fontsize=11.5, fontweight='bold', ha='left', va='top')
    y -= 0.055

ax_panel.axhline(y + 0.02, xmin=0.05, xmax=0.95, color='#2a3a4a', linewidth=0.8)
y -= 0.04

ax_panel.text(0.05, y, 'KEY INSIGHT', **title_kw)
y -= 0.065
insight = ("USD DV01 is 150×\nlarger than AUD DV01.\nFixed rate ≠ floating rate.\nThat asymmetry is\nthe hedge.")
ax_panel.text(0.05, y, insight, color='#e0e8f0', fontsize=10, ha='left', va='top', linespacing=1.6)

# ── Main title ────────────────────────────────────────────────────────────────

fig.text(0.03, 0.97,
         'Scenario P&L  (ΔMtM, AUD millions)',
         color='white', fontsize=15, fontweight='bold', va='top')
fig.text(0.03, 0.92,
         'How the AUD/USD Cross-Currency Swap MTM changes across rate and FX scenarios',
         color='#7a8a96', fontsize=10, va='top')

# ── Watermark ────────────────────────────────────────────────────────────────

fig.text(0.97, 0.015,
         'github.com/jsabazova/sovereign-xccy-swap',
         color='#3a4a5a', fontsize=8.5, ha='right', va='bottom')

plt.savefig('linkedin_heatmap.png', dpi=180, bbox_inches='tight',
            facecolor='#0f1923')
print('Saved: linkedin_heatmap.png')
