
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

APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "data"
STATE_FILE = DATA_DIR / "saved_state.json"

ROSTER_SLOTS = ["QB", "RB1", "RB2", "WR1", "WR2", "TE"] + [f"BN{i}" for i in range(1, 11)]
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

st.set_page_config(page_title="Susan Boyles Ass Sweat — Mock Draft Tool", page_icon="🏈", layout="wide")

st.markdown("""
<style>
.block-container {padding-top: 1.1rem; padding-bottom: 2rem;}
[data-testid="stMetricValue"] {font-size: 1.35rem;}
.fs-card {border:1px solid rgba(128,128,128,.28); border-radius:12px; padding:14px; margin-bottom:10px;}
.snake-cell {border:1px solid rgba(128,128,128,.30); border-radius:6px; padding:5px; min-height:58px; margin:1px; overflow:hidden;}
.snake-team-select {
    border:1px solid rgba(128,128,128,.34);
    border-radius:7px;
    min-height:38px;
    padding:5px 4px;
    text-align:center;
    background:rgba(255,255,255,.02);
}
.snake-team-select.active {
    background:#2A9D8F;
    color:white;
    border-color:#2A9D8F;
}
.snake-team-select .slot-num {
    font-size:.62rem;
    opacity:.72;
}
.snake-team-select .team-label {
    font-size:.64rem;
    font-weight:700;
    white-space:nowrap;
    overflow:hidden;
    text-overflow:ellipsis;
}
.snake-pick {font-size:.62rem; opacity:.68;}
.snake-team {font-size:.61rem; opacity:.72; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;}
.snake-player {font-weight:700; font-size:.72rem; margin-top:2px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;}
.snake-pos {font-size:.60rem; opacity:.78; font-weight:700;}
.snake-cell.pos-qb {background:linear-gradient(145deg,rgba(143,83,255,.32),rgba(60,37,94,.88)); border-color:rgba(170,120,255,.68);}
.snake-cell.pos-rb {background:linear-gradient(145deg,rgba(32,180,110,.28),rgba(22,65,55,.86)); border-color:rgba(58,205,137,.62);}
.snake-cell.pos-wr {background:linear-gradient(145deg,rgba(56,115,255,.32),rgba(24,43,83,.88)); border-color:rgba(90,145,255,.68);}
.snake-cell.pos-te {background:linear-gradient(145deg,rgba(244,151,55,.30),rgba(92,58,27,.86)); border-color:rgba(255,179,85,.64);}
.snake-cell.empty-pick {background:rgba(255,255,255,.018);}
.snake-cell.keeper-pick {box-shadow:inset 0 0 0 2px rgba(255,209,67,.85);}
.snake-cell.user-pick {border-color:#2A9D8F; box-shadow:inset 0 0 0 1px rgba(42,157,143,.65);}
.snake-cell.current-pick {border-color:#FFE45E; box-shadow:0 0 0 2px #FFE45E,0 0 16px rgba(255,228,94,.45); animation:currentPickPulse 1.2s ease-in-out infinite alternate;}
@keyframes currentPickPulse {from{filter:brightness(1)} to{filter:brightness(1.25)}}

.rec-card {border:1px solid rgba(128,128,128,.28); border-radius:12px; padding:12px; height:100%;}
.player-card {border:1px solid rgba(128,128,128,.30); border-radius:12px; padding:12px; min-height:118px; margin-top:8px; background:rgba(255,255,255,.025);}
.player-rank {font-size:.78rem; opacity:.65;}
.player-name {font-weight:800; font-size:1rem; margin-top:3px; line-height:1.2;}
.player-meta {font-size:.80rem; opacity:.72; margin-top:4px;}
.small-muted {opacity:.68; font-size:.84rem;}

.top-control-bar {
    border:1px solid rgba(150,170,210,.25);
    border-radius:14px;
    padding:10px 14px;
    background:rgba(23,36,58,.92);
    margin-bottom:10px;
}
.st-key-draft_drawer {
    position: fixed;
    left: 0;
    right: 0;
    bottom: 0;
    z-index: 999;
    background: rgba(24, 34, 53, 0.995);
    border-top: 1px solid rgba(150, 170, 210, .28);
    box-shadow: 0 -8px 20px rgba(0,0,0,.34);
    padding: 0.15rem 0.4rem 0.3rem 0.4rem;
    backdrop-filter: blur(14px);
}
.fixed-dock-spacer {
    height: 36px;
}
.roster-mini-card {
    border:1px solid rgba(150,170,210,.22);
    border-radius:8px;
    padding:5px 7px;
    margin-bottom:4px;
    background:rgba(255,255,255,.025);
}
.roster-slot {
    font-size:.72rem;
    opacity:.65;
}
.roster-player {
    font-size:.75rem;
    font-weight:700;
}


.st-key-draft_drawer .player-card {
    min-height: 88px;
    padding: 8px;
    margin-top: 4px;
}
.st-key-draft_drawer .player-rank {
    font-size: .66rem;
}
.st-key-draft_drawer .player-name {
    font-size: .82rem;
}
.st-key-draft_drawer .player-meta {
    font-size: .68rem;
    margin-top: 2px;
}
.st-key-draft_drawer h4 {
    font-size: .95rem;
    margin-bottom: .25rem;
}
.st-key-draft_drawer [data-testid="stDataFrame"] {
    font-size: .72rem;
}
.team-select-title {
    font-size:.78rem;
    opacity:.72;
    margin-bottom:.3rem;
}


.player-tile-badge {display:inline-flex;align-items:center;border-radius:999px;padding:2px 7px;font-size:.58rem;font-weight:900;margin-top:2px;color:white;}
.badge-qb{background:#7C3AED}.badge-wr{background:#2563EB}.badge-rb{background:#16A34A}.badge-te{background:#EA7C16}
.tile-nfl {font-size:.58rem;opacity:.78;margin-left:4px;}
.tile-owner {font-size:.56rem;opacity:.72;margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.war-room-title {font-size:.72rem;font-weight:900;letter-spacing:.08em;opacity:.72;margin-bottom:.2rem;}
.recommendation-card {border:1px solid rgba(150,170,210,.22);border-radius:9px;padding:7px;margin-bottom:5px;background:rgba(255,255,255,.025);}
.recommendation-player {font-weight:800;font-size:.78rem;}
.recommendation-meta {font-size:.64rem;opacity:.72;}
.st-key-draft_drawer {padding:.25rem .55rem .45rem .55rem !important;}
.st-key-draft_drawer > div {max-width:100% !important;}
.st-key-draft_drawer [data-testid="stVerticalBlock"] {gap:.35rem;}
.st-key-draft_drawer {height:38vh;overflow-y:auto;}
.fixed-dock-spacer {height:300px !important;}


.player-table-header {
    display:grid;
    grid-template-columns: 42px minmax(155px,2.2fr) 46px 48px 58px 48px 58px 36px;
    gap:5px;
    align-items:center;
    padding:5px 6px;
    font-size:.63rem;
    font-weight:800;
    opacity:.65;
    border-bottom:1px solid rgba(150,170,210,.24);
}
.player-row-shell {
    border-bottom:1px solid rgba(150,170,210,.13);
    padding:2px 0;
}
.player-row-rank {
    font-size:.68rem;
    opacity:.68;
    text-align:center;
    padding-top:7px;
}
.player-row-name {
    font-size:.78rem;
    font-weight:800;
    white-space:nowrap;
    overflow:hidden;
    text-overflow:ellipsis;
    padding-top:4px;
}
.player-row-team {
    font-size:.64rem;
    opacity:.62;
    margin-top:-2px;
}
.player-row-stat {
    font-size:.69rem;
    opacity:.80;
    text-align:center;
    padding-top:7px;
}
.pos-chip {
    display:inline-block;
    min-width:34px;
    padding:3px 5px;
    border-radius:999px;
    font-size:.62rem;
    font-weight:900;
    color:white;
    text-align:center;
    margin-top:4px;
}
.pos-chip-QB {background:#7E57C2;}
.pos-chip-WR {background:#2F80ED;}
.pos-chip-RB {background:#2E9D63;}
.pos-chip-TE {background:#F2994A;}
.pos-chip-OTHER {background:#6B7280;}
.st-key-available_player_rows {
    border:1px solid rgba(150,170,210,.20);
    border-radius:9px;
    padding:2px 6px 4px 6px;
    background:rgba(255,255,255,.012);
}
.st-key-available_player_rows button {
    min-height:29px !important;
    height:29px !important;
    padding:0 !important;
    font-size:1.05rem !important;
    font-weight:900 !important;
    border-radius:6px !important;
    margin-top:2px !important;
}


.war-room-shell {
    display:grid;
    grid-template-columns:minmax(0,3fr) minmax(260px,1fr);
    gap:10px;
}
.player-panel-title {
    font-size:.76rem;
    font-weight:800;
    opacity:.70;
    letter-spacing:.04em;
    margin-bottom:4px;
}
.player-table-grid {
    display:grid;
    grid-template-columns:38px 42px minmax(165px,2.1fr) 54px 54px 58px 58px 58px 58px 58px 58px 58px 58px 58px;
    gap:0;
    align-items:center;
}
.player-table-grid > div {
    border-right:1px solid rgba(150,170,210,.12);
}
.player-table-header2 {
    font-size:.60rem;
    font-weight:800;
    opacity:.58;
    text-align:center;
    padding:5px 3px;
    border-bottom:1px solid rgba(150,170,210,.22);
}
.player-row2 {
    min-height:44px;
    border-bottom:1px solid rgba(150,170,210,.12);
    background:rgba(255,255,255,.012);
}
.player-row2:nth-child(even) {
    background:rgba(255,255,255,.026);
}
.player-name2 {
    font-size:.76rem;
    font-weight:800;
    white-space:nowrap;
    overflow:hidden;
    text-overflow:ellipsis;
    padding:4px 6px 0 7px;
}
.player-sub2 {
    font-size:.62rem;
    opacity:.64;
    padding-left:7px;
    margin-top:-2px;
}
.stat2 {
    font-size:.67rem;
    text-align:center;
    padding-top:11px;
}
.rank2 {
    font-size:.67rem;
    text-align:center;
    opacity:.72;
    padding-top:11px;
}
.pos-dot {
    display:inline-block;
    width:6px;
    height:6px;
    border-radius:50%;
    margin-right:4px;
}
.dot-QB {background:#7E57C2;}
.dot-WR {background:#2F80ED;}
.dot-RB {background:#2E9D63;}
.dot-TE {background:#F2994A;}
.dot-OTHER {background:#6B7280;}
.st-key-war_player_list {
    border:1px solid rgba(150,170,210,.18);
    border-radius:8px;
    background:rgba(255,255,255,.01);
}
.st-key-war_player_list button {
    min-height:28px !important;
    height:28px !important;
    padding:0 !important;
    border-radius:50% !important;
    font-size:1.0rem !important;
    font-weight:900 !important;
}
.st-key-war_roster_panel {
    border-left:1px solid rgba(150,170,210,.22);
    padding-left:10px;
}
.roster-tab-title {
    font-size:.72rem;
    font-weight:800;
    color:#8EA2FF;
    margin-bottom:6px;
}
.compact-rec {
    border:1px solid rgba(150,170,210,.16);
    border-radius:8px;
    padding:6px 8px;
    margin-bottom:5px;
    background:rgba(255,255,255,.015);
}
.compact-rec-name {
    font-size:.72rem;
    font-weight:800;
}
.compact-rec-meta {
    font-size:.61rem;
    opacity:.66;
}
.war-search-row {
    margin-bottom:4px;
}


.st-key-draft_drawer [data-testid="stVerticalBlock"] {
    gap: .18rem !important;
}
.st-key-draft_drawer [data-testid="stHorizontalBlock"] {
    gap: .35rem !important;
}
.st-key-draft_drawer .stTextInput {
    margin-bottom: 0 !important;
}
.st-key-draft_drawer [data-testid="stTextInputRootElement"] {
    min-height: 32px !important;
}
.st-key-draft_drawer [data-testid="stButton"] button {
    min-height: 28px !important;
}
.st-key-draft_drawer hr {
    margin: .1rem 0 !important;
}
.st-key-war_roster_panel {
    max-height: 355px;
    overflow-y: auto;
}


/* Cleaner player table header */
.st-key-war_player_list {
    border: 0 !important;
    border-radius: 0 !important;
    background: transparent !important;
}
.st-key-war_player_list [data-testid="stHorizontalBlock"] {
    border-bottom: 1px solid rgba(150,170,210,.10);
}
.player-table-header2 {
    border-bottom: 0 !important;
    padding: 2px 3px 5px 3px !important;
    line-height: 1 !important;
    background: transparent !important;
}
.st-key-draft_drawer > div > div > div [data-testid="stHorizontalBlock"]:has(.player-table-header2) {
    border-bottom: 1px solid rgba(150,170,210,.20) !important;
    padding-bottom: 2px !important;
    margin-bottom: 2px !important;
}
.st-key-draft_drawer [data-testid="stMarkdownContainer"] p {
    margin-bottom: 0 !important;
}
.st-key-draft_drawer [data-testid="stHorizontalBlock"] {
    align-items: center !important;
}

/* Compact player rows */
.st-key-war_player_list [data-testid="stHorizontalBlock"] {
    min-height: 35px !important;
    padding: 0 !important;
}
.player-name2 {
    padding-top: 1px !important;
    font-size: .73rem !important;
}
.player-sub2 {
    margin-top: -4px !important;
    font-size: .58rem !important;
}
.stat2,
.rank2 {
    padding-top: 4px !important;
    font-size: .64rem !important;
}

/* Compact roster list */
.st-key-war_roster_panel {
    max-height: 300px !important;
    overflow-y: auto;
    padding-left: 8px !important;
}
.st-key-war_roster_panel .roster-mini-card {
    border: 0 !important;
    border-bottom: 1px solid rgba(150,170,210,.12) !important;
    border-radius: 0 !important;
    padding: 3px 2px 4px 2px !important;
    margin-bottom: 0 !important;
    background: transparent !important;
    min-height: 31px !important;
}
.st-key-war_roster_panel .roster-slot {
    font-size: .57rem !important;
    opacity: .55 !important;
    line-height: 1 !important;
}
.st-key-war_roster_panel .roster-player {
    font-size: .69rem !important;
    line-height: 1.1 !important;
    margin-top: 1px !important;
}
.st-key-war_roster_panel .small-muted {
    font-size: .56rem !important;
    line-height: 1 !important;
}
.st-key-war_roster_panel h4,
.st-key-war_roster_panel .roster-tab-title {
    margin: 0 0 3px 0 !important;
}


/* v2.3 bottom deck */
.st-key-draft_drawer {
    height: 38vh !important;
    overflow: hidden !important;
    padding: .35rem .65rem .45rem .65rem !important;
    background: rgba(35, 46, 68, .995) !important;
}
.st-key-draft_drawer [data-testid="stHorizontalBlock"] {
    gap: .5rem !important;
}
.st-key-draft_drawer [data-testid="stVerticalBlock"] {
    gap: .22rem !important;
}

/* Search and position filters */
.st-key-draft_drawer [data-testid="stTextInputRootElement"] {
    min-height: 36px !important;
    border-radius: 18px !important;
}
.st-key-draft_drawer [data-testid="stButton"] button {
    min-height: 32px !important;
}

/* Clean player table */
.player-table-header2 {
    border: 0 !important;
    padding: 4px 2px 6px 2px !important;
    font-size: .62rem !important;
    line-height: 1 !important;
    opacity: .58 !important;
}
.st-key-war_player_list {
    border: 0 !important;
    background: transparent !important;
    border-radius: 0 !important;
}
.st-key-war_player_list [data-testid="stHorizontalBlock"] {
    min-height: 42px !important;
    border-bottom: 1px solid rgba(160,175,205,.11) !important;
    padding: 0 !important;
}
.st-key-war_player_list [data-testid="stButton"] button {
    width: 30px !important;
    min-width: 30px !important;
    height: 30px !important;
    min-height: 30px !important;
    border-radius: 50% !important;
    padding: 0 !important;
    font-size: 1rem !important;
}
.player-name2 {
    font-size: .76rem !important;
    padding: 2px 5px 0 5px !important;
}
.player-sub2 {
    font-size: .60rem !important;
    margin-top: -3px !important;
    padding-left: 5px !important;
}
.stat2,
.rank2 {
    font-size: .68rem !important;
    padding-top: 5px !important;
}

/* Roster panel */
.st-key-war_roster_panel {
    height: 34vh !important;
    overflow-y: auto !important;
    border-left: 1px solid rgba(150,170,210,.20) !important;
    padding: 0 0 0 12px !important;
}
.roster-panel-label {
    color: #8FA2FF;
    font-size: .70rem;
    font-weight: 900;
    letter-spacing: .04em;
    margin-bottom: 2px;
}
.roster-panel-team {
    font-size: .94rem;
    font-weight: 850;
    margin-bottom: 0;
}
.roster-panel-count {
    font-size: .68rem;
    opacity: .62;
    margin-bottom: 8px;
}
.roster-line {
    display: grid;
    grid-template-columns: 44px minmax(0,1fr);
    gap: 9px;
    align-items: center;
    min-height: 45px;
    padding: 4px 2px;
    border-bottom: 1px solid rgba(150,170,210,.10);
}
.roster-slot-pill {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 42px;
    height: 30px;
    border-radius: 8px;
    color: white;
    font-size: .65rem;
    font-weight: 900;
}
.roster-slot-QB {background:#7E57C2;}
.roster-slot-RB {background:#2E9D63;}
.roster-slot-WR {background:#2F80ED;}
.roster-slot-TE {background:#F2994A;}
.roster-slot-BN {background:#5E6A80;}
.roster-line-player {
    font-size: .76rem;
    font-weight: 800;
    line-height: 1.1;
}
.roster-line-meta {
    font-size: .61rem;
    opacity: .58;
    margin-top: 2px;
}
.roster-empty {
    font-size: .72rem;
    opacity: .48;
}

/* More room for the draft board above */
.fixed-dock-spacer {
    height: 30px !important;
}


/* v2.4 roster alignment */
.st-key-war_roster_panel {
    padding-left: 14px !important;
}
.roster-line {
    display: grid !important;
    grid-template-columns: 52px minmax(0,1fr) !important;
    column-gap: 10px !important;
    align-items: center !important;
    min-height: 48px !important;
    padding: 3px 0 !important;
    border-bottom: 1px solid rgba(150,170,210,.10) !important;
}
.roster-slot-pill {
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    width: 50px !important;
    height: 32px !important;
    margin: 0 !important;
    border-radius: 8px !important;
    font-size: .66rem !important;
    font-weight: 900 !important;
    line-height: 1 !important;
}
.roster-player-wrap {
    display: flex !important;
    flex-direction: column !important;
    justify-content: center !important;
    min-height: 32px !important;
    padding: 0 !important;
}
.roster-line-player {
    font-size: .77rem !important;
    font-weight: 800 !important;
    line-height: 1.08 !important;
    margin: 0 !important;
    padding: 0 !important;
}
.roster-line-meta {
    font-size: .60rem !important;
    opacity: .58 !important;
    line-height: 1 !important;
    margin-top: 3px !important;
    padding: 0 !important;
}
.roster-empty {
    display: flex !important;
    align-items: center !important;
    min-height: 32px !important;
    font-size: .72rem !important;
    opacity: .48 !important;
    margin: 0 !important;
}


/* v2.5 cleaner table header */
.st-key-draft_drawer > div > div > div [data-testid="stHorizontalBlock"]:has(.player-table-header2) {
    border-bottom: 0 !important;
    margin-bottom: 0 !important;
    padding-bottom: 0 !important;
}
.player-table-header2 {
    border: 0 !important;
    padding: 2px 2px 7px 2px !important;
    margin: 0 !important;
    line-height: 1 !important;
}
.st-key-war_player_list {
    border-top: 1px solid rgba(210,220,240,.28) !important;
    padding-top: 2px !important;
}


/* v2.5 roster spacing and inline position */
.roster-panel-label {
    margin-bottom: 6px !important;
}
.roster-panel-team {
    margin-bottom: 8px !important;
}
.roster-panel-count {
    margin-bottom: 14px !important;
}
.roster-line {
    min-height: 46px !important;
    padding: 5px 0 !important;
}
.roster-player-wrap {
    justify-content: center !important;
}
.roster-line-player {
    display: flex !important;
    align-items: center !important;
    gap: 4px !important;
    font-size: .76rem !important;
    line-height: 1.15 !important;
}
.roster-inline-pos {
    font-size: .64rem !important;
    opacity: .58 !important;
    font-weight: 600 !important;
}


/* v2.6 available-player table cleanup */

/* Header row: no divider through the labels */
.st-key-draft_drawer > div > div > div [data-testid="stHorizontalBlock"]:has(.player-table-header2) {
    border-bottom: none !important;
    margin-bottom: 0 !important;
    padding-bottom: 4px !important;
}
.player-table-header2 {
    border: 0 !important;
    margin: 0 !important;
    padding: 0 2px 5px 2px !important;
    line-height: 1 !important;
}

/* Divider belongs below the complete header row */
.st-key-war_player_list {
    border-top: 1px solid rgba(210,220,240,.30) !important;
    padding-top: 4px !important;
}

/* Cleaner, evenly spaced player rows */
.st-key-war_player_list [data-testid="stHorizontalBlock"] {
    min-height: 54px !important;
    padding: 4px 0 7px 0 !important;
    border-bottom: 1px solid rgba(160,175,205,.13) !important;
    align-items: center !important;
}

/* Keep the + button centered within each row */
.st-key-war_player_list [data-testid="stButton"] {
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
}

/* Player name and subline spacing */
.player-name2 {
    padding: 3px 5px 0 5px !important;
    margin: 0 !important;
    line-height: 1.08 !important;
}
.player-sub2 {
    padding-left: 5px !important;
    margin-top: 2px !important;
    margin-bottom: 4px !important;
    line-height: 1 !important;
}

/* Keep stat columns vertically centered */
.stat2,
.rank2 {
    padding-top: 0 !important;
    margin: 0 !important;
    line-height: 1 !important;
}

/* Slightly soften the row separators */
.st-key-war_player_list [data-testid="stHorizontalBlock"]:last-child {
    border-bottom: none !important;
}


/* v2.7 final available-player table spacing */

/* Keep header text clear, then place the divider lower beneath it. */
.st-key-draft_drawer > div > div > div [data-testid="stHorizontalBlock"]:has(.player-table-header2) {
    border-bottom: none !important;
    padding-bottom: 12px !important;
    margin-bottom: 0 !important;
}
.player-table-header2 {
    border: none !important;
    padding: 0 2px !important;
    margin: 0 !important;
    line-height: 1 !important;
}
.st-key-war_player_list {
    border-top: 1px solid rgba(205, 216, 236, .30) !important;
    padding-top: 5px !important;
}

/* Give every available-player row a consistent professional separator. */
.st-key-war_player_list [data-testid="stHorizontalBlock"] {
    min-height: 58px !important;
    padding: 5px 0 9px 0 !important;
    margin: 0 !important;
    border-bottom: 1px solid rgba(170, 186, 215, .18) !important;
    align-items: center !important;
}
.st-key-war_player_list [data-testid="stHorizontalBlock"]:last-child {
    border-bottom: none !important;
}

/* Add clear breathing room below the position/team subline. */
.player-name2 {
    padding: 3px 5px 0 5px !important;
    margin: 0 !important;
    line-height: 1.08 !important;
}
.player-sub2 {
    padding-left: 5px !important;
    margin-top: 3px !important;
    margin-bottom: 7px !important;
    line-height: 1 !important;
}

/* Keep buttons and numeric columns centered within the taller rows. */
.st-key-war_player_list [data-testid="stButton"] {
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
}
.stat2,
.rank2 {
    padding-top: 0 !important;
    margin: 0 !important;
    line-height: 1 !important;
}


/* v2.8 explicit table separators */
.player-header-divider {
    height: 1px;
    width: 100%;
    background: rgba(205, 216, 236, .34);
    margin: 8px 0 5px 0;
}
.player-row-divider {
    height: 1px;
    width: 100%;
    background: rgba(170, 186, 215, .20);
    margin: 5px 0 3px 0;
}
.st-key-war_player_list {
    border-top: none !important;
    padding-top: 0 !important;
}
.st-key-war_player_list [data-testid="stHorizontalBlock"] {
    border-bottom: none !important;
    min-height: 52px !important;
    padding: 4px 0 5px 0 !important;
}
.player-sub2 {
    margin-bottom: 5px !important;
}


/* Safari-safe action buttons */
.st-key-war_player_list button,
.st-key-dock_controls button {
    color: #FFFFFF !important;
    -webkit-text-fill-color: #FFFFFF !important;
    opacity: 1 !important;
    -webkit-appearance: none !important;
    appearance: none !important;
}
.st-key-war_player_list button:disabled,
.st-key-dock_controls button:disabled {
    color: rgba(255,255,255,.42) !important;
    -webkit-text-fill-color: rgba(255,255,255,.42) !important;
}


/* v3.2 roster panel alignment */
.st-key-roster_and_controls {
    padding-top: 0 !important;
}
.st-key-war_roster_panel {
    padding-top: 0 !important;
    margin-top: 0 !important;
}
.st-key-war_roster_panel [data-testid="stVerticalBlock"] {
    gap: 0 !important;
}
.roster-header-row {
    display: grid;
    grid-template-columns: auto minmax(0, 1fr) auto;
    align-items: baseline;
    column-gap: 14px;
    min-height: 52px;
    padding: 3px 52px 8px 0;
    border-bottom: 1px solid rgba(150,170,210,.18);
    margin-bottom: 6px;
}
.roster-header-label {
    color: #4F9DFF;
    font-size: .92rem;
    font-weight: 850;
    line-height: 1.1;
    text-decoration: underline;
    text-underline-offset: 4px;
    white-space: nowrap;
}
.roster-header-team {
    color: #FFFFFF;
    font-size: .92rem;
    font-weight: 850;
    line-height: 1.1;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.roster-header-count {
    color: rgba(255,255,255,.62);
    font-size: .72rem;
    font-weight: 600;
    line-height: 1.1;
    white-space: nowrap;
}
.roster-line {
    min-height: 44px !important;
    padding: 4px 0 !important;
}


/* v3.5 structural roster alignment */
.st-key-roster_header_panel {
    position: relative !important;
    padding: 0 52px 0 10px !important;
    margin: 0 !important;
}
.st-key-roster_header_panel [data-testid="stVerticalBlock"] {
    gap: 0 !important;
}
.st-key-roster_header_panel .roster-header-row {
    height: 52px !important;
    min-height: 52px !important;
    margin: 0 !important;
    padding: 0 0 7px 0 !important;
    display: grid !important;
    align-items: center !important;
    box-sizing: border-box !important;
}
.st-key-roster_and_controls {
    padding-top: 0 !important;
    margin-top: 0 !important;
}
.st-key-war_roster_panel {
    padding-top: 0 !important;
    margin-top: 0 !important;
}


/* v3.7 keep header fixed and pull only roster slots upward */
.st-key-roster_header_anchor {
    position: relative !important;
    overflow: visible !important;
    margin: 0 !important;
    padding: 0 !important;
}
.st-key-roster_header_anchor [data-testid="stVerticalBlock"] {
    gap: 0 !important;
}
.st-key-roster_rows_overlay {
    position: absolute !important;
    top: 52px !important;
    left: 0 !important;
    right: 0 !important;
    z-index: 4 !important;
    margin: 0 !important;
    padding: 0 52px 0 10px !important;
}
.st-key-roster_rows_overlay [data-testid="stVerticalBlock"] {
    gap: 0 !important;
}
.st-key-war_roster_panel {
    margin: 0 !important;
    padding: 0 !important;
    transform: none !important;
    top: auto !important;
}
.st-key-war_roster_panel .roster-line:first-child {
    margin-top: 0 !important;
}


/* v3.8 responsive draft-button feedback */
.st-key-war_player_list button {
    transition:
        background-color .10s ease,
        border-color .10s ease,
        transform .08s ease !important;
}
.st-key-war_player_list button:active {
    transform: scale(.90) !important;
    background: #2A9D8F !important;
    border-color: #2A9D8F !important;
    color: #FFFFFF !important;
    -webkit-text-fill-color: #FFFFFF !important;
}


/* v4.0 permanent sidebar navigation */
section[data-testid="stSidebar"] {
    background:
        linear-gradient(180deg, #0C1523 0%, #101B2D 100%) !important;
    border-right: 1px solid rgba(145,165,195,.18) !important;
}
section[data-testid="stSidebar"] > div {
    padding-top: .65rem !important;
}
.sidebar-brand {
    display: flex;
    align-items: center;
    gap: 9px;
    padding: 5px 5px 14px 5px;
    margin-bottom: 6px;
    border-bottom: 1px solid rgba(145,165,195,.16);
}
.sidebar-brand-icon {
    font-size: 1.55rem;
    line-height: 1;
}
.sidebar-brand-name {
    color: #F8FAFC;
    font-size: 1.04rem;
    font-weight: 850;
    letter-spacing: -.01em;
}
.sidebar-section-label {
    color: #8292AA;
    font-size: .61rem;
    font-weight: 850;
    letter-spacing: .09em;
    margin: 8px 5px 5px 5px;
}
section[data-testid="stSidebar"] [data-testid="stRadio"] > div {
    gap: 4px !important;
}
section[data-testid="stSidebar"] [data-testid="stRadio"] label {
    min-height: 42px !important;
    padding: 8px 10px !important;
    border-radius: 8px !important;
    border: 1px solid transparent !important;
    transition: background .12s ease, border-color .12s ease !important;
}
section[data-testid="stSidebar"] [data-testid="stRadio"] label:hover {
    background: rgba(63, 112, 190, .14) !important;
    border-color: rgba(95, 145, 225, .18) !important;
}
section[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {
    background: linear-gradient(
        90deg,
        rgba(41, 94, 172, .68),
        rgba(30, 68, 122, .50)
    ) !important;
    border-color: rgba(83, 148, 246, .34) !important;
    box-shadow: inset 3px 0 0 #4F9DFF !important;
}
section[data-testid="stSidebar"] [data-testid="stRadio"] label p {
    color: #F1F5F9 !important;
    font-size: .80rem !important;
    font-weight: 720 !important;
}
.sidebar-league-card {
    border: 1px solid rgba(145,165,195,.18);
    background: rgba(255,255,255,.025);
    border-radius: 10px;
    padding: 10px 11px;
    margin-top: 12px;
    color: #CBD5E1;
}
.sidebar-league-name {
    color: #F8FAFC;
    font-size: .72rem;
    font-weight: 780;
    margin-bottom: 7px;
}
.sidebar-league-meta {
    display: flex;
    justify-content: space-between;
    gap: 6px;
    font-size: .64rem;
    color: #94A3B8;
    margin-top: 4px;
}
.sidebar-version {
    color: #64748B;
    font-size: .56rem;
    text-align: center;
    margin-top: 10px;
}
.main .block-container {
    padding-top: 1.15rem !important;
}


/* v4.1 compact application header */
.app-header-shell {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    align-items: start;
    column-gap: 22px;
    margin: 0 0 8px 0;
}
.app-header-copy {
    min-width: 0;
}
.app-header-title {
    color: #F8FAFC;
    font-size: clamp(1.70rem, 2.55vw, 2.55rem);
    font-weight: 900;
    letter-spacing: -.035em;
    line-height: 1.02;
    margin: 0;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.app-header-subtitle {
    color: #9CA8B8;
    font-size: .72rem;
    font-weight: 520;
    line-height: 1.25;
    margin-top: 7px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.st-key-compact_header_actions {
    padding-top: 0 !important;
    margin-top: 0 !important;
}
.st-key-compact_header_actions [data-testid="stHorizontalBlock"] {
    gap: .55rem !important;
    align-items: flex-start !important;
}
.st-key-compact_header_actions button {
    min-height: 42px !important;
    height: 42px !important;
    padding: 0 16px !important;
    border-radius: 9px !important;
    font-size: .78rem !important;
    font-weight: 780 !important;
}
.draft-room-heading {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    align-items: center;
    column-gap: 24px;
    margin: 4px 0 8px 0;
}
.draft-room-title {
    color: #F8FAFC;
    font-size: clamp(1.25rem, 1.8vw, 1.72rem);
    font-weight: 850;
    letter-spacing: -.025em;
    line-height: 1.05;
    margin: 0;
}
.draft-clock-block {
    min-width: 235px;
    text-align: left;
}
.draft-clock-label {
    color: #CBD5E1;
    font-size: .68rem;
    font-weight: 650;
    line-height: 1;
    margin-bottom: 5px;
}
.draft-clock-value {
    color: #F8FAFC;
    font-size: clamp(1rem, 1.45vw, 1.32rem);
    font-weight: 720;
    line-height: 1.05;
    white-space: nowrap;
}
.main .block-container {
    padding-top: .65rem !important;
}
@media (max-width: 1000px) {
    .app-header-title,
    .app-header-subtitle {
        white-space: normal;
    }
    .draft-room-heading {
        grid-template-columns: 1fr;
        row-gap: 8px;
    }
    .draft-clock-block {
        min-width: 0;
    }
}


/* v4.2 prevent compact header from clipping under Streamlit toolbar */
.main .block-container {
    padding-top: 1.15rem !important;
}
.app-header-copy {
    padding-top: 2px !important;
    overflow: visible !important;
}
.app-header-title {
    line-height: 1.08 !important;
    padding-top: 1px !important;
    overflow: visible !important;
}


/* v4.3 approved professional workspace */

/* Keep the title fully visible while making it slightly smaller. */
.main .block-container {
    padding-top: 1.35rem !important;
}
.app-header-copy {
    padding-top: 5px !important;
    overflow: visible !important;
}
.app-header-title {
    font-size: clamp(1.48rem, 2.05vw, 2.05rem) !important;
    line-height: 1.16 !important;
    padding-top: 2px !important;
    overflow: visible !important;
}
.app-header-subtitle {
    margin-top: 5px !important;
    font-size: .68rem !important;
}

/* Main draft workspace: snake board left, roster right. */
.st-key-draft_workspace {
    margin-top: 2px !important;
    padding-bottom: 4px !important;
}
.st-key-draft_workspace > div > div > [data-testid="stHorizontalBlock"] {
    align-items: flex-start !important;
}
.st-key-board_workspace_panel {
    padding-right: 4px !important;
}
.st-key-board_roster_panel {
    height: calc(100vh - 235px) !important;
    min-height: 455px !important;
    overflow-y: auto !important;
    border-left: 1px solid rgba(150,170,210,.20) !important;
    padding: 0 50px 8px 14px !important;
    margin: 0 !important;
}
.st-key-board_roster_panel [data-testid="stVerticalBlock"] {
    gap: 0 !important;
}
.st-key-board_roster_panel .roster-header-row {
    position: sticky;
    top: 0;
    z-index: 3;
    background: #0E1726;
    height: 48px !important;
    min-height: 48px !important;
    margin: 0 0 5px 0 !important;
    padding: 0 0 6px 0 !important;
}
.st-key-board_roster_panel .roster-line {
    min-height: 42px !important;
    padding: 3px 0 !important;
}

/* Bottom dock now contains only the available-player experience. */
.st-key-draft_drawer {
    padding: .35rem .65rem .42rem .65rem !important;
}
.st-key-player_filter_rail {
    border-right: 1px solid rgba(150,170,210,.18) !important;
    padding-right: 10px !important;
}
.st-key-player_filter_rail [data-testid="stVerticalBlock"] {
    gap: 6px !important;
}
.st-key-player_filter_rail [data-testid="stTextInputRootElement"] {
    min-height: 36px !important;
}
.st-key-player_filter_rail button {
    min-height: 31px !important;
    height: 31px !important;
    padding: 0 8px !important;
    font-size: .67rem !important;
    font-weight: 800 !important;
}

/* Tighter available-player rows so more names fit on screen. */
.st-key-war_player_list [data-testid="stHorizontalBlock"] {
    min-height: 40px !important;
    padding: 1px 0 3px 0 !important;
}
.st-key-war_player_list [data-testid="stButton"] button {
    width: 27px !important;
    min-width: 27px !important;
    height: 27px !important;
    min-height: 27px !important;
}
.player-name2 {
    font-size: .70rem !important;
    line-height: 1.02 !important;
    padding-top: 1px !important;
}
.player-sub2 {
    font-size: .55rem !important;
    margin-top: 1px !important;
    margin-bottom: 2px !important;
}
.stat2,
.rank2 {
    font-size: .61rem !important;
}
.player-row-divider {
    margin: 2px 0 1px 0 !important;
}

/* Board should use the extra vertical space reclaimed from the header. */
.snake-board-wrap {
    margin-top: 2px !important;
}


/* v4.4 make the fixed player dock follow the Streamlit sidebar */
.st-key-draft_drawer {
    left: 0 !important;
    width: auto !important;
    transition:
        left .22s ease-in-out,
        height .22s ease-in-out !important;
}

/* Streamlit's desktop sidebar is approximately 21rem wide. */
body:has(section[data-testid="stSidebar"][aria-expanded="true"])
    .st-key-draft_drawer {
    left: 21rem !important;
}

/* Some Streamlit builds expose the open state without aria-expanded. */
body:has(
    section[data-testid="stSidebar"]:not([aria-expanded="false"])
)
    .st-key-draft_drawer {
    left: 21rem !important;
}

/* When the sidebar is explicitly collapsed, return to full width. */
body:has(section[data-testid="stSidebar"][aria-expanded="false"])
    .st-key-draft_drawer {
    left: 0 !important;
}

/* On narrower displays the sidebar overlays the page, so keep the dock full width. */
@media (max-width: 900px) {
    .st-key-draft_drawer,
    body:has(section[data-testid="stSidebar"][aria-expanded="true"])
        .st-key-draft_drawer,
    body:has(
        section[data-testid="stSidebar"]:not([aria-expanded="false"])
    )
        .st-key-draft_drawer {
        left: 0 !important;
    }
}


/* ============================================================
   v4.5 FantasySync Official Color System
   Explicit browser-safe colors, including Safari text fill.
   ============================================================ */

:root {
    --fs-bg: #0B1220;
    --fs-panel: #162033;
    --fs-panel-deep: #111827;
    --fs-border: #2B3852;
    --fs-text-primary: #F8FAFC;
    --fs-text-secondary: #CBD5E1;
    --fs-text-muted: #94A3B8;
    --fs-header: #D8E4F8;
    --fs-blue: #5B8CFF;
    --fs-green: #2DD4BF;
    --fs-draft-green: #22C55E;
    --fs-draft-green-active: #16A34A;
    --fs-action: #F15B52;
}

/* Global application text safeguards. */
html,
body,
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
.main {
    color: var(--fs-text-primary) !important;
}

[data-testid="stAppViewContainer"] {
    background: var(--fs-bg) !important;
}

p,
span,
label,
div {
    text-rendering: optimizeLegibility;
}

/* Titles and primary labels. */
.app-header-title,
.draft-room-title,
.draft-clock-value,
.sidebar-brand-name,
.roster-header-team {
    color: var(--fs-text-primary) !important;
    -webkit-text-fill-color: var(--fs-text-primary) !important;
}

.app-header-subtitle,
.draft-clock-label,
.sidebar-league-meta,
.roster-header-count {
    color: var(--fs-text-secondary) !important;
    -webkit-text-fill-color: var(--fs-text-secondary) !important;
}

/* Available-player table: never inherit a dark browser color. */
.player-name2,
.player-row-name {
    color: var(--fs-text-primary) !important;
    -webkit-text-fill-color: var(--fs-text-primary) !important;
    opacity: 1 !important;
    font-weight: 800 !important;
}

.player-sub2,
.player-row-team {
    color: var(--fs-text-secondary) !important;
    -webkit-text-fill-color: var(--fs-text-secondary) !important;
    opacity: .82 !important;
}

.player-table-header2,
.player-row-header,
.player-panel-title {
    color: var(--fs-header) !important;
    -webkit-text-fill-color: var(--fs-header) !important;
    opacity: .84 !important;
}

.stat2,
.rank2,
.player-row-stat,
.player-row-rank {
    color: var(--fs-text-secondary) !important;
    -webkit-text-fill-color: var(--fs-text-secondary) !important;
    opacity: 1 !important;
}

/* Player rows remain distinguishable without sacrificing contrast. */
.st-key-war_player_list {
    background: var(--fs-panel) !important;
    border-color: var(--fs-border) !important;
}

.st-key-war_player_list [data-testid="stHorizontalBlock"] {
    color: var(--fs-text-primary) !important;
}

.player-row-divider,
.player-header-divider {
    background: rgba(203, 213, 225, .20) !important;
}

/* High-contrast draft + button across Safari and other browsers. */
.st-key-war_player_list button,
.st-key-available_player_rows button {
    background: var(--fs-panel-deep) !important;
    border: 1px solid #52617A !important;
    color: #FFFFFF !important;
    -webkit-text-fill-color: #FFFFFF !important;
    opacity: 1 !important;
    font-weight: 900 !important;
    text-shadow: none !important;
    box-shadow: none !important;
    -webkit-appearance: none !important;
    appearance: none !important;
}

.st-key-war_player_list button p,
.st-key-war_player_list button span,
.st-key-available_player_rows button p,
.st-key-available_player_rows button span {
    color: #FFFFFF !important;
    -webkit-text-fill-color: #FFFFFF !important;
    opacity: 1 !important;
}

.st-key-war_player_list button:hover,
.st-key-available_player_rows button:hover {
    background: var(--fs-draft-green) !important;
    border-color: var(--fs-draft-green) !important;
    color: #FFFFFF !important;
    -webkit-text-fill-color: #FFFFFF !important;
}

.st-key-war_player_list button:active,
.st-key-available_player_rows button:active {
    background: var(--fs-draft-green-active) !important;
    border-color: var(--fs-draft-green-active) !important;
    color: #FFFFFF !important;
    -webkit-text-fill-color: #FFFFFF !important;
    transform: scale(.92) !important;
}

.st-key-war_player_list button:focus-visible,
.st-key-available_player_rows button:focus-visible {
    outline: 2px solid var(--fs-blue) !important;
    outline-offset: 2px !important;
}

.st-key-war_player_list button:disabled,
.st-key-available_player_rows button:disabled {
    background: #202A3A !important;
    border-color: #3C485C !important;
    color: #E2E8F0 !important;
    -webkit-text-fill-color: #E2E8F0 !important;
    opacity: .62 !important;
}

/* Draft-board tile text. */
.snake-player {
    color: #FFFFFF !important;
    -webkit-text-fill-color: #FFFFFF !important;
    opacity: 1 !important;
    font-weight: 800 !important;
}

.snake-pick,
.tile-nfl,
.tile-owner,
.slot-num {
    color: var(--fs-text-secondary) !important;
    -webkit-text-fill-color: var(--fs-text-secondary) !important;
    opacity: .88 !important;
}

.team-label {
    color: var(--fs-text-primary) !important;
    -webkit-text-fill-color: var(--fs-text-primary) !important;
    opacity: 1 !important;
}

/* Waiting cards remain readable. */
.empty-pick .snake-player {
    color: #F1F5F9 !important;
    -webkit-text-fill-color: #F1F5F9 !important;
}

.empty-pick .tile-owner {
    color: #AEBBCB !important;
    -webkit-text-fill-color: #AEBBCB !important;
}

/* Roster panel. */
.roster-header-label {
    color: var(--fs-blue) !important;
    -webkit-text-fill-color: var(--fs-blue) !important;
}

.roster-line-player {
    color: var(--fs-text-primary) !important;
    -webkit-text-fill-color: var(--fs-text-primary) !important;
    opacity: 1 !important;
}

.roster-inline-pos,
.roster-empty {
    color: var(--fs-text-muted) !important;
    -webkit-text-fill-color: var(--fs-text-muted) !important;
    opacity: 1 !important;
}

/* Search field visibility. */
[data-testid="stTextInput"] input {
    color: var(--fs-text-primary) !important;
    -webkit-text-fill-color: var(--fs-text-primary) !important;
    caret-color: #FFFFFF !important;
    background: var(--fs-panel-deep) !important;
}

[data-testid="stTextInput"] input::placeholder {
    color: var(--fs-text-muted) !important;
    -webkit-text-fill-color: var(--fs-text-muted) !important;
    opacity: 1 !important;
}

/* Position filter and navigation buttons. */
.st-key-player_filter_rail button,
section[data-testid="stSidebar"] button {
    color: var(--fs-text-primary) !important;
    -webkit-text-fill-color: var(--fs-text-primary) !important;
}

.st-key-player_filter_rail button p,
section[data-testid="stSidebar"] button p {
    color: var(--fs-text-primary) !important;
    -webkit-text-fill-color: var(--fs-text-primary) !important;
}

/* Keep active action buttons clearly visible. */
button[kind="primary"] {
    color: #FFFFFF !important;
    -webkit-text-fill-color: #FFFFFF !important;
}

button[kind="primary"] p,
button[kind="primary"] span {
    color: #FFFFFF !important;
    -webkit-text-fill-color: #FFFFFF !important;
}


/* ============================================================
   v5.0 Player Queue and Live Value
   ============================================================ */

.st-key-queue_panel {
    height: 100% !important;
    overflow-y: auto !important;
    border-left: 1px solid rgba(150,170,210,.22) !important;
    padding: 0 6px 0 10px !important;
}

.st-key-queue_panel [data-testid="stVerticalBlock"] {
    gap: 5px !important;
}

.queue-title-row {
    display: flex;
    align-items: center;
    gap: 7px;
    min-height: 28px;
    border-bottom: 1px solid rgba(150,170,210,.18);
    margin-bottom: 4px;
}

.queue-title {
    color: #F8FAFC !important;
    -webkit-text-fill-color: #F8FAFC !important;
    font-size: .70rem;
    font-weight: 900;
    letter-spacing: .04em;
}

.queue-count {
    min-width: 20px;
    height: 19px;
    padding: 0 6px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border-radius: 999px;
    background: #2563EB;
    color: #FFFFFF;
    font-size: .58rem;
    font-weight: 900;
}

.queue-empty {
    color: #94A3B8 !important;
    -webkit-text-fill-color: #94A3B8 !important;
    font-size: .62rem;
    text-align: center;
    border: 1px dashed rgba(150,170,210,.22);
    border-radius: 8px;
    padding: 12px 6px;
    margin-bottom: 4px;
}

.queue-rank {
    width: 27px;
    height: 28px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 6px;
    background: #2563EB;
    color: #FFFFFF;
    font-size: .64rem;
    font-weight: 900;
}

.queue-player {
    color: #F8FAFC !important;
    -webkit-text-fill-color: #F8FAFC !important;
    font-size: .66rem;
    font-weight: 800;
    line-height: 1.05;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.queue-player-sub {
    color: #94A3B8 !important;
    -webkit-text-fill-color: #94A3B8 !important;
    font-size: .52rem;
    line-height: 1.05;
    margin-top: 2px;
}

.st-key-queue_panel button {
    min-height: 27px !important;
    height: 27px !important;
    padding: 0 4px !important;
    font-size: .60rem !important;
    color: #FFFFFF !important;
    -webkit-text-fill-color: #FFFFFF !important;
}

.st-key-queue_panel button p,
.st-key-queue_panel button span {
    color: #FFFFFF !important;
    -webkit-text-fill-color: #FFFFFF !important;
}

.st-key-queue_panel [data-testid="stToggle"] label p {
    color: #CBD5E1 !important;
    -webkit-text-fill-color: #CBD5E1 !important;
    font-size: .56rem !important;
}

.value-badge {
    min-width: 29px;
    height: 23px;
    padding: 0 4px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border-radius: 5px;
    color: #FFFFFF !important;
    -webkit-text-fill-color: #FFFFFF !important;
    font-size: .57rem;
    font-weight: 900;
}

.value-steal {
    background: #166534;
    border: 1px solid #22C55E;
}

.value-fair {
    background: #334155;
    border: 1px solid #64748B;
}

.value-reach {
    background: #7F1D1D;
    border: 1px solid #EF4444;
}


/* ============================================================
   FantasySync v5.3 — Layout Fix
   Board/roster align at the same top edge with no dead space.
   ============================================================ */

:root {
    --v53-bg: #07111D;
    --v53-panel: #0D1827;
    --v53-panel-2: #111E30;
    --v53-border: rgba(148, 163, 184, .18);
    --v53-border-strong: rgba(148, 163, 184, .28);
    --v53-text: #F8FAFC;
    --v53-muted: #8492A7;
    --v53-subtle: #B9C4D3;
    --v53-blue: #3B82F6;
    --v53-green: #22C55E;
    --v53-coral: #F15B52;
}

[data-testid="stAppViewContainer"] {
    background:
        radial-gradient(circle at 38% -25%, rgba(37,99,235,.12), transparent 35%),
        linear-gradient(180deg, #06101C, #081522) !important;
}

[data-testid="stHeader"] {
    background: transparent !important;
}

.main .block-container {
    max-width: none !important;
    padding: .65rem .85rem 1.5rem !important;
}

/* Old v5 header is removed from the visual flow. */
.app-header-copy,
.st-key-compact_header_actions {
    display: none !important;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    width: 13.7rem !important;
    min-width: 13.7rem !important;
    background: linear-gradient(180deg, #07111E, #091522) !important;
    border-right: 1px solid var(--v53-border) !important;
}

section[data-testid="stSidebar"] > div {
    padding: .65rem .65rem .9rem !important;
}

.sidebar-brand {
    min-height: 48px !important;
    padding: 5px 6px 12px !important;
    margin-bottom: 8px !important;
    border-bottom-color: var(--v53-border) !important;
}

.sidebar-brand-name {
    font-size: 1rem !important;
}

.sidebar-brand-icon {
    font-size: 1.25rem !important;
}

.sidebar-section-label {
    color: #64758D !important;
    font-size: .52rem !important;
    margin: 8px 7px 5px !important;
}

section[data-testid="stSidebar"] [data-testid="stRadio"] label {
    min-height: 38px !important;
    padding: 7px 9px !important;
    border-radius: 7px !important;
}

section[data-testid="stSidebar"] [data-testid="stRadio"] label p {
    font-size: .70rem !important;
    font-weight: 700 !important;
}

section[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {
    background: linear-gradient(90deg, #173E76, #12325D) !important;
    border-color: rgba(96,165,250,.30) !important;
    box-shadow: inset 3px 0 0 #60A5FA !important;
}

.sidebar-league-card {
    border-radius: 8px !important;
    background: rgba(255,255,255,.018) !important;
    border-color: var(--v53-border) !important;
}

/* Header */
.st-key-v53_header {
    padding: 1px 2px 10px !important;
    border-bottom: 1px solid var(--v53-border);
    margin-bottom: 9px !important;
}

.st-key-v53_header [data-testid="stHorizontalBlock"] {
    align-items: center !important;
    gap: .7rem !important;
}

.v53-title {
    color: var(--v53-text);
    font-size: 1.35rem;
    font-weight: 860;
    letter-spacing: -.025em;
    line-height: 1;
}

.v53-meta {
    display: flex;
    gap: 8px;
    margin-top: 11px;
}

.v53-chip {
    display: inline-flex;
    align-items: center;
    min-height: 27px;
    padding: 0 10px;
    border-radius: 6px;
    border: 1px solid var(--v53-border);
    background: rgba(255,255,255,.018);
    color: var(--v53-subtle);
    font-size: .60rem;
    font-weight: 750;
}

.v53-cpu {
    display: inline-flex;
    align-items: center;
    padding: 7px 11px;
    border: 1px solid rgba(34,197,94,.31);
    border-radius: 999px;
    color: #74E596;
    background: rgba(34,197,94,.08);
    font-size: .59rem;
    font-weight: 850;
    white-space: nowrap;
}

.v53-clock {
    width: 65px;
    height: 65px;
    margin: auto;
    border: 2px solid #397FF0;
    border-radius: 50%;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
}

.v53-clock-time {
    color: var(--v53-text);
    font-size: 1.03rem;
    font-weight: 900;
    line-height: 1;
}

.v53-clock-label {
    color: #70A6FF;
    font-size: .42rem;
    font-weight: 850;
    margin-top: 4px;
}

.st-key-v53_header_action button {
    min-height: 37px !important;
    height: 37px !important;
    border-radius: 7px !important;
    background: var(--v53-coral) !important;
    border-color: transparent !important;
    color: #FFFFFF !important;
    -webkit-text-fill-color: #FFFFFF !important;
    font-size: .67rem !important;
    font-weight: 820 !important;
}

/* Top workspace — this is the key v5.3 fix. */
.st-key-v53_top_workspace [data-testid="stHorizontalBlock"] {
    align-items: flex-start !important;
    gap: .72rem !important;
}

.st-key-v53_board_panel,
.st-key-v53_roster_panel {
    height: 430px !important;
    max-height: 430px !important;
    overflow-y: auto !important;
    overflow-x: hidden !important;
    margin: 0 !important;
}

.st-key-v53_board_panel {
    padding: 0 4px 0 0 !important;
    border: 0 !important;
    background: transparent !important;
}

/* Ensure Streamlit does not vertically center content in bounded containers. */
.st-key-v53_board_panel > div,
.st-key-v53_board_panel [data-testid="stVerticalBlock"],
.st-key-v53_roster_panel > div,
.st-key-v53_roster_panel [data-testid="stVerticalBlock"] {
    justify-content: flex-start !important;
    align-content: flex-start !important;
    gap: 0 !important;
}

.st-key-v53_roster_panel {
    background: linear-gradient(180deg, #111E30, #0C1726) !important;
    border: 1px solid var(--v53-border) !important;
    border-radius: 8px !important;
    padding: 8px 10px !important;
}

/* Draft board */
.snake-team-select {
    min-height: 43px !important;
    border-radius: 6px !important;
    background: #0D1827 !important;
    border-color: var(--v53-border) !important;
}

.snake-team-select.active {
    background: linear-gradient(180deg, #245E66, #1B4C55) !important;
    border-color: #5ED6C5 !important;
}

.snake-team-select .slot-num {
    font-size: .50rem !important;
}

.snake-team-select .team-label {
    font-size: .55rem !important;
}

.snake-cell {
    min-height: 59px !important;
    padding: 5px 6px !important;
    border-radius: 6px !important;
    border-color: rgba(148,163,184,.17) !important;
}

.snake-cell.empty-pick {
    background: #0B1523 !important;
}

.snake-cell.pos-qb {
    background: linear-gradient(145deg, #245A8D, #193D66) !important;
}

.snake-cell.pos-rb {
    background: linear-gradient(145deg, #17764A, #105238) !important;
}

.snake-cell.pos-wr {
    background: linear-gradient(145deg, #246BC8, #194781) !important;
}

.snake-cell.pos-te {
    background: linear-gradient(145deg, #A96716, #73430F) !important;
}

.snake-cell.current-pick {
    border-color: #4B91FF !important;
    box-shadow: 0 0 0 1px #4B91FF !important;
    animation: none !important;
}

.snake-pick {
    font-size: .49rem !important;
}

.snake-player {
    font-size: .62rem !important;
}

.player-tile-badge {
    font-size: .47rem !important;
    padding: 1px 5px !important;
}

.tile-nfl,
.tile-owner {
    font-size: .46rem !important;
}

/* Roster */
.roster-header-row {
    grid-template-columns: minmax(0,1fr) auto !important;
    min-height: 43px !important;
    height: auto !important;
    padding: 0 0 7px !important;
    margin: 0 0 5px !important;
    border-bottom: 1px solid var(--v53-border) !important;
}

.roster-header-label {
    display: none !important;
}

.roster-header-team {
    font-size: .83rem !important;
    color: var(--v53-text) !important;
}

.roster-header-count {
    font-size: .54rem !important;
}

.roster-line {
    min-height: 33px !important;
    grid-template-columns: 34px minmax(0,1fr) !important;
    gap: 7px !important;
    padding: 2px 0 !important;
    border-bottom-color: rgba(148,163,184,.09) !important;
}

.roster-slot-pill {
    width: 31px !important;
    height: 23px !important;
    border-radius: 5px !important;
    font-size: .50rem !important;
}

.roster-line-player {
    font-size: .60rem !important;
}

.roster-inline-pos {
    font-size: .47rem !important;
}

.roster-empty {
    font-size: .56rem !important;
}

/* Bottom workspace begins immediately after the board. */
.st-key-v53_bottom_workspace {
    margin-top: 8px !important;
    padding-top: 7px !important;
    border-top: 1px solid var(--v53-border);
}

.st-key-v53_bottom_workspace [data-testid="stHorizontalBlock"] {
    align-items: flex-start !important;
    gap: .72rem !important;
}

/* Old fixed dock becomes a normal lower workspace. */
.st-key-draft_drawer {
    position: static !important;
    left: auto !important;
    right: auto !important;
    bottom: auto !important;
    width: auto !important;
    height: auto !important;
    min-height: 0 !important;
    overflow: visible !important;
    background: transparent !important;
    border: 0 !important;
    box-shadow: none !important;
    padding: 0 !important;
    backdrop-filter: none !important;
}

.st-key-dock_controls,
.fixed-dock-spacer {
    display: none !important;
}

.v53-player-tabs {
    display: flex;
    gap: 22px;
    min-height: 33px;
    align-items: center;
    border-bottom: 1px solid var(--v53-border);
    margin-bottom: 8px;
}

.v53-player-tab {
    color: var(--v53-muted);
    font-size: .62rem;
    font-weight: 820;
    padding: 0 2px 9px;
}

.v53-player-tab.active {
    color: #68A4FF;
    border-bottom: 2px solid #4F8FF5;
}

.st-key-v53_filter_row [data-testid="stHorizontalBlock"] {
    align-items: center !important;
    gap: .45rem !important;
}

.st-key-v53_filter_row [data-testid="stTextInputRootElement"] {
    min-height: 35px !important;
    border-radius: 7px !important;
    background: #0A1523 !important;
    border-color: var(--v53-border) !important;
}

.st-key-v53_filter_row button {
    min-height: 34px !important;
    height: 34px !important;
    padding: 0 10px !important;
    border-radius: 999px !important;
    background: #101B2B !important;
    border-color: var(--v53-border) !important;
    font-size: .60rem !important;
}

.st-key-v53_filter_row button[kind="primary"] {
    background: #326ED5 !important;
    border-color: #4C87EF !important;
}

.st-key-war_player_list {
    height: 280px !important;
    max-height: 280px !important;
    overflow-y: auto !important;
    background: transparent !important;
}

.player-table-header2 {
    color: #7E8CA1 !important;
    -webkit-text-fill-color: #7E8CA1 !important;
    font-size: .50rem !important;
}

.st-key-war_player_list [data-testid="stHorizontalBlock"] {
    min-height: 39px !important;
    padding: 1px 0 2px !important;
}

.player-name2 {
    font-size: .62rem !important;
}

.player-sub2 {
    font-size: .48rem !important;
}

.stat2,
.rank2 {
    font-size: .54rem !important;
}

.player-row-divider {
    background: rgba(148,163,184,.10) !important;
    margin: 1px 0 !important;
}

.st-key-war_player_list button {
    width: 24px !important;
    min-width: 24px !important;
    height: 24px !important;
    min-height: 24px !important;
}

.value-badge {
    height: 20px !important;
    min-width: 26px !important;
    font-size: .48rem !important;
}

/* Recommendation panel */
.st-key-v53_recommendation_panel {
    min-height: 354px !important;
    background: linear-gradient(180deg, #111E30, #0C1726) !important;
    border: 1px solid var(--v53-border) !important;
    border-radius: 8px !important;
    padding: 10px 11px !important;
}

.v53-rec-eyebrow {
    color: #61A0FF;
    font-size: .57rem;
    font-weight: 900;
    margin-bottom: 12px;
}

.v53-rec-person {
    display: flex;
    align-items: center;
    gap: 11px;
}

.v53-avatar {
    width: 49px;
    height: 49px;
    border-radius: 50%;
    background: linear-gradient(145deg, #24364D, #101A29);
    border: 1px solid var(--v53-border-strong);
    display: flex;
    align-items: center;
    justify-content: center;
    color: #DDE6F3;
    font-size: .76rem;
    font-weight: 900;
}

.v53-rec-name {
    color: var(--v53-text);
    font-size: .91rem;
    font-weight: 860;
}

.v53-rec-meta {
    color: var(--v53-muted);
    font-size: .54rem;
    margin-top: 3px;
}

.v53-confidence {
    width: 62px;
    height: 62px;
    margin-left: auto;
    border-radius: 50%;
    border: 5px solid #31C873;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
}

.v53-confidence-number {
    color: var(--v53-text);
    font-size: .96rem;
    font-weight: 900;
}

.v53-confidence-label {
    color: var(--v53-muted);
    font-size: .38rem;
}

.v53-rec-divider {
    height: 1px;
    background: var(--v53-border);
    margin: 13px 0 10px;
}

.v53-rec-copy-title {
    color: var(--v53-subtle);
    font-size: .57rem;
    margin-bottom: 7px;
}

.v53-rec-reason {
    color: #D0D9E6;
    font-size: .54rem;
    line-height: 1.5;
    margin: 5px 0;
}

.v53-check {
    color: #3DD77B;
    margin-right: 6px;
}

.st-key-v53_rec_button button {
    min-height: 38px !important;
    margin-top: 10px !important;
    border-radius: 5px !important;
    background: #15953E !important;
    border-color: #26B952 !important;
    font-size: .66rem !important;
    font-weight: 850 !important;
}

/* Queue remains accessible without taking permanent width. */
.st-key-v53_queue_expander {
    margin-top: 5px !important;
}

.st-key-v53_queue_expander [data-testid="stExpander"] {
    background: #0B1625 !important;
    border-color: var(--v53-border) !important;
}

@media (max-width: 1100px) {
    section[data-testid="stSidebar"] {
        width: 12rem !important;
        min-width: 12rem !important;
    }
}


/* ============================================================
   FantasySync v5.4 — Team and Round Label Emphasis
   ============================================================ */

.snake-team-select .team-label {
    color: #7DD3FC !important;
    -webkit-text-fill-color: #7DD3FC !important;
    font-size: .64rem !important;
    font-weight: 850 !important;
    letter-spacing: .005em !important;
    line-height: 1.12 !important;
}

.snake-team-select .slot-num {
    color: #94A3B8 !important;
    -webkit-text-fill-color: #94A3B8 !important;
    font-size: .52rem !important;
    font-weight: 750 !important;
}

.snake-team-select.active .team-label {
    color: #FFFFFF !important;
    -webkit-text-fill-color: #FFFFFF !important;
}

.snake-round-label {
    min-height: 59px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    color: #7DD3FC !important;
    -webkit-text-fill-color: #7DD3FC !important;
    background: #0D1B2B !important;
    border-color: rgba(125, 211, 252, .28) !important;
    font-size: .64rem !important;
    font-weight: 850 !important;
    letter-spacing: .02em !important;
}


/* ============================================================
   FantasySync v5.5 — Matte Controls, Tray, Timer, CPU Ticks
   ============================================================ */

/* Distinct matte purple team and round labels. */
.snake-team-select {
    background: #2A1F55 !important;
    border-color: #5F4AA8 !important;
    box-shadow: none !important;
}

.snake-team-select:hover {
    background: #342668 !important;
    border-color: #7B61D1 !important;
}

.snake-team-select .team-label {
    color: #FFFFFF !important;
    -webkit-text-fill-color: #FFFFFF !important;
    font-size: .64rem !important;
    font-weight: 850 !important;
}

.snake-team-select .slot-num {
    color: #C4B8F4 !important;
    -webkit-text-fill-color: #C4B8F4 !important;
}

.snake-team-select.active {
    background: #49348A !important;
    border-color: #A78BFA !important;
    box-shadow: inset 0 0 0 1px #A78BFA !important;
}

.snake-round-label {
    background: #2A1F55 !important;
    border-color: #6D55BD !important;
    color: #FFFFFF !important;
    -webkit-text-fill-color: #FFFFFF !important;
    box-shadow: none !important;
}

/* Raise the clock so the header divider cannot intersect it. */
.v53-clock {
    transform: translateY(-7px) !important;
    background: #0A1524 !important;
}

.st-key-v53_header {
    padding-top: 8px !important;
}

/* Matte top controls and metadata chips. */
.v53-chip {
    background: #111D2E !important;
    border-color: #2A3A51 !important;
    box-shadow: none !important;
}

.v53-cpu {
    background: #0D2A20 !important;
    border-color: #1D6A48 !important;
    box-shadow: none !important;
}

.st-key-v53_header_action button {
    background: #E55B52 !important;
    border-color: #E55B52 !important;
    box-shadow: none !important;
}

.st-key-v53_header_action button:hover {
    background: #F06A61 !important;
    border-color: #F06A61 !important;
}

/* Matte player filters. */
.st-key-v53_filter_row button {
    background: #111D2E !important;
    border-color: #2A3A51 !important;
    box-shadow: none !important;
}

.st-key-v53_filter_row button:hover {
    background: #18263A !important;
    border-color: #3C526F !important;
}

.st-key-v53_filter_row button[kind="primary"] {
    background: #316CD4 !important;
    border-color: #316CD4 !important;
}

/* Matte draft and queue actions. */
.st-key-war_player_list button {
    background: #111D2E !important;
    border-color: #34455D !important;
    box-shadow: none !important;
}

.st-key-war_player_list button:hover {
    background: #188A49 !important;
    border-color: #188A49 !important;
}

.st-key-v53_rec_button button {
    background: #1D9648 !important;
    border-color: #1D9648 !important;
    box-shadow: none !important;
}

/* True draggable player-tray handle. */
.st-key-v55_tray_handle {
    display: none !important;
}

.st-key-v56_drag_handle {
    position: relative;
    z-index: 20;
    height: 34px !important;
    margin: -1px 0 0 0 !important;
    padding: 0 !important;
    border-top: 2px solid #7C5CE0;
    overflow: visible !important;
}

.st-key-v56_drag_handle [data-testid="stVerticalBlock"] {
    gap: 0 !important;
}

.v56-drag-grip {
    position: absolute;
    left: 50%;
    top: -15px;
    transform: translateX(-50%);
    min-width: 174px;
    height: 31px;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    padding: 0 14px;
    border: 1px solid #566681;
    border-radius: 9px;
    background: #202A3B;
    color: #E3EAF4;
    cursor: ns-resize;
    user-select: none;
    touch-action: none;
    box-shadow: none;
    transition:
        background-color .10s ease,
        border-color .10s ease;
}

.v56-drag-grip:hover,
.v56-drag-grip.dragging {
    background: #29364B;
    border-color: #8B72E8;
}

.v56-grip-lines {
    color: #A993FF;
    font-size: .88rem;
    font-weight: 900;
    line-height: 1;
    transform: rotate(90deg);
}

.v56-drag-label {
    color: #E3EAF4;
    font-size: .53rem;
    font-weight: 850;
    letter-spacing: .035em;
    white-space: nowrap;
}

/* Keep player workspace tight against the tray handle. */
.st-key-v53_bottom_workspace {
    margin-top: 0 !important;
    padding-top: 3px !important;
}


/* ============================================================
   FantasySync v5.7 — True Draggable Player Workspace
   ============================================================ */

.st-key-v53_top_workspace {
    height: 430px !important;
    max-height: 430px !important;
    min-height: 0 !important;
    overflow: hidden !important;
}

.st-key-v53_top_workspace > div,
.st-key-v53_top_workspace > div > div,
.st-key-v53_top_workspace [data-testid="stHorizontalBlock"] {
    height: 100% !important;
    max-height: 100% !important;
    min-height: 0 !important;
}

.st-key-v53_board_panel,
.st-key-v53_roster_panel {
    height: 100% !important;
    max-height: 100% !important;
    min-height: 0 !important;
}

.st-key-v56_drag_handle {
    margin-top: 0 !important;
}

.st-key-v53_bottom_workspace {
    margin-top: 0 !important;
}


/* ============================================================
   FantasySync v5.8 — Remove Remaining Tray Gap
   ============================================================ */

.st-key-v53_top_workspace,
.st-key-v53_top_workspace > div,
.st-key-v53_top_workspace > div > div,
.st-key-v53_top_workspace [data-testid="stHorizontalBlock"],
.st-key-v53_top_workspace [data-testid="stColumn"] {
    min-height: 0 !important;
    overflow: hidden !important;
}

.st-key-v53_board_panel,
.st-key-v53_roster_panel {
    min-height: 0 !important;
    overflow-y: auto !important;
}

.st-key-v56_drag_handle {
    margin-top: 0 !important;
}

.st-key-v53_bottom_workspace {
    margin-top: 0 !important;
}


/* ============================================================
   FantasySync v5.9 — Approved Final Layout
   ============================================================ */

/* Clean top header: no rule through chips, timer, or title. */
.st-key-v53_header {
    padding: 5px 2px 15px !important;
    margin-bottom: 9px !important;
    border-bottom: 0 !important;
    position: relative;
}

.st-key-v53_header::after {
    content: "";
    position: absolute;
    left: 0;
    right: 0;
    bottom: 0;
    height: 1px;
    background: rgba(148, 163, 184, .16);
}

.v53-title,
.v53-meta,
.v53-cpu,
.v53-clock,
.st-key-v53_header_action {
    position: relative;
    z-index: 2;
}

.v53-clock {
    transform: translateY(-9px) !important;
}

/* Slightly larger board to match the approved render. */
.st-key-v53_top_workspace {
    height: 470px !important;
    max-height: 470px !important;
    min-height: 470px !important;
    overflow: hidden !important;
    margin: 0 !important;
    padding: 0 !important;
}

.st-key-v53_top_workspace > div,
.st-key-v53_top_workspace > div > div,
.st-key-v53_top_workspace
    > div
    > div
    > [data-testid="stHorizontalBlock"] {
    height: 100% !important;
    max-height: 100% !important;
    min-height: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
}

.st-key-v53_top_workspace
    > div
    > div
    > [data-testid="stHorizontalBlock"]
    > [data-testid="stColumn"] {
    height: 100% !important;
    max-height: 100% !important;
    min-height: 0 !important;
    overflow: hidden !important;
}

.st-key-v53_board_panel,
.st-key-v53_roster_panel {
    height: 100% !important;
    max-height: 100% !important;
    min-height: 0 !important;
    margin: 0 !important;
    overflow-y: auto !important;
    overflow-x: hidden !important;
}

.st-key-v53_board_panel > div,
.st-key-v53_roster_panel > div {
    margin: 0 !important;
    padding-top: 0 !important;
}

/* Remove every possible gap around the handle and lower workspace. */
.st-key-v56_drag_handle {
    height: 32px !important;
    min-height: 32px !important;
    margin: 0 !important;
    padding: 0 !important;
    border-top: 2px solid #7C5CE0;
}

.v56-drag-grip {
    top: -15px !important;
}

.st-key-v53_bottom_workspace {
    margin: 0 !important;
    padding: 3px 0 0 !important;
    border-top: 0 !important;
}

/* Slightly larger board tiles while preserving all colors. */
.snake-team-select {
    min-height: 46px !important;
}

.snake-team-select .team-label {
    font-size: .66rem !important;
}

.snake-cell {
    min-height: 66px !important;
    padding: 5px 7px !important;
}

.snake-round-label {
    min-height: 66px !important;
    font-size: .66rem !important;
}

.snake-player {
    font-size: .64rem !important;
    line-height: 1.12 !important;
}

.snake-pick {
    font-size: .49rem !important;
}

/* Compact roster rows to align with the larger five-round board. */
.roster-line {
    min-height: 31px !important;
    padding: 1px 0 !important;
}

.roster-slot-pill {
    height: 22px !important;
}

.roster-line-player {
    font-size: .59rem !important;
}

/* Denser player list matching the approved mockup. */
.st-key-war_player_list {
    height: 290px !important;
    max-height: 290px !important;
}

.st-key-war_player_list [data-testid="stHorizontalBlock"] {
    min-height: 31px !important;
    height: 31px !important;
    padding: 0 !important;
    align-items: center !important;
}

.player-row-divider {
    margin: 0 !important;
    background: rgba(148, 163, 184, .09) !important;
}

.player-name2 {
    font-size: .59rem !important;
    line-height: 1.05 !important;
}

.player-sub2 {
    font-size: .45rem !important;
    line-height: 1 !important;
    margin-top: 1px !important;
}

.stat2,
.rank2 {
    font-size: .51rem !important;
}

.st-key-war_player_list button {
    width: 22px !important;
    min-width: 22px !important;
    height: 22px !important;
    min-height: 22px !important;
    padding: 0 !important;
}

.value-badge {
    height: 18px !important;
    min-width: 24px !important;
    font-size: .45rem !important;
}

/* Compact the player-browser heading and controls. */
.v53-player-tabs {
    min-height: 29px !important;
    margin-bottom: 6px !important;
}

.v53-player-tab {
    padding-bottom: 7px !important;
    font-size: .59rem !important;
}

.st-key-v53_filter_row [data-testid="stTextInputRootElement"] {
    min-height: 31px !important;
}

.st-key-v53_filter_row button {
    min-height: 30px !important;
    height: 30px !important;
    font-size: .57rem !important;
}

/* Recommendation panel follows the compact lower workspace. */
.st-key-v53_recommendation_panel {
    min-height: 290px !important;
    padding: 9px 10px !important;
}


/* ============================================================
   FantasySync v6.0 — Sidebar Reflow, CPU Continuity, Tight Tray
   ============================================================ */

section[data-testid="stSidebar"][aria-expanded="false"] {
    width: 0 !important;
    min-width: 0 !important;
    max-width: 0 !important;
    border-right: 0 !important;
    overflow: hidden !important;
}

body:has(section[data-testid="stSidebar"][aria-expanded="false"])
    [data-testid="stAppViewContainer"] > .main {
    width: 100vw !important;
    max-width: 100vw !important;
}

body:has(section[data-testid="stSidebar"][aria-expanded="false"])
    .main .block-container {
    width: calc(100vw - 1.7rem) !important;
    max-width: none !important;
    margin-left: 0 !important;
    margin-right: 0 !important;
}

body:has(section[data-testid="stSidebar"][aria-expanded="false"])
    .st-key-v53_top_workspace,
body:has(section[data-testid="stSidebar"][aria-expanded="false"])
    .st-key-v53_bottom_workspace,
body:has(section[data-testid="stSidebar"][aria-expanded="false"])
    .st-key-v53_header {
    width: 100% !important;
    max-width: none !important;
}

.st-key-v53_board_panel,
.st-key-v53_board_panel > div,
.st-key-v53_board_panel [data-testid="stMarkdownContainer"] {
    width: 100% !important;
    max-width: none !important;
}

.st-key-v56_drag_handle {
    height: 24px !important;
    min-height: 24px !important;
    max-height: 24px !important;
    margin: 0 !important;
    padding: 0 !important;
}

.st-key-v56_drag_handle [data-testid="stVerticalBlock"],
.st-key-v56_drag_handle [data-testid="stMarkdownContainer"],
.st-key-v56_drag_handle p {
    margin: 0 !important;
    padding: 0 !important;
    min-height: 0 !important;
}

.v56-drag-grip {
    top: -17px !important;
}

.st-key-v53_bottom_workspace {
    margin-top: -2px !important;
    padding-top: 0 !important;
}

.v53-player-tabs {
    margin-top: 0 !important;
    padding-top: 0 !important;
}


/* ============================================================
   FantasySync v6.1 — Compact Status and Player Toolbar
   ============================================================ */

/* Reduce the space between metadata chips, status message, and board. */
.st-key-v53_header {
    padding-bottom: 9px !important;
    margin-bottom: 2px !important;
}

.st-key-v61_draft_message {
    min-height: 22px !important;
    margin: 0 0 3px !important;
    padding: 0 !important;
}

.st-key-v61_draft_message [data-testid="stCaptionContainer"],
.st-key-v61_draft_message [data-testid="stMarkdownContainer"],
.st-key-v61_draft_message p {
    margin: 0 !important;
    padding: 0 !important;
    min-height: 0 !important;
    line-height: 1.2 !important;
}

.st-key-v61_draft_message p {
    font-size: .67rem !important;
    color: #93A0B3 !important;
    -webkit-text-fill-color: #93A0B3 !important;
}

.st-key-v53_top_workspace {
    margin-top: 0 !important;
}

/* One-line Players / Search / Position toolbar. */
.st-key-v61_player_toolbar {
    margin: 0 !important;
    padding: 0 0 5px !important;
    border-bottom: 1px solid rgba(148, 163, 184, .17);
}

.st-key-v61_player_toolbar > div,
.st-key-v61_player_toolbar [data-testid="stVerticalBlock"] {
    gap: 0 !important;
}

.st-key-v61_player_toolbar [data-testid="stHorizontalBlock"] {
    align-items: center !important;
    gap: .45rem !important;
    min-height: 35px !important;
}

.v61-inline-tabs {
    height: 34px;
    display: flex;
    align-items: center;
    gap: 18px;
    white-space: nowrap;
}

.v61-inline-tab {
    height: 34px;
    display: inline-flex;
    align-items: center;
    color: #8D9AAF;
    font-size: .58rem;
    font-weight: 850;
    letter-spacing: .02em;
    border-bottom: 2px solid transparent;
}

.v61-inline-tab.active {
    color: #6CA8FF;
    border-bottom-color: #4F8FF5;
}

.st-key-v61_player_toolbar [data-testid="stTextInputRootElement"] {
    min-height: 32px !important;
    height: 32px !important;
    border-radius: 7px !important;
}

.st-key-v61_player_toolbar
    [data-testid="stTextInputRootElement"]
    input {
    min-height: 30px !important;
    height: 30px !important;
    padding-top: 0 !important;
    padding-bottom: 0 !important;
    font-size: .63rem !important;
}

.st-key-v61_player_toolbar button {
    min-height: 30px !important;
    height: 30px !important;
    border-radius: 999px !important;
    padding: 0 8px !important;
    font-size: .57rem !important;
}

/* The old tabs/filter wrappers are no longer used on the Draft Room. */
.v53-player-tabs,
.st-key-v53_filter_row {
    display: none !important;
}

/* Pull the player table directly beneath the compact toolbar. */
.player-table-header2 {
    margin-top: 2px !important;
}

.st-key-war_player_list {
    margin-top: 0 !important;
}


/* ============================================================
   FantasySync v6.1.4 — Hidden autorefresh + faster CPU
   Minimal patch based on stable v6.1.
   ============================================================ */

/*
 * The gray bar was the streamlit-autorefresh component's blank iframe and
 * wrapper—not Streamlit's status widget. Hide the dedicated mount completely.
 */
.st-key-cpu_autorefresh_mount,
.st-key-cpu_autorefresh_mount > div,
.st-key-cpu_autorefresh_mount [data-testid="stVerticalBlock"],
.st-key-cpu_autorefresh_mount [data-testid="stElementContainer"],
.st-key-cpu_autorefresh_mount [data-testid="stCustomComponentV1"],
.st-key-cpu_autorefresh_mount iframe {
    display: none !important;
    visibility: hidden !important;
    position: absolute !important;
    width: 0 !important;
    height: 0 !important;
    min-width: 0 !important;
    min-height: 0 !important;
    max-width: 0 !important;
    max-height: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
    border: 0 !important;
    overflow: hidden !important;
}

/* Defensive fallback if Streamlit changes the keyed wrapper hierarchy. */
iframe[title*="streamlit_autorefresh"],
iframe[src*="streamlit_autorefresh"] {
    display: none !important;
    width: 0 !important;
    height: 0 !important;
    border: 0 !important;
}

div[data-testid="stElementContainer"]:has(
    iframe[title*="streamlit_autorefresh"]
),
div[data-testid="stElementContainer"]:has(
    iframe[src*="streamlit_autorefresh"]
),
div[data-testid="stCustomComponentV1"]:has(
    iframe[title*="streamlit_autorefresh"]
),
div[data-testid="stCustomComponentV1"]:has(
    iframe[src*="streamlit_autorefresh"]
) {
    display: none !important;
    width: 0 !important;
    height: 0 !important;
    min-height: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
}

/* Keep ordinary Streamlit status UI compact and non-disruptive. */
[data-testid="stDecoration"] {
    display: none !important;
}


/* ============================================================
   FantasySync v6.1.5 — Restore full 16-round board scrolling
   Keeps the hidden-autorefresh fix from v6.1.4.
   ============================================================ */

/* The board panel is the fixed-height scroll viewport. */
.st-key-v53_board_panel {
    height: 100% !important;
    max-height: 100% !important;
    min-height: 0 !important;
    overflow-y: auto !important;
    overflow-x: hidden !important;
    overscroll-behavior: contain !important;
    scrollbar-gutter: stable !important;
    -webkit-overflow-scrolling: touch !important;
}

/*
 * Inner Streamlit wrappers must use natural height. Earlier rules and the
 * drag script set these to 100%, clipping the content to the visible rounds.
 */
.st-key-v53_board_panel > div,
.st-key-v53_board_panel > div > div,
.st-key-v53_board_panel [data-testid="stVerticalBlockBorderWrapper"],
.st-key-v53_board_panel [data-testid="stVerticalBlock"],
.st-key-v53_board_panel [data-testid="stMarkdownContainer"] {
    height: auto !important;
    max-height: none !important;
    min-height: 0 !important;
    overflow: visible !important;
}

/* Ensure the board grid contributes the height of rounds 1–16. */
.st-key-v53_board_panel .snake-board-wrap,
.st-key-v53_board_panel .snake-board-shell,
.st-key-v53_board_panel .snake-board-grid {
    height: auto !important;
    max-height: none !important;
    min-height: max-content !important;
    overflow: visible !important;
}

/* Subtle internal scrollbar. */
.st-key-v53_board_panel {
    scrollbar-width: thin;
    scrollbar-color: #42516A #091321;
}

.st-key-v53_board_panel::-webkit-scrollbar {
    width: 7px;
}

.st-key-v53_board_panel::-webkit-scrollbar-track {
    background: #091321;
}

.st-key-v53_board_panel::-webkit-scrollbar-thumb {
    background: #42516A;
    border-radius: 999px;
}

.st-key-v53_board_panel::-webkit-scrollbar-thumb:hover {
    background: #60728F;
}


/* ============================================================
   FantasySync v6.2 — Sleeper-style full-width draft room
   Keeps v6.1.5 hidden autorefresh and fast CPU behavior.
   ============================================================ */

/* Full-width board workspace. */
.st-key-v53_top_workspace {
    width: 100% !important;
    max-width: none !important;
    overflow: hidden !important;
    margin: 0 !important;
    padding: 0 !important;
}

.st-key-v53_board_panel {
    width: 100% !important;
    max-width: none !important;
    min-height: 0 !important;
    overflow-y: auto !important;
    overflow-x: hidden !important;
    overscroll-behavior: contain !important;
    scrollbar-gutter: stable !important;
    -webkit-overflow-scrolling: touch !important;
}

/*
 * The panel is the scroll viewport. Its internal wrappers must retain natural
 * height so all 16 rounds contribute to scrollHeight.
 */
.st-key-v53_board_panel > div,
.st-key-v53_board_panel > div > div,
.st-key-v53_board_panel [data-testid="stVerticalBlockBorderWrapper"],
.st-key-v53_board_panel [data-testid="stVerticalBlock"],
.st-key-v53_board_panel [data-testid="stMarkdownContainer"] {
    height: auto !important;
    max-height: none !important;
    min-height: 0 !important;
    overflow: visible !important;
}

.st-key-v53_board_panel .snake-board-wrap,
.st-key-v53_board_panel .snake-board-shell,
.st-key-v53_board_panel .snake-board-grid {
    height: auto !important;
    max-height: none !important;
    min-height: max-content !important;
    overflow: visible !important;
}

/* Subtle Sleeper-like board scrollbar. */
.st-key-v53_board_panel {
    scrollbar-width: thin;
    scrollbar-color: #465671 #091321;
}

.st-key-v53_board_panel::-webkit-scrollbar {
    width: 7px;
}

.st-key-v53_board_panel::-webkit-scrollbar-track {
    background: #091321;
}

.st-key-v53_board_panel::-webkit-scrollbar-thumb {
    background: #465671;
    border-radius: 999px;
}

.st-key-v53_board_panel::-webkit-scrollbar-thumb:hover {
    background: #657995;
}

/* Sleeper-style snap tray divider. */
.st-key-v62_tray_controls {
    height: 36px !important;
    min-height: 36px !important;
    margin: 0 !important;
    padding: 0 !important;
    border-top: 2px solid #7C5CE0;
}

.st-key-v62_tray_controls [data-testid="stHorizontalBlock"] {
    align-items: center !important;
    gap: .25rem !important;
}

.st-key-v62_tray_controls button {
    min-height: 27px !important;
    height: 27px !important;
    padding: 0 !important;
    border-radius: 8px !important;
    background: #1C2739 !important;
    border: 1px solid #4B5B74 !important;
    color: #FFFFFF !important;
    -webkit-text-fill-color: #FFFFFF !important;
    box-shadow: none !important;
}

.st-key-v62_tray_controls button:hover {
    background: #27354A !important;
    border-color: #846CE0 !important;
}

.st-key-v62_tray_controls button:disabled {
    opacity: .38 !important;
}

.v62-tray-label {
    min-height: 27px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 8px;
    background: #1C2739;
    border: 1px solid #4B5B74;
    color: #E4EAF3;
    font-size: .53rem;
    font-weight: 850;
    letter-spacing: .04em;
    white-space: nowrap;
}

/* Lower workspace fills the full width. */
.st-key-v53_bottom_workspace {
    width: 100% !important;
    max-width: none !important;
    margin: 0 !important;
    padding: 2px 0 0 !important;
    border-top: 0 !important;
}

.st-key-v53_bottom_workspace [data-testid="stHorizontalBlock"] {
    align-items: stretch !important;
    gap: .65rem !important;
}

/* Queue and roster replace recommendations. */
.st-key-v62_queue_panel,
.st-key-v62_roster_panel {
    height: 100% !important;
    min-height: 220px !important;
    padding: 9px 10px !important;
    border: 1px solid rgba(148, 163, 184, .18) !important;
    border-radius: 8px !important;
    background: linear-gradient(180deg, #111E30, #0C1726) !important;
    overflow-y: auto !important;
}

.v62-panel-header {
    min-height: 31px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    color: #F8FAFC;
    font-size: .60rem;
    font-weight: 850;
    border-bottom: 1px solid rgba(148, 163, 184, .17);
    margin-bottom: 7px;
}

/* Recommendation panel is no longer part of the Draft Room. */
.st-key-v53_recommendation_panel {
    display: none !important;
}

/* Make the expanded board use every available horizontal pixel. */
body:has(section[data-testid="stSidebar"][aria-expanded="false"])
    .main .block-container {
    width: calc(100vw - 1.4rem) !important;
    max-width: none !important;
    margin-left: 0 !important;
    margin-right: 0 !important;
}

/* Keep queue controls compact inside the narrower middle panel. */
.st-key-v62_queue_panel button {
    min-height: 27px !important;
    height: 27px !important;
    padding: 0 6px !important;
    font-size: .54rem !important;
}

.st-key-v62_queue_panel [data-testid="stHorizontalBlock"] {
    gap: .25rem !important;
}

/* Compact roster rows in the tray. */
.st-key-v62_roster_panel .roster-header-row {
    margin-bottom: 4px !important;
}

.st-key-v62_roster_panel .roster-line {
    min-height: 29px !important;
    padding: 1px 0 !important;
}

.st-key-v62_roster_panel .roster-slot-pill {
    height: 21px !important;
}

/* Preserve the v6.1.4 hidden autorefresh mount. */
.st-key-cpu_autorefresh_mount,
.st-key-cpu_autorefresh_mount > div,
.st-key-cpu_autorefresh_mount [data-testid="stVerticalBlock"],
.st-key-cpu_autorefresh_mount [data-testid="stElementContainer"],
.st-key-cpu_autorefresh_mount [data-testid="stCustomComponentV1"],
.st-key-cpu_autorefresh_mount iframe {
    display: none !important;
    visibility: hidden !important;
    position: absolute !important;
    width: 0 !important;
    height: 0 !important;
    min-width: 0 !important;
    min-height: 0 !important;
    max-width: 0 !important;
    max-height: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
    border: 0 !important;
    overflow: hidden !important;
}


/* ============================================================
   FantasySync v6.2.1 — Higher board, native 16-round scroll,
   compact tabbed Queue/Roster utility panel
   ============================================================ */

/* Pull the entire Draft Room higher without changing its visual language. */
.main .block-container {
    padding-top: .18rem !important;
}

.st-key-v53_header {
    padding-top: 1px !important;
    padding-bottom: 5px !important;
    margin-top: 0 !important;
    margin-bottom: 0 !important;
}

.st-key-v621_draft_message {
    min-height: 16px !important;
    height: auto !important;
    margin: 0 0 2px !important;
    padding: 0 !important;
}

.st-key-v621_draft_message p,
.st-key-v621_draft_message [data-testid="stCaptionContainer"],
.st-key-v621_draft_message [data-testid="stMarkdownContainer"] {
    margin: 0 !important;
    padding: 0 !important;
    min-height: 0 !important;
    line-height: 1.05 !important;
    font-size: .57rem !important;
}

/* Do not make the outer workspace itself a clipping viewport. */
.st-key-v53_top_workspace,
.st-key-v53_top_workspace > div,
.st-key-v53_top_workspace > div > div {
    height: auto !important;
    max-height: none !important;
    min-height: 0 !important;
    overflow: visible !important;
    margin: 0 !important;
    padding: 0 !important;
}

/*
 * Native Streamlit bounded wrapper owns scrolling. The keyed outer block
 * stays natural height and must not clip it.
 */
.st-key-v53_board_panel {
    height: auto !important;
    max-height: none !important;
    min-height: 0 !important;
    overflow: visible !important;
    margin: 0 !important;
    padding: 0 !important;
}

.st-key-v53_board_panel
    [data-testid="stVerticalBlockBorderWrapper"] {
    overflow-y: auto !important;
    overflow-x: hidden !important;
    overscroll-behavior: contain !important;
    scrollbar-gutter: stable !important;
    -webkit-overflow-scrolling: touch !important;
    scrollbar-width: thin;
    scrollbar-color: #465671 #091321;
}

.st-key-v53_board_panel
    [data-testid="stVerticalBlockBorderWrapper"]
    > div,
.st-key-v53_board_panel
    [data-testid="stVerticalBlock"] {
    height: auto !important;
    max-height: none !important;
    min-height: 0 !important;
    overflow: visible !important;
}

/* Ensure rounds 1–16 contribute their full natural height. */
.st-key-v53_board_panel [data-testid="stMarkdownContainer"],
.st-key-v53_board_panel [data-testid="stMarkdownContainer"] > div,
.st-key-v53_board_panel .snake-board-wrap,
.st-key-v53_board_panel .snake-board-shell,
.st-key-v53_board_panel .snake-board-grid {
    height: auto !important;
    max-height: none !important;
    min-height: max-content !important;
    overflow: visible !important;
}

.st-key-v53_board_panel
    [data-testid="stVerticalBlockBorderWrapper"]
   ::-webkit-scrollbar {
    width: 7px;
}

.st-key-v53_board_panel
    [data-testid="stVerticalBlockBorderWrapper"]
   ::-webkit-scrollbar-track {
    background: #091321;
}

.st-key-v53_board_panel
    [data-testid="stVerticalBlockBorderWrapper"]
   ::-webkit-scrollbar-thumb {
    background: #465671;
    border-radius: 999px;
}

.st-key-v53_board_panel
    [data-testid="stVerticalBlockBorderWrapper"]
   ::-webkit-scrollbar-thumb:hover {
    background: #657995;
}

/* Keep tray immediately attached beneath the visible board. */
.st-key-v62_tray_controls {
    margin-top: 0 !important;
}

/* One compact utility box; click Queue or Roster. */
.st-key-v621_utility_panel {
    height: 100% !important;
    min-height: 220px !important;
    padding: 7px 9px !important;
    border: 1px solid rgba(148, 163, 184, .18) !important;
    border-radius: 8px !important;
    background: linear-gradient(180deg, #111E30, #0C1726) !important;
    overflow-y: auto !important;
}

.st-key-v621_utility_panel
    [data-testid="stTabs"] {
    margin: 0 !important;
}

.st-key-v621_utility_panel
    [data-testid="stTabs"] [role="tablist"] {
    gap: 4px !important;
    margin-bottom: 5px !important;
    border-bottom: 1px solid rgba(148, 163, 184, .15);
}

.st-key-v621_utility_panel
    [data-testid="stTabs"] button[role="tab"] {
    min-height: 29px !important;
    height: 29px !important;
    padding: 0 9px !important;
    font-size: .55rem !important;
    font-weight: 800 !important;
    color: #8FA0B7 !important;
    -webkit-text-fill-color: #8FA0B7 !important;
}

.st-key-v621_utility_panel
    [data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
    color: #70A7FF !important;
    -webkit-text-fill-color: #70A7FF !important;
    border-bottom-color: #4F8FF5 !important;
}

.st-key-v621_utility_panel
    [data-testid="stTabContent"] {
    padding-top: 2px !important;
}

/* Queue is intentionally more compact than the prior dedicated column. */
.st-key-v621_utility_panel .queue-title-row {
    display: none !important;
}

.st-key-v621_utility_panel .queue-empty {
    min-height: 52px !important;
    padding: 10px 7px !important;
    font-size: .53rem !important;
}

.st-key-v621_utility_panel button {
    min-height: 25px !important;
    height: 25px !important;
    padding: 0 5px !important;
    font-size: .50rem !important;
}

.st-key-v621_utility_panel [data-testid="stHorizontalBlock"] {
    gap: .20rem !important;
}

/* Roster remains one clean box when its tab is selected. */
.st-key-v621_utility_panel .roster-header-row {
    margin-bottom: 3px !important;
}

.st-key-v621_utility_panel .roster-line {
    min-height: 27px !important;
    padding: 0 !important;
}

.st-key-v621_utility_panel .roster-slot-pill {
    height: 20px !important;
}

.st-key-v621_utility_panel .roster-line-player {
    font-size: .55rem !important;
}

/* Preserve hidden autorefresh and fast CPU behavior exactly. */
.st-key-cpu_autorefresh_mount,
.st-key-cpu_autorefresh_mount > div,
.st-key-cpu_autorefresh_mount [data-testid="stVerticalBlock"],
.st-key-cpu_autorefresh_mount [data-testid="stElementContainer"],
.st-key-cpu_autorefresh_mount [data-testid="stCustomComponentV1"],
.st-key-cpu_autorefresh_mount iframe {
    display: none !important;
    visibility: hidden !important;
    position: absolute !important;
    width: 0 !important;
    height: 0 !important;
    min-width: 0 !important;
    min-height: 0 !important;
    max-width: 0 !important;
    max-height: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
    border: 0 !important;
    overflow: hidden !important;
}


/* ============================================================
   FantasySync v6.2.2 — Separate Board and Player Tray
   Visual-only patch based on v6.2.1.
   ============================================================ */

/* Board remains its own region. */
.st-key-v53_top_workspace {
    position: relative !important;
    z-index: 1 !important;
    margin: 0 0 8px !important;
    padding: 0 !important;
    background: transparent !important;
}

/* Divider controls sit between—not over—the two regions. */
.st-key-v62_tray_controls {
    position: relative !important;
    z-index: 4 !important;
    height: 38px !important;
    min-height: 38px !important;
    max-height: 38px !important;
    margin: 0 0 6px !important;
    padding: 0 !important;
    background: #081321 !important;
    border-top: 2px solid #7C5CE0 !important;
    border-bottom: 1px solid rgba(148, 163, 184, .18) !important;
    overflow: visible !important;
}

.st-key-v62_tray_controls [data-testid="stHorizontalBlock"] {
    height: 36px !important;
    min-height: 36px !important;
    align-items: center !important;
}

/* The player tray is now one solid bordered panel. */
.st-key-v53_bottom_workspace {
    position: relative !important;
    z-index: 2 !important;
    clear: both !important;
    width: 100% !important;
    max-width: none !important;
    margin: 0 !important;
    padding: 10px 12px 12px !important;
    background: #0B1625 !important;
    border: 1px solid rgba(148, 163, 184, .24) !important;
    border-radius: 10px !important;
    box-sizing: border-box !important;
    overflow: hidden !important;
}

/* Prevent any tray content from escaping upward into the board. */
.st-key-v53_bottom_workspace > div,
.st-key-v53_bottom_workspace > div > div,
.st-key-v53_bottom_workspace [data-testid="stHorizontalBlock"],
.st-key-v53_bottom_workspace [data-testid="stColumn"] {
    position: relative !important;
    z-index: 1 !important;
    margin-top: 0 !important;
    transform: none !important;
}

.st-key-v53_bottom_workspace [data-testid="stHorizontalBlock"] {
    align-items: flex-start !important;
}

/* Keep the player browser and Queue/Roster utility visibly separate. */
.st-key-v61_player_toolbar {
    background: transparent !important;
}

.st-key-v621_utility_panel {
    border: 1px solid rgba(148, 163, 184, .22) !important;
    background: #101D2E !important;
    border-radius: 8px !important;
}

/* Remove older negative offsets that could cause overlap. */
.st-key-v53_bottom_workspace,
.st-key-v61_player_toolbar,
.st-key-war_player_list,
.st-key-v621_utility_panel {
    top: auto !important;
    bottom: auto !important;
    transform: none !important;
}

/* Preserve the hidden autorefresh behavior. */
.st-key-cpu_autorefresh_mount,
.st-key-cpu_autorefresh_mount > div,
.st-key-cpu_autorefresh_mount [data-testid="stVerticalBlock"],
.st-key-cpu_autorefresh_mount [data-testid="stElementContainer"],
.st-key-cpu_autorefresh_mount [data-testid="stCustomComponentV1"],
.st-key-cpu_autorefresh_mount iframe {
    display: none !important;
    visibility: hidden !important;
    position: absolute !important;
    width: 0 !important;
    height: 0 !important;
    min-width: 0 !important;
    min-height: 0 !important;
    max-width: 0 !important;
    max-height: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
    border: 0 !important;
    overflow: hidden !important;
}


/* ============================================================
   FantasySync v6.3.3 — Compact Draft Header
   ============================================================ */

.main .block-container {
    padding-top: .10rem !important;
}

.st-key-v53_header {
    min-height: 70px !important;
    padding: 2px 0 5px !important;
    margin: 0 0 2px !important;
    border-bottom: 1px solid rgba(148,163,184,.15) !important;
}

.st-key-v53_header > div,
.st-key-v53_header > div > div,
.st-key-v53_header [data-testid="stHorizontalBlock"] {
    min-height: 0 !important;
    margin: 0 !important;
    padding-top: 0 !important;
    padding-bottom: 0 !important;
    align-items: center !important;
}

.v53-title,
.st-key-v53_header h1,
.st-key-v53_header h2,
.st-key-v53_header h3 {
    font-size: 1.18rem !important;
    line-height: 1.05 !important;
    margin: 0 !important;
}

.v53-meta {
    margin-top: 3px !important;
    gap: 5px !important;
}

.v53-meta-chip {
    min-height: 24px !important;
    height: 24px !important;
    padding: 0 9px !important;
    font-size: .54rem !important;
    border-radius: 7px !important;
}

.v53-cpu {
    min-height: 27px !important;
    height: 27px !important;
    padding: 0 10px !important;
    font-size: .55rem !important;
}

.v53-clock {
    width: 58px !important;
    min-width: 58px !important;
    height: 58px !important;
    min-height: 58px !important;
    transform: none !important;
    margin: 0 !important;
}

.v53-clock-time {
    font-size: .92rem !important;
    line-height: 1 !important;
}

.v53-clock-label {
    font-size: .38rem !important;
    line-height: 1 !important;
}

.st-key-v53_header_action button {
    min-height: 39px !important;
    height: 39px !important;
    padding: 0 18px !important;
    font-size: .71rem !important;
}

.st-key-v63_draft_message,
.st-key-v621_draft_message,
.st-key-v61_draft_message {
    min-height: 16px !important;
    margin: 0 0 2px !important;
    padding: 0 !important;
}

.st-key-v63_draft_message p,
.st-key-v621_draft_message p,
.st-key-v61_draft_message p,
.st-key-v63_draft_message [data-testid="stCaptionContainer"],
.st-key-v621_draft_message [data-testid="stCaptionContainer"],
.st-key-v61_draft_message [data-testid="stCaptionContainer"] {
    margin: 0 !important;
    padding: 0 !important;
    font-size: .58rem !important;
    line-height: 1.05 !important;
}

.st-key-v63_board_region {
    margin-top: 0 !important;
    padding-top: 0 !important;
}


/* ============================================================
   FantasySync v6.4.0 — Structural compact header
   ============================================================ */

.main .block-container {
    padding-top: .05rem !important;
}

.st-key-v640_header {
    min-height: 54px !important;
    height: 54px !important;
    margin: 0 !important;
    padding: 0 0 3px !important;
    border-bottom: 1px solid rgba(148,163,184,.16) !important;
}

.st-key-v640_header > div,
.st-key-v640_header > div > div,
.st-key-v640_header [data-testid="stHorizontalBlock"] {
    min-height: 50px !important;
    height: 50px !important;
    margin: 0 !important;
    padding: 0 !important;
    align-items: center !important;
}

.v640-title-line {
    height: 48px;
    display: flex;
    align-items: center;
    gap: 7px;
    white-space: nowrap;
    overflow: hidden;
}

.v640-title {
    flex: 0 0 auto;
    color: #F8FAFC;
    font-size: 1.08rem;
    line-height: 1;
    font-weight: 900;
    margin-right: 3px;
}

.v640-chip {
    flex: 0 0 auto;
    min-height: 23px;
    display: inline-flex;
    align-items: center;
    padding: 0 9px;
    border-radius: 7px;
    border: 1px solid #334158;
    background: #111C2D;
    color: #CED7E5;
    font-size: .50rem;
    font-weight: 780;
}

.v640-cpu {
    height: 27px;
    display: flex;
    align-items: center;
    justify-content: center;
    border: 1px solid #276744;
    border-radius: 999px;
    background: #0C2B20;
    color: #6CE38C;
    font-size: .50rem;
    font-weight: 850;
    white-space: nowrap;
}

.v640-clock {
    width: 48px;
    height: 48px;
    margin: 0 auto;
    border: 2px solid #3B82F6;
    border-radius: 50%;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
}

.v640-clock-time {
    color: #FFFFFF;
    font-size: .78rem;
    font-weight: 900;
    line-height: 1;
}

.v640-clock-label {
    color: #7EB3FF;
    font-size: .31rem;
    font-weight: 850;
    line-height: 1;
    margin-top: 3px;
}

.st-key-v640_header button {
    min-height: 35px !important;
    height: 35px !important;
    padding: 0 13px !important;
    border-radius: 7px !important;
    font-size: .62rem !important;
}

.st-key-v63_draft_message {
    min-height: 13px !important;
    height: 13px !important;
    margin: 1px 0 1px !important;
    padding: 0 !important;
    overflow: hidden !important;
}

.st-key-v63_draft_message p,
.st-key-v63_draft_message [data-testid="stCaptionContainer"] {
    margin: 0 !important;
    padding: 0 !important;
    font-size: .52rem !important;
    line-height: 1 !important;
}

/* Retire the legacy header from the Draft Room. */
.st-key-v53_header {
    display: none !important;
}

.st-key-v63_board_region {
    margin-top: 0 !important;
    padding-top: 0 !important;
}


/* ============================================================
   FantasySync v6.4.3 — Visible position filters
   ============================================================ */

/*
 * Some browsers were rendering Streamlit's secondary buttons as white
 * surfaces with white text. Force a consistent dark, high-contrast system.
 */
.st-key-v61_player_toolbar button,
.st-key-v61_player_toolbar
    [data-testid="stBaseButton-secondary"],
.st-key-v61_player_toolbar
    [data-testid="stBaseButton-primary"] {
    min-height: 30px !important;
    height: 30px !important;
    border-radius: 999px !important;
    border: 1px solid #465671 !important;
    background: #172437 !important;
    color: #E7EDF6 !important;
    -webkit-text-fill-color: #E7EDF6 !important;
    box-shadow: none !important;
    opacity: 1 !important;
}

.st-key-v61_player_toolbar button *,
.st-key-v61_player_toolbar
    [data-testid="stBaseButton-secondary"] *,
.st-key-v61_player_toolbar
    [data-testid="stBaseButton-primary"] * {
    color: #E7EDF6 !important;
    -webkit-text-fill-color: #E7EDF6 !important;
    opacity: 1 !important;
}

/* Selected filter */
.st-key-v61_player_toolbar
    [data-testid="stBaseButton-primary"],
.st-key-v61_player_toolbar button[kind="primary"] {
    background: #345EDB !important;
    border-color: #6C8CFF !important;
    color: #FFFFFF !important;
    -webkit-text-fill-color: #FFFFFF !important;
}

.st-key-v61_player_toolbar
    [data-testid="stBaseButton-primary"] *,
.st-key-v61_player_toolbar button[kind="primary"] * {
    color: #FFFFFF !important;
    -webkit-text-fill-color: #FFFFFF !important;
}

.st-key-v61_player_toolbar button:hover {
    background: #243550 !important;
    border-color: #7590B8 !important;
    color: #FFFFFF !important;
    -webkit-text-fill-color: #FFFFFF !important;
}

.st-key-v61_player_toolbar button:focus-visible {
    outline: 2px solid #7FA6FF !important;
    outline-offset: 1px !important;
}

/* Explicit keyed fallbacks for Streamlit builds that omit button kind attrs. */
.st-key-draft_pos_ALL button,
.st-key-draft_pos_QB button,
.st-key-draft_pos_RB button,
.st-key-draft_pos_WR button,
.st-key-draft_pos_TE button {
    background: #172437 !important;
    border-color: #465671 !important;
    color: #E7EDF6 !important;
    -webkit-text-fill-color: #E7EDF6 !important;
}

.st-key-draft_pos_ALL button *,
.st-key-draft_pos_QB button *,
.st-key-draft_pos_RB button *,
.st-key-draft_pos_WR button *,
.st-key-draft_pos_TE button * {
    color: inherit !important;
    -webkit-text-fill-color: inherit !important;
}

</style>
""", unsafe_allow_html=True)


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
        '<div style="display:grid;'
        'grid-template-columns:38px repeat(10,minmax(0,1fr));'
        'gap:2px;width:100%;">'
    )

    html.append('<div></div>')

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
        html.append(
            f'<div class="snake-cell snake-round-label">R{rnd}</div>'
        )

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

            html.append(
                f'<div class="{" ".join(classes)}">'
                f'<div class="snake-pick">#{int(r.overall)}{keeper_star}</div>'
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
    ensure_draft_filters()

    tabs_col, search_col, filter_col = st.columns(
        [2.15, 2.65, 4.9],
        gap="small",
    )

    with tabs_col:
        st.markdown(
            """
            <div class="v61-inline-tabs">
                <span class="v61-inline-tab active">PLAYERS</span>
                <span class="v61-inline-tab">QUEUE</span>
                <span class="v61-inline-tab">WATCHLIST</span>
            </div>
            """,
            unsafe_allow_html=True,
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




def render_draggable_player_tray():
    """
    Install a stable browser-side divider.

    The divider directly controls the complete top workspace height. Because
    the handle immediately follows that workspace in the normal document flow,
    the full Players section moves with it and no spacer can remain.
    """
    components.html(
        """
        <script>
        (() => {
          const doc = window.parent.document;
          const storage = window.parent.sessionStorage;
          const STORAGE_KEY = "fantasysync_tray_height_v59";

          const DEFAULT_HEIGHT = 470;
          const MIN_HEIGHT = 300;
          const MAX_HEIGHT = 575;
          const TOTAL_HEIGHT = 760;

          function important(element, property, value) {
            if (!element) return;
            element.style.setProperty(property, value, "important");
          }

          function panels() {
            return Array.from(
              doc.querySelectorAll(
                ".st-key-v53_board_panel, .st-key-v53_roster_panel"
              )
            );
          }

          function playerLists() {
            return Array.from(
              doc.querySelectorAll(".st-key-war_player_list")
            );
          }

          function applyHeight(rawHeight) {
            const height = Math.max(
              MIN_HEIGHT,
              Math.min(MAX_HEIGHT, Number(rawHeight) || DEFAULT_HEIGHT)
            );
            const playerHeight = Math.max(170, TOTAL_HEIGHT - height);

            const workspace = doc.querySelector(
              ".st-key-v53_top_workspace"
            );

            if (workspace) {
              important(workspace, "height", `${height}px`);
              important(workspace, "max-height", `${height}px`);
              important(workspace, "min-height", `${height}px`);
              important(workspace, "overflow", "hidden");

              const direct = workspace.querySelector(
                ':scope > div > div > [data-testid="stHorizontalBlock"]'
              );

              if (direct) {
                important(direct, "height", "100%");
                important(direct, "max-height", "100%");
                important(direct, "min-height", "0px");
                important(direct, "align-items", "stretch");

                direct.querySelectorAll(
                  ':scope > [data-testid="stColumn"]'
                ).forEach((column) => {
                  important(column, "height", "100%");
                  important(column, "max-height", "100%");
                  important(column, "min-height", "0px");
                  important(column, "overflow", "hidden");
                });
              }
            }

            panels().forEach((panel) => {
              /*
               * The panel is the scroll viewport. Do not force its inner
               * Markdown/vertical wrappers to 100% height; those wrappers must
               * keep their natural height so all 16 rounds contribute to
               * scrollHeight.
               */
              important(panel, "height", "100%");
              important(panel, "max-height", "100%");
              important(panel, "min-height", "0px");
              important(panel, "overflow-y", "auto");
              important(panel, "overflow-x", "hidden");

              const column = panel.closest('[data-testid="stColumn"]');
              if (column) {
                important(column, "height", "100%");
                important(column, "max-height", "100%");
                important(column, "min-height", "0px");
                important(column, "overflow", "hidden");
              }

              panel.querySelectorAll(
                ':scope > div, ' +
                '[data-testid="stVerticalBlockBorderWrapper"], ' +
                '[data-testid="stVerticalBlock"], ' +
                '[data-testid="stMarkdownContainer"]'
              ).forEach((inner) => {
                important(inner, "height", "auto");
                important(inner, "max-height", "none");
                important(inner, "min-height", "0px");
                important(inner, "overflow", "visible");
              });
            });

            playerLists().forEach((list) => {
              important(list, "height", `${playerHeight}px`);
              important(list, "max-height", `${playerHeight}px`);
              important(list, "min-height", "150px");
              important(list, "overflow-y", "auto");
            });

            storage.setItem(STORAGE_KEY, String(height));
          }

          function install() {
            const handle = doc.querySelector(".v56-drag-grip");
            if (!handle || handle.dataset.v59Installed === "true") {
              return false;
            }

            handle.dataset.v59Installed = "true";

            let dragging = false;
            let startY = 0;
            let startHeight = DEFAULT_HEIGHT;

            const stored = Number(storage.getItem(STORAGE_KEY));
            applyHeight(
              Number.isFinite(stored) && stored > 0
                ? stored
                : DEFAULT_HEIGHT
            );

            handle.addEventListener("pointerdown", (event) => {
              const workspace = doc.querySelector(
                ".st-key-v53_top_workspace"
              );

              dragging = true;
              startY = event.clientY;
              startHeight = workspace
                ? workspace.getBoundingClientRect().height
                : DEFAULT_HEIGHT;

              handle.setPointerCapture(event.pointerId);
              handle.classList.add("dragging");
              doc.body.style.userSelect = "none";
              doc.body.style.cursor = "ns-resize";
              event.preventDefault();
            });

            handle.addEventListener("pointermove", (event) => {
              if (!dragging) return;
              applyHeight(startHeight + (event.clientY - startY));
              event.preventDefault();
            });

            function stop(event) {
              if (!dragging) return;
              dragging = false;
              handle.classList.remove("dragging");
              doc.body.style.userSelect = "";
              doc.body.style.cursor = "";
              try {
                handle.releasePointerCapture(event.pointerId);
              } catch (_) {}
            }

            handle.addEventListener("pointerup", stop);
            handle.addEventListener("pointercancel", stop);
            handle.addEventListener("dblclick", () => {
              applyHeight(DEFAULT_HEIGHT);
            });

            return true;
          }

          let attempts = 0;
          const timer = window.setInterval(() => {
            attempts += 1;
            if (install() || attempts > 80) {
              window.clearInterval(timer);
            }
          }, 100);
        })();
        </script>
        """,
        height=0,
        width=0,
    )



def render_live_user_roster():
    render_live_roster_header()
    render_live_roster_rows()


def render_player_picker_controls():
    ensure_draft_filters()

    top_left, top_right = st.columns([2.3, 3.7])
    with top_left:
        st.text_input(
            "Search available players",
            key="draft_search",
            placeholder="🔍 Find player",
            label_visibility="collapsed",
        )
    with top_right:
        render_position_filter()


def render_player_picker_table(
    current_idx: int,
    allow_draft: bool = True,
    list_height_override: Optional[int] = None,
):
    clean_player_queue()
    pool = filtered_draft_pool()

    if pool.empty:
        st.warning("No available players match this filter.")
        return

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

    header_cols = st.columns(widths)
    for col, label in zip(header_cols, headers):
        col.markdown(
            f"<div class='player-table-header2'>{label}</div>",
            unsafe_allow_html=True,
        )

    st.markdown(
        '<div class="player-header-divider"></div>',
        unsafe_allow_html=True,
    )

    shown = pool.head(60).reset_index(drop=True)
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

            st.markdown(
                '<div class="player-row-divider"></div>',
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



def render_player_picker(
    current_idx: int,
    allow_draft: bool = True,
):
    render_player_picker_controls()
    render_player_picker_table(current_idx, allow_draft)


def render_recommendation_cards(recs: pd.DataFrame):
    st.markdown('<div class="war-room-title">RECOMMENDATIONS</div>', unsafe_allow_html=True)
    if recs.empty:
        st.caption("No recommendations available.")
        return
    for row in recs.head(5).itertuples():
        adp = "—" if pd.isna(row.ADP) else f"{row.ADP:.1f}"
        st.markdown(
            f"""
            <div class="recommendation-card">
              <div class="recommendation-player">{clean(row.Player)}</div>
              <div class="recommendation-meta">{clean(row.Pos)} · Rank {int(row.Rank)} · ADP {adp}</div>
              <div class="recommendation-meta">Chance back: {clean(getattr(row, 'Chance_Back', ''))}</div>
              <div class="recommendation-meta">{clean(row.Why)}</div>
            </div>
            """, unsafe_allow_html=True
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

with st.sidebar:
    st.markdown(
        """
        <div class="sidebar-brand">
            <div class="sidebar-brand-icon">🏈</div>
            <div class="sidebar-brand-name">FantasySync</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="sidebar-section-label">NAVIGATION</div>',
        unsafe_allow_html=True,
    )

    page_options = [
        "▣  Draft Room",
        "▥  Rankings",
        "★  Recommendations",
        "♜  Draft Grades",
        "▥  Data Status",
        "◴  League History",
        "⚙  Settings",
        "⇩  Import / Export",
        "?  Help & Docs",
    ]

    selected_nav = st.radio(
        "Navigation",
        page_options,
        key="sidebar_navigation",
        label_visibility="collapsed",
    )

    selected_page = {
        "▣  Draft Room": "Draft Room",
        "▥  Rankings": "Rankings & ADP",
        "★  Recommendations": "Recommendations",
        "♜  Draft Grades": "League History",
        "▥  Data Status": "Available Players",
        "◴  League History": "League History",
        "⚙  Settings": "Settings",
        "⇩  Import / Export": "Keepers & Picks",
        "?  Help & Docs": "League Setup",
    }[selected_nav]

    team_count = len(st.session_state.teams)
    st.markdown(
        f"""
        <div class="sidebar-league-card">
            <div class="sidebar-league-name">
                Susan Boyles Ass Sweat
            </div>
            <div class="sidebar-league-meta">
                <span>Teams</span>
                <strong>{team_count}</strong>
            </div>
            <div class="sidebar-league-meta">
                <span>Rounds</span>
                <strong>{int(st.session_state.rounds)}</strong>
            </div>
            <div class="sidebar-league-meta">
                <span>Pick Clock</span>
                <strong>{int(st.session_state.pick_clock_seconds)}s</strong>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="sidebar-section-label">DRAFT UTILITIES</div>',
        unsafe_allow_html=True,
    )

    if st.button(
        "↺ Reset Draft",
        use_container_width=True,
        key="sidebar_reset_draft",
    ):
        rebuild_draft()
        st.session_state.draft_active = False
        st.session_state.clock_running = False
        st.session_state.draft_message = (
            "Draft reset. Select a team and press Start Draft."
        )
        st.rerun()

    state_json = json.dumps(serializable_state(), indent=2)
    st.download_button(
        "⬇ Download Draft State",
        data=state_json,
        file_name="sbas_mock_draft_state.json",
        mime="application/json",
        use_container_width=True,
    )

    st.markdown(
        '<div class="sidebar-version">FantasySync · v6.4.3</div>',
        unsafe_allow_html=True,
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

