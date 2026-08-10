"""
DRHP Chart Generator
Produces matplotlib charts as PNG bytes for embedding in the ReportLab PDF.
100% local — no API calls. All charts are generated purely from provided data.
"""
import io
from typing import List, Optional

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend — safe for server use
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.ticker import FuncFormatter
import numpy as np

from reportlab.platypus import Image as RLImage

# ── Colour palette (matches SEBI Navy theme) ────────────────
NAVY   = "#003087"
BLUE   = "#1A56DB"
TEAL   = "#0E7490"
GREEN  = "#15803D"
AMBER  = "#B45309"
RED    = "#DC2626"
GREY   = "#64748B"
LGREY  = "#E2E8F0"

BAR_COLORS   = [NAVY, BLUE, TEAL, GREEN, AMBER]
LINE_COLOR   = NAVY
ACCENT_COLOR = BLUE


def _fig_to_rl(fig: plt.Figure, width_cm: float = 13.0) -> RLImage:
    """Convert a matplotlib figure to a ReportLab Image flowable."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight", facecolor="white")
    buf.seek(0)
    plt.close(fig)
    # Convert cm to ReportLab points (72 pts/inch, 2.54 cm/inch)
    width_pt  = (width_cm / 2.54) * 72
    height_pt = (fig.get_figheight() / fig.get_figwidth() * width_cm / 2.54) * 72
    # Cap height at 220pt (~7.8cm) so it never overflows an A4 frame
    if height_pt > 220:
        scale = 220 / height_pt
        width_pt  *= scale
        height_pt  = 220
    img = RLImage(buf, width=width_pt, height=height_pt)
    img.hAlign = "CENTER"
    return img


def _format_lakh(val: float, pos=None) -> str:
    if abs(val) >= 100:
        return f"₹{val/100:.1f} Cr"
    return f"₹{val:.0f} L"


def _ax_style(ax: plt.Axes, title: str, xlabel: str = "", ylabel: str = "") -> None:
    ax.set_title(title, fontsize=11, fontweight="bold", color=NAVY, pad=12)
    ax.set_xlabel(xlabel, fontsize=9, color=GREY)
    ax.set_ylabel(ylabel, fontsize=9, color=GREY)
    ax.tick_params(colors=GREY, labelsize=8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(LGREY)
    ax.spines["bottom"].set_color(LGREY)
    ax.yaxis.set_major_formatter(FuncFormatter(_format_lakh))
    ax.grid(axis="y", color=LGREY, linewidth=0.6, linestyle="--")


# ── Chart 1: Revenue & PAT Bar Chart (grouped) ──────────────

def revenue_pat_chart(years: List[str], revenues: List[Optional[float]], pats: List[Optional[float]], width_cm: float = 13) -> RLImage:
    """Revenue vs PAT bar chart. None values are shown as 0 bars with 'N/P' label."""
    n = len(years)
    x = np.arange(n)
    w = 0.35

    # Convert None to 0 for matplotlib — display 'N/P' in label
    rev_vals = [r if r is not None else 0.0 for r in revenues]
    pat_vals = [p if p is not None else 0.0 for p in pats]
    max_rev = max((r for r in rev_vals if r is not None), default=1.0)

    fig, ax = plt.subplots(figsize=(max(6, n * 1.2), 3.2), facecolor="white")
    bars1 = ax.bar(x - w / 2, rev_vals, w, label="Revenue", color=NAVY, edgecolor="white", linewidth=0.5)
    bars2 = ax.bar(x + w / 2, pat_vals, w, label="Net Profit / (Loss)", color=BLUE, edgecolor="white", linewidth=0.5)

    for i, (bar, orig) in enumerate(zip(bars1, revenues)):
        label = "N/P" if orig is None else _format_lakh(bar.get_height())
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max_rev * 0.01,
                label, ha="center", va="bottom", fontsize=7, color=NAVY, fontweight="bold")
    for i, (bar, orig) in enumerate(zip(bars2, pats)):
        h = bar.get_height()
        y = h + max_rev * 0.01 if h >= 0 else h - max_rev * 0.03
        label = "N/P" if orig is None else _format_lakh(h)
        ax.text(bar.get_x() + bar.get_width() / 2, y,
                label, ha="center", va="bottom", fontsize=7, color=BLUE, fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels(years, fontsize=9)
    ax.legend(fontsize=9, framealpha=0.7, edgecolor=LGREY)
    _ax_style(ax, "Revenue vs. Net Profit / (Loss) — Historical Trend", ylabel="INR Lakhs")
    ax.annotate("N/P = Not Provided", xy=(0.01, 0.01), xycoords='axes fraction', fontsize=7, color=GREY)
    fig.tight_layout()
    return _fig_to_rl(fig, width_cm)


# ── Chart 2: EBITDA Margin Line Chart ───────────────────────

def ebitda_margin_chart(years: List[str], revenues: List[float], ebitdas: List[float], width_cm: float = 13) -> RLImage:
    margins = [(e / r * 100) if r > 0 else 0 for e, r in zip(ebitdas, revenues)]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(max(8, len(years) * 1.3), 3.2), facecolor="white")

    # Left: EBITDA bar
    ax1.bar(years, ebitdas, color=TEAL, edgecolor="white", linewidth=0.5)
    for i, (y, v) in enumerate(zip(years, ebitdas)):
        ax1.text(i, v + max(ebitdas) * 0.01, _format_lakh(v), ha="center", va="bottom", fontsize=7, color=TEAL, fontweight="bold")
    _ax_style(ax1, "EBITDA", ylabel="INR Lakhs")
    ax1.tick_params(axis="x", labelsize=8)

    # Right: Margin % line
    ax2.plot(years, margins, marker="o", linewidth=2.0, color=LINE_COLOR, markersize=6, markerfacecolor=BLUE)
    ax2.fill_between(years, margins, alpha=0.10, color=BLUE)
    for i, (y, m) in enumerate(zip(years, margins)):
        ax2.annotate(f"{m:.1f}%", (y, m), textcoords="offset points", xytext=(0, 9),
                     ha="center", fontsize=8, color=NAVY, fontweight="bold")
    ax2.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax2.set_title("EBITDA Margin %", fontsize=11, fontweight="bold", color=NAVY, pad=12)
    ax2.tick_params(colors=GREY, labelsize=8)
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)
    ax2.spines["left"].set_color(LGREY)
    ax2.spines["bottom"].set_color(LGREY)
    ax2.grid(axis="y", color=LGREY, linewidth=0.6, linestyle="--")

    fig.tight_layout()
    return _fig_to_rl(fig, width_cm)


# ── Chart 3: Balance Sheet Composition Stacked Bar ──────────

def balance_sheet_chart(years: List[str], assets: List[float], equities: List[float], width_cm: float = 13) -> RLImage:
    debts = [max(0, a - e) for a, e in zip(assets, equities)]

    fig, ax = plt.subplots(figsize=(max(6, len(years) * 1.2), 3.2), facecolor="white")
    x = np.arange(len(years))
    w = 0.45

    ax.bar(x, equities, w, label="Equity / Net Worth", color=GREEN, edgecolor="white")
    ax.bar(x, debts, w, bottom=equities, label="Total Debt", color=RED, edgecolor="white", alpha=0.7)

    for i, (e, d) in enumerate(zip(equities, debts)):
        ax.text(i, e / 2, _format_lakh(e), ha="center", va="center", fontsize=7, color="white", fontweight="bold")
        if d > 0:
            ax.text(i, e + d / 2, _format_lakh(d), ha="center", va="center", fontsize=7, color="white", fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels(years, fontsize=9)
    ax.legend(fontsize=9, framealpha=0.7, edgecolor=LGREY)
    _ax_style(ax, "Capital Structure — Equity vs. Debt", ylabel="INR Lakhs")
    fig.tight_layout()
    return _fig_to_rl(fig, width_cm)


# ── Chart 4: Key Ratios Spider / Radar Chart ─────────────────

def ratios_radar_chart(years: List[str], fys_data: list, width_cm: float = 11) -> RLImage:
    """
    True polar radar / spider chart of key profitability ratios across years.
    Each year's ratios are plotted as a filled polygon on a polar axis.
    """
    if not fys_data:
        return None  # type: ignore

    labels = ["ROE %", "Net Margin %", "EBITDA Margin %", "Current Ratio"]
    num_labels = len(labels)
    angles = [n / float(num_labels) * 2 * np.pi for n in range(num_labels)]
    angles += angles[:1]  # Close the loop

    fig, ax = plt.subplots(figsize=(6, 5), subplot_kw={"projection": "polar"}, facecolor="white")

    # Style the polar axes
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=8.5, color=NAVY, fontweight="bold")
    ax.tick_params(colors=GREY, labelsize=8)
    ax.set_yticklabels([])
    ax.spines["polar"].set_color(LGREY)
    ax.grid(color=LGREY, linewidth=0.8, linestyle="--")

    for i, (fy, color) in enumerate(zip(fys_data, BAR_COLORS)):
        r = max(fy.revenue or 1, 1)
        e = max(fy.total_equity or 1, 1)
        roe = min(max((fy.net_profit / e * 100) if e > 0 else 0, 0), 50)  # cap at 50% for scale
        npm = min(max((fy.net_profit / r * 100) if r > 0 else 0, 0), 50)
        ebitda_m = min(max((fy.ebitda / r * 100) if (fy.ebitda and r > 0) else 0, 0), 50)
        # Current ratio: scale 0-3 mapped to 0-50 for comparability
        cr_raw = (((fy.current_assets or 0) - (fy.current_liabilities or 0)) / max(fy.current_liabilities or 1, 1) + 1)
        cr = min(max(cr_raw * 15, 0), 50)
        vals = [roe, npm, ebitda_m, cr]
        vals += vals[:1]  # Close loop
        ax.plot(angles, vals, linewidth=1.8, linestyle="solid", color=color, label=fy.year)
        ax.fill(angles, vals, color=color, alpha=0.12)

    ax.set_title("Key Profitability Ratios — Radar", fontsize=10, fontweight="bold",
                 color=NAVY, pad=18)
    ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.15), fontsize=8,
              framealpha=0.8, edgecolor=LGREY)
    fig.tight_layout()
    return _fig_to_rl(fig, width_cm)



# ── Chart 5: Post-Issue Shareholding Pie Chart ───────────────

def shareholding_pie_chart(promoters_pct: float, public_pct: float, market_maker_pct: float = 5.0, width_cm: float = 9) -> RLImage:
    # Adjust to 100%
    total = promoters_pct + public_pct + market_maker_pct
    if total > 100:
        public_pct = max(0, 100 - promoters_pct - market_maker_pct)
    labels = ["Promoters", "Public / Investors", "Market Maker"]
    sizes  = [promoters_pct, public_pct, market_maker_pct]
    colors = [NAVY, BLUE, TEAL]
    explode = (0.03, 0.03, 0.03)

    fig, ax = plt.subplots(figsize=(5, 4.0), facecolor="white")
    wedges, texts, autotexts = ax.pie(
        sizes, labels=labels, colors=colors, explode=explode,
        autopct="%1.1f%%", startangle=140,
        wedgeprops=dict(edgecolor="white", linewidth=2),
        textprops=dict(fontsize=9, color="black"),
    )
    for at in autotexts:
        at.set_fontsize(9)
        at.set_fontweight("bold")
        at.set_color("white")
    ax.set_title("Post-Issue Shareholding Pattern", fontsize=11, fontweight="bold", color=NAVY, pad=10)
    fig.tight_layout()
    return _fig_to_rl(fig, width_cm)


# ── Chart 6: Revenue Growth Waterfall-style bar ──────────────

def revenue_growth_chart(years: List[str], revenues: List[float], width_cm: float = 13) -> RLImage:
    """Shows YoY revenue growth as bars with growth % annotations."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9, 3.2), facecolor="white")

    # Left: Revenue bars
    colors = [GREEN if r > 0 else RED for r in revenues]
    ax1.bar(years, revenues, color=colors, edgecolor="white", linewidth=0.5)
    for i, (y, r) in enumerate(zip(years, revenues)):
        ax1.text(i, r + max(revenues) * 0.01, _format_lakh(r),
                 ha="center", va="bottom", fontsize=8, color=NAVY, fontweight="bold")
    _ax_style(ax1, "Revenue from Operations", ylabel="INR Lakhs")
    ax1.tick_params(axis="x", labelsize=8)

    # Right: YoY growth %
    growths = []
    growth_labels = []
    for i in range(len(revenues)):
        if i == 0 or revenues[i - 1] == 0:
            growths.append(0)
            growth_labels.append("Base Year")
        else:
            g = (revenues[i] - revenues[i - 1]) / revenues[i - 1] * 100
            growths.append(g)
            growth_labels.append(f"{g:+.1f}%")

    bar_colors = [GREEN if g >= 0 else RED for g in growths]
    ax2.bar(years, growths, color=bar_colors, edgecolor="white", linewidth=0.5, alpha=0.85)
    for i, (y, g, lbl) in enumerate(zip(years, growths, growth_labels)):
        ax2.text(i, g + (1 if g >= 0 else -2), lbl, ha="center", va="bottom", fontsize=8,
                 color=GREEN if g >= 0 else RED, fontweight="bold")
    ax2.axhline(0, color=GREY, linewidth=0.8)
    ax2.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax2.set_title("Revenue Growth % (YoY)", fontsize=11, fontweight="bold", color=NAVY, pad=12)
    ax2.tick_params(colors=GREY, labelsize=8)
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)
    ax2.spines["left"].set_color(LGREY)
    ax2.spines["bottom"].set_color(LGREY)
    ax2.grid(axis="y", color=LGREY, linewidth=0.6, linestyle="--")

    fig.tight_layout()
    return _fig_to_rl(fig, width_cm)


# ── Chart 7: Peer Comparison Horizontal Bar ──────────────────

def peer_comparison_chart(
    company_name: str,
    company_pe: float,
    company_ronw: float,
    company_ebitda_margin: float,
    peers: List[dict],  # [{"name": str, "pe": float, "ronw": float, "ebitda": float}, ...]
    width_cm: float = 14,
) -> RLImage:
    """Horizontal bar chart comparing company vs peers on key metrics."""
    all_names = [company_name] + [p["name"] for p in peers]
    all_pe    = [company_pe] + [p.get("pe", 0) for p in peers]
    all_ronw  = [company_ronw] + [p.get("ronw", 0) for p in peers]
    all_ebitda= [company_ebitda_margin] + [p.get("ebitda_margin", 0) for p in peers]

    n = len(all_names)
    y = np.arange(n)
    height = max(3.5, n * 0.65)
    fig, axes = plt.subplots(1, 3, figsize=(14, height), facecolor="white")
    fig.suptitle("Peer Comparison — Listed Industry Players", fontsize=11, fontweight="bold", color=NAVY, y=1.02)

    datasets = [
        (axes[0], all_pe,    "P/E Ratio (x)",    [GREEN if i == 0 else GREY for i in range(n)]),
        (axes[1], all_ronw,  "RoNW % (Latest FY)",[GREEN if i == 0 else GREY for i in range(n)]),
        (axes[2], all_ebitda,"EBITDA Margin %",   [GREEN if i == 0 else GREY for i in range(n)]),
    ]
    for ax, vals, title, colors_list in datasets:
        bars = ax.barh(y, vals, color=colors_list, edgecolor="white", linewidth=0.5, height=0.6)
        for j, (bar, v) in enumerate(zip(bars, vals)):
            lbl = f"{v:.1f}" if v else "N/A"
            ax.text(max(vals) * 0.02, bar.get_y() + bar.get_height() / 2, lbl,
                    va="center", ha="left", fontsize=8,
                    color="white" if j == 0 else GREY, fontweight="bold" if j == 0 else "normal")
        ax.set_yticks(y)
        ax.set_yticklabels(all_names, fontsize=8)
        ax.set_title(title, fontsize=9, fontweight="bold", color=NAVY, pad=6)
        ax.tick_params(colors=GREY, labelsize=7)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color(LGREY)
        ax.spines["bottom"].set_color(LGREY)
        ax.grid(axis="x", color=LGREY, linewidth=0.5, linestyle="--")
        ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}"))
        # Highlight company
        bars[0].set_edgecolor(NAVY)
        bars[0].set_linewidth(1.5)

    fig.tight_layout()
    return _fig_to_rl(fig, width_cm)


# ── Chart 8: Objects of Issue — Fund Utilization Donut ───────

def funds_utilization_chart(
    objects: List[dict],  # [{"label": str, "amount_cr": float}, ...]
    width_cm: float = 10,
) -> RLImage:
    """Donut chart showing Objects of Issue fund utilization."""
    if not objects:
        return None  # type: ignore
    labels = [f"{o['label']}\n(₹{o['amount_cr']:.1f} Cr)" for o in objects]
    sizes  = [o["amount_cr"] for o in objects]
    palette = [NAVY, BLUE, TEAL, GREEN, AMBER, RED, GREY]
    colors_list = [palette[i % len(palette)] for i in range(len(objects))]

    fig, ax = plt.subplots(figsize=(6, 5), facecolor="white")
    wedges, texts, autotexts = ax.pie(
        sizes, labels=None, colors=colors_list, startangle=90,
        autopct="%1.1f%%", pctdistance=0.75,
        wedgeprops=dict(width=0.55, edgecolor="white", linewidth=2),
    )
    for at in autotexts:
        at.set_fontsize(8)
        at.set_fontweight("bold")
        at.set_color("white")
    ax.legend(wedges, labels, loc="lower center", bbox_to_anchor=(0.5, -0.25),
              ncol=2, fontsize=7, framealpha=0.8, edgecolor=LGREY)
    total = sum(sizes)
    ax.text(0, 0, f"₹{total:.1f} Cr\nTotal", ha="center", va="center",
            fontsize=10, fontweight="bold", color=NAVY)
    ax.set_title("Objects of Issue — Fund Utilization", fontsize=11, fontweight="bold", color=NAVY, pad=12)
    fig.tight_layout()
    return _fig_to_rl(fig, width_cm)


# ── Chart 9: CAGR Revenue Growth Trajectory ──────────────────

def cagr_trajectory_chart(
    years: List[str],
    revenues: List[float],
    pats: List[float],
    width_cm: float = 14,
) -> RLImage:
    """Line chart with CAGR annotation showing revenue and PAT growth trajectory."""
    if len(revenues) < 2:
        return None  # type: ignore

    fig, ax = plt.subplots(figsize=(9, 3.5), facecolor="white")

    # Revenue line
    ax.plot(years, revenues, marker="o", linewidth=2.5, color=NAVY,
            markersize=8, markerfacecolor=NAVY, label="Revenue from Operations", zorder=3)
    ax.fill_between(years, revenues, alpha=0.08, color=NAVY)

    # PAT line
    ax.plot(years, pats, marker="s", linewidth=2.0, color=BLUE,
            markersize=7, markerfacecolor=BLUE, linestyle="--", label="Net Profit After Tax", zorder=3)
    ax.fill_between(years, pats, alpha=0.06, color=BLUE)

    # Annotate values
    for i, (y, r, p) in enumerate(zip(years, revenues, pats)):
        ax.annotate(_format_lakh(r), (y, r), textcoords="offset points", xytext=(0, 10),
                    ha="center", fontsize=7.5, color=NAVY, fontweight="bold")
        ax.annotate(_format_lakh(p), (y, p), textcoords="offset points",
                    xytext=(0, -14 if p < r else 10),
                    ha="center", fontsize=7.5, color=BLUE, fontweight="bold")

    # Compute and annotate CAGR
    if revenues[0] > 0 and len(revenues) > 1:
        n_years = len(revenues) - 1
        cagr_rev = ((revenues[-1] / revenues[0]) ** (1 / n_years) - 1) * 100
        ax.annotate(f"Revenue CAGR\n{cagr_rev:+.1f}%",
                    xy=(years[-1], revenues[-1]),
                    xytext=(-40, 30), textcoords="offset points",
                    fontsize=9, fontweight="bold", color=NAVY,
                    arrowprops=dict(arrowstyle="->", color=NAVY, lw=1.2),
                    bbox=dict(boxstyle="round,pad=0.3", facecolor="#EFF6FF", edgecolor=BLUE, linewidth=1))
    if pats[0] != 0 and pats[-1] > 0 and len(pats) > 1:
        n_years = len(pats) - 1
        try:
            cagr_pat = ((pats[-1] / abs(pats[0])) ** (1 / n_years) - 1) * 100
            ax.annotate(f"PAT CAGR\n{cagr_pat:+.1f}%",
                        xy=(years[-1], pats[-1]),
                        xytext=(10, -30), textcoords="offset points",
                        fontsize=9, fontweight="bold", color=BLUE,
                        arrowprops=dict(arrowstyle="->", color=BLUE, lw=1.0),
                        bbox=dict(boxstyle="round,pad=0.3", facecolor="#EFF6FF", edgecolor=BLUE, linewidth=1))
        except Exception:
            pass

    ax.yaxis.set_major_formatter(FuncFormatter(_format_lakh))
    ax.set_title("Revenue & PAT Growth Trajectory with CAGR", fontsize=11, fontweight="bold", color=NAVY, pad=12)
    ax.legend(fontsize=9, framealpha=0.8, edgecolor=LGREY)
    ax.tick_params(colors=GREY, labelsize=8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(LGREY)
    ax.spines["bottom"].set_color(LGREY)
    ax.grid(axis="y", color=LGREY, linewidth=0.6, linestyle="--")
    fig.tight_layout()
    return _fig_to_rl(fig, width_cm)


# ── Pipeline-expected chart functions ─────────────────────────────────────────
# These match the exact signatures called by drhp_pipeline.py Stage 9.

def ebitda_trend_chart(years: List[str], ebitdas: List[Optional[float]], width_cm: float = 13) -> RLImage:
    """EBITDA trend bar+line chart. Called by drhp_pipeline._stage_chart_generator().
    None values are displayed as 0-height bars with 'N/P' label annotation.
    """
    if not years or not ebitdas or len(years) < 2:
        return None  # type: ignore
    # Convert None → 0 for matplotlib drawing; track which are actual None
    draw_vals = [v if v is not None else 0.0 for v in ebitdas]
    has_none = any(v is None for v in ebitdas)
    fig, ax = plt.subplots(figsize=(max(6, len(years) * 1.5), 3.2), facecolor="white")
    x = list(range(len(years)))
    ax.bar(x, draw_vals, color=TEAL, edgecolor="white", linewidth=0.5, alpha=0.85, label="EBITDA")
    ax.plot(x, draw_vals, marker="D", linewidth=2, color=NAVY,
            markersize=7, markerfacecolor=NAVY, zorder=5, label="EBITDA Trend")
    max_val = max((abs(v) for v in draw_vals if v != 0), default=1)
    for i, (yr, orig, val) in enumerate(zip(years, ebitdas, draw_vals)):
        label = "N/P" if orig is None else _format_lakh(val)
        offset = max_val * 0.02 if val >= 0 else -max_val * 0.05
        ax.text(i, val + offset, label, ha="center", fontsize=8,
                color=NAVY, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(years, fontsize=9)
    ax.axhline(0, color=GREY, linewidth=0.8)
    _ax_style(ax, "EBITDA Trend", ylabel="INR Lakhs")
    ax.legend(fontsize=9, framealpha=0.8, edgecolor=LGREY)
    if has_none:
        ax.annotate("N/P = Not Provided", xy=(0.01, 0.01), xycoords='axes fraction', fontsize=7, color=GREY)
    fig.tight_layout()
    return _fig_to_rl(fig, width_cm)


def shareholding_chart(labels: List[str], percentages: List[float], width_cm: float = 9) -> RLImage:
    """
    Post-issue shareholding pattern pie chart.
    Called by drhp_pipeline._stage_chart_generator() with label/pct lists.
    """
    if not labels or not percentages or len(labels) != len(percentages):
        return None  # type: ignore
    total = sum(p for p in percentages if p > 0)
    if total <= 0:
        return None  # type: ignore
    norm = [max(0.0, p / total * 100) for p in percentages]
    palette = [NAVY, BLUE, TEAL, GREEN, AMBER, RED, GREY]
    chart_colors = [palette[i % len(palette)] for i in range(len(labels))]
    fig, ax = plt.subplots(figsize=(6, 4.5), facecolor="white")
    wedges, texts, autotexts = ax.pie(
        norm, labels=labels, colors=chart_colors, explode=[0.02] * len(labels),
        autopct="%1.1f%%", startangle=140,
        wedgeprops=dict(edgecolor="white", linewidth=2),
        textprops=dict(fontsize=9),
    )
    for at in autotexts:
        at.set_fontsize(8)
        at.set_fontweight("bold")
        at.set_color("white")
    ax.set_title("Post-Issue Shareholding Pattern", fontsize=11, fontweight="bold",
                 color=NAVY, pad=10)
    fig.tight_layout()
    return _fig_to_rl(fig, width_cm)


def issue_utilization_chart(labels: List[str], amounts: List[float], width_cm: float = 13) -> RLImage:
    """
    Objects of issue donut chart showing fund utilization.
    Called by drhp_pipeline._stage_chart_generator() with purpose/amount_lakhs lists.
    """
    if not labels or not amounts:
        return None  # type: ignore
    filtered = [(lbl, amt) for lbl, amt in zip(labels, amounts) if amt > 0]
    if not filtered:
        return None  # type: ignore
    labels_f, amounts_f = zip(*filtered)
    palette = [NAVY, BLUE, TEAL, GREEN, AMBER, RED, GREY]
    chart_colors = [palette[i % len(palette)] for i in range(len(labels_f))]
    fig, ax = plt.subplots(figsize=(8, 5), facecolor="white")
    wedges, texts, autotexts = ax.pie(
        amounts_f, colors=chart_colors,
        autopct=lambda pct: f"{pct:.1f}%",
        startangle=140, pctdistance=0.75,
        wedgeprops=dict(edgecolor="white", linewidth=2, width=0.55),
        textprops=dict(fontsize=8),
    )
    for at in autotexts:
        at.set_fontweight("bold")
        at.set_color("white")
    ax.legend(wedges,
              [f"{lbl} ({_format_lakh(amt)})" for lbl, amt in zip(labels_f, amounts_f)],
              loc="lower center", bbox_to_anchor=(0.5, -0.28), ncol=2,
              fontsize=7.5, framealpha=0.9, edgecolor=LGREY)
    total_f = sum(amounts_f)
    ax.text(0, 0, f"{_format_lakh(total_f)}\nTotal", ha="center", va="center",
            fontsize=10, fontweight="bold", color=NAVY)
    ax.set_title("Objects of Issue — Fund Utilization", fontsize=11,
                 fontweight="bold", color=NAVY, pad=12)
    fig.tight_layout()
    return _fig_to_rl(fig, width_cm)


# ── Chart 10: Cash Flow Waterfall (OCF / Capex / FCF) ────────────────────

def cash_flow_waterfall_chart(
    years: List[str],
    ocf_list: List[float],
    capex_list: List[float],
    fcf_list: List[float],
    width_cm: float = 14,
) -> RLImage:
    """
    Grouped bar chart showing Operating Cash Flow, Capex, and Free Cash Flow.
    Called as a supplementary MDA exhibit. FCF bars are highlighted in a contrasting color.
    Returns None for empty data.
    """
    if not years or not ocf_list or not capex_list or not fcf_list:
        return None  # type: ignore
    if len(years) == 0:
        return None  # type: ignore

    n = len(years)
    x = np.arange(n)
    w = 0.25

    fig, ax = plt.subplots(figsize=(max(7, n * 1.8), 3.5), facecolor="white")

    # OCF bars
    bars_ocf = ax.bar(x - w, ocf_list, w, label="Operating Cash Flow", color=TEAL, edgecolor="white", linewidth=0.5)
    # Capex bars (shown as negative to emphasize it's an outflow)
    capex_display = [-abs(c) for c in capex_list]
    bars_cap = ax.bar(x, capex_display, w, label="Capital Expenditure", color=RED, edgecolor="white", linewidth=0.5, alpha=0.8)
    # FCF bars
    fcf_colors = [GREEN if f >= 0 else RED for f in fcf_list]
    bars_fcf = ax.bar(x + w, fcf_list, w, label="Free Cash Flow", color=fcf_colors, edgecolor="white", linewidth=0.5)

    # Annotate values
    all_vals = ocf_list + [abs(c) for c in capex_list] + [abs(f) for f in fcf_list]
    max_val = max(all_vals) if all_vals else 1
    for bar, v in zip(bars_ocf, ocf_list):
        offset = max_val * 0.02 if v >= 0 else -max_val * 0.05
        ax.text(bar.get_x() + bar.get_width() / 2, v + offset,
                _format_lakh(v), ha="center", va="bottom", fontsize=7, color=TEAL, fontweight="bold")
    for bar, v in zip(bars_cap, capex_display):
        ax.text(bar.get_x() + bar.get_width() / 2, v - max_val * 0.03,
                _format_lakh(abs(v)), ha="center", va="top", fontsize=7, color=RED, fontweight="bold")
    for bar, v in zip(bars_fcf, fcf_list):
        offset = max_val * 0.02 if v >= 0 else -max_val * 0.05
        ax.text(bar.get_x() + bar.get_width() / 2, v + offset,
                _format_lakh(v), ha="center", va="bottom", fontsize=7,
                color=GREEN if v >= 0 else RED, fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels(years, fontsize=9)
    ax.axhline(0, color=GREY, linewidth=0.8)
    ax.legend(fontsize=8.5, framealpha=0.8, edgecolor=LGREY)
    _ax_style(ax, "Cash Flow Analysis — OCF, Capex & Free Cash Flow", ylabel="INR Lakhs")
    fig.tight_layout()
    return _fig_to_rl(fig, width_cm)
