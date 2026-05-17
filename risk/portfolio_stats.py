# ============================================================
# US WATCH v2 — risk/portfolio_stats.py
# Institutional Risk Metrics
# Sharpe · Sortino · Max Drawdown · Correlation · VaR
# ============================================================

import numpy as np
import pandas as pd
from config import RISK_CONFIG, EQUITY_TICKERS


def compute_sharpe(returns: pd.Series,
                    risk_free: float = None,
                    window: int = 252) -> float:
    """Annualized Sharpe Ratio."""
    rf  = risk_free or RISK_CONFIG["risk_free_rate"]
    ret = returns.dropna()
    if len(ret) < 30:
        return 0.0
    excess = ret - rf / 252
    if excess.std() == 0:
        return 0.0
    return round((excess.mean() / excess.std()) * np.sqrt(252), 3)


def compute_sortino(returns: pd.Series,
                     risk_free: float = None) -> float:
    """
    Sortino Ratio: only penalizes downside volatility.
    Better than Sharpe for asymmetric return distributions.
    """
    rf      = risk_free or RISK_CONFIG["risk_free_rate"]
    ret     = returns.dropna()
    excess  = ret - rf / 252
    downside = excess[excess < 0]
    if len(downside) == 0 or downside.std() == 0:
        return 0.0
    return round((excess.mean() / downside.std()) * np.sqrt(252), 3)


def compute_max_drawdown(prices: pd.Series) -> float:
    """Maximum drawdown from peak. Returns negative %."""
    px = prices.dropna()
    if px.empty:
        return 0.0
    rolling_max = px.cummax()
    drawdown    = (px - rolling_max) / rolling_max
    return round(drawdown.min() * 100, 2)


def compute_calmar(returns: pd.Series, prices: pd.Series) -> float:
    """Calmar Ratio = Annual Return / |Max Drawdown|. Preferred by trend-following funds."""
    ret  = returns.dropna()
    mdd  = abs(compute_max_drawdown(prices))
    if mdd == 0 or len(ret) < 30:
        return 0.0
    annual_ret = ret.mean() * 252 * 100
    return round(annual_ret / mdd, 3)


def compute_var(returns: pd.Series, confidence: float = 0.95) -> float:
    """
    Historical Value at Risk (VaR) at confidence level.
    Returns daily loss at given percentile (negative %).
    """
    ret = returns.dropna()
    if ret.empty:
        return 0.0
    return round(np.percentile(ret, (1 - confidence) * 100) * 100, 2)


def compute_correlation_matrix(prices_df: pd.DataFrame,
                                tickers: list = None) -> pd.DataFrame:
    """
    Return correlation matrix for given tickers.
    Used for: diversification assessment, portfolio construction.
    """
    syms = tickers or EQUITY_TICKERS
    avail = [t for t in syms if t in prices_df.columns]
    if not avail:
        return pd.DataFrame()
    returns = prices_df[avail].pct_change().dropna()
    return returns.corr().round(3)


def full_risk_report(prices_df: pd.DataFrame,
                      tickers: list = None) -> dict:
    """
    Full risk report for all tickers.
    Returns dict: {ticker → risk_metrics}
    """
    syms    = tickers or EQUITY_TICKERS
    rf      = RISK_CONFIG["risk_free_rate"]
    results = {}

    for t in syms:
        if t not in prices_df.columns:
            continue
        px  = prices_df[t].dropna()
        ret = px.pct_change().dropna()

        vol_20d  = ret.rolling(20).std().iloc[-1]  * np.sqrt(252) * 100 if len(ret) >= 20  else 0
        vol_60d  = ret.rolling(60).std().iloc[-1]  * np.sqrt(252) * 100 if len(ret) >= 60  else 0
        vol_252d = ret.rolling(252).std().iloc[-1] * np.sqrt(252) * 100 if len(ret) >= 252 else 0

        results[t] = {
            "ticker":        t,
            "sharpe":        compute_sharpe(ret, rf),
            "sortino":       compute_sortino(ret, rf),
            "calmar":        compute_calmar(ret, px),
            "max_drawdown":  compute_max_drawdown(px),
            "var_95":        compute_var(ret, 0.95),
            "vol_20d":       round(vol_20d, 2),
            "vol_60d":       round(vol_60d, 2),
            "vol_252d":      round(vol_252d, 2),
            "annual_return": round(ret.mean() * 252 * 100, 2),
        }

    return results
