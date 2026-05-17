# ============================================================
# US WATCH v2 — data/fetcher.py
# Unified data layer: prices, fundamentals, macro proxies
# ============================================================

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from config import ALL_TICKERS, MACRO_TICKERS


def fetch_prices(tickers: list = None, period: str = "2y") -> pd.DataFrame:
    """Fetch adjusted close prices. Returns DataFrame [dates × tickers]."""
    symbols = tickers or ALL_TICKERS
    try:
        raw = yf.download(symbols, period=period, auto_adjust=True, progress=False)
        if isinstance(raw.columns, pd.MultiIndex):
            prices = raw["Close"]
        else:
            prices = raw[["Close"]]
            prices.columns = symbols
        prices.dropna(how="all", inplace=True)
        return prices
    except Exception as e:
        print(f"[fetcher] Price fetch error: {e}")
        return pd.DataFrame()


def fetch_macro_prices(period: str = "2y") -> pd.DataFrame:
    """Fetch macro proxy ETF/index prices for regime detection."""
    symbols = list(MACRO_TICKERS.values())
    labels  = list(MACRO_TICKERS.keys())
    try:
        raw = yf.download(symbols, period=period, auto_adjust=True, progress=False)
        if isinstance(raw.columns, pd.MultiIndex):
            prices = raw["Close"]
        else:
            prices = raw[["Close"]]
        # Rename to labels
        rename_map = {v: k for k, v in MACRO_TICKERS.items()}
        prices.rename(columns=rename_map, inplace=True)
        prices.dropna(how="all", inplace=True)
        return prices
    except Exception as e:
        print(f"[fetcher] Macro price fetch error: {e}")
        return pd.DataFrame()


def fetch_fundamentals(ticker: str) -> dict:
    """
    Fetch full fundamental snapshot for one ticker.
    Covers: valuation, profitability, analyst consensus.
    """
    try:
        t = yf.Ticker(ticker)
        info = t.info

        # Analyst recommendations (last 3 months)
        try:
            recs = t.recommendations
            if recs is not None and not recs.empty:
                recent = recs.tail(10)
                buy_count    = recent.get("buy", pd.Series([0])).sum() + recent.get("strongBuy", pd.Series([0])).sum()
                total_count  = recent.shape[0]
                analyst_buy_pct = (buy_count / total_count * 100) if total_count > 0 else 50.0
            else:
                analyst_buy_pct = 50.0
        except:
            analyst_buy_pct = 50.0

        price    = info.get("currentPrice") or info.get("regularMarketPrice", 0)
        target   = info.get("targetMeanPrice", price)
        prev_target_est = target * 0.97  # Proxy: assume 3% upward revision if no history

        return {
            "ticker":              ticker,
            "price":               price,
            "prev_close":          info.get("previousClose", price),
            "52w_high":            info.get("fiftyTwoWeekHigh", price),
            "52w_low":             info.get("fiftyTwoWeekLow", price),
            "market_cap":          info.get("marketCap", 0),
            # Valuation
            "pe_ratio":            info.get("trailingPE") or 25.0,
            "forward_pe":          info.get("forwardPE") or 20.0,
            "pb_ratio":            info.get("priceToBook") or 3.0,
            "ps_ratio":            info.get("priceToSalesTrailing12Months") or 5.0,
            "ev_ebitda":           info.get("enterpriseToEbitda") or 15.0,
            # Profitability
            "roe":                 (info.get("returnOnEquity") or 0.15) * 100,
            "roa":                 (info.get("returnOnAssets") or 0.05) * 100,
            "profit_margin":       (info.get("profitMargins") or 0.15) * 100,
            "operating_margin":    (info.get("operatingMargins") or 0.20) * 100,
            "revenue_growth":      (info.get("revenueGrowth") or 0.0) * 100,
            "earnings_growth":     (info.get("earningsGrowth") or 0.0) * 100,
            # Leverage
            "debt_to_equity":      info.get("debtToEquity") or 50.0,
            "current_ratio":       info.get("currentRatio") or 1.5,
            # Analyst
            "analyst_target":      target,
            "analyst_target_prev": prev_target_est,
            "analyst_buy_pct":     analyst_buy_pct,
            "analyst_upside":      ((target / price) - 1) * 100 if price > 0 else 0,
            "num_analysts":        info.get("numberOfAnalystOpinions") or 0,
            # Risk
            "beta":                info.get("beta") or 1.0,
            "volume":              info.get("volume") or 0,
            "avg_volume":          info.get("averageVolume") or 1,
        }
    except Exception as e:
        print(f"[fetcher] Fundamentals error for {ticker}: {e}")
        return {"ticker": ticker, "price": 0, "pe_ratio": 25, "forward_pe": 20,
                "pb_ratio": 3, "roe": 15, "profit_margin": 15, "debt_to_equity": 50,
                "analyst_target": 0, "analyst_buy_pct": 50, "analyst_upside": 0,
                "beta": 1, "prev_close": 0, "52w_high": 0, "52w_low": 0,
                "market_cap": 0, "analyst_target_prev": 0, "revenue_growth": 0,
                "earnings_growth": 0, "current_ratio": 1.5, "roa": 5,
                "operating_margin": 20, "ps_ratio": 5, "ev_ebitda": 15,
                "num_analysts": 0, "volume": 0, "avg_volume": 1}


def fetch_all_fundamentals(tickers: list = None) -> dict:
    """Fetch fundamentals for all tickers. Returns dict[ticker → fundamentals]."""
    symbols = tickers or ALL_TICKERS
    return {t: fetch_fundamentals(t) for t in symbols}


def get_2y_yield() -> float:
    """Fetch 2Y Treasury yield for yield curve slope (GS indicator)."""
    try:
        t = yf.Ticker("^IRX")   # 13-week T-bill as proxy
        hist = t.history(period="5d")
        return hist["Close"].iloc[-1] / 10 if not hist.empty else 5.0
    except:
        return 5.0
