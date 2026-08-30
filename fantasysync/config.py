"""Stable application constants.

Keep league-independent constants here so UI edits do not require touching the
Streamlit entrypoint or application runtime.
"""

ROSTER_SLOTS = ["QB", "RB1", "RB2", "WR1", "WR2", "TE", "FLEX"] + [
    f"BN{i}" for i in range(1, 10)
]

STARTER_TARGETS = {"QB": 1, "RB": 2, "WR": 2, "TE": 1}

# Default CPU draft-pick position weights (fantasysync/draft_engine.py's
# cpu_best_available()). >1 = CPU leans toward that position beyond what
# rank/need alone would suggest, <1 = leans away. RB/WR biased above QB/TE
# by default per Peter's request (2026-08-27) - real roster-construction
# wisdom, since RB/WR carry more injury/committee risk and more starting
# slots than QB/TE in this league's format. Adjustable live on the
# Settings page; these are just what a fresh session starts at.
DEFAULT_CPU_POSITION_WEIGHTS = {"QB": 0.90, "RB": 1.15, "WR": 1.15, "TE": 0.90}

# This league's scoring format - single source of truth for both the
# header display ("10-Team Half PPR") and the live data fetches in
# rankings_sources.py, which need it to pull ADP/points for the right
# format rather than defaulting to full PPR.
SCORING_FORMAT_LABEL = "Half PPR"
SCORING_FORMAT_FFCALCULATOR = "half-ppr"
SCORING_FORMAT_FANTASYPROS = "HALF"
PPR_RECEPTION_VALUE = 0.5

ADP_COLUMNS = {
    "Consensus": "consensus_adp",
    "Underdog": "underdog_adp",
    "NFL.com": "nfl_adp",
    "Sleeper": "sleeper_adp",
    "Yahoo": "yahoo_adp",
    "ESPN": "espn_adp",
    "FantasyPros": "fantasypros_adp",
    "WalterPicks": "walterpicks_adp",
}
