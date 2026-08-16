"""FantasySync Streamlit runtime: session init, navigation, and page dispatch.

Executed fresh on every Streamlit rerun by ``fantasysync.entrypoint``. This is
the module that actually draws the app; the individual page/component
modules (``fantasysync.draft_engine``, ``fantasysync.app_state``,
``fantasysync.player_pool``, ``components.*``) only expose functions and are
never invoked on their own.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st
from streamlit_autorefresh import st_autorefresh

from components import DraftRoomDependencies, render_header_and_board, render_tray
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
from fantasysync.config import (
    PPR_RECEPTION_VALUE,
    ROSTER_SLOTS,
    SCORING_FORMAT_LABEL,
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
from fantasysync.espn_sync import fetch_espn_league_summary
from fantasysync.navigation import render_top_navigation
from fantasysync.player_pool import apply_team_query_selection
from fantasysync.rankings_sources import get_stats_season_label

# Milliseconds between each revealed CPU pick, for the ticker effect.
#
# History: this used to gate a full-page rerun (a ~90-row player table plus
# the board), which measured 1.3-3.5s at 900ms and needed 1200ms of margin
# just to stay stable. Two things changed since: (1) the CPU ticker now
# lives inside _live_board_fragment (a @st.fragment), so a tick only
# re-renders the header/board, not the whole page - direct timing showed a
# flat ~35-45ms per tick regardless of how far into the draft (confirmed
# with 50+ consecutive samples). (2) current_open_index() was rewritten
# from a row-by-row `.iterrows()` scan to a vectorized pandas op - it used
# to be called once per *filled* board cell inside snake_board_html(),
# which made per-tick cost grow the further into a draft you got (~60ms
# early, 400ms+ by pick 50) - it's now computed once per render and stays
# flat.
#
# With that much more headroom, bisected live in-browser again: 400ms and
# 250ms both held a clean, stable cadence with zero pileup or skipped
# picks across many consecutive ticks on localhost. 150ms didn't actually
# tick any faster than 250ms in practice (real gaps landed in the same
# ~200-300ms range either way) - that's a round-trip/scheduling floor, not
# something a smaller requested interval can push past.
#
# Shipped at 250ms first, then scaled back to 400ms - still a real 3x
# speedup over the old 1200ms, with more margin for Streamlit Community
# Cloud's shared CPU and real network latency than 250ms had (localhost
# has neither, so anything bisected there needs some margin held back for
# the deployed environment regardless of how clean it tested locally).
_CPU_TICKER_INTERVAL_MS = 400


def _tick_cpu_draft() -> None:
    """Reveal CPU-owned picks one at a time, ticker-style.

    A 10-team snake draft spends most picks on CPU teams. Resolving all of
    them in a single instant batch felt jarring, so this reveals exactly one
    CPU pick per rerun. Once the open pick belongs to the user, it starts
    their pick clock; while it doesn't, _live_board_fragment's own
    run_every keeps calling this on a fixed schedule to reveal the next one.

    Called from inside _live_board_fragment (a @st.fragment(run_every=...)),
    so each tick reruns only that fragment - the search/filter toolbar and
    Queue/Roster tray rendered outside it are untouched and stay clickable
    while the CPU picks, instead of the whole page (including a ~90-row
    player table) re-running on every tick like before.

    An earlier version of this used the third-party streamlit_autorefresh
    component (conditionally mounted only while more CPU picks were due)
    instead of the fragment's own native run_every. That combination is
    unreliable: confirmed live, with zero user interaction, ticks would
    stop firing entirely after 4-5 fragment-only cycles and never resume on
    their own. run_every is Streamlit's own first-party mechanism for
    exactly this (a fragment rerunning itself on a schedule) and doesn't
    have that failure mode - tested clean across many consecutive ticks.
    The tradeoff is run_every can't be conditionally unmounted, so the
    fragment now reruns itself on schedule for the whole session once the
    draft starts, including while it's the user's own turn - each of those
    ticks is a quick no-op (the two early-return branches below), and a
    fragment rerun is cheap by design, so this is a small, constant cost
    rather than the large, spiky one the old approach had.
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
        # run_every keeps rerunning this fragment regardless, but a
        # fragment-scoped rerun never touches code outside the fragment -
        # without this, the tray (rendered outside it) would stay frozen in
        # its "CPU is picking, drafting disabled" state even though it's
        # now genuinely the user's turn. One full-page rerun right at this
        # transition wakes it back up; every tick before this one stays
        # fragment-only and cheap.
        st.rerun()


@st.fragment(run_every=_CPU_TICKER_INTERVAL_MS / 1000)
def _live_board_fragment(deps: DraftRoomDependencies) -> tuple:
    """Everything that needs to redraw on every CPU-ticker tick: the pick
    clock/header, team selector, and board grid. Wrapped in a fragment so
    those ticks rerun only this part of the page - see _tick_cpu_draft's
    docstring."""
    _tick_cpu_draft()
    return render_header_and_board(deps)


def _render_draft_room_page() -> None:
    apply_team_query_selection()

    deps = DraftRoomDependencies(
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

    current_index, user_turn = _live_board_fragment(deps)

    if st.session_state.draft_active and user_turn and st.session_state.clock_running:
        # Ticks the pick clock and re-checks for an expired timer even if the
        # user never interacts with a widget during their turn. This stays
        # a full-page rerun (not fragment-scoped) since it's the user's own
        # turn - if their time actually expires and a pick gets auto-drafted,
        # the tray legitimately needs to update too.
        with st.container(key="cpu_autorefresh_mount"):
            st_autorefresh(interval=3000, limit=None, key="pick_clock_tick")
        if auto_pick_user_if_expired():
            st.rerun()

    render_tray(deps, current_index, user_turn)


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


def _render_data_status_page() -> None:
    """ESPN league sync status - what's actually connected and pulling in,
    compared against what the site itself is configured for. Read-only:
    this page never writes back to data/teams.csv or data/keepers.csv,
    since ESPN doesn't expose draft order or keepers until the real draft
    happens and the site's manually-maintained versions are already
    correct for the upcoming draft (see fantasysync/espn_sync.py)."""
    st.header("Data Status")
    st.caption("What's connected, what's live, and how it compares to the site's own settings.")

    espn = fetch_espn_league_summary()

    st.subheader("ESPN League Sync")
    if espn is None:
        st.warning(
            "Not connected. Add `ESPN_LEAGUE_ID`, `ESPN_S2`, and `ESPN_SWID` "
            "to this app's Streamlit secrets to enable live sync."
        )
    else:
        site_team_count = len(st.session_state.teams)
        site_keeper_count = int((st.session_state.keepers["player"].astype(str).str.strip() != "").sum())
        site_reception_pts = PPR_RECEPTION_VALUE

        st.success(f"Connected to **{espn['league_name']}**")

        col1, col2, col3 = st.columns(3)
        with col1:
            match = "✅" if espn["team_count"] == site_team_count else "⚠️"
            st.metric("Teams", f"{espn['team_count']}", help=f"Site: {site_team_count} {match}")
        with col2:
            match = "✅" if espn["reception_points"] == site_reception_pts else "⚠️"
            st.metric(
                "Points / Reception",
                f"{espn['reception_points']}",
                help=f"Site: {site_reception_pts} ({SCORING_FORMAT_LABEL}) {match}",
            )
        with col3:
            st.metric(
                "Keeper Slots (ESPN, per team)",
                f"{espn['keeper_count']}",
                help=f"Site currently has {site_keeper_count} keeper(s) assigned across all teams (manually maintained in data/keepers.csv, not synced from ESPN).",
            )

        draft_note = (
            "ESPN shows this league's draft as **completed**."
            if espn["draft_completed"]
            else "ESPN shows this league's draft as **not yet completed** - draft order and keeper "
            "designations aren't exposed by ESPN's API until then, so the site's manually-set draft "
            "order and keepers (League Setup / Keepers pages) remain the source of truth and are not "
            "overwritten by this sync."
        )
        st.caption(draft_note)

        st.markdown("**Roster slots**")
        slot_col, espn_col = st.columns(2)
        with slot_col:
            st.caption("Site (fantasysync/config.py)")
            st.code("\n".join(ROSTER_SLOTS), language=None)
        with espn_col:
            st.caption("ESPN (live)")
            st.code(
                "\n".join(f"{slot}: {count}" for slot, count in espn["position_slot_counts"].items()),
                language=None,
            )

        st.markdown("**Full scoring rules (ESPN, live)**")
        rules_df = pd.DataFrame(espn["scoring_rules"])
        st.dataframe(rules_df, width="stretch", hide_index=True, height=280)

        st.markdown("**Teams (ESPN, live)**")
        teams_df = pd.DataFrame(espn["teams"])
        st.dataframe(teams_df, width="stretch", hide_index=True)
        st.caption(
            "ESPN's own team IDs don't correspond to this site's draft order - matching is by "
            "name/owner only, nothing here is written back into the site's team list."
        )

    st.divider()
    st.subheader("Rankings Data Pipeline")
    stats_season = get_stats_season_label()
    st.write(f"- Fantasy Football Calculator ADP: live, refreshes every 6 hours")
    st.write(f"- ESPN platform-wide ADP: live, refreshes every 6 hours (no key needed, blended into the same ADP column)")
    st.write(f"- nflverse season stats baseline: {stats_season if stats_season else 'unavailable'}")
    try:
        fp_key = bool(st.secrets.get("FANTASYPROS_API_KEY", ""))
    except Exception:
        fp_key = False
    st.write(f"- FantasyPros consensus/projections: {'connected' if fp_key else 'not configured (no API key in secrets)'}")


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


def _render_keeper_board_grid() -> None:
    """Click-to-assign keeper editor: a grid shaped like the draft board
    itself (one row per round, one column per team, same round.pick
    labels), rather than the flat team-by-team list below it. Click any
    cell - empty or already a keeper - to assign, change, or clear it
    right there, matching the click-a-cell UX Peter asked for instead of
    picking a team from a dropdown list first.

    Each cell is a real st.popover rather than part of the read-only HTML
    string the live Draft Room board renders (fantasysync.draft_engine.
    snake_board_html) - that board is one big markdown string specifically
    so it stays cheap to redraw on every CPU-ticker fragment tick (see
    runtime._live_board_fragment). This page has no ticker running at all,
    so real per-cell widgets here don't carry that same cost concern.
    """
    teams = st.session_state.teams.sort_values("draft_slot")
    team_by_slot = {int(row.draft_slot): row for row in teams.itertuples()}
    max_round = int(st.session_state.rounds)
    all_player_names = sorted(
        st.session_state.players["player"].dropna().map(clean).unique().tolist()
    )

    # A pick counts as "the draft has started" only once something other
    # than a keeper has been selected there - keeper pre-fills happen
    # automatically at rebuild time regardless of draft progress, so they
    # don't count.
    picks = st.session_state.picks
    draft_started = bool((
        (picks["selected_player"] != "") & (picks["source"] != "Keeper")
    ).any())
    if draft_started:
        st.info(
            "A draft is in progress. Assigning or changing a keeper here "
            "will reset it and rebuild the board, same as saving the list "
            "editor below."
        )

    st.markdown('<div class="keeper-grid-header-row">', unsafe_allow_html=True)
    header_cols = st.columns(10, gap="small")
    for col, slot in zip(header_cols, range(1, 11)):
        team_row = team_by_slot.get(slot)
        col.markdown(
            f"<div class='keeper-grid-team'>{clean(team_row.team_name) if team_row else ''}</div>",
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)

    for rnd in range(1, max_round + 1):
        row_cols = st.columns(10, gap="small")
        for slot in range(1, 11):
            team_row = team_by_slot.get(slot)
            if team_row is None:
                continue
            team_id = int(team_row.team_id)
            pick_label = _pick_label(rnd, slot)

            keepers = st.session_state.keepers
            existing = keepers[
                (keepers["team_id"] == team_id) & (keepers["keeper_round"] == rnd)
            ]
            existing_idx = existing.index[0] if not existing.empty else None
            existing_player = (
                clean(existing.iloc[0]["player"]) if existing_idx is not None else ""
            )

            with row_cols[slot - 1]:
                with st.popover(
                    existing_player if existing_player else pick_label,
                    use_container_width=True,
                    key=f"keeper_cell_{rnd}_{slot}",
                ):
                    st.caption(f"{pick_label} · {clean(team_row.team_name)}")

                    used_elsewhere = {
                        clean(p) for i, p in keepers["player"].items()
                        if i != existing_idx and clean(p)
                    }
                    options = [_NO_KEEPER] + [
                        p for p in all_player_names if p not in used_elsewhere
                    ]
                    current_value = existing_player if existing_player else _NO_KEEPER
                    if current_value not in options:
                        options.insert(1, current_value)

                    chosen = st.selectbox(
                        "Player",
                        options,
                        index=options.index(current_value),
                        key=f"keeper_cell_select_{rnd}_{slot}",
                        label_visibility="collapsed",
                    )

                    if st.button(
                        "Save",
                        key=f"keeper_cell_save_{rnd}_{slot}",
                        type="primary",
                        use_container_width=True,
                    ):
                        chosen_player = "" if chosen == _NO_KEEPER else chosen
                        new_keepers = st.session_state.keepers.copy()
                        if existing_idx is not None:
                            if chosen_player:
                                new_keepers.loc[existing_idx, "player"] = chosen_player
                            else:
                                new_keepers = new_keepers.drop(index=existing_idx)
                        elif chosen_player:
                            new_row = pd.DataFrame([{
                                "team_id": team_id,
                                "player": chosen_player,
                                "keeper_round": rnd,
                                "exact_pick_override": "",
                            }])
                            new_keepers = pd.concat(
                                [new_keepers, new_row], ignore_index=True
                            )
                        st.session_state.keepers = new_keepers
                        rebuild_draft()
                        st.session_state["_keepers_just_saved"] = True
                        st.rerun()


def _render_keepers_page() -> None:
    # The app's global CSS forces the page's block-container to full
    # viewport width (needed for the wide draft board on other pages), which
    # otherwise runs this page's content right to the browser edge too. This
    # insets just this page's own container instead of touching that global
    # rule, which other pages still depend on.
    st.markdown(
        """
        <style>
        .st-key-keepers_page {
            padding: 0 32px !important;
            box-sizing: border-box !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    with st.container(key="keepers_page"):
        st.header("Keepers")
        # st.rerun() below cuts the script off immediately, so a success
        # message shown right before it would never actually paint - stash
        # it in session state and show it on the render that follows the
        # rerun instead. Shared by both editors below.
        if st.session_state.pop("_keepers_just_saved", False):
            st.success("Keepers saved. Draft board updated.")

        st.caption(
            "Click any cell to assign, change, or clear that team's keeper "
            "for that round - shaped like the draft board itself."
        )
        _render_keeper_board_grid()

        st.divider()
        st.subheader("Or edit as a list")
        st.caption(
            "Same data, team-by-team instead of cell-by-cell. Edits below "
            "are staged; nothing changes on the draft board until you "
            "click Save."
        )

        keepers = st.session_state.keepers.copy()
        teams = st.session_state.teams.sort_values("draft_slot")
        all_player_names = sorted(
            st.session_state.players["player"].dropna().map(clean).unique().tolist()
        )
        max_round = int(st.session_state.rounds)

        header_cols = st.columns([2.2, 3.4, 1.1])
        for col, label in zip(header_cols, ["TEAM", "PLAYER", "ROUND"]):
            col.markdown(f"**{label}**")

        # Widget values are staged here as (orig_idx, player, round,
        # team_name) rather than written to st.session_state.keepers
        # immediately - nothing is applied to the draft board until Save
        # Changes is clicked below.
        pending = []

        for _, team_row in teams.iterrows():
            team_id = int(team_row["team_id"])
            team_name = clean(team_row["team_name"])
            team_keeper_rows = keepers[keepers["team_id"] == team_id]

            for slot_index, (orig_idx, keeper_row) in enumerate(team_keeper_rows.iterrows()):
                current_player = clean(keeper_row["player"])
                current_round = int(numeric(keeper_row["keeper_round"], 1))

                # Excludes players already claimed by another keeper slot (in
                # the saved data) so the same player can't end up placed in
                # two draft cells at once - except this row's own current
                # pick, which must stay selectable. A duplicate introduced
                # across *unsaved* edits (e.g. picking the same free agent in
                # two rows before saving) is still possible here and is
                # instead caught at save time below, since each row can't
                # see what's selected in other not-yet-saved rows while
                # rendering.
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


def _pick_label(round_: int, slot: int) -> str:
    """Matches the draft board's own "round.pick" notation (snake order
    reverses the visual pick-in-round on even rounds)."""
    pick_in_round = slot if round_ % 2 == 1 else 11 - slot
    return f"{round_}.{pick_in_round}"


def _render_trades_page() -> None:
    # Same edge-inset pattern as the Keepers page - see the comment there.
    st.markdown(
        """
        <style>
        .st-key-trades_page {
            padding: 0 32px !important;
            box-sizing: border-box !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    with st.container(key="trades_page"):
        st.header("Trades")
        st.caption(
            "Reassign an upcoming pick to another team when picks change "
            "hands mid-season. Only undrafted, non-keeper picks are listed "
            "- a pick that's already been made or is spoken for by a "
            "keeper can't be traded. Unlike Keepers/League Setup, saving a "
            "trade does NOT reset an in-progress draft - it only changes "
            "who owns picks that haven't happened yet."
        )

        if st.session_state.pop("_trades_just_saved", False):
            st.success("Trade(s) saved. Draft board updated.")

        picks = st.session_state.picks
        teams = st.session_state.teams.sort_values("draft_slot")
        team_names = teams["team_name"].map(clean).tolist()

        tradeable = picks[picks["selected_player"] == ""].sort_values("overall")
        if tradeable.empty:
            st.info("No undrafted picks remain to trade.")
            return

        header_cols = st.columns([0.8, 0.9, 2.6, 2.6])
        for col, label in zip(header_cols, ["#", "PICK", "ORIGINAL TEAM", "CURRENT OWNER"]):
            col.markdown(f"**{label}**")

        # Same staged-edit-then-save pattern as the Keepers page: widget
        # values are collected here rather than written to
        # st.session_state.picks immediately, so nothing on the board
        # changes until Save Trades is clicked.
        pending = []

        for idx, row in tradeable.iterrows():
            overall = int(row["overall"])
            pick_label = _pick_label(int(row["round"]), int(row["slot"]))
            original_owner = clean(row["original_owner"])
            current_owner = clean(row["current_owner"])

            cols = st.columns([0.8, 0.9, 2.6, 2.6])
            cols[0].markdown(str(overall))
            cols[1].markdown(pick_label)
            cols[2].markdown(original_owner)
            with cols[3]:
                selected_owner = st.selectbox(
                    "Current owner",
                    team_names,
                    index=team_names.index(current_owner) if current_owner in team_names else 0,
                    key=f"trade_owner_{idx}",
                    label_visibility="collapsed",
                )

            if selected_owner != current_owner:
                pending.append((idx, selected_owner))

        if not pending:
            return

        st.divider()
        st.warning(
            f"{len(pending)} unsaved trade(s). Nothing on the draft board "
            "has changed yet."
        )

        if st.button("💾 Save Trades", type="primary", key="trades_save_changes"):
            new_picks = st.session_state.picks.copy()
            for idx, new_owner in pending:
                new_picks.loc[idx, "current_owner"] = new_owner
            st.session_state.picks = new_picks
            st.session_state["_trades_just_saved"] = True
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
    elif route == "Trades":
        _render_trades_page()
    elif route == "Available Players":
        _render_data_status_page()
    else:
        _render_placeholder_page(route)
