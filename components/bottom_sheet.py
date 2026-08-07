
from __future__ import annotations

import random

import json
import math
import time
from pathlib import Path
from typing import Dict, Optional

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from streamlit_autorefresh import st_autorefresh
from components.draft_room import (
    DraftRoomDependencies,
    render_draft_room,
)

from fantasysync.config import ADP_COLUMNS, ROSTER_SLOTS, STARTER_TARGETS
from fantasysync.paths import DATA_DIR, PROJECT_ROOT, STATE_FILE
from fantasysync.navigation import render_top_navigation
from styles.loader import inject_css

# Compatibility alias retained for older functions that reference APP_DIR.
APP_DIR = PROJECT_ROOT

# v7.0.1 startup preflight runs before application CSS. This prevents a missing
# data/style file from presenting as an unexplained black page.
_REQUIRED_STARTUP_FILES = [
    DATA_DIR / "players.csv",
    DATA_DIR / "teams.csv",
    DATA_DIR / "keepers.csv",
    PROJECT_ROOT / "styles" / "legacy.css",
]
_missing_startup_files = [p for p in _REQUIRED_STARTUP_FILES if not p.exists()]
if _missing_startup_files:
    st.error("FantasySync installation is incomplete.")
    st.write("Missing required files:")
    for _missing_path in _missing_startup_files:
        st.code(str(_missing_path))
    st.stop()


def clean(value) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def numeric(value, fallback=None):
    try:
        if pd.isna(value) or clean(value) == "":
            return fallback
        return float(value)
    except (TypeError, ValueError):
        return fallback


@st.cache_data
def load_defaults():
    players = pd.read_csv(DATA_DIR / "players.csv")
    teams = pd.read_csv(DATA_DIR / "teams.csv")
    keepers = pd.read_csv(DATA_DIR / "keepers.csv")

    for col in ["rank", "custom_rank", "market_rank", "consensus_adp", "underdog_adp",
                "nfl_adp", "sleeper_adp", "yahoo_adp", "espn_adp",
                "fantasypros_adp", "walterpicks_adp", "peter_score"]:
        if col in players.columns:
            players[col] = pd.to_numeric(players[col], errors="coerce")

    players["rank"] = players["rank"].fillna(9999).astype(int)
    players["custom_rank"] = players["custom_rank"].fillna(players["rank"]).astype(int)
    teams["team_id"] = teams["team_id"].astype(int)
    teams["draft_slot"] = teams["draft_slot"].astype(int)

    if not keepers.empty:
        keepers["team_id"] = pd.to_numeric(keepers["team_id"], errors="coerce").fillna(0).astype(int)
        keepers["keeper_round"] = pd.to_numeric(keepers["keeper_round"], errors="coerce").fillna(0).astype(int)

    return players, teams, keepers


def snake_order(teams_df: pd.DataFrame, rounds: int) -> pd.DataFrame:
    by_slot = {
        int(row.draft_slot): {"team_id": int(row.team_id), "team_name": clean(row.team_name)}
        for row in teams_df.itertuples()
    }
    rows = []
    overall = 1
    for rnd in range(1, rounds + 1):
        slots = list(range(1, len(teams_df) + 1))
        if rnd % 2 == 0:
            slots.reverse()
        for slot in slots:
            team = by_slot[slot]
            rows.append({
                "overall": overall,
                "round": rnd,
                "slot": slot,
                "original_team_id": team["team_id"],
                "original_owner": team["team_name"],
                "current_owner": team["team_name"],
                "keeper_player": "",
                "selected_player": "",
                "source": "",
            })
            overall += 1
    return pd.DataFrame(rows)


def assign_keepers(picks: pd.DataFrame, keepers_df: pd.DataFrame, teams_df: pd.DataFrame) -> pd.DataFrame:
    picks = picks.copy()
    team_name_by_id = dict(zip(teams_df["team_id"], teams_df["team_name"]))
    for row in keepers_df.itertuples():
        if not clean(row.player) or int(row.team_id) not in team_name_by_id:
            continue
        target_idx = None
        exact = getattr(row, "exact_pick_override", "")
        if clean(exact):
            matches = picks.index[picks["overall"] == int(float(exact))].tolist()
            target_idx = matches[0] if matches else None
        if target_idx is None:
            owner = team_name_by_id[int(row.team_id)]
            matches = picks.index[
                (picks["round"] == int(row.keeper_round))
                & (picks["current_owner"] == owner)
                & (picks["keeper_player"] == "")
            ].tolist()
            target_idx = matches[0] if matches else None
        if target_idx is not None:
            picks.at[target_idx, "keeper_player"] = clean(row.player)
            picks.at[target_idx, "selected_player"] = clean(row.player)
            picks.at[target_idx, "source"] = "Keeper"
    return picks


def init_state(force=False):
    players, teams, keepers = load_defaults()
    defaults = {
        "players": players.copy(),
        "teams": teams.copy(),
        "keepers": keepers.copy(),
        "rounds": 16,
        "user_team": clean(teams.iloc[0]["team_name"]),
        "picks": assign_keepers(snake_order(teams, 16), keepers, teams),
        "draft_message": "",
        "turn_started_at": None,
        "turn_pick_overall": None,
        "pick_clock_seconds": 60,
        "clock_running": False,
        "draft_active": False,
        "clock_paused_remaining": 60,
        "dock_level": 1,
        "cpu_variance_enabled": None,
        "cpu_variance_seed": None,
        "player_queue": [],
        "queue_auto_draft": False,
        "player_tray_level": 1,
    }
    for key, value in defaults.items():
        if force or key not in st.session_state:
            st.session_state[key] = value




PLAYER_TRAY_LEVELS = {
    0: {
        "name": "Lower",
        "board_height": 500,
        "player_height": 205,
    },
    1: {
        "name": "Standard",
        "board_height": 430,
        "player_height": 280,
    },
    2: {
        "name": "Raised",
        "board_height": 350,
        "player_height": 360,
    },
}


def player_tray_settings() -> dict:
    level = int(st.session_state.get("player_tray_level", 1))
    level = max(0, min(2, level))
    st.session_state.player_tray_level = level
    return PLAYER_TRAY_LEVELS[level]


def move_player_tray(direction: int):
    current = int(st.session_state.get("player_tray_level", 1))
    st.session_state.player_tray_level = max(
        0,
        min(2, current + direction),
    )


def render_player_tray_css():
    """Legacy no-op retained for compatibility with non-Draft Room pages."""
    return None



DOCK_LEVELS = {
    0: {"name": "Compact", "dock_vh": 24, "list_px": 178, "roster_vh": 20},
    1: {"name": "Standard", "dock_vh": 38, "list_px": 350, "roster_vh": 34},
    2: {"name": "Expanded", "dock_vh": 64, "list_px": 620, "roster_vh": 59},
}


def dock_settings() -> dict:
    level = int(st.session_state.get("dock_level", 1))
    level = max(0, min(2, level))
    st.session_state.dock_level = level
    return DOCK_LEVELS[level]


def move_dock(direction: int):
    current = int(st.session_state.get("dock_level", 1))
    st.session_state.dock_level = max(0, min(2, current + direction))


def render_dynamic_dock_css():
    settings = dock_settings()
    st.markdown(
        f"""
        <style>
        .st-key-draft_drawer {{
            height: {settings["dock_vh"]}vh !important;
            overflow: hidden !important;
            transition: height .22s ease-in-out !important;
        }}
        .st-key-draft_drawer {{
            position: fixed !important;
        }}
        .st-key-dock_controls {{
            position: absolute !important;
            top: 8px !important;
            right: 8px !important;
            z-index: 1005 !important;
            width: 40px !important;
            min-width: 40px !important;
            padding: 0 !important;
            margin: 0 !important;
            background: rgba(18, 27, 43, .96) !important;
            border: 1px solid rgba(150,170,210,.22) !important;
            border-radius: 9px !important;
            box-shadow: 0 4px 12px rgba(0,0,0,.28) !important;
        }}
        .st-key-dock_controls [data-testid="stVerticalBlock"] {{
            gap: 4px !important;
            padding: 4px !important;
        }}
        .st-key-dock_controls button {{
            min-height: 32px !important;
            height: 32px !important;
            padding: 0 !important;
            font-size: .94rem !important;
            font-weight: 900 !important;
            border-radius: 7px !important;
        }}
        
/* ============================================================
   FantasySync v6.7.1 — Full-width snake board + round.pick labels
   ============================================================ */

/* Force the Streamlit page shell to use the browser width, regardless of
   older max-width rules retained from pre-v6.7 sidebar builds. */
[data-testid="stMain"],
[data-testid="stMainBlockContainer"],
[data-testid="stAppViewContainer"] .main,
.main,
.main .block-container {{
    width: 100vw !important;
    max-width: 100vw !important;
    min-width: 0 !important;
    margin-left: 0 !important;
    margin-right: 0 !important;
    padding-left: 0 !important;
    padding-right: 0 !important;
    box-sizing: border-box !important;
}}

/* Navigation/header stay comfortably inset while the board itself uses nearly
   the full viewport. */
.st-key-v670_top_nav,
.st-key-v640_header,
.st-key-v63_draft_message {{
    width: calc(100vw - 28px) !important;
    max-width: calc(100vw - 28px) !important;
    margin-left: 14px !important;
    margin-right: 14px !important;
    box-sizing: border-box !important;
}}

/* The draft grid is intentionally wider than the ordinary content column. */
.st-key-v63_board_region {{
    width: calc(100vw - 16px) !important;
    max-width: calc(100vw - 16px) !important;
    margin-left: 8px !important;
    margin-right: 8px !important;
    padding-left: 0 !important;
    padding-right: 0 !important;
    box-sizing: border-box !important;
}}

.st-key-v63_board_region .v643-board-scroll,
.st-key-v63_board_region .v643-board-content,
.st-key-v63_board_region .snake-board-wrap,
.st-key-v63_board_region .snake-board-shell,
.st-key-v63_board_region .snake-board-grid,
.st-key-v63_board_region .snake-draft-grid {{
    width: 100% !important;
    max-width: 100% !important;
    min-width: 0 !important;
    margin-left: 0 !important;
    margin-right: 0 !important;
    box-sizing: border-box !important;
}}

/* Round labels no longer exist; prevent stale CSS from reserving space if a
   browser keeps an old DOM fragment during a rerun. */
.st-key-v63_board_region .snake-round-label {{
    display: none !important;
    width: 0 !important;
    min-width: 0 !important;
    max-width: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
    border: 0 !important;
}}

/* Pick notation is now the useful orientation cue, so make it a touch easier
   to read without competing with the player name. */
.st-key-v63_board_region .snake-pick {{
    font-size: .52rem !important;
    font-weight: 780 !important;
    letter-spacing: .01em !important;
    opacity: .78 !important;
}}

</style>
        """,
        unsafe_allow_html=True,
    )



def player_map() -> Dict[str, dict]:
    result = {}
    for row in st.session_state.players.itertuples():
        result[clean(row.player)] = {
            "position": clean(row.position),
            "nfl_team": clean(row.nfl_team),
            "rank": int(row.rank),
            "custom_rank": int(row.custom_rank),
            "tier": clean(row.tier),
            "consensus_adp": numeric(getattr(row, "consensus_adp", None)),
            "peter_score": numeric(getattr(row, "peter_score", None)),
        }
    return result


def unavailable_players() -> set:
    return {clean(v) for v in st.session_state.picks["selected_player"].tolist() if clean(v)}


def available_players() -> pd.DataFrame:
    unavailable = unavailable_players()
    df = st.session_state.players.copy()
    return df[~df["player"].map(clean).isin(unavailable)].sort_values(["custom_rank", "rank"])


def current_open_index() -> Optional[int]:
    for idx, row in st.session_state.picks.iterrows():
        if not clean(row["selected_player"]):
            return idx
    return None



def initialize_cpu_variance():
    """
    Choose one CPU behavior mode for the entire mock draft.

    Roughly 25% of drafts use mild top-five variance.
    The remaining drafts use strict best available.
    """
    if st.session_state.cpu_variance_enabled is None:
        seed = random.SystemRandom().randint(1, 2_147_483_647)
        st.session_state.cpu_variance_seed = seed
        rng = random.Random(seed)
        st.session_state.cpu_variance_enabled = rng.random() < 0.25


def reset_cpu_variance():
    """Choose a fresh CPU behavior mode for a newly reset draft."""
    st.session_state.cpu_variance_enabled = None
    st.session_state.cpu_variance_seed = None
    initialize_cpu_variance()


def cpu_best_available() -> Optional[str]:
    """
    Select the CPU player.

    Normal drafts take the best available player.
    Variance drafts choose among the top five with a strong top-heavy bias.
    """
    df = available_players()
    if df.empty:
        return None

    initialize_cpu_variance()

    if not st.session_state.cpu_variance_enabled:
        return clean(df.iloc[0]["player"])

    candidates = df.head(5).reset_index(drop=True)
    weights = [45, 25, 15, 10, 5][: len(candidates)]

    idx = current_open_index()
    overall_pick = 0
    if idx is not None:
        overall_pick = int(
            st.session_state.picks.loc[idx, "overall"]
        )

    seed = int(st.session_state.cpu_variance_seed or 0)
    rng = random.Random(seed + overall_pick * 10_007)

    selected_index = rng.choices(
        range(len(candidates)),
        weights=weights,
        k=1,
    )[0]

    return clean(candidates.iloc[selected_index]["player"])



def best_available() -> Optional[str]:
    df = available_players()
    return None if df.empty else clean(df.iloc[0]["player"])


def make_pick(idx: int, player: str, source: str):
    if not player:
        return
    if player in unavailable_players():
        st.error(f"{player} is already unavailable.")
        return
    st.session_state.picks.at[idx, "selected_player"] = player
    st.session_state.picks.at[idx, "source"] = source
    remove_from_queue(player)





def clean_player_queue():
    """Remove drafted, unavailable, missing, and duplicate players."""
    available = set(available_players()["player"].map(clean))
    cleaned_queue = []
    seen = set()

    for player in st.session_state.get("player_queue", []):
        player = clean(player)
        if player and player in available and player not in seen:
            cleaned_queue.append(player)
            seen.add(player)

    st.session_state.player_queue = cleaned_queue


def add_to_queue(player: str):
    clean_player_queue()
    player = clean(player)
    if player and player not in st.session_state.player_queue:
        st.session_state.player_queue.append(player)


def remove_from_queue(player: str):
    player = clean(player)
    st.session_state.player_queue = [
        queued
        for queued in st.session_state.get("player_queue", [])
        if clean(queued) != player
    ]


def move_queue_player(player: str, direction: int):
    clean_player_queue()
    player = clean(player)
    queue = list(st.session_state.player_queue)

    if player not in queue:
        return

    current_index = queue.index(player)
    target_index = max(
        0,
        min(len(queue) - 1, current_index + direction),
    )

    if current_index == target_index:
        return

    queue[current_index], queue[target_index] = (
        queue[target_index],
        queue[current_index],
    )
    st.session_state.player_queue = queue


def clear_player_queue():
    st.session_state.player_queue = []


def top_queue_player() -> Optional[str]:
    clean_player_queue()
    if not st.session_state.player_queue:
        return None
    return clean(st.session_state.player_queue[0])


def draft_top_queue_player():
    player = top_queue_player()
    if not player:
        st.session_state.draft_message = "Your queue is empty."
        return
    handle_user_draft_click(player)


def player_value_number(
    row: pd.Series,
    current_idx: int,
) -> Optional[int]:
    """Positive value means the player has fallen beyond ADP."""
    adp = numeric(row.get("consensus_adp"), None)
    if adp is None:
        return None

    current_pick = int(
        st.session_state.picks.loc[current_idx, "overall"]
    )
    return int(round(current_pick - adp))


def player_value_badge(
    row: pd.Series,
    current_idx: int,
) -> tuple[str, str]:
    value = player_value_number(row, current_idx)

    if value is None:
        return "—", "value-fair"
    if value >= 5:
        return f"+{value}", "value-steal"
    if value <= -5:
        return str(value), "value-reach"
    return "0", "value-fair"



def handle_user_draft_click(player: str):
    """Process a draft-button click before Streamlit's next rerun."""
    idx = current_open_index()

    if idx is None:
        st.session_state.draft_message = "The draft is already complete."
        return

    owner = clean(st.session_state.picks.loc[idx, "current_owner"])
    user_team = clean(st.session_state.user_team)

    if owner != user_team:
        st.session_state.draft_message = (
            f"It is currently {owner}'s turn."
        )
        return

    if player in unavailable_players():
        st.session_state.draft_message = (
            f"{player} is already unavailable."
        )
        return

    make_pick(idx, player, "User")
    st.session_state.draft_message = (
        f"{player} drafted by {user_team}."
    )
    reset_pick_clock()
    st.session_state.draft_active = True
    st.session_state.clock_running = True



def run_one_cpu_pick() -> bool:
    idx = current_open_index()

    if idx is None:
        st.session_state.draft_message = "The mock draft is complete."
        return False

    row = st.session_state.picks.loc[idx]
    owner = clean(row["current_owner"])

    if owner == clean(st.session_state.user_team):
        return False

    player = cpu_best_available()
    if not player:
        st.session_state.draft_message = "No available players remain."
        return False

    make_pick(idx, player, "CPU")
    st.session_state.draft_message = (
        f"CPU drafted {player} for {owner} at pick "
        f"{int(row['overall'])}."
    )
    return True


def run_cpu_until_user():
    made = 0
    while True:
        idx = current_open_index()
        if idx is None:
            st.session_state.draft_message = f"Draft complete. {made} CPU picks made."
            break
        row = st.session_state.picks.loc[idx]
        owner = clean(row["current_owner"])
        if owner == clean(st.session_state.user_team):
            st.session_state.draft_message = (
                f"{owner} is on the clock at pick {int(row['overall'])}. "
                f"CPU completed {made} pick(s)."
            )
            break
        player = cpu_best_available()
        if not player:
            st.session_state.draft_message = "No available players remain."
            break
        make_pick(idx, player, "CPU")
        made += 1


def selected_for_team(team_name: str) -> pd.DataFrame:
    return st.session_state.picks[
        (st.session_state.picks["current_owner"].map(clean) == clean(team_name))
        & (st.session_state.picks["selected_player"].map(clean) != "")
    ].sort_values("overall")


def roster_position_counts(team_name: str) -> Dict[str, int]:
    pmap = player_map()
    counts = {"QB": 0, "RB": 0, "WR": 0, "TE": 0}
    for player in selected_for_team(team_name)["selected_player"]:
        pos = pmap.get(clean(player), {}).get("position", "")
        if pos in counts:
            counts[pos] += 1
    return counts


def build_team_roster(team_name: str) -> pd.DataFrame:
    pmap = player_map()
    drafted = []
    for row in selected_for_team(team_name).itertuples():
        player = clean(row.selected_player)
        meta = pmap.get(player, {})
        drafted.append({"player": player, "position": meta.get("position", ""), "overall": int(row.overall)})

    starters = {"QB": None, "RB1": None, "RB2": None, "WR1": None, "WR2": None, "TE": None}
    bench = []
    for item in drafted:
        pos = item["position"]
        if pos == "QB" and starters["QB"] is None:
            starters["QB"] = item
        elif pos == "RB" and starters["RB1"] is None:
            starters["RB1"] = item
        elif pos == "RB" and starters["RB2"] is None:
            starters["RB2"] = item
        elif pos == "WR" and starters["WR1"] is None:
            starters["WR1"] = item
        elif pos == "WR" and starters["WR2"] is None:
            starters["WR2"] = item
        elif pos == "TE" and starters["TE"] is None:
            starters["TE"] = item
        else:
            bench.append(item)

    rows = []
    for slot in ["QB", "RB1", "RB2", "WR1", "WR2", "TE"]:
        item = starters[slot]
        rows.append({"Slot": slot, "Player": item["player"] if item else "", "Pos": item["position"] if item else ""})
    for i in range(10):
        item = bench[i] if i < len(bench) else None
        rows.append({"Slot": f"BN{i+1}", "Player": item["player"] if item else "", "Pos": item["position"] if item else ""})
    return pd.DataFrame(rows)


def next_user_pick(after_overall: int) -> Optional[int]:
    candidates = st.session_state.picks[
        (st.session_state.picks["overall"] > after_overall)
        & (st.session_state.picks["current_owner"].map(clean) == clean(st.session_state.user_team))
        & (st.session_state.picks["selected_player"].map(clean) == "")
    ]
    if candidates.empty:
        return None
    return int(candidates.iloc[0]["overall"])


def estimated_return_probability(adp: Optional[float], next_pick: Optional[int]) -> Optional[float]:
    if adp is None or next_pick is None:
        return None
    # Smooth heuristic: ADP well after next pick => likely to return.
    delta = adp - next_pick
    return max(0.01, min(0.99, 1.0 / (1.0 + math.exp(-delta / 5.5))))


def team_need_score(position: str, counts: Dict[str, int]) -> float:
    target = STARTER_TARGETS.get(position, 0)
    current = counts.get(position, 0)
    if current < target:
        return 28.0 - (current * 5)
    depth_targets = {"QB": 1, "RB": 5, "WR": 6, "TE": 2}
    if current < depth_targets.get(position, target):
        return 8.0
    return 0.0


def recommendations(limit=5) -> pd.DataFrame:
    idx = current_open_index()
    if idx is None:
        return pd.DataFrame()
    current = st.session_state.picks.loc[idx]
    overall = int(current["overall"])
    next_pick = next_user_pick(overall)
    counts = roster_position_counts(st.session_state.user_team)
    avail = available_players().head(35).copy()
    rows = []
    for row in avail.itertuples():
        pos = clean(row.position)
        rank = int(row.custom_rank)
        adp = numeric(getattr(row, "consensus_adp", None))
        return_prob = estimated_return_probability(adp, next_pick)
        need = team_need_score(pos, counts)
        rank_component = max(0.0, 55.0 - rank * 0.65)
        urgency = 0.0 if return_prob is None else (1.0 - return_prob) * 20.0
        score = rank_component + need + urgency
        if return_prob is None:
            return_text = "Unknown"
        else:
            return_text = f"{return_prob:.0%}"
        reason_bits = []
        if need >= 20:
            reason_bits.append(f"fills a starting {pos} need")
        elif need > 0:
            reason_bits.append(f"adds useful {pos} depth")
        else:
            reason_bits.append("best-player value")
        if return_prob is not None:
            if return_prob < 0.30:
                reason_bits.append("unlikely to reach your next pick")
            elif return_prob > 0.70:
                reason_bits.append("reasonable chance to wait")
            else:
                reason_bits.append("borderline next-pick availability")
        rows.append({
            "Player": clean(row.player),
            "Pos": pos,
            "Rank": rank,
            "ADP": adp,
            "Need Score": round(need, 1),
            "Chance Back": return_text,
            "Recommendation Score": round(score, 1),
            "Why": "; ".join(reason_bits),
        })
    return pd.DataFrame(rows).sort_values(
        ["Recommendation Score", "Rank"], ascending=[False, True]
    ).head(limit)


def rebuild_draft():
    st.session_state.draft_active = False
    st.session_state.picks = assign_keepers(
        snake_order(st.session_state.teams, int(st.session_state.rounds)),
        st.session_state.keepers,
        st.session_state.teams,
    )
    reset_cpu_variance()
    st.session_state.draft_message = (
        "Draft reset with current teams, keepers, and draft order."
    )
    reset_pick_clock()


def serializable_state():
    return {
        "rounds": int(st.session_state.rounds),
        "user_team": clean(st.session_state.user_team),
        "teams": st.session_state.teams.to_dict(orient="records"),
        "keepers": st.session_state.keepers.fillna("").to_dict(orient="records"),
        "picks": st.session_state.picks.fillna("").to_dict(orient="records"),
        "player_queue": list(st.session_state.player_queue),
        "queue_auto_draft": bool(st.session_state.queue_auto_draft),
    }


def save_state():
    STATE_FILE.write_text(json.dumps(serializable_state(), indent=2), encoding="utf-8")


def load_state_data(data):
    st.session_state.rounds = int(data["rounds"])
    st.session_state.user_team = clean(data["user_team"])
    st.session_state.teams = pd.DataFrame(data["teams"])
    st.session_state.keepers = pd.DataFrame(data["keepers"])
    st.session_state.picks = pd.DataFrame(data["picks"])
    st.session_state.player_queue = [
        clean(player)
        for player in data.get("player_queue", [])
    ]
    st.session_state.queue_auto_draft = bool(
        data.get("queue_auto_draft", False)
    )
    clean_player_queue()
    reset_pick_clock()


def snake_board_html() -> str:
    teams = st.session_state.teams.sort_values("draft_slot")
    team_by_slot = {
        int(row.draft_slot): {
            "team_id": int(row.team_id),
            "team_name": clean(row.team_name),
        }
        for row in teams.itertuples()
    }
    pmap = player_map()

    html = ['<div style="width:100%;">']
    html.append(
        '<div class="snake-draft-grid" style="display:grid;'
        'grid-template-columns:repeat(10,minmax(0,1fr));'
        'gap:2px;width:100%;">'
    )

    for slot in range(1, 11):
        team = team_by_slot.get(
            slot,
            {"team_id": slot, "team_name": f"Team {slot}"}
        )
        team_name = team["team_name"]
        team_id = team["team_id"]
        active = team_name == clean(st.session_state.user_team)
        active_class = " active" if active else ""
        check = "✓ " if active else ""

        html.append(
            f'<a href="?team={team_id}" target="_self" '
            f'style="text-decoration:none;color:inherit;">'
            f'<div class="snake-team-select{active_class}">'
            f'<div class="slot-num">{slot}</div>'
            f'<div class="team-label" title="{team_name}">'
            f'{check}{team_name}</div>'
            f'</div></a>'
        )

    for rnd in range(1, int(st.session_state.rounds) + 1):
        round_rows = st.session_state.picks[
            st.session_state.picks["round"] == rnd
        ]
        by_slot = {int(r.slot): r for r in round_rows.itertuples()}

        for slot in range(1, 11):
            r = by_slot.get(slot)

            if not r:
                html.append('<div class="snake-cell"></div>')
                continue

            player = clean(r.selected_player) or "—"
            pos = pmap.get(player, {}).get("position", "")
            source = clean(r.source)
            owner = clean(r.current_owner)
            tag = " K" if source == "Keeper" else ""

            classes = ["snake-cell"]
            if player == "—":
                classes.append("empty-pick")
            elif pos in {"QB", "RB", "WR", "TE"}:
                classes.append(f"pos-{pos.lower()}")
            if source == "Keeper":
                classes.append("keeper-pick")
            if owner == clean(st.session_state.user_team):
                classes.append("user-pick")
            current_idx = current_open_index()
            if current_idx is not None:
                current_overall = int(st.session_state.picks.loc[current_idx, "overall"])
                if int(r.overall) == current_overall:
                    classes.append("current-pick")

            badge = ""
            nfl = ""
            if player != "—":
                nfl = pmap.get(player, {}).get("nfl_team", "")
                if pos in {"QB", "RB", "WR", "TE"}:
                    badge = (
                        f'<span class="player-tile-badge badge-{pos.lower()}">{pos}</span>'
                        f'<span class="tile-nfl">{nfl}</span>'
                    )

            keeper_star = " ⭐" if source == "Keeper" else ""
            waiting = "Waiting…" if player == "—" else player

            # Sleeper-style snake notation keeps team columns fixed while
            # showing the actual pick sequence within each round.
            pick_in_round = slot if rnd % 2 == 1 else 11 - slot
            pick_label = f"{rnd}.{pick_in_round}"

            html.append(
                f'<div class="{" ".join(classes)}">'
                f'<div class="snake-pick">{pick_label}{keeper_star}</div>'
                f'<div class="snake-player" title="{player}">{waiting}</div>'
                f'<div>{badge}</div>'
                f'<div class="tile-owner" title="{owner}">{owner}</div>'
                f'</div>'
            )

    html.append("</div></div>")
    return "".join(html)





def sync_user_turn_clock():
    idx = current_open_index()

    if idx is None:
        st.session_state.turn_started_at = None
        st.session_state.turn_pick_overall = None
        st.session_state.clock_running = False
        st.session_state.draft_active = False
        st.session_state.clock_paused_remaining = int(st.session_state.pick_clock_seconds)
        return

    row = st.session_state.picks.loc[idx]
    owner = clean(row["current_owner"])
    overall = int(row["overall"])

    if owner != clean(st.session_state.user_team):
        st.session_state.turn_started_at = None
        st.session_state.turn_pick_overall = None
        st.session_state.clock_running = False
        st.session_state.clock_paused_remaining = int(st.session_state.pick_clock_seconds)
        return

    if st.session_state.turn_pick_overall != overall:
        st.session_state.turn_pick_overall = overall
        st.session_state.clock_paused_remaining = int(
            st.session_state.pick_clock_seconds
        )
        if st.session_state.clock_running:
            st.session_state.turn_started_at = time.time()
        else:
            st.session_state.turn_started_at = None


def remaining_pick_time() -> int:
    sync_user_turn_clock()

    if not st.session_state.clock_running:
        return max(0, int(st.session_state.clock_paused_remaining))

    if st.session_state.turn_started_at is None:
        st.session_state.turn_started_at = time.time()

    elapsed = int(time.time() - st.session_state.turn_started_at)
    return max(0, int(st.session_state.clock_paused_remaining) - elapsed)


def start_pick_clock():
    sync_user_turn_clock()
    if st.session_state.clock_running:
        return
    if int(st.session_state.clock_paused_remaining) <= 0:
        st.session_state.clock_paused_remaining = int(st.session_state.pick_clock_seconds)
    st.session_state.turn_started_at = time.time()
    st.session_state.clock_running = True


def pause_pick_clock():
    if not st.session_state.clock_running:
        return

    idx = current_open_index()
    if idx is not None:
        owner = clean(st.session_state.picks.loc[idx, "current_owner"])
        if owner == clean(st.session_state.user_team):
            st.session_state.clock_paused_remaining = remaining_pick_time()

    st.session_state.turn_started_at = None
    st.session_state.clock_running = False


def reset_pick_clock():
    st.session_state.turn_started_at = None
    st.session_state.clock_running = False
    st.session_state.clock_paused_remaining = int(st.session_state.pick_clock_seconds)


def auto_pick_user_if_expired():
    idx = current_open_index()
    if idx is None or not st.session_state.clock_running:
        return False

    row = st.session_state.picks.loc[idx]
    if clean(row["current_owner"]) != clean(st.session_state.user_team):
        return False

    if remaining_pick_time() > 0:
        return False

    player = None
    source = "User Auto"

    if st.session_state.queue_auto_draft:
        player = top_queue_player()
        if player:
            source = "Queue Auto"

    if not player:
        player = best_available()

    if not player:
        st.session_state.draft_message = (
            "Pick clock expired, but no available player remained."
        )
        return False

    make_pick(idx, player, source)
    st.session_state.draft_message = (
        f"Pick clock expired. {player} was auto-selected for "
        f"{st.session_state.user_team}."
    )
    reset_pick_clock()
    st.session_state.clock_running = True
    return True


def render_pick_clock():
    remaining = remaining_pick_time()
    state_label = "RUNNING" if st.session_state.clock_running else "PAUSED"

    if st.session_state.clock_running:
        # The clock counts down in the browser without rerunning Streamlit.
        # At zero, it reloads once so the server can perform the auto-pick.
        components.html(
            f"""
            <div id="pick-clock-wrap" style="
                border:1px solid rgba(128,128,128,.28);
                border-radius:12px;
                padding:10px;
                text-align:center;
                margin-bottom:8px;
                font-family:system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
                color:#F4F7FB;
                background:rgba(255,255,255,.015);
            ">
              <div style="font-size:.76rem;opacity:.72;">
                PICK CLOCK · {state_label}
              </div>
              <div id="pick-clock-value" style="
                  font-size:2rem;
                  font-weight:800;
                  color:#2A9D8F;
                  line-height:1.05;
                  margin-top:3px;
              "></div>
              <div style="font-size:.70rem;opacity:.64;margin-top:4px;">
                Best available is selected at 0:00
              </div>
            </div>

            <script>
            (() => {{
                let remaining = {int(remaining)};
                const value = document.getElementById("pick-clock-value");
                const wrap = document.getElementById("pick-clock-wrap");

                function draw() {{
                    const mins = Math.floor(remaining / 60);
                    const secs = remaining % 60;
                    value.textContent = `${{mins}}:${{String(secs).padStart(2, "0")}}`;

                    if (remaining <= 15) {{
                        value.style.color = "#E76F51";
                    }}

                    if (remaining <= 0) {{
                        value.textContent = "0:00";
                        wrap.style.opacity = "0.72";
                        window.parent.location.reload();
                        return;
                    }}

                    remaining -= 1;
                    window.setTimeout(draw, 1000);
                }}

                draw();
            }})();
            </script>
            """,
            height=116,
        )
    else:
        mins, secs = divmod(remaining, 60)
        st.markdown(
            f"""
            <div style="
                border:1px solid rgba(128,128,128,.28);
                border-radius:12px;
                padding:10px;
                text-align:center;
                margin-bottom:8px;
            ">
              <div style="font-size:.76rem;opacity:.72;">
                PICK CLOCK · {state_label}
              </div>
              <div style="
                  font-size:2rem;
                  font-weight:800;
                  color:#2A9D8F;
                  line-height:1.05;
                  margin-top:3px;
              ">
                {mins}:{secs:02d}
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    c1, c2 = st.columns(2)

    if not st.session_state.clock_running:
        label = (
            "▶️ Start"
            if remaining == int(st.session_state.pick_clock_seconds)
            else "▶️ Resume"
        )
        if c1.button(label, use_container_width=True, type="primary"):
            start_pick_clock()
            st.rerun()
    else:
        if c1.button("⏸️ Pause", use_container_width=True):
            pause_pick_clock()
            st.rerun()

    if c2.button("↺ Reset", use_container_width=True):
        reset_pick_clock()
        st.rerun()



def ensure_draft_filters():

    if "draft_position_filter" not in st.session_state:
        st.session_state.draft_position_filter = "ALL"
    if "draft_search" not in st.session_state:
        st.session_state.draft_search = ""

    # v7.3 player-table sorting persists through Streamlit/CPU reruns.
    if "player_sort_column" not in st.session_state:
        st.session_state.player_sort_column = "RK"
    if "player_sort_ascending" not in st.session_state:
        st.session_state.player_sort_ascending = True


PLAYER_SORT_CONFIG = {
    "RK": ("custom_rank", True),
    "PLAYER": ("player", True),
    "POS": ("position", True),
    "ADP": ("consensus_adp", True),
    "TIER": ("tier", True),
    "SCORE": ("peter_score", False),
    "PROJ": ("proj_pts", False),
    "AVG": ("proj_avg", False),
    "RUSH": ("rush_yds", False),
    "REC": ("rec_yds", False),
    "PASS": ("pass_yds", False),
    "BYE": ("bye", True),
    "VAL": ("_fs_value_sort", False),
}


def set_player_sort(column: str) -> None:
    """Toggle active player-table sorting without resetting the tray."""
    ensure_draft_filters()
    column = str(column).upper()
    if column not in PLAYER_SORT_CONFIG:
        return

    current = str(st.session_state.player_sort_column).upper()
    if current == column:
        st.session_state.player_sort_ascending = not bool(
            st.session_state.player_sort_ascending
        )
    else:
        st.session_state.player_sort_column = column
        st.session_state.player_sort_ascending = PLAYER_SORT_CONFIG[column][1]


def sort_player_pool(pool: pd.DataFrame, current_idx: int) -> pd.DataFrame:
    """Sort the filtered draft pool by the active user-selected column."""
    ensure_draft_filters()
    result = pool.copy()

    # VAL is live value vs the current overall pick.
    adp_numeric = pd.to_numeric(
        result.get("consensus_adp"),
        errors="coerce",
    )
    current_pick = int(st.session_state.picks.loc[current_idx, "overall"])
    result["_fs_value_sort"] = current_pick - adp_numeric

    column = str(st.session_state.player_sort_column).upper()
    field, default_ascending = PLAYER_SORT_CONFIG.get(
        column,
        ("custom_rank", True),
    )
    ascending = bool(
        st.session_state.get(
            "player_sort_ascending",
            default_ascending,
        )
    )

    if field not in result.columns:
        field = "custom_rank"
        ascending = True

    numeric_fields = {
        "custom_rank",
        "consensus_adp",
        "peter_score",
        "proj_pts",
        "proj_avg",
        "rush_yds",
        "rec_yds",
        "pass_yds",
        "bye",
        "_fs_value_sort",
    }

    if field in numeric_fields:
        result["_fs_active_sort"] = pd.to_numeric(
            result[field],
            errors="coerce",
        )
        result = result.sort_values(
            ["_fs_active_sort", "custom_rank"],
            ascending=[ascending, True],
            na_position="last",
            kind="stable",
        )
    else:
        result["_fs_active_sort"] = (
            result[field].fillna("").astype(str).str.casefold()
        )
        result = result.sort_values(
            ["_fs_active_sort", "custom_rank"],
            ascending=[ascending, True],
            na_position="last",
            kind="stable",
        )

    return result.drop(
        columns=["_fs_active_sort", "_fs_value_sort"],
        errors="ignore",
    )


def render_position_filter():
    positions = ["ALL", "QB", "RB", "WR", "TE"]
    labels = {"ALL": "ALL", "QB": "QB", "RB": "RB", "WR": "WR", "TE": "TE"}
    cols = st.columns(len(positions))
    for i, pos in enumerate(positions):
        active = st.session_state.draft_position_filter == pos
        button_type = "primary" if active else "secondary"
        if cols[i].button(
            labels[pos],
            key=f"draft_pos_{pos}",
            use_container_width=True,
            type=button_type,
        ):
            st.session_state.draft_position_filter = pos
            st.rerun()



def render_player_filter_rail():
    ensure_draft_filters()

    st.text_input(
        "Search available players",
        key="draft_search",
        placeholder="🔍 Find player",
        label_visibility="collapsed",
    )

    positions = ["ALL", "QB", "RB", "WR", "TE"]
    for pos in positions:
        active = st.session_state.draft_position_filter == pos
        if st.button(
            pos,
            key=f"draft_rail_pos_{pos}",
            use_container_width=True,
            type="primary" if active else "secondary",
        ):
            st.session_state.draft_position_filter = pos
            st.rerun()



def filtered_draft_pool() -> pd.DataFrame:
    pool = available_players().copy()
    selected_pos = st.session_state.draft_position_filter
    if selected_pos != "ALL":
        pool = pool[pool["position"] == selected_pos]
    query = clean(st.session_state.draft_search)
    if query:
        pool = pool[pool["player"].str.contains(query, case=False, na=False)]
    return pool.sort_values(["custom_rank", "rank"])




def apply_team_query_selection():
    team_id_param = st.query_params.get("team")
    if not team_id_param:
        return

    try:
        team_id = int(team_id_param)
    except (TypeError, ValueError):
        return

    match = st.session_state.teams[
        st.session_state.teams["team_id"] == team_id
    ]

    if match.empty:
        return

    team_name = clean(match.iloc[0]["team_name"])

    if team_name != clean(st.session_state.user_team):
        st.session_state.user_team = team_name
        reset_pick_clock()

    st.query_params.clear()



def player_stat_value(row, *names, default="—"):
    for name in names:
        if hasattr(row, name):
            value = getattr(row, name)
            if not pd.isna(value) and clean(value) != "":
                try:
                    number = float(value)
                    return f"{number:.1f}" if number % 1 else f"{int(number)}"
                except Exception:
                    return clean(value)
    return default


def render_compact_recommendations(limit=4):
    recs = recommendations(limit)
    st.markdown("<div class='roster-tab-title'>RECOMMENDATIONS</div>", unsafe_allow_html=True)
    if recs.empty:
        st.caption("No recommendations available.")
        return

    for row in recs.itertuples():
        st.markdown(
            f"""
            <div class="compact-rec">
                <div class="compact-rec-name">{clean(row.Player)}</div>
                <div class="compact-rec-meta">
                    {clean(row.Pos)} · Rank {row.Rank} · ADP {row.ADP if not pd.isna(row.ADP) else "—"} · {clean(getattr(row, "Chance_Back", ""))}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def current_user_roster():
    roster = build_team_roster(st.session_state.user_team)
    # This league's visible roster excludes kicker and defense.
    return roster[
        ~roster["Slot"].astype(str).str.upper().isin(
            {"K", "DEF", "DST", "D/ST"}
        )
    ].reset_index(drop=True)


def render_live_roster_header():
    roster = current_user_roster()
    filled = int((roster["Player"] != "").sum())

    st.markdown(
        f"""
        <div class="roster-header-row">
            <div class="roster-header-label">ROSTER</div>
            <div class="roster-header-team">{st.session_state.user_team}</div>
            <div class="roster-header-count">{filled} / 16 players</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_live_roster_rows():
    roster = current_user_roster()

    for row in roster.itertuples():
        player = clean(row.Player)
        slot = clean(row.Slot)
        pos = clean(row.Pos)

        if slot.startswith("RB"):
            slot_group = "RB"
        elif slot.startswith("WR"):
            slot_group = "WR"
        elif slot.startswith("QB"):
            slot_group = "QB"
        elif slot.startswith("TE"):
            slot_group = "TE"
        else:
            slot_group = "BN"

        if player:
            player_html = (
                f'<div class="roster-player-wrap">'
                f'<div class="roster-line-player">'
                f'<span>{player}</span>'
                f'<span class="roster-inline-pos">({pos})</span>'
                f'</div>'
                f'</div>'
            )
        else:
            player_html = (
                '<div class="roster-player-wrap">'
                '<div class="roster-empty">Empty</div>'
                '</div>'
            )

        st.markdown(
            f"""
            <div class="roster-line">
                <div class="roster-slot-pill roster-slot-{slot_group}">{slot}</div>
                {player_html}
            </div>
            """,
            unsafe_allow_html=True,
        )



def render_v53_header(current_idx: Optional[int]):
    if current_idx is None:
        round_number = int(st.session_state.rounds)
        overall_pick = len(st.session_state.picks)
        remaining_text = "DONE"
        clock_label = "COMPLETE"
    else:
        current = st.session_state.picks.loc[current_idx]
        round_number = int(current["round"])
        overall_pick = int(current["overall"])
        remaining = remaining_pick_time()
        remaining_text = f"{remaining // 60}:{remaining % 60:02d}"
        clock_label = (
            "YOUR PICK"
            if clean(current["current_owner"]) == clean(st.session_state.user_team)
            else "CPU PICK"
        )

    with st.container(key="v53_header"):
        title_col, cpu_col, clock_col, action_col = st.columns(
            [5.5, 1.05, .85, 1.15],
            gap="small",
        )

        with title_col:
            st.markdown(
                f"""
                <div class="v53-title">Mock Draft</div>
                <div class="v53-meta">
                    <div class="v53-chip">Round {round_number} · Pick {overall_pick}</div>
                    <div class="v53-chip">10-Team PPR</div>
                    <div class="v53-chip">Snake Draft</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with cpu_col:
            status = "CPU ON" if st.session_state.draft_active else "CPU PAUSED"
            st.markdown(
                f'<div class="v53-cpu">● {status}</div>',
                unsafe_allow_html=True,
            )

        with clock_col:
            st.markdown(
                f"""
                <div class="v53-clock">
                    <div class="v53-clock-time">{remaining_text}</div>
                    <div class="v53-clock-label">{clock_label}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with action_col:
            with st.container(key="v53_header_action"):
                if st.session_state.draft_active:
                    if st.button(
                        "Pause Draft",
                        use_container_width=True,
                        key="v53_pause",
                    ):
                        st.session_state.draft_active = False
                        pause_pick_clock()
                        st.rerun()
                else:
                    if st.button(
                        "Start Draft",
                        use_container_width=True,
                        key="v53_start",
                    ):
                        st.session_state.draft_active = True
                        if current_idx is not None:
                            current_owner = clean(
                                st.session_state.picks.loc[
                                    current_idx,
                                    "current_owner",
                                ]
                            )
                            if current_owner == clean(st.session_state.user_team):
                                start_pick_clock()
                        st.rerun()


def render_v61_player_toolbar():
    """Compact tray toolbar: search + always-visible position filters."""
    ensure_draft_filters()

    search_col, filter_col = st.columns(
        [2.65, 7.35],
        gap="small",
    )

    with search_col:
        st.text_input(
            "Search players",
            key="draft_search",
            placeholder="⌕  Search players...",
            label_visibility="collapsed",
        )

    with filter_col:
        render_position_filter()


def v53_recommendation_row():
    recs = recommendations(limit=1)
    if recs.empty:
        return None
    return recs.iloc[0]


def render_v53_recommendation(
    current_idx: int,
    allow_draft: bool,
):
    row = v53_recommendation_row()

    if row is None:
        st.markdown(
            """
            <div class="v53-rec-eyebrow">★ FANTASYSYNC RECOMMENDATION</div>
            <div class="queue-empty">No recommendation is available.</div>
            """,
            unsafe_allow_html=True,
        )
        return

    player = clean(row.get("Player", row.get("player", "")))
    pos = clean(row.get("Pos", row.get("position", "")))
    nfl_team = clean(row.get("Team", row.get("nfl_team", "")))
    rank = row.get("Rank", row.get("custom_rank", "—"))
    adp = row.get("ADP", row.get("consensus_adp", "—"))
    confidence = 94

    initials = "".join(
        part[0]
        for part in player.replace("-", " ").split()
        if part
    )[:2].upper() or "FS"

    st.markdown(
        f"""
        <div class="v53-rec-eyebrow">★ FANTASYSYNC RECOMMENDATION</div>
        <div class="v53-rec-person">
            <div class="v53-avatar">{initials}</div>
            <div>
                <div class="v53-rec-name">{player}</div>
                <div class="v53-rec-meta">{pos} · {nfl_team}</div>
                <div class="v53-rec-meta">Rank {rank} &nbsp;&nbsp; ADP {adp}</div>
            </div>
            <div class="v53-confidence">
                <div class="v53-confidence-number">{confidence}%</div>
                <div class="v53-confidence-label">CONFIDENCE</div>
            </div>
        </div>
        <div class="v53-rec-divider"></div>
        <div class="v53-rec-copy-title">Why we love this pick</div>
        <div class="v53-rec-reason"><span class="v53-check">✓</span>Best available player at a premium position</div>
        <div class="v53-rec-reason"><span class="v53-check">✓</span>Strong value relative to current ADP</div>
        <div class="v53-rec-reason"><span class="v53-check">✓</span>Fits the selected roster's current needs</div>
        <div class="v53-rec-reason"><span class="v53-check">✓</span>Helps avoid the next positional tier drop</div>
        """,
        unsafe_allow_html=True,
    )

    with st.container(key="v53_rec_button"):
        if st.button(
            f"DRAFT {player.upper()}  ›",
            use_container_width=True,
            type="primary",
            disabled=not allow_draft,
            key=f"v53_recommendation_{current_idx}_{player}",
        ):
            handle_user_draft_click(player)
            st.rerun()






def render_player_picker_table(
    current_idx: int,
    allow_draft: bool = True,
    list_height_override: Optional[int] = None,
):
    clean_player_queue()
    ensure_draft_filters()

    pool = filtered_draft_pool()

    if pool.empty:
        st.warning("No available players match this filter.")
        return

    pool = sort_player_pool(pool, current_idx)

    headers = [
        "",
        "",
        "RK",
        "PLAYER",
        "POS",
        "ADP",
        "TIER",
        "SCORE",
        "PROJ",
        "AVG",
        "RUSH",
        "REC",
        "PASS",
        "BYE",
        "VAL",
    ]
    widths = [
        0.38,
        0.36,
        0.40,
        1.65,
        0.46,
        0.50,
        0.48,
        0.54,
        0.56,
        0.54,
        0.54,
        0.54,
        0.54,
        0.46,
        0.48,
    ]

    active_sort = str(st.session_state.player_sort_column).upper()
    active_ascending = bool(st.session_state.player_sort_ascending)

    header_cols = st.columns(widths)
    for index, (col, label) in enumerate(zip(header_cols, headers)):
        if not label:
            col.markdown(
                "<div class='player-table-header2'></div>",
                unsafe_allow_html=True,
            )
            continue

        indicator = ""
        if label == active_sort:
            indicator = " ▲" if active_ascending else " ▼"

        with col:
            if st.button(
                f"{label}{indicator}",
                key=f"v730_sort_{label}",
                help=f"Sort by {label}",
                use_container_width=True,
                type="secondary",
            ):
                set_player_sort(label)
                st.rerun()

    shown = pool.head(100).reset_index(drop=True)
    list_height = (
        int(list_height_override)
        if list_height_override is not None
        else dock_settings()["list_px"]
    )

    with st.container(height=list_height, key="war_player_list"):
        for _, row in shown.iterrows():
            player = clean(row["player"])
            pos = clean(row["position"])
            nfl_team = clean(row["nfl_team"])
            rank = int(row["custom_rank"])
            adp = numeric(row.get("consensus_adp"), None)
            tier = clean(row.get("tier", ""))
            score = numeric(row.get("peter_score"), None)
            proj = numeric(row.get("proj_pts"), None)
            avg = numeric(row.get("proj_avg"), None)

            adp_text = "—" if adp is None else f"{adp:.1f}"
            score_text = "—" if score is None else f"{score:.0f}"
            proj_text = "—" if proj is None else f"{proj:.1f}"
            avg_text = "—" if avg is None else f"{avg:.1f}"
            rush_text = clean(row.get("rush_yds", "")) or "—"
            rec_text = clean(row.get("rec_yds", "")) or "—"
            pass_text = clean(row.get("pass_yds", "")) or "—"
            bye_text = clean(row.get("bye", "")) or "—"
            value_text, value_class = player_value_badge(
                row,
                current_idx,
            )
            pos_class = (
                pos
                if pos in {"QB", "RB", "WR", "TE"}
                else "OTHER"
            )
            in_queue = player in st.session_state.player_queue

            cols = st.columns(widths)

            cols[0].button(
                "+",
                key=f"draft_plus_{current_idx}_{player}",
                use_container_width=True,
                type="secondary",
                disabled=not allow_draft,
                help=f"Draft {player}",
                on_click=handle_user_draft_click,
                args=(player,),
            )

            if cols[1].button(
                "★" if in_queue else "☆",
                key=f"queue_star_{current_idx}_{player}",
                use_container_width=True,
                help=(
                    f"Remove {player} from queue"
                    if in_queue
                    else f"Add {player} to queue"
                ),
            ):
                if in_queue:
                    remove_from_queue(player)
                else:
                    add_to_queue(player)
                st.rerun()

            cols[2].markdown(
                f"<div class='rank2'>{rank}</div>",
                unsafe_allow_html=True,
            )
            cols[3].markdown(
                f"""
                <div class='player-name2' title='{player}'>{player}</div>
                <div class='player-sub2'>
                    <span class='pos-dot dot-{pos_class}'></span>
                    {pos} · {nfl_team}
                </div>
                """,
                unsafe_allow_html=True,
            )

            values = [
                pos,
                adp_text,
                tier or "—",
                score_text,
                proj_text,
                avg_text,
                rush_text,
                rec_text,
                pass_text,
                bye_text,
            ]

            for col, value in zip(cols[4:14], values):
                col.markdown(
                    f"<div class='stat2'>{value}</div>",
                    unsafe_allow_html=True,
                )

            cols[14].markdown(
                f"""
                <div class="value-badge {value_class}">
                    {value_text}
                </div>
                """,
                unsafe_allow_html=True,
            )



def render_queue_panel(
    current_idx: int,
    allow_draft: bool,
):
    clean_player_queue()
    queue = list(st.session_state.player_queue)

    st.markdown(
        f"""
        <div class="queue-title-row">
            <div class="queue-title">MY QUEUE</div>
            <div class="queue-count">{len(queue)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not queue:
        st.markdown(
            """
            <div class="queue-empty">
                Add players with the ☆ button.
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        pmap = player_map()

        for queue_index, player in enumerate(queue):
            info = pmap.get(player, {})
            pos = clean(info.get("position", ""))
            nfl_team = clean(info.get("nfl_team", ""))

            row_cols = st.columns(
                [0.42, 2.0, 0.34, 0.34, 0.34]
            )

            row_cols[0].markdown(
                f'<div class="queue-rank">{queue_index + 1}</div>',
                unsafe_allow_html=True,
            )
            row_cols[1].markdown(
                f"""
                <div class="queue-player">{player}</div>
                <div class="queue-player-sub">
                    {pos} · {nfl_team}
                </div>
                """,
                unsafe_allow_html=True,
            )

            if row_cols[2].button(
                "↑",
                key=f"queue_up_{queue_index}_{player}",
                disabled=queue_index == 0,
                help="Move up",
            ):
                move_queue_player(player, -1)
                st.rerun()

            if row_cols[3].button(
                "↓",
                key=f"queue_down_{queue_index}_{player}",
                disabled=queue_index == len(queue) - 1,
                help="Move down",
            ):
                move_queue_player(player, 1)
                st.rerun()

            if row_cols[4].button(
                "×",
                key=f"queue_remove_{queue_index}_{player}",
                help="Remove from queue",
            ):
                remove_from_queue(player)
                st.rerun()

    if st.button(
        "➤ Draft Top Queue Player",
        use_container_width=True,
        type="primary",
        disabled=not allow_draft or not queue,
        key=f"draft_top_queue_{current_idx}",
    ):
        draft_top_queue_player()
        st.rerun()

    utility_left, utility_right = st.columns(
        [0.90, 1.25]
    )

    with utility_left:
        if st.button(
            "Clear Queue",
            use_container_width=True,
            disabled=not queue,
            key="clear_queue_button",
        ):
            clear_player_queue()
            st.rerun()

    with utility_right:
        st.toggle(
            "Auto-draft from Queue",
            key="queue_auto_draft",
            help=(
                "At 0:00, draft your top queued player. "
                "If the queue is empty, use best available."
            ),
        )






init_state()
initialize_cpu_variance()
apply_team_query_selection()
render_dynamic_dock_css()
render_player_tray_css()

# Only CPU turns use full-page refreshes.
# User turns rely on the browser-side clock, so player clicks stay responsive.
_current_idx = current_open_index()
_current_owner = None

if _current_idx is not None:
    _current_owner = clean(
        st.session_state.picks.loc[_current_idx, "current_owner"]
    )

_cpu_turn_active = (
    st.session_state.draft_active
    and _current_idx is not None
    and _current_owner != clean(st.session_state.user_team)
)

if _cpu_turn_active:
    # Mount the autorefresh component inside a dedicated hidden container.
    # This keeps its blank iframe from creating the wide gray bar above the app.
    current_pick_number = int(
        st.session_state.picks.loc[_current_idx, "overall"]
    )

    with st.container(key="cpu_autorefresh_mount"):
        st_autorefresh(
            interval=180,
            limit=None,
            key=f"cpu_pick_tick_{current_pick_number}",
        )

    run_one_cpu_pick()

# Enforce the user's pick clock only on user-controlled turns.
if auto_pick_user_if_expired():
    st.rerun()

# The Draft Room renders its own compact v5.3 header.

# -----------------------------------------------------------------------------
# v7.0.0 — Navigation lives in fantasysync/navigation.py
# -----------------------------------------------------------------------------
selected_page = render_top_navigation(
    rebuild_draft=rebuild_draft,
    serializable_state=serializable_state,
)

if selected_page == "Draft Room":
    render_draft_room(
        DraftRoomDependencies(
            current_open_index=current_open_index,
            render_player_tray_css=render_player_tray_css,
            render_header=render_v53_header,
            clean=clean,
            remaining_pick_time=remaining_pick_time,
            pause_pick_clock=pause_pick_clock,
            start_pick_clock=start_pick_clock,
            current_user_roster=current_user_roster,
            player_tray_settings=player_tray_settings,
            snake_board_html=snake_board_html,
            move_player_tray=move_player_tray,
            render_player_toolbar=render_v61_player_toolbar,
            render_player_picker=render_player_picker_table,
            render_queue=render_queue_panel,
            render_roster_header=render_live_roster_header,
            render_roster_rows=render_live_roster_rows,
        )
    )



elif selected_page == "Recommendations":
    st.subheader("Team-Aware Recommendations")
    idx = current_open_index()
    if idx is None:
        st.success("Draft complete.")
    else:
        current = st.session_state.picks.loc[idx]
        counts = roster_position_counts(st.session_state.user_team)
        next_pick = next_user_pick(int(current["overall"]))
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("QB", counts["QB"])
        c2.metric("RB", counts["RB"])
        c3.metric("WR", counts["WR"])
        c4.metric("TE", counts["TE"])
        c5.metric("Next User Pick", next_pick or "—")
        recs = recommendations(8)
        st.dataframe(recs, hide_index=True, use_container_width=True)
        st.caption(
            "Chance Back is a heuristic derived from consensus ADP versus your next open pick. "
            "It is directional—not a guarantee."
        )

elif selected_page == "Rankings & ADP":
    st.subheader("Player Rankings & ADP Comparison")
    df = st.session_state.players.copy()
    pos_options = ["All"] + sorted([p for p in df["position"].dropna().unique().tolist() if p])
    c1, c2 = st.columns([1, 2])
    with c1:
        pos = st.selectbox("Position filter", pos_options, key="ranking_pos")
    with c2:
        query = st.text_input("Search player", key="ranking_search")
    if pos != "All":
        df = df[df["position"] == pos]
    if query:
        df = df[df["player"].str.contains(query, case=False, na=False)]

    display_cols = [
        "rank", "player", "position", "nfl_team", "custom_rank", "market_rank",
        "consensus_adp", "underdog_adp", "nfl_adp", "sleeper_adp", "yahoo_adp",
        "espn_adp", "fantasypros_adp", "walterpicks_adp", "tier", "peter_score"
    ]
    labels = {
        "rank": "Board Rank", "player": "Player", "position": "Pos", "nfl_team": "NFL",
        "custom_rank": "Custom Rank", "market_rank": "Market Rank",
        "consensus_adp": "Consensus ADP", "underdog_adp": "Underdog",
        "nfl_adp": "NFL.com", "sleeper_adp": "Sleeper", "yahoo_adp": "Yahoo",
        "espn_adp": "ESPN", "fantasypros_adp": "FantasyPros",
        "walterpicks_adp": "WalterPicks", "tier": "Tier", "peter_score": "Peter Score"
    }
    ranking_table = df[display_cols].rename(columns=labels)
    st.dataframe(ranking_table, hide_index=True, use_container_width=True, height=650)

    st.markdown("#### Add or update site ADP data")
    st.caption(
        "Your workbook currently contains Consensus and Underdog ADP. "
        "The remaining site columns are ready for CSV imports as those datasets become available."
    )
    template = st.session_state.players[["player"]].copy()
    for site, col in ADP_COLUMNS.items():
        template[col] = st.session_state.players[col] if col in st.session_state.players else ""
    st.download_button(
        "Download ADP import template",
        template.to_csv(index=False).encode("utf-8"),
        file_name="fantasysync_adp_template.csv",
        mime="text/csv",
    )
    uploaded = st.file_uploader("Upload completed ADP CSV", type=["csv"])
    if uploaded is not None:
        incoming = pd.read_csv(uploaded)
        if "player" not in incoming.columns:
            st.error("The CSV must contain a player column.")
        else:
            merged = st.session_state.players.drop(
                columns=[c for c in ADP_COLUMNS.values() if c in st.session_state.players.columns],
                errors="ignore"
            ).merge(incoming, on="player", how="left")
            for col in ADP_COLUMNS.values():
                if col not in merged:
                    merged[col] = pd.NA
                merged[col] = pd.to_numeric(merged[col], errors="coerce")
            st.session_state.players = merged
            st.success("ADP comparison data loaded for this session.")
            st.rerun()

elif selected_page == "Available Players":
    avail = available_players().copy()
    pos_options = ["All"] + sorted([p for p in avail["position"].dropna().unique().tolist() if p])
    pos = st.selectbox("Position", pos_options)
    query = st.text_input("Search player")
    if pos != "All":
        avail = avail[avail["position"] == pos]
    if query:
        avail = avail[avail["player"].str.contains(query, case=False, na=False)]
    st.dataframe(
        avail[["rank", "player", "position", "nfl_team", "consensus_adp", "underdog_adp", "tier", "peter_score"]],
        use_container_width=True, hide_index=True, height=650,
    )

elif selected_page == "Team Rosters":
    team_names = st.session_state.teams.sort_values("draft_slot")["team_name"].tolist()
    for start in range(0, len(team_names), 2):
        cols = st.columns(2)
        for j, team_name in enumerate(team_names[start:start+2]):
            with cols[j]:
                roster = build_team_roster(team_name)
                count = int((roster["Player"] != "").sum())
                st.subheader(team_name)
                st.caption(f"Rostered: {count} / 16")
                st.dataframe(roster, hide_index=True, use_container_width=True, height=610)

elif selected_page == "League Setup":
    st.subheader("Teams and Draft Slots")
    edited_teams = st.data_editor(
        st.session_state.teams, use_container_width=True, hide_index=True, num_rows="fixed",
        column_config={
            "team_id": st.column_config.NumberColumn("Team ID", disabled=True),
            "team_name": st.column_config.TextColumn("Team Name", required=True),
            "draft_slot": st.column_config.NumberColumn("Draft Slot", min_value=1, max_value=10, step=1),
        }, key="team_editor",
    )
    if st.button("Apply team setup"):
        if len(set(edited_teams["draft_slot"])) != len(edited_teams):
            st.error("Each draft slot must be unique.")
        elif len(set(edited_teams["team_name"].map(clean))) != len(edited_teams):
            st.error("Each team name must be unique.")
        else:
            old_names = dict(zip(st.session_state.teams["team_id"], st.session_state.teams["team_name"]))
            new_names = dict(zip(edited_teams["team_id"], edited_teams["team_name"]))
            st.session_state.teams = edited_teams.copy()
            for team_id, old_name in old_names.items():
                new_name = new_names[team_id]
                st.session_state.picks.loc[
                    st.session_state.picks["original_team_id"] == team_id, "original_owner"
                ] = new_name
                st.session_state.picks.loc[
                    st.session_state.picks["current_owner"] == old_name, "current_owner"
                ] = new_name
            st.success("Team setup applied. Reset the draft to regenerate the snake order.")

elif selected_page == "Keepers & Picks":
    st.subheader("Keeper Manager")
    player_choices = st.session_state.players["player"].tolist()
    team_ids = st.session_state.teams["team_id"].tolist()
    edited_keepers = st.data_editor(
        st.session_state.keepers, use_container_width=True, hide_index=True, num_rows="dynamic",
        column_config={
            "team_id": st.column_config.SelectboxColumn("Team ID", options=team_ids, required=True),
            "player": st.column_config.SelectboxColumn("Player", options=player_choices, required=True),
            "keeper_round": st.column_config.NumberColumn("Keeper Round", min_value=1, max_value=20, step=1),
            "exact_pick_override": st.column_config.NumberColumn("Exact Pick Override", min_value=1, max_value=200, step=1),
        }, key="keeper_editor",
    )
    if st.button("Apply keepers"):
        st.session_state.keepers = edited_keepers.copy()
        rebuild_draft()
        st.success("Keepers applied and draft reset.")
        st.rerun()

    st.divider()
    st.subheader("Draft Pick Ownership")
    st.caption("Change Current Owner to represent a traded pick.")
    owners = st.session_state.teams["team_name"].tolist()
    edited_picks = st.data_editor(
        st.session_state.picks[[
            "overall", "round", "slot", "original_owner", "current_owner", "keeper_player", "selected_player"
        ]],
        use_container_width=True, hide_index=True, num_rows="fixed",
        column_config={
            "overall": st.column_config.NumberColumn(disabled=True),
            "round": st.column_config.NumberColumn(disabled=True),
            "slot": st.column_config.NumberColumn(disabled=True),
            "original_owner": st.column_config.TextColumn(disabled=True),
            "current_owner": st.column_config.SelectboxColumn(options=owners),
            "keeper_player": st.column_config.TextColumn(disabled=True),
            "selected_player": st.column_config.TextColumn(disabled=True),
        }, key="pick_owner_editor",
    )
    if st.button("Apply pick trades"):
        st.session_state.picks["current_owner"] = edited_picks["current_owner"].tolist()
        st.success("Pick ownership updated.")
        st.rerun()

elif selected_page == "League History":
    st.subheader("League History")
    st.caption(
        "Saved drafts and season history will appear here in a future update."
    )

    completed = st.session_state.picks[
        st.session_state.picks["selected_player"].map(clean) != ""
    ].copy()

    if completed.empty:
        st.info(
            "Complete or import a draft to begin building league history."
        )
    else:
        history_display = completed[
            [
                "overall",
                "round",
                "current_owner",
                "selected_player",
                "source",
            ]
        ].copy()
        history_display.columns = [
            "Pick",
            "Round",
            "Team",
            "Player",
            "Source",
        ]
        st.dataframe(
            history_display,
            hide_index=True,
            use_container_width=True,
            height=650,
        )


elif selected_page == "Settings":
    st.subheader("Application Settings")
    st.caption(
        "These settings were previously shown in the left sidebar."
    )

    settings_left, settings_right = st.columns(2)

    with settings_left:
        new_rounds = st.number_input(
            "Draft rounds",
            min_value=1,
            max_value=20,
            value=int(st.session_state.rounds),
            key="settings_rounds",
        )

        new_clock = st.number_input(
            "Pick clock length (seconds)",
            min_value=15,
            max_value=300,
            value=int(st.session_state.pick_clock_seconds),
            step=15,
            key="settings_pick_clock",
        )

        if st.button(
            "Apply Draft Settings",
            type="primary",
            use_container_width=True,
        ):
            rounds_changed = int(new_rounds) != int(
                st.session_state.rounds
            )
            st.session_state.rounds = int(new_rounds)
            st.session_state.pick_clock_seconds = int(new_clock)

            if rounds_changed:
                rebuild_draft()
                st.session_state.clock_running = False

            reset_pick_clock()
            st.success("Draft settings updated.")
            st.rerun()

    with settings_right:
        st.markdown("#### Import Draft State")
        uploaded_state = st.file_uploader(
            "Upload a saved draft-state JSON file",
            type=["json"],
            key="settings_draft_state_uploader",
        )

        if uploaded_state is not None:
            if st.button(
                "Apply Uploaded State",
                use_container_width=True,
            ):
                try:
                    load_state_data(json.load(uploaded_state))
                    st.success("Draft state loaded.")
                    st.rerun()
                except Exception as exc:
                    st.error(
                        f"Could not load draft state: {exc}"
                    )

        st.markdown("#### CPU Draft Behavior")
        variance_status = (
            "Mild top-five variance"
            if st.session_state.cpu_variance_enabled
            else "Strict best available"
        )
        st.info(
            f"Current draft mode: **{variance_status}**. "
            "A fresh mode is chosen whenever the draft is reset. "
            "About one out of every four drafts uses mild variance."
        )

        st.markdown("#### Display")
        st.info(
            "Additional color, font, and accessibility settings "
            "will be added here during the UI polish pass."
        )
