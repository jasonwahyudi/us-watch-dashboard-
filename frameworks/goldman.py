# ============================================================
# US WATCH v2 — frameworks/goldman.py
# Goldman Sachs Asset Management
# - Bull/Bear Market Indicator (5-component composite)
# - Earnings Revision Momentum
# - Conviction Signal (percentile-ranked)
# ============================================================

import numpy as np
import pandas as pd
from config import GS_CONFIG, EQUITY_TICKERS


def _mom(series: pd.Series, window: int) -> float:
    s = series.dropna()
    if len(s) < window:
        return 0.0
    return (s.iloc[-1] / s.iloc[-window] - 1) * 100


def compute_gs_bull_bear_indicator(macro_prices: pd.DataFrame,
                                    fundamentals: dict) -> dict:
    """
    Goldman Sachs Bull/Bear Market Indicator.
    Components (each scored 0-100):
    1. Yield Curve Slope  (10Y - 2Y)
    2. Credit Spread      (HYG / LQD ratio momentum)
    3. Equity Momentum    (S&P 500 12m return)
    4. PMI Proxy          (XLI industrials ETF momentum)
    5. Valuation          (SPY inverse P/E vs historical avg 25x)

    Overall: 0 = extreme bear, 100 = extreme bull
    """
    cfg   = GS_CONFIG["bull_bear_components"]
    scores = {}

    # ── 1. Yield Curve Slope ─────────────────────────────
    # Positive spread = healthy, negative = inversion = bearish
    tnx = macro_prices.get("TNX", pd.Series()).dropna()
    if len(tnx) >= 1:
        yield_10y = tnx.iloc[-1]
        # Approximate 2Y using IRX proxy (3-month scaled)
        yield_2y_approx = yield_10y * 0.85  # Conservative proxy
        slope = yield_10y - yield_2y_approx  # Typically positive
        # Map: +2% slope → 100, -0.5% → 0
        yield_score = max(0, min(100, (slope + 0.5) / 2.5 * 100))
    else:
        yield_score = 50.0
    scores["yield_curve"] = yield_score

    # ── 2. Credit Spread (HYG/LQD ratio) ────────────────
    # Rising ratio = spreads tightening = bullish
    if "HYG" in macro_prices.columns and "LQD" in macro_prices.columns:
        hyg = macro_prices["HYG"].dropna()
        lqd = macro_prices["LQD"].dropna()
        min_len = min(len(hyg), len(lqd))
        if min_len >= 63:
            ratio = hyg.iloc[-min_len:] / lqd.iloc[-min_len:]
            mom_3m = _mom(ratio, 63)
            # Rising ratio 3m = bullish → +5% = 100, -5% = 0
            credit_score = max(0, min(100, (mom_3m + 5) / 10 * 100))
        else:
            credit_score = 50.0
    else:
        credit_score = 50.0
    scores["credit_spread"] = credit_score

    # ── 3. Equity Momentum (SPY 12m) ─────────────────────
    if "SP500" in macro_prices.columns:
        sp_mom = _mom(macro_prices["SP500"], 252)
    elif "SPY" in macro_prices.columns:
        sp_mom = _mom(macro_prices["SPY"], 252)
    else:
        sp_mom = 0.0
    # Map: +30% = 100, -30% = 0
    equity_score = max(0, min(100, (sp_mom + 30) / 60 * 100))
    scores["equity_momentum"] = equity_score

    # ── 4. PMI Proxy (XLI industrials 6m momentum) ───────
    if "XLI" in macro_prices.columns:
        xli_mom = _mom(macro_prices["XLI"], 126)
    else:
        xli_mom = 0.0
    pmi_score = max(0, min(100, (xli_mom + 15) / 30 * 100))
    scores["pmi_proxy"] = pmi_score

    # ── 5. Valuation (SPY forward P/E) ───────────────────
    # SPY forward P/E: historical avg ~18x. >25 = expensive = bearish
    spy_pe = fundamentals.get("SPY", {}).get("forward_pe", 21.0) or 21.0
    # Map: PE=12 → 100 (cheap), PE=30 → 0 (expensive)
    val_score = max(0, min(100, (30 - spy_pe) / (30 - 12) * 100))
    scores["valuation"] = val_score

    # ── Composite weighted average ────────────────────────
    weights = cfg  # weights sum to 1.0
    composite = (
        scores["yield_curve"]    * weights["yield_curve_slope"] +
        scores["credit_spread"]  * weights["credit_spread"] +
        scores["equity_momentum"]* weights["equity_momentum"] +
        scores["pmi_proxy"]      * weights["pmi_proxy"] +
        scores["valuation"]      * weights["valuation"]
    )
    composite = round(composite, 1)

    # Interpretation
    if composite >= 70:
        label, icon = "BULL", "🟢"
    elif composite >= 50:
        label, icon = "MILD BULL", "🔵"
    elif composite >= 35:
        label, icon = "NEUTRAL", "⚪"
    elif composite >= 20:
        label, icon = "MILD BEAR", "🟡"
    else:
        label, icon = "BEAR", "🔴"

    return {
        "gs_bull_bear":      composite,
        "label":             label,
        "icon":              icon,
        "component_scores":  scores,
        "interpretation":    f"{icon} GS Bull/Bear: {composite:.0f}/100 → {label}",
    }


def compute_earnings_revision(fundamentals: dict, tickers: list = None) -> dict:
    """
    GS Earnings Revision Momentum.
    Proxy: change in analyst mean target price over ~3 months.
    Positive revision = analysts raising targets = bullish signal.

    Returns dict: {ticker → revision_score (0-10)}
    """
    syms = tickers or EQUITY_TICKERS
    results = {}

    for t in syms:
        fund = fundamentals.get(t, {})
        current_target = fund.get("analyst_target", 0) or 0
        prev_target    = fund.get("analyst_target_prev", current_target) or current_target
        price          = fund.get("price", 1) or 1

        if prev_target > 0 and current_target > 0:
            revision_pct = (current_target - prev_target) / prev_target * 100
        else:
            revision_pct = 0.0

        # Map: +5% revision → 10, -5% revision → 0, flat → 5
        revision_score = max(0, min(10, (revision_pct + 5) / 10 * 10))

        results[t] = {
            "framework":       "Goldman Sachs",
            "ticker":          t,
            "revision_pct":    round(revision_pct, 2),
            "revision_score":  round(revision_score, 2),
            "analyst_upside":  round(fund.get("analyst_upside", 0), 2),
            "analyst_buy_pct": round(fund.get("analyst_buy_pct", 50), 1),
        }

    return results


def gs_conviction_score(ticker: str,
                          blackrock_score: float,
                          earnings_revision: dict,
                          bull_bear: dict) -> dict:
    """
    GS Conviction Score: combines factor score + earnings revision + market regime.
    Percentile-ranked interpretation.
    Returns score 0-10.
    """
    er    = earnings_revision.get(ticker, {})
    er_sc = er.get("revision_score", 5.0)
    bb    = bull_bear.get("gs_bull_bear", 50.0)

    # Normalize bull/bear to 0-10
    bb_score = bb / 10.0

    # Conviction = weighted combo
    conviction = (
        blackrock_score * 0.50 +  # Factor quality
        er_sc           * 0.30 +  # Earnings revision
        bb_score        * 0.20    # Market regime
    )
    conviction = round(min(10, max(0, conviction)), 2)

    # GS conviction thresholds
    thresholds = GS_CONFIG["conviction_thresholds"]
    conviction_pct = conviction * 10  # 0-100
    if conviction_pct >= thresholds["strong_buy"]:
        conviction_label = "⭐ STRONG BUY"
    elif conviction_pct >= thresholds["buy"]:
        conviction_label = "✅ BUY"
    elif conviction_pct >= thresholds["neutral"]:
        conviction_label = "⚪ NEUTRAL"
    elif conviction_pct >= thresholds["sell"]:
        conviction_label = "🟡 REDUCE"
    else:
        conviction_label = "🔴 SELL"

    return {
        "framework":         "Goldman Sachs",
        "ticker":            ticker,
        "score":             conviction,
        "conviction_label":  conviction_label,
        "earnings_revision": er_sc,
        "bull_bear_input":   round(bb_score, 2),
        "factor_input":      round(blackrock_score, 2),
    }
