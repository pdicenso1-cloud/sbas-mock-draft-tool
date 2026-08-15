"""Stable application constants.

Keep league-independent constants here so UI edits do not require touching the
Streamlit entrypoint or application runtime.
"""

ROSTER_SLOTS = ["QB", "RB1", "RB2", "WR1", "WR2", "TE", "FLEX"] + [
    f"BN{i}" for i in range(1, 10)
]

STARTER_TARGETS = {"QB": 1, "RB": 2, "WR": 2, "TE": 1}

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
