"""Core draft logic: picks, CPU behavior, the pick clock, queue, rosters,
and recommendations.

Split out of the former monolithic runtime.py. This module has no
Streamlit-rendering (no st.markdown/st.button UI) except where session
state itself is the natural place for it (e.g. draft_message).
"""
from __future__ import annotations

import math
import random
import time
from typing import Dict, Optional

import pandas as pd
import streamlit as st

from fantasysync.app_state import assign_keepers, clean, numeric, snake_order
from fantasysync.config import STARTER_TARGETS


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
            "headshot_url": clean(getattr(row, "headshot_url", "")),
        }
    return result


def unavailable_players() -> set:
    return {clean(v) for v in st.session_state.picks["selected_player"].tolist() if clean(v)}


def available_players() -> pd.DataFrame:
    unavailable = unavailable_players()
    df = st.session_state.players.copy()
    return df[~df["player"].map(clean).isin(unavailable)].sort_values(["custom_rank", "rank"])


def current_open_index() -> Optional[int]:
    """First still-open pick, by row position (picks are already in overall
    order). Vectorized rather than the row-by-row `.iterrows()` loop this
    used to be - that scan's cost grew with how many picks were already
    filled in, and this is called from inside snake_board_html()'s per-cell
    loop (see below), so a linear-time implementation here compounded into
    a real O(n^2) cost that measurably slowed the board down further into
    a draft (confirmed live: ~60ms per tick early on, 400ms+ by pick 50)."""
    picks = st.session_state.picks
    open_mask = picks["selected_player"].map(clean) == ""
    if not open_mask.any():
        return None
    return picks.index[open_mask][0]



def initialize_cpu_variance():
    """
    Choose one CPU behavior mode for the entire mock draft.

    ~45% of drafts use mild top-five variance. The rest use strict best
    available.

    This is a deliberate regression back to the original simple mechanic
    (was 25%, and a fancier ADP-standard-deviation/roster-need-weighted
    system was tried in between) - that fancier version measurably hit
    its own stated constraints in testing (no reaches past 5 picks of real
    ADP, elite players staying top-5, etc.) but still didn't feel right in
    practice, so this goes back to the simpler, previously-working
    mechanic and just turns up how often the variance kicks in.
    """
    if st.session_state.cpu_variance_enabled is None:
        seed = random.SystemRandom().randint(1, 2_147_483_647)
        st.session_state.cpu_variance_seed = seed
        rng = random.Random(seed)
        st.session_state.cpu_variance_enabled = rng.random() < 0.45


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

    # Matches the real league's ESPN roster settings (confirmed live
    # 2026-08-14): QB/RB/RB/WR/WR/TE dedicated starters plus one RB/WR/TE
    # flex slot, 9 bench spots - the flex used to be a plain 10th bench
    # slot before this.
    starters = {"QB": None, "RB1": None, "RB2": None, "WR1": None, "WR2": None, "TE": None, "FLEX": None}
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
        elif pos in {"RB", "WR", "TE"} and starters["FLEX"] is None:
            starters["FLEX"] = item
        else:
            bench.append(item)

    rows = []
    for slot in ["QB", "RB1", "RB2", "WR1", "WR2", "TE", "FLEX"]:
        item = starters[slot]
        rows.append({"Slot": slot, "Player": item["player"] if item else "", "Pos": item["position"] if item else ""})
    for i in range(9):
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
    pmap = player_map()

    # Computed once rather than inside the per-cell loop below (previously
    # once per filled cell) - see current_open_index()'s docstring for why
    # that mattered.
    current_idx = current_open_index()
    current_overall = (
        int(st.session_state.picks.loc[current_idx, "overall"])
        if current_idx is not None
        else None
    )

    html = ['<div style="width:100%;">']
    html.append(
        '<div class="snake-draft-grid" style="display:grid;'
        'grid-template-columns:repeat(10,minmax(0,1fr));'
        'gap:2px;width:100%;">'
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
            original_owner = clean(getattr(r, "original_owner", ""))
            tag = " K" if source == "Keeper" else ""

            # A pick shows as traded once its owner differs from who it
            # originally belonged to (set by the Trades page). Keeper picks
            # are excluded there already - can't trade a pick that's spoken
            # for by a keeper - but source != "Keeper" here too, just so a
            # keeper cell can never show both flags if that ever changes.
            traded = bool(original_owner) and owner != original_owner and source != "Keeper"

            classes = ["snake-cell"]
            if player == "—":
                classes.append("empty-pick")
            elif pos in {"QB", "RB", "WR", "TE"}:
                classes.append(f"pos-{pos.lower()}")
            if source == "Keeper":
                classes.append("keeper-pick")
            if traded:
                classes.append("traded-pick")
            if owner == clean(st.session_state.user_team):
                classes.append("user-pick")
            if current_overall is not None and int(r.overall) == current_overall:
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

            keeper_flag = '<div class="snake-keeper-flag">KEEP</div>' if source == "Keeper" else ""
            traded_flag = '<div class="snake-traded-flag">TRADED</div>' if traded else ""
            waiting = "Waiting…" if player == "—" else player

            cell_title = f"{owner} (via trade from {original_owner})" if traded else owner

            # Only emitted when a real photo URL was matched - never a
            # broken-image icon for an unmatched player, same "degrade
            # quietly" rule the live-data fetchers follow.
            headshot_url = pmap.get(player, {}).get("headshot_url", "") if player != "—" else ""
            headshot = (
                f'<img class="snake-headshot" src="{headshot_url}" '
                f'loading="lazy" alt="" aria-hidden="true" '
                f'onerror="this.remove()">'
                if headshot_url else ""
            )

            # Sleeper-style snake notation keeps team columns fixed while
            # showing the actual pick sequence within each round.
            pick_in_round = slot if rnd % 2 == 1 else 11 - slot
            pick_label = f"{rnd}.{pick_in_round}"

            html.append(
                f'<div class="{" ".join(classes)}" title="{cell_title}">'
                f'{headshot}'
                f'<div class="snake-pick">{pick_label}</div>'
                f'<div class="snake-player" title="{player}">{waiting}</div>'
                f'<div class="tile-badge-row">{badge}</div>'
                f'{keeper_flag}'
                f'{traded_flag}'
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
