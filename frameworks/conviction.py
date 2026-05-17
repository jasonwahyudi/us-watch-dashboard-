# ============================================================
# US WATCH v2 — frameworks/conviction.py
# 10-Year Hold Conviction Checker + Replacement Engine
#
# Logic:
# 1. Check each portfolio stock against 10-year hold criteria
# 2. Flag any that fail the long-term thesis
# 3. Scan replacement universe → return single best pick
# ============================================================

import yfinance as yf
import numpy as np
import pandas as pd

# ── 10-Year conviction thresholds ────────────────────────────
CONVICTION_THRESHOLDS = {
    "quality_score_min":       4.0,   # BlackRock quality < 4 = weak moat
    "revenue_growth_min":     -5.0,   # % — negative = structural decline
    "profit_margin_min":       8.0,   # % — below 8% = commoditized
    "debt_to_equity_max":    300.0,   # > 300 = overleveraged
    "composite_score_min":     4.0,   # Overall score < 4 = thesis broken
    "aqr_trend_ok":         ["📈 TREND UP", "⚪ FLAT"],  # Trend DOWN = warning
}

# ── Replacement universe ──────────────────────────────────────
# Curated long-term quality candidates — grouped by thesis
REPLACEMENT_UNIVERSE = {
    # AI / Semiconductor
    "TSM":  {"name": "TSMC",            "thesis": "Monopoly on advanced chip manufacturing. No AI without TSMC.",          "sector": "Semiconductors"},
    "AMD":  {"name": "AMD",             "thesis": "NVDA's only credible challenger in AI GPU. Duopoly dynamic.",           "sector": "Semiconductors"},
    "ASML": {"name": "ASML",            "thesis": "Sole supplier of EUV lithography machines. Hard monopoly.",             "sector": "Semiconductor Equipment"},
    "QCOM": {"name": "Qualcomm",        "thesis": "Edge AI on mobile. 5G modem dominance. Automotive pivot.",             "sector": "Semiconductors"},
    # Big Tech / Quality Compounder
    "AAPL": {"name": "Apple",           "thesis": "Services flywheel + hardware loyalty. 1B+ locked ecosystem.",          "sector": "Technology"},
    "GOOGL": {"name": "Alphabet",       "thesis": "Search monopoly + YouTube + GCP + DeepMind. Undervalued AI assets.",  "sector": "Technology"},
    "META": {"name": "Meta",            "thesis": "Social media monopoly. 3B+ users. AI infrastructure leader.",         "sector": "Technology"},
    "AMZN": {"name": "Amazon",          "thesis": "AWS cloud leader + retail moat. Compounding FCF machine.",            "sector": "Cloud/Retail"},
    # Clean Energy / Nuclear
    "NEE":  {"name": "NextEra Energy",  "thesis": "Largest renewable utility. Regulatory moat. 10-year backlog.",        "sector": "Utilities"},
    "VST":  {"name": "Vistra Energy",   "thesis": "Nuclear + natural gas. AI datacenter power demand beneficiary.",       "sector": "Utilities"},
    "NRG":  {"name": "NRG Energy",      "thesis": "Retail energy + generation mix. Power demand secular tailwind.",       "sector": "Utilities"},
    # Quality Compounder / Financial
    "BRK-B": {"name": "Berkshire B",   "thesis": "Buffett's fortress. Insurance float + quality equity portfolio.",      "sector": "Diversified"},
    "V":    {"name": "Visa",            "thesis": "Payment network monopoly. 40%+ margins. Cashless secular trend.",     "sector": "Financials"},
    # Defensive Tech
    "ORCL": {"name": "Oracle",          "thesis": "Cloud database + AI infrastructure pivot. Government contracts.",      "sector": "Enterprise Tech"},
}

# ── Scoring weights for 10-year lens ─────────────────────────
LONGTERM_WEIGHTS = {
    "moat":         0.30,   # Competitive advantage durability
    "growth":       0.25,   # Revenue growth runway
    "profitability":0.20,   # Margin quality
    "balance_sheet":0.15,   # Debt safety
    "valuation":    0.10,   # Not overpaying (secondary for 10yr)
}


def check_conviction(ticker: str, fundamentals: dict,
                     composite_score: float, aqr_data: dict) -> dict:
    """
    Check if a stock passes the 10-year hold conviction test.
    Returns: {passes (bool), flags (list), conviction_score (0-10)}
    """
    fund  = fundamentals.get(ticker, {})
    thres = CONVICTION_THRESHOLDS
    flags = []

    # ── Test 1: Quality / moat ────────────────────────────
    quality = aqr_data.get("quality_rank", 5.0)
    if quality < thres["quality_score_min"]:
        flags.append(f"Low moat score ({quality:.1f}/10) — competitive advantage may be eroding")

    # ── Test 2: Revenue growth ────────────────────────────
    rev_growth = fund.get("revenue_growth", 0.0)
    if rev_growth < thres["revenue_growth_min"]:
        flags.append(f"Negative revenue growth ({rev_growth:.1f}%) — structural decline risk")

    # ── Test 3: Profit margin ─────────────────────────────
    margin = fund.get("profit_margin", 15.0)
    if margin < thres["profit_margin_min"]:
        flags.append(f"Thin profit margin ({margin:.1f}%) — commoditized business risk")

    # ── Test 4: Leverage ──────────────────────────────────
    de = fund.get("debt_to_equity", 50.0)
    if de > thres["debt_to_equity_max"]:
        flags.append(f"High debt/equity ({de:.0f}%) — balance sheet risk over 10yr horizon")

    # ── Test 5: Composite signal ──────────────────────────
    if composite_score < thres["composite_score_min"]:
        flags.append(f"Framework consensus weak ({composite_score:.1f}/10) — all 4 firms bearish")

    # ── Test 6: AQR trend ─────────────────────────────────
    ts_label = aqr_data.get("ts_label", "⚪ FLAT")
    if ts_label not in thres["aqr_trend_ok"]:
        flags.append(f"Price trend broken ({ts_label}) — momentum against you")

    # Conviction score: starts at 10, deduct per flag
    conviction_score = max(0, 10 - len(flags) * 1.8)

    return {
        "ticker":           ticker,
        "passes":           len(flags) == 0,
        "flags":            flags,
        "flag_count":       len(flags),
        "conviction_score": round(conviction_score, 1),
        "status": (
            "✅ HOLD — thesis intact"       if len(flags) == 0 else
            "⚠️ WATCH — 1–2 concerns"       if len(flags) <= 2 else
            "🔴 REVIEW — thesis weakening"
        )
    }


def _fetch_replacement_fundamentals(ticker: str) -> dict:
    """Fetch key fundamentals for a replacement candidate."""
    try:
        t    = yf.Ticker(ticker)
        info = t.info
        price  = info.get("currentPrice") or info.get("regularMarketPrice", 0)
        target = info.get("targetMeanPrice", price)
        return {
            "ticker":         ticker,
            "price":          price,
            "pe_ratio":       info.get("trailingPE") or 25.0,
            "forward_pe":     info.get("forwardPE") or 20.0,
            "pb_ratio":       info.get("priceToBook") or 3.0,
            "roe":            (info.get("returnOnEquity") or 0.15) * 100,
            "profit_margin":  (info.get("profitMargins") or 0.15) * 100,
            "revenue_growth": (info.get("revenueGrowth") or 0.05) * 100,
            "debt_to_equity": info.get("debtToEquity") or 50.0,
            "analyst_upside": ((target / price) - 1) * 100 if price > 0 else 0,
            "beta":           info.get("beta") or 1.0,
            "market_cap":     info.get("marketCap") or 0,
        }
    except:
        return {"ticker": ticker, "price": 0, "pe_ratio": 25, "forward_pe": 20,
                "roe": 15, "profit_margin": 15, "revenue_growth": 5,
                "debt_to_equity": 50, "analyst_upside": 5, "pb_ratio": 3,
                "beta": 1, "market_cap": 0}


def _score_longterm(fund: dict) -> float:
    """
    Score a candidate on 10-year lens (0-10).
    Prioritizes: moat (ROE) > growth > profitability > balance sheet > valuation
    """
    w = LONGTERM_WEIGHTS

    # Moat proxy: ROE (>20% = strong, <10% = weak)
    roe    = min(fund.get("roe", 15), 50)
    moat   = (roe - 5) / 45 * 10

    # Growth runway (revenue growth)
    rg     = fund.get("revenue_growth", 5)
    growth = max(0, min(10, (rg + 5) / 40 * 10))

    # Profitability (profit margin)
    pm     = min(fund.get("profit_margin", 15), 50)
    profit = max(0, min(10, (pm - 3) / 47 * 10))

    # Balance sheet (lower D/E = safer)
    de     = fund.get("debt_to_equity", 50)
    bs     = max(0, min(10, (300 - de) / 300 * 10))

    # Valuation (forward P/E — lower = cheaper)
    fpe    = fund.get("forward_pe", 20)
    val    = max(0, min(10, (50 - fpe) / 45 * 10))

    score  = (
        moat   * w["moat"] +
        growth * w["growth"] +
        profit * w["profitability"] +
        bs     * w["balance_sheet"] +
        val    * w["valuation"]
    )
    return round(min(10, max(0, score)), 2)


def find_best_replacement(flagged_ticker: str,
                           current_portfolio: list,
                           exclude: list = None) -> dict:
    """
    Scan REPLACEMENT_UNIVERSE, score each on 10-year lens.
    Returns single best replacement with full reasoning.

    Excludes: tickers already in portfolio + explicitly excluded.
    """
    portfolio_info = REPLACEMENT_UNIVERSE.get(flagged_ticker, {})
    flagged_sector = portfolio_info.get("sector", "")

    exclude_set = set(current_portfolio + (exclude or []))
    candidates  = {t: v for t, v in REPLACEMENT_UNIVERSE.items()
                   if t not in exclude_set}

    if not candidates:
        return {"error": "No candidates available"}

    scored = []
    for ticker, meta in candidates.items():
        fund  = _fetch_replacement_fundamentals(ticker)
        score = _score_longterm(fund)

        # Sector affinity bonus: same sector as flagged = +0.5
        sector_bonus = 0.5 if meta["sector"] == flagged_sector else 0.0

        scored.append({
            "ticker":        ticker,
            "name":          meta["name"],
            "sector":        meta["sector"],
            "thesis":        meta["thesis"],
            "score":         round(score + sector_bonus, 2),
            "raw_score":     score,
            "fundamentals":  fund,
            "sector_match":  meta["sector"] == flagged_sector,
        })

    scored.sort(key=lambda x: x["score"], reverse=True)
    best = scored[0]

    # Build human-readable rationale
    fund = best["fundamentals"]
    rationale_parts = []
    if fund["roe"] > 20:
        rationale_parts.append(f"ROE {fund['roe']:.0f}% (strong moat)")
    if fund["revenue_growth"] > 10:
        rationale_parts.append(f"revenue growing {fund['revenue_growth']:.0f}%/yr")
    if fund["profit_margin"] > 15:
        rationale_parts.append(f"{fund['profit_margin']:.0f}% profit margin")
    if fund["analyst_upside"] > 10:
        rationale_parts.append(f"analyst upside {fund['analyst_upside']:.0f}%")
    if fund["debt_to_equity"] < 80:
        rationale_parts.append("clean balance sheet")

    best["rationale"] = "; ".join(rationale_parts) if rationale_parts else "Strong long-term fundamentals"

    return best


def run_conviction_check(composites: list,
                          fundamentals: dict,
                          aqr_scores: dict) -> dict:
    """
    Master function: check all portfolio stocks.
    Returns full report including replacement if needed.
    """
    results    = {}
    flagged    = []
    portfolio  = [c["ticker"] for c in composites]

    for c in composites:
        ticker = c["ticker"]
        check  = check_conviction(
            ticker,
            fundamentals,
            c["composite_score"],
            aqr_scores.get(ticker, {})
        )
        results[ticker] = check
        if check["flag_count"] >= 2:
            flagged.append(ticker)

    # Find the most at-risk stock (highest flag count)
    replacement = None
    worst_ticker = None
    if flagged:
        worst_ticker = max(flagged, key=lambda t: results[t]["flag_count"])
        replacement  = find_best_replacement(worst_ticker, portfolio)

    return {
        "checks":         results,
        "flagged":        flagged,
        "worst_ticker":   worst_ticker,
        "replacement":    replacement,
        "all_pass":       len(flagged) == 0,
    }
