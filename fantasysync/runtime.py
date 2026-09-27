"""FantasySync Streamlit runtime: session init, navigation, and page dispatch.

Executed fresh on every Streamlit rerun by ``fantasysync.entrypoint``. This is
the module that actually draws the app; the individual page/component
modules (``fantasysync.draft_engine``, ``fantasysync.app_state``,
``fantasysync.player_pool``, ``components.*``) only expose functions and are
never invoked on their own.
"""
from __future__ import annotations

import html

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
    player_tray_settings,
    render_dynamic_dock_css,
    render_player_tray_css,
)
from fantasysync.config import (
    PPR_RECEPTION_VALUE,
    SCORING_FORMAT_LABEL,
    STARTER_TARGETS,
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
from fantasysync.navigation import (
    go_to_page,
    render_draft_room_actions,
    render_top_navigation,
)
from fantasysync.persistence import save_shared_picks
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
        # The draft just finished - a real checkpoint (see
        # fantasysync/persistence.py), and the tray needs to wake up out
        # of its "drafting disabled" state same as the user's-turn
        # transition below, so this gets its own st.rerun() too.
        #
        # The actual save is deferred to _render_draft_room_page (a flag,
        # not a direct call here) rather than done inline before
        # st.rerun() - confirmed live against the real deployed app that a
        # save done here blocks this fragment on a real network round trip
        # to Supabase *before* the rerun that's supposed to wake the tray
        # back up, so the whole page visibly freezes for however long that
        # request takes. Deferring it to run after the tray has already
        # rendered on the next full rerun means the user sees their turn
        # arrive immediately - the save then happens in the background of
        # that same script run instead of blocking the transition.
        st.session_state.draft_active = False
        st.session_state["_pending_shared_save"] = True
        st.rerun()

    next_owner = clean(st.session_state.picks.loc[next_idx, "current_owner"])
    if next_owner == clean(st.session_state.user_team):
        start_pick_clock()
        st.session_state["_pending_shared_save"] = True
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
    docstring.

    Always mounted, even in Edit Board mode - it just skips ticking and
    shows a placeholder instead of unmounting itself. Streamlit's own
    run_every timer keeps firing against this fragment's id regardless of
    what the rest of the page does; toggling Edit Board used to skip
    calling this function entirely, and the still-in-flight scheduled tick
    would then arrive for a fragment id the page no longer had, which
    reliably blanked the whole page (confirmed live - see the "fragment
    ... does not exist anymore" warning in the server log). Keeping it
    mounted and just making it a no-op while editing avoids that class of
    bug entirely.
    """
    if st.session_state.get("board_edit_mode"):
        return current_open_index(), False
    _tick_cpu_draft()
    return render_header_and_board(deps)


def _rename_team(team_id: int, new_name: str) -> None:
    """Renames a team from its Draft Room team-selector button (see
    components.draft_room's rename popover). Permanent and shared, not
    session-local - cascades the new name into every pick's
    original_owner/current_owner (the strings the rest of the app actually
    matches team identity by, per app_state.snake_order) and saves through
    the same shared-picks persistence as everything else on the board, so
    every visitor sees it and it survives a reboot (see the team_name
    reconciliation in app_state.init_state, which reads it back out)."""
    new_name = clean(new_name)
    if not new_name:
        return

    teams = st.session_state.teams
    match = teams.index[teams["team_id"] == team_id]
    if match.empty:
        return
    old_name = clean(teams.loc[match[0], "team_name"])
    if old_name == new_name:
        return

    teams = teams.copy()
    teams.loc[match[0], "team_name"] = new_name
    st.session_state.teams = teams

    picks = st.session_state.picks.copy()
    picks.loc[picks["original_owner"] == old_name, "original_owner"] = new_name
    picks.loc[picks["current_owner"] == old_name, "current_owner"] = new_name
    st.session_state.picks = picks

    if clean(st.session_state.user_team) == old_name:
        st.session_state.user_team = new_name

    save_shared_picks(picks)


def _render_draft_room_page() -> None:
    apply_team_query_selection()

    header_cols = st.columns([2.4, 1.5], gap="small")
    with header_cols[0]:
        edit_mode = st.toggle(
            "✎ Edit Board",
            key="board_edit_mode",
            help=(
                "Set keepers or trade an undrafted pick directly on the "
                "board. Pauses the live draft while it's on."
            ),
        )
    with header_cols[1]:
        render_draft_room_actions(
            rebuild_draft=rebuild_draft,
            serializable_state=serializable_state,
        )

    deps = DraftRoomDependencies(
        current_open_index=current_open_index,
        render_player_tray_css=render_player_tray_css,
        render_header=render_v53_header,
        clean=clean,
        remaining_pick_time=remaining_pick_time,
        pause_pick_clock=pause_pick_clock,
        start_pick_clock=start_pick_clock,
        reset_pick_clock=reset_pick_clock,
        rename_team=_rename_team,
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

    if edit_mode:
        # Real st.popover widgets per cell (see _render_board_edit_grid's
        # docstring) are only cheap to pay for because this replaces the
        # ticker's own rendering instead of running alongside it - the
        # fragment above is still mounted (see its own docstring) but is a
        # no-op while this is on.
        if st.session_state.pop("_board_edit_saved", False):
            st.success("Saved. Draft board updated.")
        st.info("Edit Board is on - the live draft is paused. Turn it off to resume drafting.")
        _render_board_edit_grid()
        return

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

    # Deferred shared-board checkpoints (see _tick_cpu_draft and
    # auto_pick_user_if_expired) land here, after the tray has already
    # rendered - the real Supabase network round trip happens in the
    # background of finishing this script run instead of blocking the
    # st.rerun() that's supposed to make the transition feel instant.
    if st.session_state.pop("_pending_shared_save", False):
        save_shared_picks(st.session_state.picks)


def _render_home_page() -> None:
    """Landing page: league snapshot, quick links, and a compact fantasy
    football quick-reference - the site's front door instead of dropping
    straight into the Draft Room. Every number here is real (this league's
    own settings/teams/keepers), not placeholder copy."""
    espn = fetch_espn_league_summary()
    league_name = espn["league_name"] if espn else "FantasySync Mock Draft"
    team_count = len(st.session_state.teams)
    keeper_count = int((st.session_state.keepers["player"].astype(str).str.strip() != "").sum())
    rounds = int(st.session_state.rounds)

    with st.container(key="home_hero"):
        st.markdown(
            f"""
            <div class="home-hero-title">{league_name}</div>
            <div class="home-hero-chips">
                <span class="home-chip">{team_count}-Team {SCORING_FORMAT_LABEL}</span>
                <span class="home-chip">Snake Draft</span>
                <span class="home-chip">{rounds} Rounds</span>
                <span class="home-chip">{keeper_count} Keeper{"s" if keeper_count != 1 else ""} Set</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.write("")
    link_cols = st.columns(2, gap="small")
    with link_cols[0]:
        if st.button("Enter Draft Room", key="home_go_draft", use_container_width=True, type="primary"):
            go_to_page("Draft Room")
    with link_cols[1]:
        if st.button("Rankings & ADP", key="home_go_rankings", use_container_width=True):
            go_to_page("Rankings")

    st.write("")
    snapshot_col, reference_col = st.columns([1.1, 1], gap="large")

    with snapshot_col:
        st.subheader("League Snapshot")
        teams = st.session_state.teams.sort_values("draft_slot")

        # ESPN is the source of truth for what a team is currently called
        # and who owns it - data/teams.csv (League Setup) only still
        # supplies draft order and is a fallback for when ESPN isn't
        # connected or a specific team has no match. Matched by team name
        # first - the local teams.csv has no ESPN team id of its own, and
        # team name is the most direct shared field - but several owners
        # have renamed their team on ESPN since teams.csv was last updated
        # (confirmed live: 4 of 10 team names have since diverged), so
        # unmatched teams fall back to a substring match against the ESPN
        # owner's name instead, which held stable for all of them.
        espn_teams_by_name = {}
        espn_teams_by_owner = []
        if espn is not None:
            for espn_team in espn.get("teams", []):
                name_key = clean(espn_team.get("team_name", "")).lower()
                if name_key:
                    espn_teams_by_name[name_key] = espn_team
                owner_key = clean(espn_team.get("owner", "")).lower()
                if owner_key:
                    espn_teams_by_owner.append((owner_key, espn_team))

        def _find_espn_team(team_name: str, owner: str) -> dict | None:
            espn_team = espn_teams_by_name.get(team_name.lower())
            if espn_team:
                return espn_team
            owner_lower = owner.lower()
            if owner_lower:
                for owner_key, espn_team in espn_teams_by_owner:
                    if owner_lower in owner_key or owner_key in owner_lower:
                        return espn_team
            return None

        for row in teams.itertuples():
            local_owner = clean(getattr(row, "owner", ""))
            local_team_name = clean(row.team_name)
            espn_team = _find_espn_team(local_team_name, local_owner)

            team_name = clean(espn_team.get("team_name", "")) if espn_team else local_team_name
            owner = clean(espn_team.get("owner", "")) if espn_team else local_owner
            logo_url = espn_team.get("logo_url") if espn_team else None
            owner_suffix = f" — {html.escape(owner)}" if owner else ""

            if logo_url:
                st.markdown(
                    f"""
                    <div class="team-snapshot-row">
                        <img class="team-snapshot-logo" src="{html.escape(logo_url, quote=True)}" alt="">
                        <span><b>{int(row.draft_slot)}.</b> {html.escape(team_name)}{owner_suffix}</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f"**{int(row.draft_slot)}.** {html.escape(team_name)}{owner_suffix}"
                )
        if espn is None:
            st.caption(
                "Not connected to ESPN. Add `ESPN_LEAGUE_ID`/`ESPN_S2`/`ESPN_SWID` "
                "in Streamlit secrets, or check the Data Status page."
            )

    with reference_col:
        st.subheader("Quick Reference")
        starters = ", ".join(f"{n}× {pos}" for pos, n in STARTER_TARGETS.items())
        st.markdown(
            f"""
- **Snake draft:** pick order reverses each round, so the team picking last in Round 1 picks first in Round 2.
- **{SCORING_FORMAT_LABEL} scoring:** {PPR_RECEPTION_VALUE} points per reception, on top of standard yardage/TD scoring.
- **Starting lineup:** {starters}, plus 1× FLEX (RB/WR/TE).
- **Keepers** lock in before the draft and are marked on the board automatically - see the Keepers page to add or edit one.
            """
        )

    st.write("")
    stats_season = get_stats_season_label()
    st.caption(
        (f"Rankings pulling live ADP + {stats_season} season stats. " if stats_season else "")
        + "Full data source status on the Data Status page."
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


_NO_KEEPER = "— None (no keeper) —"


def _pick_label(round_: int, slot: int) -> str:
    """Matches the draft board's own "round.pick" notation (snake order
    reverses the visual pick-in-round on even rounds)."""
    pick_in_round = slot if round_ % 2 == 1 else 11 - slot
    return f"{round_}.{pick_in_round}"


def _render_board_edit_grid() -> None:
    """Click-a-cell board editor: set a keeper and/or trade an undrafted
    pick, right on a grid shaped like the draft board itself (one row per
    round, one column per team) - the same two things the old separate
    Keepers and Trades tabs did, now merged into one per-cell popover and
    only shown while Edit Board mode is on (see _render_draft_room_page).

    Real st.popover widgets per cell, same as the pages this replaces -
    the live Draft Room board is normally one static HTML string
    (fantasysync.draft_engine.snake_board_html) specifically so it stays
    cheap to redraw on every CPU-ticker fragment tick; this grid only
    renders in Edit Board mode, which pauses that ticker first, so it
    never pays the interactive-widget cost during normal ticking play.
    """
    teams = st.session_state.teams.sort_values("draft_slot")
    team_by_slot = {int(row.draft_slot): row for row in teams.itertuples()}
    team_names = teams["team_name"].map(clean).tolist()
    max_round = int(st.session_state.rounds)
    all_player_names = sorted(
        st.session_state.players["player"].dropna().map(clean).unique().tolist()
    )

    picks = st.session_state.picks
    # A pick counts as "the draft has started" only once something other
    # than a keeper has been selected there - keeper pre-fills happen
    # automatically at rebuild time regardless of draft progress, so they
    # don't count.
    draft_started = bool((
        (picks["selected_player"] != "") & (picks["source"] != "Keeper")
    ).any())
    if draft_started:
        st.info(
            "A draft is in progress. Setting or changing a keeper here "
            "will reset it and rebuild the board. Trading a pick will not."
        )

    with st.container(key="board_edit_grid"):
        header_cols = st.columns(10, gap="small")
        for col, slot in zip(header_cols, range(1, 11)):
            team_row = team_by_slot.get(slot)
            col.markdown(
                f"<div class='keeper-grid-team'>{clean(team_row.team_name) if team_row else ''}</div>",
                unsafe_allow_html=True,
            )

        for rnd in range(1, max_round + 1):
            row_cols = st.columns(10, gap="small")
            for slot in range(1, 11):
                team_row = team_by_slot.get(slot)
                if team_row is None:
                    continue
                team_id = int(team_row.team_id)
                pick_label = _pick_label(rnd, slot)

                pick_matches = picks.index[
                    (picks["round"] == rnd) & (picks["slot"] == slot)
                ].tolist()
                pick_idx = pick_matches[0] if pick_matches else None
                pick_row = picks.loc[pick_idx] if pick_idx is not None else None
                current_owner = (
                    clean(pick_row["current_owner"]) if pick_row is not None
                    else clean(team_row.team_name)
                )
                drafted_player = clean(pick_row["selected_player"]) if pick_row is not None else ""
                tradeable = pick_row is not None and drafted_player == ""

                keepers = st.session_state.keepers
                existing = keepers[
                    (keepers["team_id"] == team_id) & (keepers["keeper_round"] == rnd)
                ]
                existing_idx = existing.index[0] if not existing.empty else None
                existing_player = (
                    clean(existing.iloc[0]["player"]) if existing_idx is not None else ""
                )

                cell_label = existing_player or drafted_player or pick_label

                with row_cols[slot - 1]:
                    with st.popover(
                        cell_label,
                        use_container_width=True,
                        key=f"board_cell_{rnd}_{slot}",
                    ):
                        caption = f"{pick_label} · {current_owner}"
                        if drafted_player and not existing_player:
                            caption += f" · Drafted: {drafted_player}"
                        st.caption(caption)

                        st.markdown("**Set keeper**")
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
                            key=f"board_cell_keeper_select_{rnd}_{slot}",
                            label_visibility="collapsed",
                        )

                        if st.button(
                            "Save Keeper",
                            key=f"board_cell_keeper_save_{rnd}_{slot}",
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
                            st.session_state["_board_edit_saved"] = True
                            st.rerun()

                        if tradeable:
                            st.divider()
                            st.markdown("**Trade this pick**")
                            new_owner = st.selectbox(
                                "Current owner",
                                team_names,
                                index=team_names.index(current_owner) if current_owner in team_names else 0,
                                key=f"board_cell_trade_select_{rnd}_{slot}",
                                label_visibility="collapsed",
                            )
                            if st.button(
                                "Save Trade",
                                key=f"board_cell_trade_save_{rnd}_{slot}",
                                use_container_width=True,
                            ):
                                if new_owner != current_owner:
                                    new_picks = st.session_state.picks.copy()
                                    new_picks.loc[pick_idx, "current_owner"] = new_owner
                                    st.session_state.picks = new_picks
                                    save_shared_picks(st.session_state.picks)
                                    st.session_state["_board_edit_saved"] = True
                                    st.rerun()


def render_app() -> None:
    init_state()
    render_dynamic_dock_css()

    route = render_top_navigation()

    if route == "Home":
        _render_home_page()
    elif route == "Draft Room":
        _render_draft_room_page()
    elif route == "Rankings & ADP":
        _render_rankings_page()
