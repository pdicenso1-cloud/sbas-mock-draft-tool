from __future__ import annotations

import json

import pandas as pd
import streamlit as st
from streamlit_autorefresh import st_autorefresh
from components.draft_room import (
    DraftRoomDependencies,
    render_draft_room,
)
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
from fantasysync.config import ADP_COLUMNS
from fantasysync.draft_engine import (
    auto_pick_user_if_expired,
    available_players,
    build_team_roster,
    current_open_index,
    initialize_cpu_variance,
    load_state_data,
    next_user_pick,
    pause_pick_clock,
    rebuild_draft,
    recommendations,
    remaining_pick_time,
    reset_pick_clock,
    roster_position_counts,
    run_one_cpu_pick,
    serializable_state,
    snake_board_html,
    start_pick_clock,
)
from fantasysync.navigation import render_top_navigation
from fantasysync.paths import DATA_DIR, PROJECT_ROOT
from fantasysync.player_pool import apply_team_query_selection

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

