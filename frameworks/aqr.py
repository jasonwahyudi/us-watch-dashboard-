# ============================================================
# US WATCH v2 — frameworks/aqr.py
# AQR Capital Management (Cliff Asness)
# - Cross-Sectional Momentum Ranking
# - Value × Momentum Combo
# - Time-Series (Trend Following) Signal
# ============================================================

import numpy as np
import pandas as pd
from config import AQR_CONFIG, EQUITY_TICKERS


def _return(prices: pd.Series, window: int, skip: int = 0) -> float:
    """% return over window, with optional skip of recent days."""
    px = prices.dropna()
    if len(px) < window + skip:
        return 0.0
    end   = -skip if skip > 0 else len(px)
    start = -(window + skip)
    return (px.iloc[end-1] / px.iloc[start] - 1) * 100


def _rank_normalize(values: list) -> list:
    """
    Convert values to percentile ranks (0-10 scale).
    AQR uses cross-sectional ranking, not z-scores.
    """
    n   = len(values)
    arr = np.array(values, dtype=float)
    # Replace nan with median
    arr = np.where(np.isfinite(arr), arr, np.nanmedian(arr))
    # Rank 0 to n-1, then normalize to 0-10
    order = arr.argsort()
    ranks = np.empty_like(order)
    ranks[order] = np.arange(n)
    return list(ranks / (n - 1) * 10 if n > 1 else [5.0] * n)


def compute_cross_sectional_momentum(prices_df: pd.DataFrame,
                                      tickers: list) -> dict:
    """
    AQR Cross-Sectional Momentum.
    Multi-window: 12m, 6m, 3m (all skip last month).
    Cross-sectionally ranked (not z-scored) — pure relative ranking.
    """
    cfg     = AQR_CONFIG
    windows = cfg["cs_momentum_windows"]  # [252, 126, 63]
    skip    = cfg["cs_momentum_skip"]     # 21

    window_returns = {}
    for w in windows:
        rets = []
        for t in tickers:
            if t not in prices_df.columns:
                rets.append(0.0)
                continue
            rets.append(_return(prices_df[t], w, skip))
        window_returns[w] = rets

    # Rank each window cross-sectionally
    ranked = {}
    for w, rets in window_returns.items():
        ranked[w] = _rank_normalize(rets)

    # Combine: 12m=40%, 6m=40%, 3m=20%
    weights = {252: 0.40, 126: 0.40, 63: 0.20}
    scores  = {}
    for i, t in enumerate(tickers):
        composite = sum(ranked[w][i] * weights[w] for w in windows)
        scores[t] = {
            "cs_momentum_score": round(composite, 2),
            "return_12m":        round(window_returns[252][i], 2),
            "return_6m":         round(window_returns[126][i], 2),
            "return_3m":         round(window_returns[63][i], 2),
            "rank_12m":          round(ranked[252][i], 2),
            "rank_6m":           round(ranked[126][i], 2),
        }

    return scores


def compute_time_series_momentum(prices_df: pd.DataFrame,
                                  tickers: list) -> dict:
    """
    AQR Time-Series (Trend Following) Momentum.
    Signal: if 12m risk-adjusted return > 0 → long bias; else → reduce.
    Vol-scaled return (return / realized vol).
    """
    cfg   = AQR_CONFIG
    w_ts  = cfg["ts_momentum_window"]
    w_vol = cfg["ts_vol_window"]

    results = {}
    for t in tickers:
        if t not in prices_df.columns:
            results[t] = {"ts_signal": 0.0, "ts_label": "NEUTRAL"}
            continue

        px  = prices_df[t].dropna()
        ret = px.pct_change().dropna()

        if len(px) < w_ts:
            results[t] = {"ts_signal": 0.0, "ts_label": "NEUTRAL"}
            continue

        # 12-month raw return
        raw_return = _return(px, w_ts, 0)

        # Realized vol (60-day annualized)
        if len(ret) >= w_vol:
            vol = ret.rolling(w_vol).std().iloc[-1] * np.sqrt(252) * 100
        else:
            vol = 20.0

        # Risk-adjusted signal
        risk_adj = raw_return / max(vol, 5.0)

        # Map to 0-10: risk_adj +2.0 → 10, -2.0 → 0
        ts_score = max(0, min(10, (risk_adj + 2.0) / 4.0 * 10))

        label = ("📈 TREND UP"   if ts_score >= 6.5 else
                 "📉 TREND DOWN" if ts_score <= 3.5 else
                 "⚪ FLAT")

        results[t] = {
            "ts_signal":     round(ts_score, 2),
            "ts_label":      label,
            "raw_return_12m": round(raw_return, 2),
            "vol_60d":       round(vol, 2),
            "risk_adj":      round(risk_adj, 3),
        }

    return results


def compute_aqr_value(fundamentals: dict, tickers: list) -> dict:
    """
    AQR Value Factor: cross-sectional rank by forward P/E inverse.
    Cheaper = higher rank = higher score.
    """
    fpe_vals = []
    for t in tickers:
        fpe = fundamentals.get(t, {}).get("forward_pe", 20.0) or 20.0
        fpe_vals.append(1 / max(fpe, 1))  # Inverse: lower PE = higher value

    ranks = _rank_normalize(fpe_vals)
    return {t: round(ranks[i], 2) for i, t in enumerate(tickers)}


def aqr_composite(prices_df: pd.DataFrame,
                   fundamentals: dict,
                   tickers: list = None) -> dict:
    """
    AQR Full Composite: CS Momentum + TS Momentum + Value + Quality
    Returns dict: {ticker → {score, breakdown}}
    """
    syms = tickers or EQUITY_TICKERS
    cfg  = AQR_CONFIG

    cs_mom = compute_cross_sectional_momentum(prices_df, syms)
    ts_mom = compute_time_series_momentum(prices_df, syms)
    value  = compute_aqr_value(fundamentals, syms)

    # Quality proxy: ROE ranks cross-sectionally
    roe_vals = [fundamentals.get(t, {}).get("roe", 15.0) or 15.0 for t in syms]
    quality_ranks = _rank_normalize(roe_vals)
    quality = {t: round(quality_ranks[i], 2) for i, t in enumerate(syms)}

    results = {}
    fw = cfg["factor_weights"]
    for t in syms:
        cs_score = cs_mom.get(t, {}).get("cs_momentum_score", 5.0)
        ts_score = ts_mom.get(t, {}).get("ts_signal", 5.0)
        val_score = value.get(t, 5.0)
        qual_score = quality.get(t, 5.0)

        composite = (
            cs_score  * fw["cs_momentum"] +
            val_score * fw["value"] +
            qual_score* fw["quality"]
        )
        # Blend in TS momentum as overlay
        composite = composite * 0.80 + ts_score * 0.20
        composite = round(min(10, max(0, composite)), 2)

        results[t] = {
            "framework":         "AQR",
            "ticker":            t,
            "score":             composite,
            "cs_momentum":       cs_score,
            "ts_momentum":       ts_score,
            "ts_label":          ts_mom.get(t, {}).get("ts_label", "⚪ FLAT"),
            "value_rank":        val_score,
            "quality_rank":      qual_score,
            "return_12m":        cs_mom.get(t, {}).get("return_12m", 0),
            "return_6m":         cs_mom.get(t, {}).get("return_6m", 0),
        }

    return results
