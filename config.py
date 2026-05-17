# ============================================================
# US WATCH SYSTEM v2 — config.py
# Institutional-Grade Configuration
# Frameworks: Bridgewater · BlackRock · Goldman Sachs · AQR
# ============================================================

# ── WATCHLIST ────────────────────────────────────────────────
TICKERS = {
    "AVGO": {"name": "Broadcom",             "sector": "Semiconductors", "type": "growth"},
    "MSFT": {"name": "Microsoft",            "sector": "Technology",     "type": "quality"},
    "NVDA": {"name": "NVIDIA",               "sector": "Semiconductors", "type": "growth"},
    "CEG":  {"name": "Constellation Energy", "sector": "Utilities",      "type": "defensive"},
    "SPY":  {"name": "S&P 500 ETF",          "sector": "Benchmark",      "type": "benchmark"},
}

BENCHMARK        = "SPY"
EQUITY_TICKERS   = ["AVGO", "MSFT", "NVDA", "CEG"]   # Excl. benchmark for scoring
ALL_TICKERS      = list(TICKERS.keys())

# ── MACRO PROXY TICKERS (yfinance) ──────────────────────────
MACRO_TICKERS = {
    "VIX":   "^VIX",       # Fear gauge
    "TNX":   "^TNX",       # 10Y US Treasury yield
    "TIP":   "TIP",        # Inflation-linked bonds ETF
    "IEF":   "IEF",        # 7-10Y Treasury ETF
    "HYG":   "HYG",        # High-yield credit ETF
    "LQD":   "LQD",        # Investment-grade credit ETF
    "XLI":   "XLI",        # Industrials ETF (PMI proxy)
    "DXY":   "DX-Y.NYB",   # Dollar index
    "GLD":   "GLD",        # Gold (inflation hedge)
    "SP500": "^GSPC",      # S&P 500 index
}

# ════════════════════════════════════════════════════════════
# BRIDGEWATER — All Weather / Pure Alpha
# ════════════════════════════════════════════════════════════
BRIDGEWATER_CONFIG = {
    # Growth indicator: SPY 6-month return
    "growth_lookback":      126,   # ~6 months trading days
    # Inflation indicator: TIP/IEF ratio 6-month return
    "inflation_lookback":   126,
    # Risk parity lookback for vol estimation
    "risk_parity_window":   60,
    # Regime asset preferences (4 quadrants)
    "regimes": {
        "RISING_GROWTH_RISING_INFLATION": {
            "label": "Expansion 🔥",
            "description": "GDP up, CPI up — commodities & real assets win",
            "asset_prefs": {"NVDA": 1.6, "AVGO": 1.5, "MSFT": 1.2, "CEG": 1.4, "SPY": 1.3},
        },
        "RISING_GROWTH_FALLING_INFLATION": {
            "label": "Goldilocks ✨",
            "description": "Best regime — growth stocks dominate",
            "asset_prefs": {"NVDA": 1.9, "AVGO": 1.7, "MSFT": 1.5, "CEG": 0.9, "SPY": 1.4},
        },
        "FALLING_GROWTH_RISING_INFLATION": {
            "label": "Stagflation ⚠️",
            "description": "Worst regime — real assets, energy, nuclear",
            "asset_prefs": {"CEG": 1.8, "MSFT": 1.2, "SPY": 0.9, "AVGO": 0.7, "NVDA": 0.6},
        },
        "FALLING_GROWTH_FALLING_INFLATION": {
            "label": "Deflation/Recession 🔴",
            "description": "Bonds win — quality equity only",
            "asset_prefs": {"MSFT": 1.4, "CEG": 1.2, "SPY": 1.0, "AVGO": 0.7, "NVDA": 0.5},
        },
    },
}

# ════════════════════════════════════════════════════════════
# BLACKROCK — Factor Framework (Systematic Active Equity)
# ════════════════════════════════════════════════════════════
BLACKROCK_CONFIG = {
    "factors": {
        "quality": {
            "weight":      0.25,
            "components":  ["roe", "profit_margin", "debt_to_equity_inv"],
            "description": "ROE + margins + low leverage",
        },
        "value": {
            "weight":      0.20,
            "components":  ["pe_inv", "forward_pe_inv", "pb_inv"],
            "description": "Cheap vs history/peers",
        },
        "momentum": {
            "weight":      0.25,
            "components":  ["return_12_1", "return_6_1"],
            "description": "12-1 month & 6-1 month price return",
        },
        "low_volatility": {
            "weight":      0.15,
            "components":  ["vol_20d_inv", "vol_60d_inv"],
            "description": "Lower vol = higher score",
        },
        "sentiment": {
            "weight":      0.15,
            "components":  ["analyst_upside", "analyst_buy_pct"],
            "description": "Analyst consensus & upside",
        },
    },
    "momentum_windows": {
        "long":  252,   # 12 months
        "skip":  21,    # Skip last month (reversion effect)
        "med":   126,   # 6 months
    },
}

# ════════════════════════════════════════════════════════════
# GOLDMAN SACHS — Bull/Bear Indicator + Earnings Revision
# ════════════════════════════════════════════════════════════
GS_CONFIG = {
    # GS Bull/Bear Market Indicator components
    "bull_bear_components": {
        "yield_curve_slope":  0.20,   # 10Y - 2Y spread
        "credit_spread":      0.20,   # HYG/LQD ratio
        "equity_momentum":    0.20,   # SPY 12m momentum
        "pmi_proxy":          0.20,   # XLI (Industrials) momentum
        "valuation":          0.20,   # SPY trailing P/E vs historical avg
    },
    "earnings_revision_window": 90,   # 3 months for target price change
    # GS conviction signals
    "conviction_thresholds": {
        "strong_buy":   80,   # Percentile
        "buy":          60,
        "neutral":      40,
        "sell":         20,
    },
}

# ════════════════════════════════════════════════════════════
# AQR — Cross-Sectional Ranking + Time-Series Momentum
# ════════════════════════════════════════════════════════════
AQR_CONFIG = {
    # Cross-sectional momentum lookbacks
    "cs_momentum_windows": [252, 126, 63],   # 12m, 6m, 3m
    "cs_momentum_skip":    21,               # Skip last month
    # Value factor
    "value_metric":        "forward_pe_inv",  # Primary value signal
    # Combo weighting
    "factor_weights": {
        "cs_momentum": 0.40,
        "value":       0.30,
        "quality":     0.30,
    },
    # Time-series momentum (trend following)
    "ts_momentum_window":  252,
    "ts_vol_window":       60,
}

# ════════════════════════════════════════════════════════════
# RISK CONFIG (Risk Parity + Portfolio Stats)
# ════════════════════════════════════════════════════════════
RISK_CONFIG = {
    "vol_window":          60,    # Days for vol estimation
    "corr_window":         252,   # Days for correlation matrix
    "max_weight":          0.40,  # Max single position weight
    "min_weight":          0.05,  # Min single position weight
    "target_vol":          0.15,  # 15% annual portfolio vol target
    "risk_free_rate":      0.053, # Current US risk-free rate (~5.3%)
    "sharpe_window":       252,
}

# ════════════════════════════════════════════════════════════
# ALERT CONFIG
# ════════════════════════════════════════════════════════════
ALERT_CONFIG = {
    "daily_move":          0.03,   # ±3% daily
    "weekly_move":         0.07,   # ±7% weekly
    "rsi_oversold":        35,
    "rsi_overbought":      70,
    "drawdown_alert":     -0.10,   # -10% from 52w high
    "gs_bearish_threshold": 40,    # GS Bull/Bear below 40 = bearish
    "factor_divergence":   2.0,    # Z-score divergence alert
}
