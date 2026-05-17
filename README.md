# US Watch System v2 — Institutional Grade
## Jason's US Holdings Monitor

Frameworks: **Bridgewater · BlackRock · Goldman Sachs · AQR**

---

## What Each Framework Does

### 🔵 Bridgewater (Ray Dalio) — 25% weight
- **4-Quadrant Regime**: Growth × Inflation (not just VIX)
- **Risk Parity Weights**: Each asset weighted by inverse volatility
- Detects: Goldilocks / Expansion / Stagflation / Recession

### 🟢 BlackRock (Systematic Active Equity) — 30% weight
- **5-Factor Scoring**: Quality · Value · Momentum · Low Vol · Sentiment
- Cross-sectional z-scored (normalized across tickers)
- Momentum: Fama-French 12-1 month (skips last month for reversal)

### 🟡 Goldman Sachs (GSAM) — 25% weight
- **Bull/Bear Market Indicator**: 5 components (yield curve, credit, equity momentum, PMI, valuation)
- **Earnings Revision Momentum**: Change in analyst target prices
- **Conviction Score**: Percentile-ranked (Strong Buy / Buy / Neutral / Reduce / Sell)

### 🔴 AQR Capital (Cliff Asness) — 20% weight
- **Cross-Sectional Momentum**: Ranked relative to peers (not absolute)
- **Time-Series Momentum**: Trend-following signal (risk-adjusted 12m return)
- **Value × Momentum Combo**: Combined factor ranking

---

## Setup

```bash
# Install dependencies
pip3 install -r requirements.txt

# Run
cd ~/Downloads/us_watch_v2
streamlit run main.py
```

**Daily command:**
```bash
cd ~/Downloads/us_watch_v2 && streamlit run main.py
```

---

## Project Structure

```
us_watch_v2/
├── main.py                    ← Streamlit dashboard
├── config.py                  ← All parameters for all frameworks
├── requirements.txt
├── data/
│   └── fetcher.py             ← yfinance: prices + fundamentals + macro
├── frameworks/
│   ├── bridgewater.py         ← 4-quadrant regime + risk parity
│   ├── blackrock.py           ← 5-factor model (z-scored)
│   ├── goldman.py             ← Bull/Bear indicator + earnings revision
│   └── aqr.py                 ← CS momentum + TS trend + value
├── signals/
│   └── composite.py           ← Master aggregator + daily briefing
└── risk/
    └── portfolio_stats.py     ← Sharpe · Sortino · VaR · Correlation
```

---

## Dashboard Sections
1. **Bridgewater 4-Quadrant** — Growth × Inflation regime map
2. **GS Bull/Bear Indicator** — 0-100 composite with component breakdown
3. **BlackRock 5-Factor Heatmap** — Factor scores per ticker
4. **AQR Momentum Map** — 6m vs 12m scatter with trend signals
5. **Master Composite Scorecard** — Final ranked list with radar chart
6. **Risk Dashboard** — Sharpe, Sortino, Calmar, VaR, Correlation matrix
7. **Price Chart** — Normalized performance
8. **Daily Briefing** — Plain-language Jason summary
