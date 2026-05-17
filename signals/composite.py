# ============================================================
# US WATCH v2 — signals/composite.py
# Master Signal Aggregator
# Combines: Bridgewater + BlackRock + Goldman + AQR → Final Score
# ============================================================

import numpy as np
from config import EQUITY_TICKERS, GS_CONFIG


# Framework weights in final composite
FRAMEWORK_WEIGHTS = {
    "bridgewater": 0.25,   # Regime + risk parity
    "blackrock":   0.30,   # Factor quality (most granular)
    "goldman":     0.25,   # Conviction + earnings revision
    "aqr":         0.20,   # Momentum + value ranking
}


def build_composite(
    ticker: str,
    bridgewater_score: dict,
    blackrock_score: dict,
    gs_conviction: dict,
    aqr_score: dict,
) -> dict:
    """
    Final composite score from all 4 frameworks.
    Each framework contributes 0-10 score, weighted.
    """
    bw  = bridgewater_score.get("score", 5.0)
    br  = blackrock_score.get("score",   5.0)
    gs  = gs_conviction.get("score",     5.0)
    aqr = aqr_score.get("score",         5.0)

    composite = (
        bw  * FRAMEWORK_WEIGHTS["bridgewater"] +
        br  * FRAMEWORK_WEIGHTS["blackrock"] +
        gs  * FRAMEWORK_WEIGHTS["goldman"] +
        aqr * FRAMEWORK_WEIGHTS["aqr"]
    )
    composite = round(min(10, max(0, composite)), 2)

    # ── Signal label ─────────────────────────────────────
    if composite >= 8.0:
        signal, badge = "⭐ STRONG BUY",  "green"
    elif composite >= 6.5:
        signal, badge = "🟢 BUY",         "green"
    elif composite >= 5.0:
        signal, badge = "🔵 HOLD",        "blue"
    elif composite >= 3.5:
        signal, badge = "🟡 REDUCE",      "yellow"
    else:
        signal, badge = "🔴 SELL / AVOID","red"

    # Agreement score: how aligned are the 4 frameworks?
    scores_list = [bw, br, gs, aqr]
    agreement   = round(10 - np.std(scores_list) * 2, 2)
    agreement   = max(0, min(10, agreement))

    agreement_label = ("🎯 High Conviction" if agreement >= 7 else
                       "⚠️ Mixed Signals"   if agreement >= 4 else
                       "❌ Conflicted")

    return {
        "ticker":              ticker,
        "composite_score":     composite,
        "signal":              signal,
        "badge":               badge,
        "agreement":           agreement,
        "agreement_label":     agreement_label,
        # Per-framework breakdown
        "bridgewater_score":   round(bw, 2),
        "blackrock_score":     round(br, 2),
        "goldman_score":       round(gs, 2),
        "aqr_score":           round(aqr, 2),
        # Sub-signals (for display)
        "gs_conviction":       gs_conviction.get("conviction_label", "N/A"),
        "aqr_trend":           aqr_score.get("ts_label", "N/A"),
        "br_momentum":         round(blackrock_score.get("momentum", 5.0), 2),
        "br_quality":          round(blackrock_score.get("quality", 5.0), 2),
        "br_value":            round(blackrock_score.get("value", 5.0), 2),
        "rp_weight":           bridgewater_score.get("rp_weight", 25.0),
    }


def rank_all(composites: list) -> list:
    """
    Add cross-sectional ranking to all composite results.
    AQR-style: relative rank matters as much as absolute score.
    """
    sorted_by_score = sorted(composites, key=lambda x: x["composite_score"], reverse=True)
    n = len(sorted_by_score)
    for i, item in enumerate(sorted_by_score):
        item["rank"] = i + 1
        item["rank_label"] = f"#{i+1} of {n}"
    return sorted_by_score


def generate_jason_summary(composites: list, regime: dict, gs_bb: dict) -> str:
    """
    Generate plain-language summary for Jason's daily review.
    Actionable, direct, no fluff.
    """
    top    = composites[0]
    bottom = composites[-1]
    regime_label = regime.get("regime_label", "Unknown")
    bb_score     = gs_bb.get("gs_bull_bear", 50)
    bb_label     = gs_bb.get("label", "NEUTRAL")

    lines = [
        f"📊 DAILY BRIEFING",
        f"Regime: {regime_label} | GS Bull/Bear: {bb_score:.0f}/100 ({bb_label})",
        f"",
        f"🏆 Best: {top['ticker']} — Score {top['composite_score']}/10 | {top['signal']}",
        f"⚠️  Weakest: {bottom['ticker']} — Score {bottom['composite_score']}/10 | {bottom['signal']}",
        f"",
        f"Ranking:",
    ]
    for c in composites:
        lines.append(
            f"  #{c['rank']} {c['ticker']:5s} {c['composite_score']:.1f}/10 | "
            f"{c['signal']:20s} | {c['agreement_label']}"
        )
    lines.append("")
    lines.append(
        "⚠️ Not financial advice. Always verify with primary sources."
    )
    return "\n".join(lines)
