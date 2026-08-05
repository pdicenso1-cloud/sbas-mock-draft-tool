
from __future__ import annotations

import json
import math
import time
from pathlib import Path
from typing import Dict, Optional

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from streamlit_autorefresh import st_autorefresh

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
        "clock_paused_remaining": 60,
        "dock_level": 1,
    }
    for key, value in defaults.items():
        if force or key not in st.session_state:
            st.session_state[key] = value



DOCK_LEVELS = {
    0: {"name": "Compact", "dock_vh": 24, "list_px": 165, "roster_vh": 20},
    1: {"name": "Standard", "dock_vh": 38, "list_px": 330, "roster_vh": 34},
    2: {"name": "Expanded", "dock_vh": 64, "list_px": 590, "roster_vh": 59},
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
        .st-key-war_roster_panel {{
            height: calc({settings["roster_vh"]}vh - 52px) !important;
            max-height: calc({settings["roster_vh"]}vh - 52px) !important;
            overflow-y: auto !important;
        }}
        .st-key-draft_drawer {{
            position: fixed !important;
        }}
        .st-key-roster_and_controls {{
            height: {settings["roster_vh"]}vh !important;
            overflow: hidden !important;
            padding-right: 50px !important;
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

    player = best_available()
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
        player = best_available()
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
    st.session_state.picks = assign_keepers(
        snake_order(st.session_state.teams, int(st.session_state.rounds)),
        st.session_state.keepers,
        st.session_state.teams,
    )
    st.session_state.draft_message = "Draft reset with current teams, keepers, and draft order."
    reset_pick_clock()


def serializable_state():
    return {
        "rounds": int(st.session_state.rounds),
        "user_team": clean(st.session_state.user_team),
        "teams": st.session_state.teams.to_dict(orient="records"),
        "keepers": st.session_state.keepers.fillna("").to_dict(orient="records"),
        "picks": st.session_state.picks.fillna("").to_dict(orient="records"),
    }


def save_state():
    STATE_FILE.write_text(json.dumps(serializable_state(), indent=2), encoding="utf-8")


def load_state_data(data):
    st.session_state.rounds = int(data["rounds"])
    st.session_state.user_team = clean(data["user_team"])
    st.session_state.teams = pd.DataFrame(data["teams"])
    st.session_state.keepers = pd.DataFrame(data["keepers"])
    st.session_state.picks = pd.DataFrame(data["picks"])
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
            f'<div class="snake-cell" style="min-height:58px;'
            f'font-weight:700;text-align:center;font-size:.68rem;">R{rnd}</div>'
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

    player = best_available()
    if not player:
        st.session_state.draft_message = "Pick clock expired, but no available player remained."
        return False

    make_pick(idx, player, "User Auto")
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
):
    pool = filtered_draft_pool()
    if pool.empty:
        st.warning("No available players match this filter.")
        return

    headers = [
        "", "RK", "PLAYER", "POS", "ADP", "TIER", "SCORE",
        "PROJ", "AVG", "RUSH", "REC", "PASS", "BYE", ""
    ]
    widths = [
        0.42, 0.46, 2.1, 0.55, 0.56, 0.56, 0.60,
        0.60, 0.60, 0.62, 0.62, 0.62, 0.54, 0.42
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
    list_height = dock_settings()["list_px"]

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
            rush = row.get("rush_yds", "")
            rec = row.get("rec_yds", "")
            pas = row.get("pass_yds", "")
            bye = row.get("bye", "")

            adp_text = "—" if adp is None else f"{adp:.1f}"
            score_text = "—" if score is None else f"{score:.0f}"
            proj_text = "—" if proj is None else f"{proj:.1f}"
            avg_text = "—" if avg is None else f"{avg:.1f}"
            rush_text = clean(rush) or "—"
            rec_text = clean(rec) or "—"
            pass_text = clean(pas) or "—"
            bye_text = clean(bye) or "—"
            pos_class = pos if pos in {"QB", "RB", "WR", "TE"} else "OTHER"

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

            cols[1].markdown(
                f"<div class='rank2'>{rank}</div>",
                unsafe_allow_html=True,
            )
            cols[2].markdown(
                f"""
                <div class='player-name2' title='{player}'>{player}</div>
                <div class='player-sub2'>
                    <span class='pos-dot dot-{pos_class}'></span>
                    {pos} · {nfl_team}
                </div>
                """,
                unsafe_allow_html=True,
            )

            for col, value in zip(
                cols[3:13],
                [
                    pos, adp_text, tier or "—", score_text, proj_text,
                    avg_text, rush_text, rec_text, pass_text, bye_text
                ],
            ):
                col.markdown(
                    f"<div class='stat2'>{value}</div>",
                    unsafe_allow_html=True,
                )

            st.markdown(
                '<div class="player-row-divider"></div>',
                unsafe_allow_html=True,
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
apply_team_query_selection()
render_dynamic_dock_css()

# Only CPU turns use full-page refreshes.
# User turns rely on the browser-side clock, so player clicks stay responsive.
_current_idx = current_open_index()
_current_owner = None

if _current_idx is not None:
    _current_owner = clean(
        st.session_state.picks.loc[_current_idx, "current_owner"]
    )

_cpu_turn_active = (
    st.session_state.clock_running
    and _current_idx is not None
    and _current_owner != clean(st.session_state.user_team)
)

if _cpu_turn_active:
    st_autorefresh(
        interval=1000,
        limit=None,
        key="cpu_draft_animation_refresh",
    )
    run_one_cpu_pick()

# Enforce the user's pick clock only on user-controlled turns.
if auto_pick_user_if_expired():
    st.rerun()

header_copy_col, header_actions_col = st.columns(
    [5.7, 2.3],
    gap="large",
)

with header_copy_col:
    st.markdown(
        """
        <div class="app-header-copy">
            <div class="app-header-title">
                🏈 Susan Boyles Ass Sweat — Mock Draft Tool
            </div>
            <div class="app-header-subtitle">
                Live 10-team mock draft room with keepers, animated CPU picks,
                and team-aware recommendations.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with header_actions_col:
    with st.container(key="compact_header_actions"):
        top_action_col, top_reset_col = st.columns(2, gap="small")

        with top_action_col:
            if st.session_state.clock_running:
                if st.button(
                    "⏸ Pause Draft",
                    use_container_width=True,
                    type="primary",
                    key="page_top_pause",
                ):
                    pause_pick_clock()
                    st.rerun()
            else:
                if st.button(
                    "▶ Start Draft",
                    use_container_width=True,
                    type="primary",
                    key="page_top_start",
                ):
                    st.session_state.clock_running = True
                    current_idx = current_open_index()
                    if current_idx is not None:
                        current_owner = clean(
                            st.session_state.picks.loc[
                                current_idx,
                                "current_owner",
                            ]
                        )
                        if current_owner == clean(
                            st.session_state.user_team
                        ):
                            start_pick_clock()
                    st.rerun()

        with top_reset_col:
            if st.button(
                "↺ Reset Draft",
                use_container_width=True,
                key="page_top_reset",
            ):
                rebuild_draft()
                st.session_state.clock_running = False
                st.session_state.draft_message = (
                    "Draft reset. Select a team and press Start Draft."
                )
                st.rerun()

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
        "🏠  Draft Room",
        "⭐  Recommendations",
        "📊  Rankings & ADP",
        "👥  Available Players",
        "🛡️  Team Rosters",
        "⚙️  League Setup",
        "🔖  Keepers & Picks",
        "🕘  League History",
        "🔧  Settings",
    ]

    selected_nav = st.radio(
        "Navigation",
        page_options,
        key="sidebar_navigation",
        label_visibility="collapsed",
    )

    selected_page = {
        "🏠  Draft Room": "Draft Room",
        "⭐  Recommendations": "Recommendations",
        "📊  Rankings & ADP": "Rankings & ADP",
        "👥  Available Players": "Available Players",
        "🛡️  Team Rosters": "Team Rosters",
        "⚙️  League Setup": "League Setup",
        "🔖  Keepers & Picks": "Keepers & Picks",
        "🕘  League History": "League History",
        "🔧  Settings": "Settings",
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
        '<div class="sidebar-version">FantasySync Public Beta · v4.1</div>',
        unsafe_allow_html=True,
    )

if selected_page == "Draft Room":
    idx = current_open_index()

    if idx is None:
        draft_clock_label = "Draft Status"
        draft_clock_value = "Complete"
    else:
        current = st.session_state.picks.loc[idx]
        draft_clock_label = "On the Clock"
        draft_clock_value = (
            f"#{int(current['overall'])} · "
            f"{clean(current['current_owner'])}"
        )

    st.markdown(
        f"""
        <div class="draft-room-heading">
            <div class="draft-room-title">
                Live Snake Draft Board
            </div>
            <div class="draft-clock-block">
                <div class="draft-clock-label">
                    {draft_clock_label}
                </div>
                <div class="draft-clock-value">
                    {draft_clock_value}
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.session_state.draft_message:
        st.info(st.session_state.draft_message)

    st.markdown(snake_board_html(), unsafe_allow_html=True)

    with st.expander("View Draft Log", expanded=False):
        display = st.session_state.picks[[
            "overall", "round", "slot", "current_owner",
            "keeper_player", "selected_player", "source"
        ]].copy()
        display.columns = [
            "Overall", "Round", "Slot", "Current Owner",
            "Keeper", "Player Selected", "Source"
        ]
        st.dataframe(
            display,
            use_container_width=True,
            hide_index=True,
            height=460,
        )

    # Persistent draft panel with player list flush to the top.
    with st.container(key="draft_drawer"):
        if idx is None:
            st.success("Draft complete")
        else:
            current = st.session_state.picks.loc[idx]
            owner = clean(current["current_owner"])
            user_turn = owner == clean(st.session_state.user_team)

            # Shared top row: keep the roster header aligned with the filters.
            top_available, top_roster = st.columns(
                [4.35, 1.87],
                gap="small",
            )

            with top_available:
                render_player_picker_controls()

            with top_roster:
                with st.container(key="roster_header_anchor"):
                    with st.container(key="roster_header_panel"):
                        render_live_roster_header()

                    # Roster slots are positioned directly beneath the header,
                    # independent of the player-table header height on the left.
                    with st.container(key="roster_rows_overlay"):
                        with st.container(key="war_roster_panel"):
                            render_live_roster_rows()

            # Player table remains in its own left-side content row.
            content_available, content_spacer = st.columns(
                [4.35, 1.87],
                gap="small",
            )

            with content_available:
                render_player_picker_table(
                    idx,
                    allow_draft=user_turn,
                )

            with content_spacer:
                st.empty()

            # Overlay controls pinned to the dock's top-right corner.
            with st.container(key="dock_controls"):
                level = int(st.session_state.dock_level)

                if st.button(
                    "▲",
                    key="dock_move_up",
                    use_container_width=True,
                    disabled=level >= 2,
                    help="Expand player selector",
                ):
                    move_dock(1)
                    st.rerun()

                if st.button(
                    "▼",
                    key="dock_move_down",
                    use_container_width=True,
                    disabled=level <= 0,
                    help="Collapse player selector",
                ):
                    move_dock(-1)
                    st.rerun()

    st.markdown(
        '<div class="fixed-dock-spacer"></div>',
        unsafe_allow_html=True,
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

        st.markdown("#### Display")
        st.info(
            "Additional color, font, and accessibility settings "
            "will be added here during the UI polish pass."
        )

