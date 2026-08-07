"""Stable application constants.

Keep league-independent constants here so UI edits do not require touching the
Streamlit entrypoint or application runtime.
"""

ROSTER_SLOTS = ["QB", "RB1", "RB2", "WR1", "WR2", "TE"] + [
    f"BN{i}" for i in range(1, 11)
]

STARTER_TARGETS = {"QB": 1, "RB": 2, "WR": 2, "TE": 1}

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
