# ============================================================
# US WATCH v2 — frameworks/bridgewater.py
# Ray Dalio / Bridgewater Associates
# - All Weather: 4-Quadrant Growth × Inflation Regime
# - Pure Alpha: Risk Parity Weighting
# ============================================================

import numpy as np
import pandas as pd
from config import BRIDGEWATER_CONFIG, EQUITY_TICKERS, RISK_CONFIG


def _momentum(series: pd.Series, window: int) -> float:
    """% return over window days."""
    s = series.dropna()
    if len(s) < window:
        return 0.0
    return (s.iloc[-1] / s.iloc[-window] - 1) * 100


def detect_bridgewater_regime(macro_prices: pd.DataFrame) -> dict:
    """
    Bridgewater 4-Quadrant regime detection.

    Growth proxy    : SPY 6-month return  (positive = rising growth)
    Inflation proxy : TIP/IEF ratio 6-month return (positive = rising inflation)

    Returns:
        regime_key (str), regime_info (dict), growth_score (float), inflation_score (float)
    """
    cfg = BRIDGEWATER_CONFIG
    g_window = cfg["growth_lookback"]
    i_window = cfg["inflation_lookback"]

    # ── Growth signal ─────────────────────────────────────
    growth_score = 0.0
    if "SP500" in macro_prices.columns:
        growth_score = _momentum(macro_prices["SP500"], g_window)
    elif "SPY" in macro_prices.columns:
        growth_score = _momentum(macro_prices["SPY"], g_window)

    # ── Inflation signal ──────────────────────────────────
    inflation_score = 0.0
    if "TIP" in macro_prices.columns and "IEF" in macro_prices.columns:
        tip = macro_prices["TIP"].dropna()
        ief = macro_prices["IEF"].dropna()
        min_len = min(len(tip), len(ief))
        if min_len >= i_window:
            tip_aligned = tip.iloc[-min_len:]
            ief_aligned = ief.iloc[-min_len:]
            tip_ief_ratio = tip_aligned / ief_aligned
            inflation_score = _momentum(tip_ief_ratio, i_window)
    elif "TNX" in macro_prices.columns:
        # Fallback: rising 10Y yield = rising inflation
        tnx = macro_prices["TNX"].dropna()
        if len(tnx) >= i_window:
            inflation_score = tnx.iloc[-1] - tnx.iloc[-i_window]

    # ── Quadrant assignment ───────────────────────────────
    rising_growth    = growth_score > 0
    rising_inflation = inflation_score > 0

    if rising_growth and rising_inflation:
        key = "RISING_GROWTH_RISING_INFLATION"
    elif rising_growth and not rising_inflation:
        key = "RISING_GROWTH_FALLING_INFLATION"
    elif not rising_growth and rising_inflation:
        key = "FALLING_GROWTH_RISING_INFLATION"
    else:
        key = "FALLING_GROWTH_FALLING_INFLATION"

    regime_info = cfg["regimes"][key]

    return {
        "regime_key":        key,
        "regime_label":      regime_info["label"],
        "regime_description": regime_info["description"],
        "asset_preferences": regime_info["asset_prefs"],
        "growth_score":      round(growth_score, 2),
        "inflation_score":   round(inflation_score, 4),
        "rising_growth":     rising_growth,
        "rising_inflation":  rising_inflation,
    }


def compute_risk_parity_weights(prices_df: pd.DataFrame,
                                 tickers: list = None) -> dict:
    """
    Bridgewater Risk Parity: weight each asset inversely to its volatility.
    Equal risk contribution across portfolio.

    Returns: dict {ticker: weight (0-1)}
    """
    cfg_r = RISK_CONFIG
    syms  = tickers or EQUITY_TICKERS
    window = cfg_r["vol_window"]
    max_w  = cfg_r["max_weight"]
    min_w  = cfg_r["min_weight"]

    vols = {}
    for t in syms:
        if t not in prices_df.columns:
            continue
        px = prices_df[t].dropna()
        if len(px) < window:
            vols[t] = 0.20  # Default 20% vol
            continue
        daily_returns = px.pct_change().dropna()
        vol_daily = daily_returns.rolling(window).std().iloc[-1]
        vol_annual = vol_daily * np.sqrt(252)
        vols[t] = max(vol_annual, 0.05)  # Floor at 5%

    if not vols:
        equal = 1 / len(syms)
        return {t: equal for t in syms}

    # Inverse volatility weights
    inv_vols = {t: 1 / v for t, v in vols.items()}
    total    = sum(inv_vols.values())
    raw_weights = {t: v / total for t, v in inv_vols.items()}

    # Apply min/max constraints and renormalize
    weights = {}
    for t, w in raw_weights.items():
        weights[t] = max(min_w, min(max_w, w))

    total_w = sum(weights.values())
    weights = {t: round(w / total_w, 4) for t, w in weights.items()}

    return weights


def bridgewater_score(ticker: str, regime: dict, risk_parity_weights: dict) -> dict:
    """
    Combine regime preference + risk parity for Bridgewater composite score.
    Returns score 0-10.
    """
    regime_pref = regime["asset_preferences"].get(ticker, 1.0)
    rp_weight   = risk_parity_weights.get(ticker, 0.25)

    # Normalize risk parity weight to score contribution (0.05 min → 0.40 max maps to 0-10)
    rp_score = (rp_weight - 0.05) / (0.40 - 0.05) * 10
    rp_score = max(0, min(10, rp_score))

    # Regime preference maps 0.5-2.0 → 0-10
    regime_score = (regime_pref - 0.5) / (2.0 - 0.5) * 10
    regime_score = max(0, min(10, regime_score))

    composite = round(regime_score * 0.6 + rp_score * 0.4, 2)

    return {
        "framework":       "Bridgewater",
        "ticker":          ticker,
        "score":           composite,
        "regime_pref":     regime_pref,
        "rp_weight":       round(rp_weight * 100, 1),
        "regime_score":    round(regime_score, 2),
        "rp_score":        round(rp_score, 2),
    }
