from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional

import streamlit as st


@dataclass(frozen=True)
class DraftHeaderDependencies:
    clean: Callable[[Any], str]
    remaining_pick_time: Callable[[], int]
    pause_pick_clock: Callable[[], None]
    start_pick_clock: Callable[[], None]


def render_compact_draft_header(
    deps: DraftHeaderDependencies,
    current_idx: Optional[int],
) -> None:
    """Render one compact top control strip above the board."""

    if current_idx is None:
        round_number = int(st.session_state.rounds)
        overall_pick = len(st.session_state.picks)
        remaining_text = "DONE"
        clock_label = "COMPLETE"
        current_owner = ""
    else:
        current = st.session_state.picks.loc[current_idx]
        round_number = int(current["round"])
        overall_pick = int(current["overall"])
        remaining = max(0, int(deps.remaining_pick_time()))
        remaining_text = f"{remaining // 60}:{remaining % 60:02d}"
        current_owner = deps.clean(current["current_owner"])
        clock_label = (
            "YOUR PICK"
            if current_owner == deps.clean(st.session_state.user_team)
            else "CPU PICK"
        )

    with st.container(key="v640_header"):
        title_col, cpu_col, clock_col, action_col = st.columns(
            [6.6, 0.95, 0.72, 1.18],
            gap="small",
        )

        with title_col:
            st.markdown(
                f"""
                <div class="v640-title-line">
                    <span class="v640-title">Mock Draft</span>
                    <span class="v640-chip">Round {round_number} · Pick {overall_pick}</span>
                    <span class="v640-chip">10-Team PPR</span>
                    <span class="v640-chip">Snake Draft</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with cpu_col:
            status = "CPU ON" if st.session_state.draft_active else "CPU PAUSED"
            st.markdown(
                f'<div class="v640-cpu">● {status}</div>',
                unsafe_allow_html=True,
            )

        with clock_col:
            st.markdown(
                f"""
                <div class="v640-clock">
                    <div class="v640-clock-time">{remaining_text}</div>
                    <div class="v640-clock-label">{clock_label}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with action_col:
            if st.session_state.draft_active:
                if st.button(
                    "Pause Draft",
                    use_container_width=True,
                    key="v640_pause",
                ):
                    st.session_state.draft_active = False
                    deps.pause_pick_clock()
                    st.rerun()
            else:
                if st.button(
                    "Start Draft",
                    use_container_width=True,
                    key="v640_start",
                ):
                    st.session_state.draft_active = True
                    if (
                        current_idx is not None
                        and current_owner
                        == deps.clean(st.session_state.user_team)
                    ):
                        deps.start_pick_clock()
                    st.rerun()
