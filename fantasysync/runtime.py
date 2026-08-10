"""FantasySync Streamlit runtime: session init, navigation, and page dispatch.

Executed fresh on every Streamlit rerun by ``fantasysync.entrypoint``. This is
the module that actually draws the app; the individual page/component
modules (``fantasysync.draft_engine``, ``fantasysync.app_state``,
``fantasysync.player_pool``, ``components.*``) only expose functions and are
never invoked on their own.
"""
from __future__ import annotations

import streamlit as st
from streamlit_autorefresh import st_autorefresh

from components import DraftRoomDependencies, render_draft_room
from components.draft_room_widgets import (
    current_user_roster,
    render_live_roster_header,
    render_live_roster_rows,
    render_player_picker_table,
    render_queue_panel,
    render_v53_header,
    render_v61_player_toolbar,
)
from fantasysync.app_state import (
    clean,
    init_state,
    move_player_tray,
    numeric,
    player_tray_settings,
    render_dynamic_dock_css,
    render_player_tray_css,
)
from fantasysync.draft_engine import (
    auto_pick_user_if_expired,
    current_open_index,
    pause_pick_clock,
    rebuild_draft,
    remaining_pick_time,
    reset_pick_clock,
    run_one_cpu_pick,
    serializable_state,
    snake_board_html,
    start_pick_clock,
)
from fantasysync.navigation import render_top_navigation
from fantasysync.player_pool import apply_team_query_selection
from fantasysync.rankings_sources import get_stats_season_label

# Milliseconds between each revealed CPU pick, for the ticker effect.
_CPU_TICKER_INTERVAL_MS = 900


def _tick_cpu_draft() -> None:
    """Reveal CPU-owned picks one at a time, ticker-style.

    A 10-team snake draft spends most picks on CPU teams. Resolving all of
    them in a single instant batch felt jarring, so this reveals exactly one
    CPU pick per rerun and, if more CPU picks remain before the user's next
    turn, schedules a quick autorefresh to reveal the next one. Once the open
    pick belongs to the user, it starts their pick clock and stops ticking.
    """
    if not st.session_state.draft_active:
        return

    idx = current_open_index()
    if idx is None:
        st.session_state.draft_active = False
        return

    owner = clean(st.session_state.picks.loc[idx, "current_owner"])
    if owner == clean(st.session_state.user_team):
        start_pick_clock()
        return

    run_one_cpu_pick()

    next_idx = current_open_index()
    if next_idx is None:
        st.session_state.draft_active = False
        return

    next_owner = clean(st.session_state.picks.loc[next_idx, "current_owner"])
    if next_owner == clean(st.session_state.user_team):
        start_pick_clock()
    else:
        with st.container(key="cpu_autorefresh_mount"):
            st_autorefresh(interval=_CPU_TICKER_INTERVAL_MS, limit=None, key="cpu_ticker")


def _render_draft_room_page() -> None:
    apply_team_query_selection()
    _tick_cpu_draft()

    idx = current_open_index()
    user_is_up = idx is not None and clean(
        st.session_state.picks.loc[idx, "current_owner"]
    ) == clean(st.session_state.user_team)

    if st.session_state.draft_active and user_is_up and st.session_state.clock_running:
        # Ticks the pick clock and re-checks for an expired timer even if the
        # user never interacts with a widget during their turn. This page is
        # widget-heavy (a ~100-row player table), so a full rerender is not
        # cheap - refresh every few seconds rather than every second to keep
        # the tab responsive.
        with st.container(key="cpu_autorefresh_mount"):
            st_autorefresh(interval=3000, limit=None, key="pick_clock_tick")
        if auto_pick_user_if_expired():
            st.rerun()

    render_draft_room(
        DraftRoomDependencies(
            current_open_index=current_open_index,
            render_player_tray_css=render_player_tray_css,
            render_header=render_v53_header,
            clean=clean,
            remaining_pick_time=remaining_pick_time,
            pause_pick_clock=pause_pick_clock,
            start_pick_clock=start_pick_clock,
            reset_pick_clock=reset_pick_clock,
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


def _render_rankings_page() -> None:
    """Full player list with live ADP/bye - the same st.session_state.players
    the Draft Room's player tray reads from, so the two pages can never show
    inconsistent data within a session."""
    st.header("Rankings & ADP")
    stats_season = get_stats_season_label()
    stats_note = (
        f" Rush/Rec/Pass Yds and Proj Pts are {stats_season} season stats via "
        "[nflverse](https://github.com/nflverse/nflverse-data) until a FantasyPros "
        "key is configured, then switch to forward projections automatically."
        if stats_season
        else ""
    )
    st.caption(
        "ADP and bye weeks refresh automatically every few hours. "
        "Live ADP via [Fantasy Football Calculator](https://fantasyfootballcalculator.com/adp)."
        + stats_note
    )

    players = st.session_state.players.copy()

    search_col, pos_col = st.columns([2, 3])
    with search_col:
        query = st.text_input(
            "Search players",
            key="rankings_search",
            placeholder="Search players...",
            label_visibility="collapsed",
        )
    with pos_col:
        selected_pos = st.radio(
            "Position",
            ["ALL", "QB", "RB", "WR", "TE"],
            key="rankings_position_filter",
            horizontal=True,
            label_visibility="collapsed",
        )

    if query:
        players = players[players["player"].str.contains(query, case=False, na=False)]
    if selected_pos != "ALL":
        players = players[players["position"] == selected_pos]

    players = players.sort_values(["custom_rank", "rank"])

    display = players[["custom_rank", "player", "position", "nfl_team", "tier", "consensus_adp"]].rename(
        columns={
            "custom_rank": "Rank",
            "player": "Player",
            "position": "Pos",
            "nfl_team": "Team",
            "tier": "Tier",
            "consensus_adp": "ADP",
        }
    )
    if "bye" in players.columns:
        display["Bye"] = players["bye"]
    for col, label in [
        ("proj_pts", "Proj Pts"),
        ("rush_yds", "Rush Yds"),
        ("rec_yds", "Rec Yds"),
        ("pass_yds", "Pass Yds"),
    ]:
        if col in players.columns and players[col].notna().any():
            display[label] = players[col]

    st.dataframe(display, width="stretch", hide_index=True, height=600)


def _swap_draft_slot(team_id: int, direction: int) -> None:
    """Moves one team's draft position by one slot and rebuilds the board.

    Draft order determines the whole snake sequence, so there's no way to
    reorder it without invalidating any picks already made - rebuild_draft()
    regenerates the full picks table from the (now-reordered) teams and the
    existing keepers, same as the top nav's own Reset button does.
    """
    teams = st.session_state.teams
    current_row = teams.loc[teams["team_id"] == team_id].iloc[0]
    current_slot = int(current_row["draft_slot"])
    target_slot = current_slot + direction

    target_mask = teams["draft_slot"] == target_slot
    if not target_mask.any():
        return

    teams.loc[teams["team_id"] == team_id, "draft_slot"] = target_slot
    teams.loc[target_mask, "draft_slot"] = current_slot
    st.session_state.teams = teams
    rebuild_draft()


def _render_league_setup_page() -> None:
    st.header("League Setup")

    if st.session_state.draft_active:
        st.warning(
            "A draft is currently in progress. Changing draft order below "
            "will reset it and rebuild the board from scratch."
        )
    else:
        st.caption(
            "Team names and draft order for this league. Changing draft "
            "order rebuilds the mock draft board from scratch."
        )

    teams = st.session_state.teams.sort_values("draft_slot").reset_index(drop=True)
    slot_count = len(teams)

    header_cols = st.columns([0.7, 3, 2, 0.6, 0.6])
    for col, label in zip(header_cols, ["SLOT", "TEAM", "OWNER", "", ""]):
        col.markdown(f"**{label}**")

    for i, row in teams.iterrows():
        team_id = int(row["team_id"])
        slot = int(row["draft_slot"])
        cols = st.columns([0.7, 3, 2, 0.6, 0.6])
        cols[0].markdown(str(slot))
        cols[1].markdown(clean(row["team_name"]))
        cols[2].markdown(clean(row.get("owner", "")))
        if cols[3].button("↑", key=f"league_order_up_{team_id}", disabled=(slot == 1)):
            _swap_draft_slot(team_id, -1)
            st.rerun()
        if cols[4].button("↓", key=f"league_order_down_{team_id}", disabled=(slot == slot_count)):
            _swap_draft_slot(team_id, 1)
            st.rerun()


_NO_KEEPER = "— None (no keeper) —"


def _render_keepers_page() -> None:
    st.header("Keepers")
    st.caption(
        "Set each team's keepers - player and the round the keeper costs. "
        "Edits below are staged; nothing changes on the draft board until "
        "you click Save."
    )
    # st.rerun() below cuts the script off immediately, so a success message
    # shown right before it would never actually paint - stash it in session
    # state and show it on the render that follows the rerun instead.
    if st.session_state.pop("_keepers_just_saved", False):
        st.success("Keepers saved. Draft board updated.")

    keepers = st.session_state.keepers.copy()
    teams = st.session_state.teams.sort_values("draft_slot")
    all_player_names = sorted(
        st.session_state.players["player"].dropna().map(clean).unique().tolist()
    )
    max_round = int(st.session_state.rounds)

    header_cols = st.columns([2.2, 3.4, 1.1])
    for col, label in zip(header_cols, ["TEAM", "PLAYER", "ROUND"]):
        col.markdown(f"**{label}**")

    # Widget values are staged here as (orig_idx, player, round, team_name)
    # rather than written to st.session_state.keepers immediately - nothing
    # is applied to the draft board until Save Changes is clicked below.
    pending = []

    for _, team_row in teams.iterrows():
        team_id = int(team_row["team_id"])
        team_name = clean(team_row["team_name"])
        team_keeper_rows = keepers[keepers["team_id"] == team_id]

        for slot_index, (orig_idx, keeper_row) in enumerate(team_keeper_rows.iterrows()):
            current_player = clean(keeper_row["player"])
            current_round = int(numeric(keeper_row["keeper_round"], 1))

            # Excludes players already claimed by another keeper slot (in the
            # saved data) so the same player can't end up placed in two
            # draft cells at once - except this row's own current pick,
            # which must stay selectable. A duplicate introduced across
            # *unsaved* edits (e.g. picking the same free agent in two
            # rows before saving) is still possible here and is instead
            # caught at save time below, since each row can't see what's
            # selected in other not-yet-saved rows while rendering.
            used_elsewhere = {
                clean(p) for i, p in keepers["player"].items() if i != orig_idx
            } - {""}
            options = [_NO_KEEPER] + [
                p for p in all_player_names if p not in used_elsewhere
            ]
            current_value = current_player if current_player else _NO_KEEPER
            if current_value not in options:
                options.insert(1, current_value)

            cols = st.columns([2.2, 3.4, 1.1])
            cols[0].markdown(team_name)
            with cols[1]:
                selected_value = st.selectbox(
                    "Player",
                    options,
                    index=options.index(current_value),
                    key=f"keeper_player_{team_id}_{slot_index}",
                    label_visibility="collapsed",
                )
            with cols[2]:
                selected_round = st.number_input(
                    "Round",
                    min_value=1,
                    max_value=max_round,
                    value=min(current_round, max_round),
                    step=1,
                    key=f"keeper_round_{team_id}_{slot_index}",
                    label_visibility="collapsed",
                )

            selected_player = "" if selected_value == _NO_KEEPER else selected_value
            if selected_player != current_player or int(selected_round) != current_round:
                pending.append((orig_idx, selected_player, int(selected_round), team_name))

    if not pending:
        return

    st.divider()

    dupes = {p for p in (row[1] for row in pending if row[1]) if [r[1] for r in pending].count(p) > 1}
    if dupes:
        st.error(
            "Can't save - the same player is set as a keeper in more than "
            "one row: " + ", ".join(sorted(dupes))
        )
        return

    reset_note = (
        " A draft is currently in progress, so this will also reset it and "
        "rebuild the board from scratch."
        if st.session_state.draft_active
        else ""
    )
    st.warning(
        f"{len(pending)} unsaved keeper change(s).{reset_note} "
        "Nothing on the draft board has changed yet."
    )

    if st.button("💾 Save Changes", type="primary", key="keepers_save_changes"):
        for orig_idx, player, round_, _ in pending:
            keepers.loc[orig_idx, "player"] = player
            keepers.loc[orig_idx, "keeper_round"] = round_
        st.session_state.keepers = keepers
        rebuild_draft()
        st.session_state["_keepers_just_saved"] = True
        st.rerun()


def _render_placeholder_page(route: str) -> None:
    st.header(route)
    st.info(
        f"The “{route}” page has not been built yet. "
        "Only Draft Room, Rankings & ADP, League Setup, and Keepers are "
        "implemented today."
    )


def render_app() -> None:
    init_state()
    render_dynamic_dock_css()

    route = render_top_navigation(
        rebuild_draft=rebuild_draft,
        serializable_state=serializable_state,
    )

    if route == "Draft Room":
        _render_draft_room_page()
    elif route == "Rankings & ADP":
        _render_rankings_page()
    elif route == "League Setup":
        _render_league_setup_page()
    elif route == "Keepers & Picks":
        _render_keepers_page()
    else:
        _render_placeholder_page(route)
