# ============================================================
# US WATCH v2 — frameworks/blackrock.py
# BlackRock Systematic Active Equity — 5-Factor Model
# Factors: Quality · Value · Momentum · Low Volatility · Sentiment
# ============================================================

import numpy as np
import pandas as pd
from scipy import stats
from config import BLACKROCK_CONFIG, EQUITY_TICKERS


def _zscore(values: list) -> list:
    """Cross-sectional z-score normalization across tickers."""
    arr = np.array(values, dtype=float)
    # Replace nan/inf with median
    median = np.nanmedian(arr)
    arr = np.where(np.isfinite(arr), arr, median)
    if arr.std() == 0:
        return [0.0] * len(arr)
    return list(stats.zscore(arr))


def _winsorize(z_scores: list, limit: float = 3.0) -> list:
    """Cap z-scores at ±3 to remove outlier distortion."""
    return [max(-limit, min(limit, z)) for z in z_scores]


def _compute_momentum(prices_df: pd.DataFrame, ticker: str,
                       long_window: int, skip: int) -> float:
    """12-1 month momentum (standard Fama-French)."""
    if ticker not in prices_df.columns:
        return 0.0
    px = prices_df[ticker].dropna()
    if len(px) < long_window:
        return 0.0
    return (px.iloc[-(skip+1)] / px.iloc[-long_window] - 1) * 100


def _safe(val, default=0.0):
    """Safe value — return default if None/inf/nan."""
    if val is None or not np.isfinite(float(val)):
        return default
    return float(val)


def compute_quality_factor(fundamentals: dict, tickers: list) -> dict:
    """
    Quality Factor: ROE + Profit Margin + Low Leverage
    Cross-sectional z-scored then averaged.
    """
    cfg = BLACKROCK_CONFIG["factors"]["quality"]

    roe_vals  = [_safe(fundamentals[t].get("roe", 15)) for t in tickers]
    marg_vals = [_safe(fundamentals[t].get("profit_margin", 15)) for t in tickers]
    # Inverse debt: lower debt = higher quality
    de_vals   = [1 / max(_safe(fundamentals[t].get("debt_to_equity", 50)), 1) * 100
                 for t in tickers]

    z_roe  = _winsorize(_zscore(roe_vals))
    z_marg = _winsorize(_zscore(marg_vals))
    z_de   = _winsorize(_zscore(de_vals))

    scores = {}
    for i, t in enumerate(tickers):
        raw = (z_roe[i] + z_marg[i] + z_de[i]) / 3
        # Map z-score (-3 to +3) → (0 to 10)
        scores[t] = round((raw + 3) / 6 * 10, 2)

    return scores


def compute_value_factor(fundamentals: dict, tickers: list) -> dict:
    """
    Value Factor: Inverse P/E + Inverse Forward P/E + Inverse P/B
    Cross-sectional z-scored.
    """
    pe_inv  = [1 / max(_safe(fundamentals[t].get("pe_ratio", 25)), 1) for t in tickers]
    fpe_inv = [1 / max(_safe(fundamentals[t].get("forward_pe", 20)), 1) for t in tickers]
    pb_inv  = [1 / max(_safe(fundamentals[t].get("pb_ratio", 3)), 0.1) for t in tickers]

    z_pe  = _winsorize(_zscore(pe_inv))
    z_fpe = _winsorize(_zscore(fpe_inv))
    z_pb  = _winsorize(_zscore(pb_inv))

    scores = {}
    for i, t in enumerate(tickers):
        raw = (z_pe[i] * 0.4 + z_fpe[i] * 0.4 + z_pb[i] * 0.2)
        scores[t] = round((raw + 3) / 6 * 10, 2)

    return scores


def compute_momentum_factor(prices_df: pd.DataFrame, tickers: list) -> dict:
    """
    Momentum Factor (Fama-French): 12-1 month + 6-1 month
    Skip last month to avoid short-term reversal.
    """
    cfg = BLACKROCK_CONFIG
    w_long = cfg["momentum_windows"]["long"]   # 252
    w_skip = cfg["momentum_windows"]["skip"]   # 21
    w_med  = cfg["momentum_windows"]["med"]    # 126

    mom_12 = [_compute_momentum(prices_df, t, w_long, w_skip) for t in tickers]
    mom_6  = [_compute_momentum(prices_df, t, w_med,  w_skip) for t in tickers]

    z_12 = _winsorize(_zscore(mom_12))
    z_6  = _winsorize(_zscore(mom_6))

    scores = {}
    for i, t in enumerate(tickers):
        raw = z_12[i] * 0.6 + z_6[i] * 0.4
        scores[t] = round((raw + 3) / 6 * 10, 2)

    return scores


def compute_low_vol_factor(prices_df: pd.DataFrame, tickers: list) -> dict:
    """
    Low Volatility Factor: lower vol = higher score.
    Uses 20-day and 60-day realized vol.
    """
    vols_20, vols_60 = [], []
    for t in tickers:
        if t not in prices_df.columns:
            vols_20.append(0.20); vols_60.append(0.20)
            continue
        px = prices_df[t].dropna()
        ret = px.pct_change().dropna()
        v20 = ret.rolling(20).std().iloc[-1] * np.sqrt(252) if len(ret) >= 20 else 0.20
        v60 = ret.rolling(60).std().iloc[-1] * np.sqrt(252) if len(ret) >= 60 else 0.20
        vols_20.append(v20); vols_60.append(v60)

    # Invert: lower vol → higher score
    inv_20 = [-v for v in vols_20]
    inv_60 = [-v for v in vols_60]

    z_20 = _winsorize(_zscore(inv_20))
    z_60 = _winsorize(_zscore(inv_60))

    scores = {}
    for i, t in enumerate(tickers):
        raw = z_20[i] * 0.5 + z_60[i] * 0.5
        scores[t] = round((raw + 3) / 6 * 10, 2)

    return scores


def compute_sentiment_factor(fundamentals: dict, tickers: list) -> dict:
    """
    Sentiment Factor: Analyst buy % + Upside to target.
    """
    buy_pct = [_safe(fundamentals[t].get("analyst_buy_pct", 50)) for t in tickers]
    upside  = [_safe(fundamentals[t].get("analyst_upside", 0)) for t in tickers]

    z_buy    = _winsorize(_zscore(buy_pct))
    z_upside = _winsorize(_zscore(upside))

    scores = {}
    for i, t in enumerate(tickers):
        raw = z_buy[i] * 0.5 + z_upside[i] * 0.5
        scores[t] = round((raw + 3) / 6 * 10, 2)

    return scores


def blackrock_composite(
    prices_df: pd.DataFrame,
    fundamentals: dict,
    tickers: list = None,
) -> dict:
    """
    Full BlackRock 5-Factor composite score per ticker.
    Returns dict: {ticker → {score, factor_breakdown}}
    """
    syms = tickers or EQUITY_TICKERS
    cfg  = BLACKROCK_CONFIG["factors"]

    quality_scores  = compute_quality_factor(fundamentals, syms)
    value_scores    = compute_value_factor(fundamentals, syms)
    momentum_scores = compute_momentum_factor(prices_df, syms)
    lowvol_scores   = compute_low_vol_factor(prices_df, syms)
    sentiment_scores= compute_sentiment_factor(fundamentals, syms)

    results = {}
    for t in syms:
        q  = quality_scores.get(t, 5.0)
        v  = value_scores.get(t, 5.0)
        m  = momentum_scores.get(t, 5.0)
        lv = lowvol_scores.get(t, 5.0)
        s  = sentiment_scores.get(t, 5.0)

        composite = (
            q  * cfg["quality"]["weight"] +
            v  * cfg["value"]["weight"] +
            m  * cfg["momentum"]["weight"] +
            lv * cfg["low_volatility"]["weight"] +
            s  * cfg["sentiment"]["weight"]
        )

        results[t] = {
            "framework":     "BlackRock",
            "ticker":        t,
            "score":         round(composite, 2),
            "quality":       q,
            "value":         v,
            "momentum":      m,
            "low_volatility": lv,
            "sentiment":     s,
        }

    return results
