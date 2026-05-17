# ============================================================
# US WATCH SYSTEM v2 — main.py
# Institutional-Grade: Bridgewater · BlackRock · GS · AQR
# Run: streamlit run main.py
# ============================================================

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import sys, os
from datetime import datetime

# ── Path setup ───────────────────────────────────────────────
ROOT = os.path.dirname(__file__)
for d in [ROOT,
          os.path.join(ROOT, "data"),
          os.path.join(ROOT, "frameworks"),
          os.path.join(ROOT, "signals"),
          os.path.join(ROOT, "risk")]:
    if d not in sys.path:
        sys.path.insert(0, d)

from config import TICKERS, EQUITY_TICKERS, ALL_TICKERS, BENCHMARK
from data.fetcher import fetch_prices, fetch_macro_prices, fetch_all_fundamentals
from frameworks.bridgewater import detect_bridgewater_regime, compute_risk_parity_weights, bridgewater_score
from frameworks.blackrock import blackrock_composite
from frameworks.goldman import compute_gs_bull_bear_indicator, compute_earnings_revision, gs_conviction_score
from frameworks.aqr import aqr_composite
from signals.composite import build_composite, rank_all, generate_jason_summary
from risk.portfolio_stats import full_risk_report, compute_correlation_matrix
from frameworks.conviction import run_conviction_check, REPLACEMENT_UNIVERSE

# ════════════════════════════════════════════════════════════
# PAGE CONFIG
# ════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="US Watch v2 — Institutional",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
.fw-card { background:#1a1a2e; border-radius:8px; padding:12px; margin:4px 0;
           border-left: 4px solid #7c3aed; }
.bw-card { border-left-color: #3b82f6 !important; }
.br-card { border-left-color: #10b981 !important; }
.gs-card { border-left-color: #f59e0b !important; }
.aq-card { border-left-color: #ef4444 !important; }
.score-high { color: #10b981; font-weight: bold; font-size: 1.3rem; }
.score-mid  { color: #f59e0b; font-weight: bold; font-size: 1.3rem; }
.score-low  { color: #ef4444; font-weight: bold; font-size: 1.3rem; }
</style>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
# SIDEBAR
# ════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("## 🏛️ US Watch v2")
    st.caption("Institutional-Grade Analysis")
    st.caption("Bridgewater · BlackRock · GS · AQR")
    st.divider()

    if st.button("🔄 Refresh All Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    period = st.selectbox("Price History", ["1y", "2y", "3y"], index=1)
    show_raw = st.checkbox("Show Raw Framework Scores", value=False)

    st.divider()
    st.markdown("**Framework Weights**")
    st.markdown("- 🔵 Bridgewater: 25%")
    st.markdown("- 🟢 BlackRock: 30%")
    st.markdown("- 🟡 Goldman Sachs: 25%")
    st.markdown("- 🔴 AQR: 20%")
    st.divider()
    st.caption(f"Updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")


# ════════════════════════════════════════════════════════════
# DATA LOADING
# ════════════════════════════════════════════════════════════
@st.cache_data(ttl=3600, show_spinner=False)
def load_all(period):
    prices = fetch_prices(ALL_TICKERS, period)
    macro  = fetch_macro_prices("2y")
    funds  = fetch_all_fundamentals(ALL_TICKERS)
    return prices, macro, funds

with st.spinner("🔄 Loading institutional data..."):
    prices_df, macro_df, fundamentals = load_all(period)

if prices_df.empty:
    st.error("❌ Cannot fetch price data. Check your internet connection.")
    st.stop()

# ── Run all frameworks ───────────────────────────────────────
with st.spinner("🧠 Running framework analysis..."):
    # Bridgewater
    bw_regime    = detect_bridgewater_regime(macro_df)
    rp_weights   = compute_risk_parity_weights(prices_df, EQUITY_TICKERS)
    bw_scores    = {t: bridgewater_score(t, bw_regime, rp_weights) for t in EQUITY_TICKERS}

    # BlackRock
    br_scores    = blackrock_composite(prices_df, fundamentals, EQUITY_TICKERS)

    # Goldman Sachs
    gs_bull_bear  = compute_gs_bull_bear_indicator(macro_df, fundamentals)
    gs_er         = compute_earnings_revision(fundamentals, EQUITY_TICKERS)
    gs_scores     = {t: gs_conviction_score(t, br_scores[t]["score"], gs_er, gs_bull_bear)
                     for t in EQUITY_TICKERS}

    # AQR
    aqr_scores   = aqr_composite(prices_df, fundamentals, EQUITY_TICKERS)

    # Risk metrics
    risk_report  = full_risk_report(prices_df, EQUITY_TICKERS)
    corr_matrix  = compute_correlation_matrix(prices_df, EQUITY_TICKERS)

    # Composite
    composites = []
    for t in EQUITY_TICKERS:
        c = build_composite(t, bw_scores[t], br_scores[t], gs_scores[t], aqr_scores[t])
        composites.append(c)
    composites = rank_all(composites)
    comp_map   = {c["ticker"]: c for c in composites}
    conviction_report = run_conviction_check(composites, fundamentals, aqr_scores)


# ════════════════════════════════════════════════════════════
# HEADER
# ════════════════════════════════════════════════════════════
st.markdown("# 🏛️ US Watch System v2 — Institutional Grade")
st.caption(f"Jason's US Holdings | {datetime.now().strftime('%A, %d %B %Y')} | "
           f"Frameworks: Bridgewater · BlackRock · Goldman Sachs · AQR")
st.divider()


# ════════════════════════════════════════════════════════════
# SECTION 1: MACRO REGIME (BRIDGEWATER 4-QUADRANT)
# ════════════════════════════════════════════════════════════
st.markdown("## 🔵 Bridgewater: 4-Quadrant Macro Regime")

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Regime", bw_regime["regime_label"])
    st.caption(bw_regime["regime_description"])
with col2:
    g_color = "normal" if bw_regime["rising_growth"] else "inverse"
    st.metric("Growth Signal (SPY 6m)", f"{bw_regime['growth_score']:+.1f}%",
              delta="Rising ↑" if bw_regime["rising_growth"] else "Falling ↓",
              delta_color=g_color)
with col3:
    i_color = "inverse" if bw_regime["rising_inflation"] else "normal"
    st.metric("Inflation Signal (TIP/IEF)", f"{bw_regime['inflation_score']:+.4f}",
              delta="Rising ↑" if bw_regime["rising_inflation"] else "Falling ↓",
              delta_color=i_color)
with col4:
    st.markdown("**Risk Parity Weights**")
    for t, w in rp_weights.items():
        st.progress(w, text=f"{t}: {w*100:.1f}%")

# 4-Quadrant visual
fig_quad = go.Figure()
growth_val = bw_regime["growth_score"]
inflat_val = bw_regime["inflation_score"] * 100

quadrant_labels = [
    ("Goldilocks ✨", -20, 20, "#1a472a"),
    ("Expansion 🔥", 20, 20, "#7d2020"),
    ("Deflation 🔴", -20, -20, "#1a1a5e"),
    ("Stagflation ⚠️", 20, -20, "#7d6d20"),
]

for label, x, y, color in quadrant_labels:
    fig_quad.add_shape(type="rect",
        x0=0 if x > 0 else -40, x1=40 if x > 0 else 0,
        y0=0 if y > 0 else -40, y1=40 if y > 0 else 0,
        fillcolor=color, opacity=0.3, line=dict(color="gray", width=0.5))
    fig_quad.add_annotation(x=x, y=y, text=label, showarrow=False,
                             font=dict(color="white", size=11))

fig_quad.add_trace(go.Scatter(
    x=[growth_val], y=[inflat_val * 10],
    mode="markers+text",
    text=["📍 NOW"],
    textposition="top center",
    marker=dict(size=20, color="#7c3aed", symbol="diamond"),
    name="Current Position"
))

fig_quad.add_hline(y=0, line_color="gray", line_width=1)
fig_quad.add_vline(x=0, line_color="gray", line_width=1)
fig_quad.update_layout(
    title="Bridgewater 4-Quadrant: Growth × Inflation",
    xaxis_title="Growth →", yaxis_title="← Deflation | Inflation →",
    plot_bgcolor="#0e1117", paper_bgcolor="#0e1117", font_color="white",
    height=350, showlegend=False,
    xaxis=dict(range=[-40, 40], showgrid=False),
    yaxis=dict(range=[-40, 40], showgrid=False),
)
st.plotly_chart(fig_quad, use_container_width=True)
st.divider()


# ════════════════════════════════════════════════════════════
# SECTION 2: GOLDMAN SACHS BULL/BEAR
# ════════════════════════════════════════════════════════════
st.markdown("## 🟡 Goldman Sachs: Bull/Bear Market Indicator")

bb_val = gs_bull_bear["gs_bull_bear"]
col1, col2 = st.columns([1, 2])

with col1:
    score_class = "score-high" if bb_val >= 60 else "score-mid" if bb_val >= 40 else "score-low"
    st.markdown(
        f'<div class="fw-card gs-card">'
        f'<b>GS Bull/Bear Score</b><br>'
        f'<span class="{score_class}">{bb_val:.0f} / 100</span><br>'
        f'{gs_bull_bear["interpretation"]}'
        f'</div>',
        unsafe_allow_html=True
    )

with col2:
    comp_scores = gs_bull_bear.get("component_scores", {})
    comp_df = pd.DataFrame({
        "Component": ["Yield Curve", "Credit Spread", "Equity Momentum", "PMI Proxy", "Valuation"],
        "Score": [
            comp_scores.get("yield_curve", 50),
            comp_scores.get("credit_spread", 50),
            comp_scores.get("equity_momentum", 50),
            comp_scores.get("pmi_proxy", 50),
            comp_scores.get("valuation", 50),
        ]
    })
    fig_bb = px.bar(comp_df, x="Component", y="Score",
                     color="Score", color_continuous_scale="RdYlGn",
                     range_color=[0, 100], range_y=[0, 100],
                     title="GS Bull/Bear Components (0=Bear, 100=Bull)")
    fig_bb.add_hline(y=50, line_dash="dash", line_color="gray")
    fig_bb.update_layout(plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
                          font_color="white", height=280, showlegend=False)
    st.plotly_chart(fig_bb, use_container_width=True)

st.divider()


# ════════════════════════════════════════════════════════════
# SECTION 3: BLACKROCK 5-FACTOR HEATMAP
# ════════════════════════════════════════════════════════════
st.markdown("## 🟢 BlackRock: 5-Factor Analysis")

factor_names = ["quality", "value", "momentum", "low_volatility", "sentiment"]
factor_data  = []
for t in EQUITY_TICKERS:
    row = [br_scores[t].get(f, 5.0) for f in factor_names]
    factor_data.append(row)

factor_df = pd.DataFrame(
    factor_data,
    index=EQUITY_TICKERS,
    columns=["Quality", "Value", "Momentum", "Low Vol", "Sentiment"]
)

fig_heat = px.imshow(
    factor_df,
    color_continuous_scale="RdYlGn",
    range_color=[0, 10],
    aspect="auto",
    title="BlackRock 5-Factor Heatmap (0=Weak, 10=Strong)",
    text_auto=".1f",
)
fig_heat.update_layout(
    plot_bgcolor="#0e1117", paper_bgcolor="#0e1117", font_color="white", height=300
)
st.plotly_chart(fig_heat, use_container_width=True)

# Factor bar breakdown
fig_br = go.Figure()
colors = {"Quality": "#3b82f6", "Value": "#10b981", "Momentum": "#f59e0b",
          "Low Vol": "#8b5cf6", "Sentiment": "#ef4444"}
for factor, col in colors.items():
    key = factor.lower().replace(" ", "_")
    vals = [br_scores[t].get(key, 5.0) for t in EQUITY_TICKERS]
    fig_br.add_trace(go.Bar(name=factor, x=EQUITY_TICKERS, y=vals, marker_color=col))

fig_br.update_layout(
    barmode="group", title="Factor Scores by Ticker",
    plot_bgcolor="#0e1117", paper_bgcolor="#0e1117", font_color="white",
    height=350, yaxis=dict(range=[0, 10]),
    legend=dict(orientation="h", yanchor="bottom", y=1.02)
)
st.plotly_chart(fig_br, use_container_width=True)
st.divider()


# ════════════════════════════════════════════════════════════
# SECTION 4: AQR MOMENTUM + RANKING
# ════════════════════════════════════════════════════════════
st.markdown("## 🔴 AQR: Cross-Sectional Ranking + Trend")

aqr_data = []
for t in EQUITY_TICKERS:
    aq = aqr_scores[t]
    aqr_data.append({
        "Ticker":      t,
        "AQR Score":   aq["score"],
        "CS Momentum": round(aq["cs_momentum"], 2),
        "TS Trend":    aq["ts_label"],
        "Return 12m":  f"{aq['return_12m']:+.1f}%",
        "Return 6m":   f"{aq['return_6m']:+.1f}%",
        "Value Rank":  round(aq["value_rank"], 1),
    })

st.dataframe(pd.DataFrame(aqr_data), use_container_width=True, hide_index=True)

# AQR Momentum scatter
fig_aqr = go.Figure()
for t in EQUITY_TICKERS:
    aq = aqr_scores[t]
    fig_aqr.add_trace(go.Scatter(
        x=[aq["return_6m"]], y=[aq["return_12m"]],
        mode="markers+text",
        text=[t], textposition="top center",
        marker=dict(size=aq["score"] * 3 + 5, color=aq["score"],
                    colorscale="RdYlGn", cmin=0, cmax=10,
                    line=dict(color="white", width=1)),
        name=t, showlegend=True,
    ))
fig_aqr.add_hline(y=0, line_dash="dash", line_color="gray", line_width=0.5)
fig_aqr.add_vline(x=0, line_dash="dash", line_color="gray", line_width=0.5)
fig_aqr.update_layout(
    title="AQR Momentum Map — 6m vs 12m Return (bubble size = AQR score)",
    xaxis_title="6-Month Return (%)", yaxis_title="12-Month Return (%)",
    plot_bgcolor="#0e1117", paper_bgcolor="#0e1117", font_color="white",
    height=380, showlegend=False,
)
st.plotly_chart(fig_aqr, use_container_width=True)
st.divider()


# ════════════════════════════════════════════════════════════
# SECTION 5: MASTER COMPOSITE SCORECARD
# ════════════════════════════════════════════════════════════
st.markdown("## 🏆 Master Composite: All 4 Frameworks")
st.caption("Bridgewater 25% + BlackRock 30% + Goldman Sachs 25% + AQR 20%")

for c in composites:
    score = c["composite_score"]
    color = "#10b981" if score >= 6.5 else "#f59e0b" if score >= 5.0 else "#ef4444"

    col1, col2, col3, col4, col5, col6 = st.columns([1, 2, 2, 2, 2, 2])
    with col1:
        st.markdown(f"**#{c['rank']}**")
    with col2:
        st.markdown(f"**{c['ticker']}**")
        st.caption(TICKERS.get(c["ticker"], {}).get("name", ""))
    with col3:
        st.markdown(
            f'<span style="color:{color}; font-size:1.4rem; font-weight:bold;">'
            f'{score}/10</span>',
            unsafe_allow_html=True
        )
        st.caption(c["signal"])
    with col4:
        st.caption(f"🔵 BW: {c['bridgewater_score']}")
        st.caption(f"🟢 BR: {c['blackrock_score']}")
    with col5:
        st.caption(f"🟡 GS: {c['goldman_score']}")
        st.caption(f"🔴 AQR: {c['aqr_score']}")
    with col6:
        st.caption(c["agreement_label"])
        st.caption(c["gs_conviction"])

st.divider()

# Radar chart — per ticker framework breakdown
fig_radar = go.Figure()
categories = ["Bridgewater", "BlackRock", "Goldman", "AQR"]
for c in composites:
    vals = [c["bridgewater_score"], c["blackrock_score"],
            c["goldman_score"],     c["aqr_score"]]
    fig_radar.add_trace(go.Scatterpolar(
        r=vals + [vals[0]],
        theta=categories + [categories[0]],
        fill="toself", opacity=0.5,
        name=c["ticker"]
    ))
fig_radar.update_layout(
    polar=dict(radialaxis=dict(visible=True, range=[0, 10])),
    title="Framework Score Radar — All Tickers",
    plot_bgcolor="#0e1117", paper_bgcolor="#0e1117", font_color="white",
    height=420,
    legend=dict(orientation="h", yanchor="bottom", y=-0.2)
)
st.plotly_chart(fig_radar, use_container_width=True)
st.divider()


# ════════════════════════════════════════════════════════════
# SECTION 6: INSTITUTIONAL RISK METRICS
# ════════════════════════════════════════════════════════════
st.markdown("## ⚖️ Risk Dashboard (Institutional Metrics)")

risk_data = []
for t in EQUITY_TICKERS:
    r = risk_report.get(t, {})
    risk_data.append({
        "Ticker":        t,
        "Sharpe":        r.get("sharpe", 0),
        "Sortino":       r.get("sortino", 0),
        "Calmar":        r.get("calmar", 0),
        "Max DD%":       r.get("max_drawdown", 0),
        "VaR 95%":       r.get("var_95", 0),
        "Vol 20d%":      r.get("vol_20d", 0),
        "Vol 60d%":      r.get("vol_60d", 0),
        "Annual Ret%":   r.get("annual_return", 0),
    })

risk_df = pd.DataFrame(risk_data)

def color_sharpe(val):
    if isinstance(val, float):
        if val >= 1.0: return "color: #10b981"
        if val >= 0.5: return "color: #f59e0b"
        return "color: #ef4444"
    return ""

st.dataframe(
    risk_df.style.applymap(color_sharpe, subset=["Sharpe", "Sortino"]),
    use_container_width=True, hide_index=True
)

# Correlation heatmap
if not corr_matrix.empty:
    fig_corr = px.imshow(
        corr_matrix,
        color_continuous_scale="RdBu_r",
        range_color=[-1, 1],
        text_auto=".2f",
        title="Correlation Matrix (lower = better diversification)",
    )
    fig_corr.update_layout(
        plot_bgcolor="#0e1117", paper_bgcolor="#0e1117", font_color="white", height=350
    )
    st.plotly_chart(fig_corr, use_container_width=True)

st.divider()


# ════════════════════════════════════════════════════════════
# SECTION 7: PRICE CHART
# ════════════════════════════════════════════════════════════
st.markdown("## 📈 Price History (Normalized to 100)")

norm = prices_df[EQUITY_TICKERS + [BENCHMARK]].dropna()
norm = norm / norm.iloc[0] * 100

palette = {"NVDA":"#76b900","AVGO":"#cc0000","MSFT":"#00a4ef","CEG":"#ffa500","SPY":"#888888"}
fig_px = go.Figure()
for t in norm.columns:
    fig_px.add_trace(go.Scatter(
        x=norm.index, y=norm[t], name=t,
        line=dict(color=palette.get(t, "#fff"), width=2 if t != BENCHMARK else 1,
                  dash="dot" if t == BENCHMARK else "solid"),
    ))
fig_px.add_hline(y=100, line_dash="dot", line_color="gray", line_width=0.5)
fig_px.update_layout(
    plot_bgcolor="#0e1117", paper_bgcolor="#0e1117", font_color="white", height=400,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor="#2d2d2d"),
)
st.plotly_chart(fig_px, use_container_width=True)
st.divider()


# ════════════════════════════════════════════════════════════
# SECTION 8: DAILY BRIEFING (JASON MODE)
# ════════════════════════════════════════════════════════════
st.markdown("## 📋 Daily Briefing")
summary = generate_jason_summary(composites, bw_regime, gs_bull_bear)
st.code(summary, language=None)

# Raw scores toggle
if show_raw:
    st.divider()
    st.markdown("### Raw Framework Scores (Debug)")
    tabs = st.tabs(["Bridgewater", "BlackRock", "Goldman", "AQR"])
    with tabs[0]:
        st.json({t: bw_scores[t] for t in EQUITY_TICKERS})
    with tabs[1]:
        st.json({t: br_scores[t] for t in EQUITY_TICKERS})
    with tabs[2]:
        st.json({t: gs_scores[t] for t in EQUITY_TICKERS})
    with tabs[3]:
        st.json({t: aqr_scores[t] for t in EQUITY_TICKERS})

# ── Footer ───────────────────────────────────────────────────
st.divider()
st.caption(
    "US Watch v2 · Jason's US Portfolio Monitor · "
    "Data: Yahoo Finance · Not financial advice · "
    "Frameworks: Bridgewater All Weather, BlackRock SAE, Goldman Sachs GSAM, AQR Capital"
)

# ════════════════════════════════════════════════════════════
# SECTION 9: 10-YEAR CONVICTION CHECKER + REPLACEMENT ENGINE
# ════════════════════════════════════════════════════════════
st.divider()
st.markdown("## 🔍 10-Year Conviction Checker")
st.caption("Is every stock still worth holding for a decade? If not — here's the best replacement.")

checks = conviction_report["checks"]
flagged = conviction_report["flagged"]

# ── Status cards per ticker ───────────────────────────────
cols = st.columns(len(checks))
for i, (ticker, check) in enumerate(checks.items()):
    with cols[i]:
        score = check["conviction_score"]
        color = "#10b981" if score >= 7 else "#f59e0b" if score >= 5 else "#ef4444"
        st.markdown(
            f"<div style='text-align:center; padding:10px; border:0.5px solid var(--color-border-tertiary); border-radius:8px;'>"
            f"<div style='font-size:18px; font-weight:500;'>{ticker}</div>"
            f"<div style='font-size:22px; font-weight:500; color:{color};'>{score}/10</div>"
            f"<div style='font-size:12px; color:var(--color-text-secondary);'>{check['status']}</div>"
            f"</div>",
            unsafe_allow_html=True
        )

st.markdown("")

# ── Flag details ──────────────────────────────────────────
any_flags = any(c["flag_count"] > 0 for c in checks.values())
if any_flags:
    with st.expander("View conviction flags detail", expanded=True):
        for ticker, check in checks.items():
            if check["flags"]:
                st.markdown(f"**{ticker}** — {check['flag_count']} flag(s)")
                for flag in check["flags"]:
                    st.markdown(f"&nbsp;&nbsp;&nbsp;• {flag}")
else:
    st.success("✅ All holdings pass 10-year conviction test — no action needed.")

# ── Replacement recommendation ────────────────────────────
if conviction_report["replacement"]:
    st.divider()
    worst  = conviction_report["worst_ticker"]
    best   = conviction_report["replacement"]
    fund_r = best.get("fundamentals", {})

    st.markdown(f"### 🔄 Recommended Replacement for **{worst}**")

    col_out, col_in = st.columns(2)

    with col_out:
        st.markdown(
            f"<div style='padding:14px; border:0.5px solid #ef4444; border-radius:8px; background:var(--color-background-secondary);'>"
            f"<div style='font-size:12px; color:#A32D2D; font-weight:500; margin-bottom:6px;'>CONSIDER REPLACING</div>"
            f"<div style='font-size:24px; font-weight:500;'>{worst}</div>"
            f"<div style='font-size:12px; color:var(--color-text-secondary); margin-top:4px;'>"
            f"{checks[worst]['flag_count']} conviction flags — thesis weakening</div>"
            f"<div style='margin-top:8px;'>"
            + "".join([f"<div style='font-size:11px; color:#A32D2D; margin-top:3px;'>⚠ {f[:60]}...</div>"
                       if len(f) > 60 else
                       f"<div style='font-size:11px; color:#A32D2D; margin-top:3px;'>⚠ {f}</div>"
                       for f in checks[worst]["flags"][:3]])
            + "</div></div>",
            unsafe_allow_html=True
        )

    with col_in:
        st.markdown(
            f"<div style='padding:14px; border:0.5px solid #10b981; border-radius:8px; background:var(--color-background-secondary);'>"
            f"<div style='font-size:12px; color:#3B6D11; font-weight:500; margin-bottom:6px;'>BEST REPLACEMENT — 10yr LENS</div>"
            f"<div style='font-size:24px; font-weight:500;'>{best['ticker']}</div>"
            f"<div style='font-size:13px; color:var(--color-text-secondary);'>{best['name']} · {best['sector']}</div>"
            f"<div style='font-size:12px; color:var(--color-text-primary); margin-top:8px; line-height:1.5;'>{best['thesis']}</div>"
            f"<div style='margin-top:8px; font-size:11px; color:#3B6D11;'>Why now: {best.get('rationale','Strong long-term fundamentals')}</div>"
            f"</div>",
            unsafe_allow_html=True
        )

    # Replacement fundamentals mini-table
    st.markdown("")
    st.caption(f"Key fundamentals — {best['ticker']}")
    r_cols = st.columns(5)
    metrics = [
        ("Price",        f"${fund_r.get('price', 0):,.0f}"),
        ("Fwd P/E",      f"{fund_r.get('forward_pe', 0):.1f}x"),
        ("ROE",          f"{fund_r.get('roe', 0):.0f}%"),
        ("Rev Growth",   f"{fund_r.get('revenue_growth', 0):.0f}%"),
        ("Analyst ↑",    f"+{fund_r.get('analyst_upside', 0):.0f}%"),
    ]
    for col, (label, val) in zip(r_cols, metrics):
        with col:
            st.metric(label, val)

    st.markdown(
        "<div style='margin-top:8px; padding:10px; background:var(--color-background-secondary); "
        "border-radius:8px; font-size:12px; color:var(--color-text-secondary);'>"
        "This is a research signal, not a sell order. Verify the thesis independently before acting. "
        "Long-term conviction investing means thesis changes — not price changes — drive decisions."
        "</div>",
        unsafe_allow_html=True
    )

elif conviction_report["all_pass"]:
    st.info("All 4 stocks pass the 10-year conviction test. No replacement needed at this time.")

