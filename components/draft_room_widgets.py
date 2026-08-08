"""Draft Room UI widgets: header, player toolbar, player table, and queue
panel.

Split out of the former monolithic runtime.py. These functions do the
actual st.markdown/st.button rendering for the Draft Room; draft_room.py
and bottom_sheet.py handle the surrounding layout/CSS.
"""
from __future__ import annotations

from typing import Optional

import pandas as pd
import streamlit as st

from fantasysync.app_state import clean, dock_settings, numeric
from fantasysync.draft_engine import (
    add_to_queue,
    build_team_roster,
    clear_player_queue,
    clean_player_queue,
    draft_top_queue_player,
    handle_user_draft_click,
    move_queue_player,
    pause_pick_clock,
    player_map,
    player_value_badge,
    remaining_pick_time,
    remove_from_queue,
    start_pick_clock,
)
from fantasysync.player_pool import (
    ensure_draft_filters,
    filtered_draft_pool,
    render_position_filter,
    set_player_sort,
    sort_player_pool,
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

    with st.container(key="v61_player_toolbar"):
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

    # Sleeper-style two-tier header: a group row (PROJ / RUSHING /
    # RECEIVING / PASSING) sits above the sortable sub-columns. Both rows
    # reuse this same `widths` list so their column boundaries line up
    # exactly. Each stat group only has one populated sub-column today
    # (e.g. RUSHING -> RUSH yards only, no attempts/TDs yet), but the
    # structure is ready for more columns per group later.
    headers = [
        "",
        "",
        "RK",
        "PLAYER",
        "TIER",
        "SCORE",
        "ADP",
        "BYE",
        "PROJ",
        "AVG",
        "RUSH",
        "REC",
        "PASS",
        "VAL",
    ]
    widths = [
        0.38,
        0.36,
        0.40,
        1.65,
        0.48,
        0.54,
        0.50,
        0.46,
        0.56,
        0.54,
        0.54,
        0.54,
        0.54,
        0.48,
    ]
    group_labels = {
        "PROJ": "PROJ",
        "RUSH": "RUSHING",
        "REC": "RECEIVING",
        "PASS": "PASSING",
    }

    with st.container(key="v731_group_header"):
        group_cols = st.columns(widths)
        for col, label in zip(group_cols, headers):
            group_text = group_labels.get(label, "")
            css_class = "player-table-group2"
            if label in group_labels:
                css_class += " player-table-group2-divider"
            col.markdown(
                f"<div class='{css_class}'>{group_text}</div>",
                unsafe_allow_html=True,
            )

    active_sort = str(st.session_state.player_sort_column).upper()
    active_ascending = bool(st.session_state.player_sort_ascending)

    with st.container(key="v732_column_header"):
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
                tier or "—",
                score_text,
                adp_text,
                bye_text,
                proj_text,
                avg_text,
                rush_text,
                rec_text,
                pass_text,
            ]

            for col, value in zip(cols[4:13], values):
                col.markdown(
                    f"<div class='stat2'>{value}</div>",
                    unsafe_allow_html=True,
                )

            cols[13].markdown(
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
