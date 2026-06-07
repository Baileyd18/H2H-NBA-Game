
import os
import json
import hashlib
from urllib.parse import quote
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

try:
    from head_to_head_7_game_mode_fixed import render_head_to_head_mode
except Exception:
    render_head_to_head_mode = None

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


# ============================================================
# CONFIG
# ============================================================

DATA_PATH = "Clean NBA Data Full API With Profiles.csv"
FALLBACK_DATA_PATH = "Clean NBA Data.csv"
LOGO_PATH = "baileybi_logo.png"

# ============================================================
# OPENAI API KEY - ONLY PASTE YOUR KEY ON THIS ONE LINE
# ============================================================
# 1. Revoke any key you pasted into chat.
# 2. Create a brand-new key.
# 3. Paste it between the quotes below.
# 4. Do NOT paste your key anywhere else in this file.
OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY", "")

# Internal placeholder. Do not edit this line.
PLACEHOLDER_API_KEY = "PASTE_YOUR_NEW_OPENAI_API_KEY_HERE"

SALARY_CAP_LEVELS = {
    "Salary Cap": 165_000_000,
    "Salary Floor": 149_000_000,
    "Luxury Tax Level": 201_000_000,
    "First Apron": 209_000_000,
    "Second Apron": 222_000_000,
    "Custom": 350_000_000,
}

DEFAULT_SALARY_CAP = SALARY_CAP_LEVELS["Second Apron"]

ROSTER_SLOTS = [
    "Starting PG",
    "Starting SG",
    "Starting SF",
    "Starting PF",
    "Starting C",
    "Bench 1",
    "Bench 2",
    "Bench 3",
    "Bench 4",
    "Bench 5",
    "Bench 6",
    "Bench 7",
    "Bench 8",
    "Two-Way 1",
    "Two-Way 2",
]

MIN_RESULTS_PLAYERS = 9
DEFAULT_ROSTER_SIZE = 15
MAX_ROSTER_SIZE = 15

REQUIRED_COLUMNS = [
    "Player", "Team", "Pos", "Salary",
    "MP", "PTS", "AST", "TRB", "STL", "BLK", "TOV",
    "FG%", "3P%", "eFG%", "TS%", "PER", "USG%",
    "OBPM", "DBPM", "BPM", "VORP",
    "Impact_Score", "Value_Score"
]


# ============================================================
# PAGE SETUP
# ============================================================

st.set_page_config(
    page_title="NBA Front Office Simulator",
    page_icon="🏀",
    layout="wide"
)


# ============================================================
# CSS
# ============================================================

st.markdown(
    """
<style>
.stApp {
    background: #020617;
    color: #f8fafc;
}

.block-container {
    padding-top: 2.2rem;
    max-width: 1750px;
}

.main-title {
    font-size: 42px;
    font-weight: 950;
    color: #f8fafc;
    margin-bottom: 4px;
    letter-spacing: -0.04em;
}

.sub-title {
    font-size: 17px;
    color: #94a3b8;
    margin-bottom: 24px;
}

.section-title {
    color: #f8fafc;
    font-size: 23px;
    font-weight: 900;
    margin-top: 12px;
    margin-bottom: 12px;
}

.metric-card {
    background: linear-gradient(145deg, #111827, #020617);
    border: 1px solid #1e293b;
    border-radius: 18px;
    padding: 16px;
    box-shadow: 0 10px 25px rgba(0,0,0,.25);
    min-height: 92px;
}

.metric-label {
    color: #94a3b8;
    font-size: 12px;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: .06em;
}

.metric-value {
    color: #f8fafc;
    font-size: 24px;
    font-weight: 950;
    word-break: normal;
    white-space: nowrap;
    margin-top: 4px;
}

.roster-card {
    background: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 16px;
    padding: 12px 14px;
    margin-bottom: 10px;
}

.roster-slot {
    font-size: 12px;
    color: #38bdf8;
    font-weight: 950;
    letter-spacing: .04em;
    text-transform: uppercase;
}

.roster-player {
    font-size: 16px;
    color: #f8fafc;
    font-weight: 900;
    margin-top: 2px;
}

.roster-detail {
    font-size: 13px;
    color: #94a3b8;
    margin-top: 3px;
}

.fit-good {
    color: #22c55e;
    font-weight: 900;
}

.fit-bad {
    color: #ef4444;
    font-weight: 900;
}

.fit-neutral {
    color: #facc15;
    font-weight: 900;
}

.report-shell {
    background: #0f172a;
    border: 1px solid #334155;
    border-radius: 18px;
    padding: 24px;
    line-height: 1.65;
}

.small-note {
    color: #64748b;
    font-size: 13px;
    line-height: 1.55;
    margin-bottom: 12px;
}

div[data-testid="stDataFrame"] {
    border-radius: 14px;
    overflow: hidden;
}

.draft-board-note {
    color: #94a3b8;
    font-size: 13px;
    margin-top: -4px;
    margin-bottom: 10px;
}

div[data-testid="stDataFrame"] {
    border-radius: 18px;
    overflow: hidden;
    border: 1px solid #1e293b;
}

div[data-testid="stDataFrame"] * {
    font-size: 14px;
}


.hero-wrap {
    background:
        radial-gradient(circle at top left, rgba(56, 189, 248, 0.18), transparent 35%),
        linear-gradient(135deg, #020617 0%, #0f172a 52%, #111827 100%);
    border: 1px solid #1e293b;
    border-radius: 26px;
    padding: 26px 30px;
    margin-bottom: 26px;
    box-shadow: 0 18px 45px rgba(0,0,0,.32);
}

.hero-grid {
    display: grid;
    grid-template-columns: 120px 1fr;
    gap: 24px;
    align-items: center;
}

.hero-logo {
    width: 112px;
    height: 112px;
    object-fit: contain;
    border-radius: 24px;
    background: rgba(15, 23, 42, 0.45);
    padding: 10px;
    border: 1px solid rgba(148, 163, 184, 0.25);
}

.hero-eyebrow {
    color: #38bdf8;
    font-size: 13px;
    font-weight: 950;
    letter-spacing: .14em;
    text-transform: uppercase;
    margin-bottom: 4px;
}

.hero-badges {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin-top: 14px;
}

.hero-badge {
    background: rgba(14, 165, 233, 0.13);
    border: 1px solid rgba(56, 189, 248, 0.24);
    color: #bae6fd;
    padding: 7px 11px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 800;
}

.brand-sidebar {
    background: linear-gradient(145deg, #020617, #0f172a);
    border: 1px solid #1e293b;
    border-radius: 18px;
    padding: 14px;
    margin-bottom: 18px;
    text-align: center;
}

.brand-sidebar img {
    max-width: 120px;
    margin: 0 auto 8px auto;
}

.brand-sidebar-title {
    color: #f8fafc;
    font-size: 14px;
    font-weight: 950;
    letter-spacing: .08em;
}

.brand-sidebar-sub {
    color: #94a3b8;
    font-size: 11px;
    margin-top: 2px;
}

.visual-strip {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 14px;
    margin: 16px 0 26px 0;
}

.visual-tile {
    background: linear-gradient(145deg, #0f172a, #020617);
    border: 1px solid #1e293b;
    border-radius: 18px;
    padding: 16px;
    min-height: 96px;
    box-shadow: 0 10px 25px rgba(0,0,0,.22);
}

.visual-icon {
    font-size: 28px;
    margin-bottom: 6px;
}

.visual-title {
    color: #f8fafc;
    font-size: 15px;
    font-weight: 950;
}

.visual-copy {
    color: #94a3b8;
    font-size: 12px;
    margin-top: 4px;
    line-height: 1.35;
}

.metric-card, .roster-card {
    transition: transform .15s ease, border-color .15s ease, box-shadow .15s ease;
}

.metric-card:hover, .roster-card:hover, .visual-tile:hover {
    transform: translateY(-2px);
    border-color: rgba(56, 189, 248, 0.45);
    box-shadow: 0 14px 34px rgba(14, 165, 233, 0.10);
}

@media (max-width: 900px) {
    .hero-grid {
        grid-template-columns: 1fr;
        text-align: center;
    }
    .hero-logo {
        margin: 0 auto;
    }
    .visual-strip {
        grid-template-columns: 1fr 1fr;
    }
}


/* ============================================================
   MOBILE RESPONSIVE POLISH
   ============================================================ */

.mobile-only {
    display: none;
}

.desktop-only {
    display: block;
}

@media (max-width: 900px) {
    .block-container {
        padding-top: 1rem;
        padding-left: 0.85rem;
        padding-right: 0.85rem;
        max-width: 100%;
    }

    .main-title {
        font-size: 30px;
        line-height: 1.05;
        letter-spacing: -0.045em;
    }

    .sub-title {
        font-size: 14px;
        line-height: 1.45;
        margin-bottom: 12px;
    }

    .hero-wrap {
        padding: 18px 16px;
        border-radius: 20px;
        margin-bottom: 16px;
    }

    .hero-grid {
        grid-template-columns: 1fr;
        gap: 12px;
        text-align: center;
    }

    .hero-logo {
        width: 92px;
        height: 92px;
        margin: 0 auto;
    }

    .hero-eyebrow {
        font-size: 11px;
    }

    .hero-badges {
        justify-content: center;
        gap: 7px;
    }

    .hero-badge {
        font-size: 10px;
        padding: 6px 8px;
    }

    .visual-strip {
        grid-template-columns: 1fr 1fr;
        gap: 10px;
        margin: 12px 0 18px 0;
    }

    .visual-tile {
        padding: 12px;
        min-height: 86px;
        border-radius: 14px;
    }

    .visual-icon {
        font-size: 22px;
    }

    .visual-title {
        font-size: 13px;
    }

    .visual-copy {
        font-size: 10.5px;
    }

    .section-title {
        font-size: 20px;
        margin-top: 10px;
        margin-bottom: 10px;
    }

    .metric-card {
        padding: 13px;
        border-radius: 15px;
        min-height: 82px;
        margin-bottom: 8px;
    }

    .metric-label {
        font-size: 10px;
    }

    .metric-value {
        font-size: 21px;
        white-space: normal;
    }

    .roster-card {
        padding: 11px 12px;
        border-radius: 14px;
        margin-bottom: 8px;
    }

    .roster-slot {
        font-size: 11px;
    }

    .roster-player {
        font-size: 15px;
    }

    .roster-detail {
        font-size: 12px;
        line-height: 1.35;
    }

    .draft-board-note {
        font-size: 12px;
    }

    div[data-testid="stDataFrame"] {
        max-width: 100%;
        overflow-x: auto;
    }

    div[data-testid="stDataFrame"] * {
        font-size: 12px !important;
    }

    div[data-testid="stHorizontalBlock"] {
        gap: 0.75rem;
    }

    .stButton > button {
        width: 100%;
        border-radius: 12px;
        min-height: 42px;
    }

    .stSelectbox, .stMultiSelect, .stTextInput, .stSlider {
        margin-bottom: 8px;
    }

    .report-shell {
        padding: 16px;
        border-radius: 16px;
        line-height: 1.55;
    }

    h1 {
        font-size: 30px !important;
        line-height: 1.12 !important;
    }

    h2 {
        font-size: 24px !important;
    }

    h3 {
        font-size: 20px !important;
    }

    p, li {
        font-size: 15px !important;
        line-height: 1.55 !important;
    }

    .mobile-only {
        display: block;
    }

    .desktop-only {
        display: none;
    }
}

@media (max-width: 560px) {
    .main-title {
        font-size: 26px;
    }

    .hero-logo {
        width: 78px;
        height: 78px;
    }

    .visual-strip {
        grid-template-columns: 1fr;
    }

    .metric-value {
        font-size: 19px;
    }

    .section-title {
        font-size: 18px;
    }

    .roster-player {
        font-size: 14px;
    }

    .roster-detail {
        font-size: 11.5px;
    }

    div[data-testid="stDataFrame"] {
        border-radius: 12px;
    }
}


/* Mobile draft simplification */
.mobile-draft-panel {
    display: none;
}

@media (max-width: 900px) {
    .desktop-draft-board {
        display: none !important;
    }

    .mobile-draft-panel {
        display: block;
        background: linear-gradient(145deg, #0f172a, #020617);
        border: 1px solid #1e293b;
        border-radius: 18px;
        padding: 14px;
        margin-bottom: 16px;
        box-shadow: 0 12px 28px rgba(0,0,0,.24);
    }

    .mobile-draft-title {
        color: #f8fafc;
        font-size: 17px;
        font-weight: 950;
        margin-bottom: 4px;
    }

    .mobile-draft-copy {
        color: #94a3b8;
        font-size: 12px;
        line-height: 1.4;
        margin-bottom: 12px;
    }

    .mobile-player-preview {
        background: #020617;
        border: 1px solid #1e293b;
        border-radius: 14px;
        padding: 11px 12px;
        margin: 10px 0 12px 0;
    }

    .mobile-player-name {
        color: #f8fafc;
        font-size: 16px;
        font-weight: 950;
    }

    .mobile-player-meta {
        color: #94a3b8;
        font-size: 12px;
        margin-top: 3px;
        line-height: 1.35;
    }
}


/* Mobile filters callout */
.mobile-filter-callout {
    display: none;
}

@media (max-width: 900px) {
    .mobile-filter-callout {
        display: block;
        background: linear-gradient(135deg, #0284c7, #0ea5e9);
        color: #ffffff;
        border: 1px solid rgba(186, 230, 253, 0.55);
        border-radius: 16px;
        padding: 14px 16px;
        margin: 0 0 16px 0;
        text-align: center;
        box-shadow: 0 14px 32px rgba(14, 165, 233, 0.25);
    }

    .mobile-filter-title {
        font-size: 16px;
        font-weight: 950;
        letter-spacing: .02em;
        margin-bottom: 3px;
    }

    .mobile-filter-copy {
        font-size: 12px;
        font-weight: 750;
        opacity: .95;
        line-height: 1.35;
    }
}


/* Mobile roster popover helper */
.mobile-roster-callout {
    display: none;
}

@media (max-width: 900px) {
    .mobile-roster-callout {
        display: block;
        background: linear-gradient(135deg, #111827, #0f172a);
        color: #ffffff;
        border: 1px solid rgba(148, 163, 184, 0.35);
        border-radius: 16px;
        padding: 13px 15px;
        margin: 0 0 14px 0;
        text-align: center;
        box-shadow: 0 14px 32px rgba(0, 0, 0, 0.25);
    }

    .mobile-roster-title {
        font-size: 16px;
        font-weight: 950;
        margin-bottom: 3px;
    }

    .mobile-roster-copy {
        font-size: 12px;
        color: #cbd5e1;
        line-height: 1.35;
    }
}


/* Roster popover cards */
.popover-roster-card {
    background: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 16px;
    padding: 12px 14px;
    margin-bottom: 10px;
}

.popover-roster-slot {
    font-size: 12px;
    color: #38bdf8;
    font-weight: 950;
    letter-spacing: .04em;
    text-transform: uppercase;
}

.popover-roster-player {
    font-size: 16px;
    color: #f8fafc;
    font-weight: 900;
    margin-top: 2px;
}

.popover-roster-detail {
    font-size: 13px;
    color: #94a3b8;
    margin-top: 3px;
    line-height: 1.35;
}


.dialog-player-card {
    display: grid;
    grid-template-columns: 58px 1fr;
    gap: 14px;
    align-items: center;
    background: rgba(15, 23, 42, .82);
    border: 1px solid rgba(51, 65, 85, .8);
    border-radius: 18px;
    padding: 14px;
    margin: 12px 0 16px 0;
}

.slot-pill-button-row {
    margin-top: 18px;
}

.empty-info-block {
    padding-top: 16px;
}

.empty-right-block {
    padding-top: 14px;
}

.chev-button-row {
    padding-top: 21px;
}

/* Style the real Streamlit + buttons so they look like the mockup box. */
div[data-testid="stButton"] button:has(p) {
    border-radius: 18px;
}

div[data-testid="stButton"] button p {
    font-weight: 950;
}


</style>
""",
    unsafe_allow_html=True
)


# ============================================================
# DATA
# ============================================================

@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        st.error(f"Missing required columns from CSV: {missing}")
        st.stop()

    # Optional headshot fields. The app works without these,
    # but real NBA headshots will show when HeadshotURL exists.
    if "PLAYER_ID" not in df.columns:
        df["PLAYER_ID"] = ""

    if "HeadshotURL" not in df.columns:
        df["HeadshotURL"] = ""

    df["HeadshotURL"] = df["HeadshotURL"].fillna("").astype(str).str.strip()

    numeric_cols = [
        "Salary", "G", "MP", "PTS", "AST", "TRB", "STL", "BLK", "TOV",
        "FG%", "3P%", "3P", "3PA", "eFG%", "TS%", "PER", "USG%",
        "OBPM", "DBPM", "BPM", "VORP", "Impact_Score", "Value_Score"
    ]

    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    if "3PA" not in df.columns:
        df["3PA"] = 0

    if "3P" not in df.columns:
        df["3P"] = 0

    df["Salary_M"] = df["Salary"] / 1_000_000

    # Clean draft-board display fields
    df["Salary Display"] = df["Salary"].apply(lambda x: f"${x / 1_000_000:.1f}M")
    df["PPG"] = df["PTS"].round(1)
    df["APG"] = df["AST"].round(1)
    df["RPG"] = df["TRB"].round(1)
    df["FG% Display"] = (df["FG%"] * 100).round(1).astype(str) + "%"
    df["3P% Display"] = (df["3P%"] * 100).round(1).astype(str) + "%"
    df["TS% Display"] = (df["TS%"] * 100).round(1).astype(str) + "%"

    df["Display"] = df.apply(
        lambda r: f"{r['Player']} | {r['Team']} | {r['Pos']} | ${r['Salary_M']:.1f}M",
        axis=1
    )

    return df


try:
    df = load_data(DATA_PATH)
except FileNotFoundError:
    try:
        df = load_data(FALLBACK_DATA_PATH)
        st.warning(
            f"`{DATA_PATH}` was not found, so the app loaded `{FALLBACK_DATA_PATH}` instead. "
            "Headshots will only appear if the loaded CSV has a HeadshotURL column."
        )
    except FileNotFoundError:
        st.error(
            f"Could not find `{DATA_PATH}` or `{FALLBACK_DATA_PATH}`. "
            "Put this app file in the same folder as your CSV."
        )
        st.stop()


# ============================================================
# PRESET CURRENT ROSTERS
# ============================================================

PRESET_ROSTERS = {
    'Atlanta': [
        ('Starting PG', 'CJ McCollum'),
        ('Starting SG', 'Nickeil Alexander-Walker'),
        ('Starting SF', 'Dyson Daniels'),
        ('Starting PF', 'Jalen Johnson'),
        ('Starting C', 'Onyeka Okongwu'),
        ('Bench 1', 'Gabe Vincent'),
        ('Bench 2', 'Corey Kispert'),
        ('Bench 3', 'Jonathan Kuminga'),
        ('Bench 4', 'Mouhamed Gueye'),
        ('Bench 5', 'Jock Landale'),
        ('Bench 6', 'Zaccharie Risacher'),
        ('Two-Way 1', 'Keaton Wallace'),
        ('Two-Way 2', 'Asa Newell'),
        ('Bench 7', 'Tony Bradley'),
        ('Bench 8', 'Buddy Hield'),
    ],
    'Boston': [
        ('Starting PG', 'Derrick White'),
        ('Starting SG', 'Jaylen Brown'),
        ('Starting SF', 'Sam Hauser'),
        ('Starting PF', 'Jayson Tatum'),
        ('Starting C', 'Neemias Queta'),
        ('Bench 1', 'Payton Pritchard'),
        ('Bench 2', 'Baylor Scheierman'),
        ('Bench 3', 'Jordan Walsh'),
        ('Bench 4', 'Nikola Vucevic'),
        ('Bench 5', 'Dalano Banton'),
        ('Bench 6', 'Hugo Gonzalez'),
        ('Two-Way 1', 'Luka Garza'),
        ('Two-Way 2', 'Max Shulga'),
        ('Bench 7', 'Ron Harper Jr.'),
        ('Bench 8', 'Amari Williams'),
    ],
    'Brooklyn': [
        ('Starting PG', 'Egor Demin'),
        ('Starting SG', 'Drake Powell'),
        ('Starting SF', 'Michael Porter Jr.'),
        ('Starting PF', 'Noah Clowney'),
        ('Starting C', 'Nic Claxton'),
        ('Bench 1', 'Ben Saraf'),
        ('Bench 2', 'Terance Mann'),
        ('Bench 3', 'Ziaire Williams'),
        ('Bench 4', 'Danny Wolf'),
        ('Bench 5', "Day'Ron Sharpe"),
        ('Bench 6', 'Nolan Traore'),
        ('Two-Way 1', 'Josh Minott'),
        ('Two-Way 2', 'Tyson Etienne'),
        ('Bench 7', 'Malachi Smith'),
        ('Bench 8', 'Jalen Wilson'),
    ],
    'Charlotte': [
        ('Starting PG', 'LaMelo Ball'),
        ('Starting SG', 'Kon Knueppel'),
        ('Starting SF', 'Brandon Miller'),
        ('Starting PF', 'Miles Bridges'),
        ('Starting C', 'Moussa Diabate'),
        ('Bench 1', 'Coby White'),
        ('Bench 2', 'Josh Green'),
        ('Bench 3', 'Sion James'),
        ('Bench 4', 'Grant Williams'),
        ('Bench 5', 'Ryan Kalkbrenner'),
        ('Bench 6', 'Tre Mann'),
        ('Two-Way 1', 'Tidjane Salaun'),
        ('Two-Way 2', 'Xavier Tillman'),
        ('Bench 7', 'Liam McNeeley'),
        ('Bench 8', 'PJ Hall'),
    ],
    'Chicago': [
        ('Starting PG', 'Josh Giddey'),
        ('Starting SG', 'Tre Jones'),
        ('Starting SF', 'Isaac Okoro'),
        ('Starting PF', 'Matas Buzelis'),
        ('Starting C', 'Jalen Smith'),
        ('Bench 1', 'Rob Dillingham'),
        ('Bench 2', 'Collin Sexton'),
        ('Bench 3', 'Leonard Miller'),
        ('Bench 4', 'Patrick Williams'),
        ('Bench 5', 'Zach Collins'),
        ('Bench 6', 'Anfernee Simons'),
        ('Two-Way 1', 'Guerschon Yabusele'),
        ('Two-Way 2', 'Nick Richards'),
        ('Bench 7', 'Noa Essengue'),
        ('Bench 8', 'Lachlan Olbrich'),
    ],
    'Cleveland': [
        ('Starting PG', 'James Harden'),
        ('Starting SG', 'Donovan Mitchell'),
        ('Starting SF', 'Max Strus'),
        ('Starting PF', 'Evan Mobley'),
        ('Starting C', 'Jarrett Allen'),
        ('Bench 1', 'Dennis Schroder'),
        ('Bench 2', 'Sam Merrill'),
        ('Bench 3', 'Jaylon Tyson'),
        ('Bench 4', 'Dean Wade'),
        ('Bench 5', 'Craig Porter Jr.'),
        ('Bench 6', 'Keon Ellis'),
        ('Two-Way 1', "Nae'Qwan Tomlin"),
        ('Two-Way 2', 'Thomas Bryant'),
        ('Bench 7', 'Tyrese Proctor'),
        ('Bench 8', 'Larry Nance Jr.'),
    ],
    'Dallas': [
        ('Starting PG', 'Kyrie Irving'),
        ('Starting SG', 'Max Christie'),
        ('Starting SF', 'Cooper Flagg'),
        ('Starting PF', 'PJ Washington'),
        ('Starting C', 'Dereck Lively II'),
        ('Bench 1', 'Brandon Williams'),
        ('Bench 2', 'Naji Marshall'),
        ('Bench 3', 'Klay Thompson'),
        ('Bench 4', 'Khris Middleton'),
        ('Bench 5', 'Daniel Gafford'),
        ('Bench 6', 'Ryan Nembhard'),
        ('Two-Way 1', 'Caleb Martin'),
        ('Two-Way 2', 'Marvin Bagley III'),
        ('Bench 7', 'John Poulakidas'),
        ('Bench 8', 'Moussa Cisse'),
    ],
    'Denver': [
        ('Starting PG', 'Jamal Murray'),
        ('Starting SG', 'Christian Braun'),
        ('Starting SF', 'Cameron Johnson'),
        ('Starting PF', 'Aaron Gordon'),
        ('Starting C', 'Nikola Jokic'),
        ('Bench 1', 'Bruce Brown'),
        ('Bench 2', 'Tim Hardaway Jr.'),
        ('Bench 3', 'Peyton Watson'),
        ('Bench 4', 'Spencer Jones'),
        ('Bench 5', 'Tyus Jones'),
        ('Bench 6', 'Julian Strawther'),
        ('Two-Way 1', 'Jonas Valanciunas'),
        ('Two-Way 2', 'Jalen Pickett'),
        ('Bench 7', 'Zeke Nnaji'),
        ('Bench 8', 'KJ Simpson'),
    ],
    'Detroit': [
        ('Starting PG', 'Cade Cunningham'),
        ('Starting SG', 'Duncan Robinson'),
        ('Starting SF', 'Ausar Thompson'),
        ('Starting PF', 'Tobias Harris'),
        ('Starting C', 'Jalen Duren'),
        ('Bench 1', 'Daniss Jenkins'),
        ('Bench 2', 'Caris LeVert'),
        ('Bench 3', 'Isaiah Stewart'),
        ('Bench 4', 'Marcus Sasser'),
        ('Bench 5', 'Javonte Green'),
        ('Bench 6', 'Paul Reed'),
        ('Two-Way 1', 'Kevin Huerter'),
        ('Two-Way 2', 'Ron Holland'),
        ('Bench 7', 'Tyler Smith'),
        ('Bench 8', 'Isaac Jones'),
    ],
    'Golden State': [
        ('Starting PG', 'Stephen Curry'),
        ('Starting SG', 'Brandin Podziemski'),
        ('Starting SF', 'Gui Santos'),
        ('Starting PF', 'Draymond Green'),
        ('Starting C', 'Kristaps Porzingis'),
        ('Bench 1', 'Gary Payton II'),
        ('Bench 2', "De'Anthony Melton"),
        ('Bench 3', 'Al Horford'),
        ('Bench 4', 'Pat Spencer'),
        ('Bench 5', 'Will Richard'),
        ('Bench 6', 'Charles Bassey'),
        ('Two-Way 1', 'LJ Cryer'),
        ('Two-Way 2', 'Malevy Leons'),
        ('Bench 7', 'Quinten Post'),
        ('Bench 8', 'Nate Williams'),
    ],
    'Houston': [
        ('Starting PG', 'Fred VanVleet'),
        ('Starting SG', 'Amen Thompson'),
        ('Starting SF', 'Kevin Durant'),
        ('Starting PF', 'Jabari Smith Jr.'),
        ('Starting C', 'Alperen Sengun'),
        ('Bench 1', 'Reed Sheppard'),
        ('Bench 2', 'Tari Eason'),
        ('Bench 3', 'Dorian Finney-Smith'),
        ('Bench 4', 'Steven Adams'),
        ('Bench 5', 'Aaron Holiday'),
        ('Bench 6', 'Josh Okogie'),
        ('Two-Way 1', "Jae'Sean Tate"),
        ('Two-Way 2', 'Clint Capela'),
        ('Bench 7', 'JD Davison'),
        ('Bench 8', 'Jeff Green'),
    ],
    'Indiana': [
        ('Starting PG', 'Tyrese Haliburton'),
        ('Starting SG', 'Andrew Nembhard'),
        ('Starting SF', 'Aaron Nesmith'),
        ('Starting PF', 'Pascal Siakam'),
        ('Starting C', 'Ivica Zubac'),
        ('Bench 1', 'TJ McConnell'),
        ('Bench 2', 'Ben Sheppard'),
        ('Bench 3', 'Jarace Walker'),
        ('Bench 4', 'Obi Toppin'),
        ('Bench 5', 'Micah Potter'),
        ('Bench 6', 'Johnny Furphy'),
        ('Two-Way 1', 'Kobe Brown'),
        ('Two-Way 2', 'Jay Huff'),
        ('Bench 7', 'Quenton Jackson'),
        ('Bench 8', 'Kam Jones'),
    ],
    'LA Clippers': [
        ('Starting PG', 'Darius Garland'),
        ('Starting SG', 'Kris Dunn'),
        ('Starting SF', 'Kawhi Leonard'),
        ('Starting PF', 'Derrick Jones Jr.'),
        ('Starting C', 'Brook Lopez'),
        ('Bench 1', 'Jordan Miller'),
        ('Bench 2', 'Bennedict Mathurin'),
        ('Bench 3', 'Kobe Sanders'),
        ('Bench 4', 'John Collins'),
        ('Bench 5', 'Isaiah Jackson'),
        ('Bench 6', 'Nicolas Batum'),
        ('Two-Way 1', 'Yanic Konan Niederhauser'),
        ('Two-Way 2', 'Bogdan Bogdanovic'),
        ('Bench 7', 'Norchad Omier'),
        ('Bench 8', 'TyTy Washington Jr.'),
    ],
    'LA Lakers': [
        ('Starting PG', 'Luka Doncic'),
        ('Starting SG', 'Austin Reaves'),
        ('Starting SF', 'Marcus Smart'),
        ('Starting PF', 'LeBron James'),
        ('Starting C', 'Deandre Ayton'),
        ('Bench 1', 'Luke Kennard'),
        ('Bench 2', 'Rui Hachimura'),
        ('Bench 3', 'Jarred Vanderbilt'),
        ('Bench 4', 'Jaxson Hayes'),
        ('Bench 5', 'Jake LaRavia'),
        ('Bench 6', 'Maxi Kleber'),
        ('Two-Way 1', 'Bronny James'),
        ('Two-Way 2', 'Adou Thiero'),
        ('Bench 7', 'Drew Timme'),
        ('Bench 8', 'Nick Smith Jr.'),
    ],
    'Memphis': [
        ('Starting PG', 'Ja Morant'),
        ('Starting SG', 'Cedric Coward'),
        ('Starting SF', 'Jaylen Wells'),
        ('Starting PF', 'Santi Aldama'),
        ('Starting C', 'Zach Edey'),
        ('Bench 1', 'Scotty Pippen Jr.'),
        ('Bench 2', 'Ty Jerome'),
        ('Bench 3', 'Kentavious Caldwell-Pope'),
        ('Bench 4', 'Taylor Hendricks'),
        ('Bench 5', 'Olivier-Maxence Prosper'),
        ('Bench 6', 'Javon Small'),
        ('Two-Way 1', 'GG Jackson II'),
        ('Two-Way 2', 'Walter Clayton Jr.'),
        ('Bench 7', 'Cam Spencer'),
        ('Bench 8', 'Rayan Rupert'),
    ],
    'Miami': [
        ('Starting PG', 'Davion Mitchell'),
        ('Starting SG', 'Tyler Herro'),
        ('Starting SF', 'Norman Powell'),
        ('Starting PF', 'Andrew Wiggins'),
        ('Starting C', 'Bam Adebayo'),
        ('Bench 1', 'Kasparas Jakucionis'),
        ('Bench 2', 'Pelle Larsson'),
        ('Bench 3', 'Jaime Jaquez Jr.'),
        ('Bench 4', 'Simone Fontecchio'),
        ('Bench 5', "Kel'el Ware"),
        ('Bench 6', 'Dru Smith'),
        ('Two-Way 1', 'Nikola Jovic'),
        ('Two-Way 2', 'Keshad Johnson'),
        ('Bench 7', 'Myron Gardner'),
    ],
    'Milwaukee': [
        ('Starting PG', 'Ryan Rollins'),
        ('Starting SG', 'Kevin Porter Jr.'),
        ('Starting SF', 'Kyle Kuzma'),
        ('Starting PF', 'Giannis Antetokounmpo'),
        ('Starting C', 'Myles Turner'),
        ('Bench 1', 'AJ Green'),
        ('Bench 2', 'Ousmane Dieng'),
        ('Bench 3', 'Bobby Portis'),
        ('Bench 4', 'Jericho Sims'),
        ('Bench 5', 'Cormac Ryan'),
        ('Bench 6', 'Gary Trent Jr.'),
        ('Two-Way 1', 'Taurean Prince'),
        ('Two-Way 2', 'Pete Nance'),
        ('Bench 7', 'Thanasis Antetokounmpo'),
        ('Bench 8', 'Gary Harris'),
    ],
    'Minnesota': [
        ('Starting PG', 'Ayo Dosunmu'),
        ('Starting SG', 'Anthony Edwards'),
        ('Starting SF', 'Jaden McDaniels'),
        ('Starting PF', 'Julius Randle'),
        ('Starting C', 'Rudy Gobert'),
        ('Bench 1', 'Mike Conley'),
        ('Bench 2', 'Terrence Shannon Jr.'),
        ('Bench 3', 'Naz Reid'),
        ('Bench 4', 'Bones Hyland'),
        ('Bench 5', 'Jaylen Clark'),
        ('Bench 6', 'Kyle Anderson'),
        ('Two-Way 1', 'Joan Beringer'),
        ('Two-Way 2', 'Zyon Pullin'),
        ('Bench 7', 'Julian Phillips'),
        ('Bench 8', 'Rocco Zikarsky'),
    ],
    'New Orleans': [
        ('Starting PG', 'Dejounte Murray'),
        ('Starting SG', 'Trey Murphy III'),
        ('Starting SF', 'Saddiq Bey'),
        ('Starting PF', 'Zion Williamson'),
        ('Starting C', 'Herbert Jones'),
        ('Bench 1', 'Jeremiah Fears'),
        ('Bench 2', 'Derik Queen'),
        ('Bench 3', 'Yves Missi'),
        ('Bench 4', 'Trey Alexander'),
        ('Bench 5', 'Jordan Hawkins'),
        ('Bench 6', 'Micah Peavy'),
        ('Two-Way 1', 'Karlo Matkovic'),
        ('Two-Way 2', 'Jordan Poole'),
        ('Bench 7', 'Bryce McGowens'),
        ('Bench 8', 'Kevon Looney'),
    ],
    'New York': [
        ('Starting PG', 'Jalen Brunson'),
        ('Starting SG', 'Josh Hart'),
        ('Starting SF', 'Mikal Bridges'),
        ('Starting PF', 'OG Anunoby'),
        ('Starting C', 'Karl-Anthony Towns'),
        ('Bench 1', 'Miles McBride'),
        ('Bench 2', 'Landry Shamet'),
        ('Bench 3', 'Jordan Clarkson'),
        ('Bench 4', 'Mitchell Robinson'),
        ('Bench 5', 'Jose Alvarado'),
        ('Bench 6', 'Mohamed Diawara'),
        ('Two-Way 1', 'Ariel Hukporti'),
        ('Two-Way 2', 'Tyler Kolek'),
        ('Bench 7', 'Jeremy Sochan'),
        ('Bench 8', 'Pacome Dadiet'),
    ],
    'Oklahoma City': [
        ('Starting PG', 'Shai Gilgeous-Alexander'),
        ('Starting SG', 'Luguentz Dort'),
        ('Starting SF', 'Jalen Williams'),
        ('Starting PF', 'Chet Holmgren'),
        ('Starting C', 'Isaiah Hartenstein'),
        ('Bench 1', 'Ajay Mitchell'),
        ('Bench 2', 'Jared McCain'),
        ('Bench 3', 'Cason Wallace'),
        ('Bench 4', 'Alex Caruso'),
        ('Bench 5', 'Kenrich Williams'),
        ('Bench 6', 'Jaylin Williams'),
        ('Two-Way 1', 'Isaiah Joe'),
        ('Two-Way 2', 'Aaron Wiggins'),
        ('Bench 7', 'Branden Carlson'),
        ('Bench 8', 'Nikola Topic'),
    ],
    'Orlando': [
        ('Starting PG', 'Jalen Suggs'),
        ('Starting SG', 'Desmond Bane'),
        ('Starting SF', 'Franz Wagner'),
        ('Starting PF', 'Paolo Banchero'),
        ('Starting C', 'Wendell Carter Jr.'),
        ('Bench 1', 'Anthony Black'),
        ('Bench 2', 'Jamal Cain'),
        ('Bench 3', 'Tristan Da Silva'),
        ('Bench 4', 'Goga Bitadze'),
        ('Bench 5', 'Jevon Carter'),
        ('Bench 6', 'Jett Howard'),
        ('Two-Way 1', 'Jonathan Isaac'),
        ('Two-Way 2', 'Moritz Wagner'),
        ('Bench 7', 'Jase Richardson'),
        ('Bench 8', 'Noah Penda'),
    ],
    'Philadelphia': [
        ('Starting PG', 'Tyrese Maxey'),
        ('Starting SG', 'VJ Edgecombe'),
        ('Starting SF', 'Kelly Oubre Jr.'),
        ('Starting PF', 'Paul George'),
        ('Starting C', 'Joel Embiid'),
        ('Bench 1', 'Quentin Grimes'),
        ('Bench 2', 'Dominick Barlow'),
        ('Bench 3', 'Andre Drummond'),
        ('Bench 4', 'Justin Edwards'),
        ('Bench 5', 'Adem Bona'),
        ('Bench 6', 'Kyle Lowry'),
        ('Two-Way 1', 'Dalen Terry'),
        ('Two-Way 2', 'Jabari Walker'),
        ('Bench 7', 'Trendon Watford'),
        ('Bench 8', 'Tyrese Martin'),
    ],
    'Phoenix': [
        ('Starting PG', 'Devin Booker'),
        ('Starting SG', 'Jalen Green'),
        ('Starting SF', 'Jordan Goodwin'),
        ('Starting PF', 'Dillon Brooks'),
        ('Starting C', 'Mark Williams'),
        ('Bench 1', 'Collin Gillespie'),
        ('Bench 2', 'Grayson Allen'),
        ('Bench 3', "Royce O'Neale"),
        ('Bench 4', 'Oso Ighodaro'),
        ('Bench 5', 'Jamaree Bouyea'),
        ('Bench 6', 'Haywood Highsmith'),
        ('Two-Way 1', 'Ryan Dunn'),
        ('Two-Way 2', 'Khaman Maluach'),
        ('Bench 7', 'Rasheer Fleming'),
        ('Bench 8', 'Amir Coffey'),
    ],
    'Portland': [
        ('Starting PG', 'Scoot Henderson'),
        ('Starting SG', 'Jrue Holiday'),
        ('Starting SF', 'Toumani Camara'),
        ('Starting PF', 'Deni Avdija'),
        ('Starting C', 'Donovan Clingan'),
        ('Bench 1', 'Shaedon Sharpe'),
        ('Bench 2', 'Matisse Thybulle'),
        ('Bench 3', 'Jerami Grant'),
        ('Bench 4', 'Robert Williams'),
        ('Bench 5', 'Kris Murray'),
        ('Bench 6', 'Sidy Cissoko'),
        ('Two-Way 1', 'Blake Wesley'),
        ('Two-Way 2', 'Vit Krejci'),
        ('Bench 7', 'Yang Hansen'),
        ('Bench 8', 'Damian Lillard'),
    ],
    'Sacramento': [
        ('Starting PG', 'Russell Westbrook'),
        ('Starting SG', 'Zach LaVine'),
        ('Starting SF', 'DeMar DeRozan'),
        ('Starting PF', 'Keegan Murray'),
        ('Starting C', 'Domantas Sabonis'),
        ('Bench 1', 'Malik Monk'),
        ('Bench 2', 'Nique Clifford'),
        ('Bench 3', "De'Andre Hunter"),
        ('Bench 4', 'Precious Achiuwa'),
        ('Bench 5', 'Maxime Raynaud'),
        ('Bench 6', 'Devin Carter'),
        ('Two-Way 1', 'Dylan Cardwell'),
        ('Two-Way 2', 'Killian Hayes'),
        ('Bench 7', 'Daeqwon Plowden'),
        ('Bench 8', 'Drew Eubanks'),
    ],
    'San Antonio': [
        ('Starting PG', "De'Aaron Fox"),
        ('Starting SG', 'Stephon Castle'),
        ('Starting SF', 'Devin Vassell'),
        ('Starting PF', 'Julian Champagnie'),
        ('Starting C', 'Victor Wembanyama'),
        ('Bench 1', 'Dylan Harper'),
        ('Bench 2', 'Keldon Johnson'),
        ('Bench 3', 'Carter Bryant'),
        ('Bench 4', 'Harrison Barnes'),
        ('Bench 5', 'Luke Kornet'),
        ('Bench 6', 'Jordan McLaughlin'),
        ('Two-Way 1', 'Mason Plumlee'),
        ('Two-Way 2', 'David Jones Garcia'),
        ('Bench 7', 'Lindy Waters III'),
        ('Bench 8', 'Kelly Olynyk'),
    ],
    'Toronto': [
        ('Starting PG', 'Immanuel Quickley'),
        ('Starting SG', 'Brandon Ingram'),
        ('Starting SF', 'RJ Barrett'),
        ('Starting PF', 'Scottie Barnes'),
        ('Starting C', 'Jakob Poeltl'),
        ('Bench 1', 'Jamal Shead'),
        ('Bench 2', "Ja'Kobe Walter"),
        ('Bench 3', 'Jamison Battle'),
        ('Bench 4', 'Collin Murray-Boyles'),
        ('Bench 5', 'Sandro Mamukelashvili'),
        ('Bench 6', 'A.J. Lawson'),
        ('Two-Way 1', 'Gradey Dick'),
        ('Two-Way 2', 'Jonathan Mogbo'),
        ('Bench 7', 'Trayce Jackson-Davis'),
        ('Bench 8', 'Chucky Hepburn'),
    ],
    'Utah': [
        ('Starting PG', 'Keyonte George'),
        ('Starting SG', 'Ace Bailey'),
        ('Starting SF', 'Lauri Markkanen'),
        ('Starting PF', 'Jaren Jackson Jr.'),
        ('Starting C', 'Walker Kessler'),
        ('Bench 1', 'Isaiah Collier'),
        ('Bench 2', 'Cody Williams'),
        ('Bench 3', 'Brice Sensabaugh'),
        ('Bench 4', 'Kyle Filipowski'),
        ('Bench 5', 'Jusuf Nurkic'),
        ('Bench 6', 'Elijah Harkless'),
        ('Two-Way 1', 'John Konchar'),
        ('Two-Way 2', 'Bez Mbeng'),
        ('Bench 7', 'Kevin Love'),
        ('Bench 8', 'Blake Hinson'),
    ],
    'Washington': [
        ('Starting PG', 'Trae Young'),
        ('Starting SG', 'Kyshawn George'),
        ('Starting SF', 'Bilal Coulibaly'),
        ('Starting PF', 'Anthony Davis'),
        ('Starting C', 'Alex Sarr'),
        ('Bench 1', 'Bub Carrington'),
        ('Bench 2', 'Tre Johnson'),
        ('Bench 3', 'Will Riley'),
        ('Bench 4', 'Justin Champagnie'),
        ('Bench 5', 'Tristan Vukcevic'),
        ('Bench 6', 'Sharife Cooper'),
        ('Two-Way 1', 'Jaden Hardy'),
        ('Two-Way 2', 'Cam Whitmore'),
        ('Bench 7', "D'Angelo Russell"),
        ('Bench 8', 'Jamir Watkins'),
    ],
}


def normalize_name_for_match(name: str) -> str:
    return (
        str(name)
        .lower()
        .replace(".", "")
        .replace("'", "")
        .replace("’", "")
        .replace("-", " ")
        .replace("ć", "c")
        .replace("č", "c")
        .replace("š", "s")
        .replace("ž", "z")
        .replace("ģ", "g")
        .replace("ņ", "n")
        .replace("ā", "a")
        .replace("í", "i")
        .replace("é", "e")
        .replace("è", "e")
        .replace("ö", "o")
        .replace("ü", "u")
        .strip()
    )


def find_player_row(player_name: str, player_df: pd.DataFrame):
    """
    Presets now use full player names from NBA Depth Chart FullNames Latin.csv.
    Exact full-name matching is prioritized so players with shared initials/last names
    no longer get mixed up.
    """
    target = normalize_name_for_match(player_name)
    normalized = player_df["Player"].apply(normalize_name_for_match)

    # Exact full-name match.
    exact = player_df[normalized == target]
    if len(exact) > 0:
        return exact.iloc[0]

    # Safe containment fallback for punctuation/accent differences.
    contains = player_df[normalized.str.contains(target, na=False) | normalized.apply(lambda x: target in x)]
    if len(contains) > 0:
        if "MP" in contains.columns:
            return contains.sort_values("MP", ascending=False).iloc[0]
        return contains.iloc[0]

    # Last-name fallback only when unique.
    parts = target.split()
    if len(parts) >= 2:
        last = parts[-1]
        last_matches = player_df[normalized.apply(lambda x: len(x.split()) > 0 and x.split()[-1] == last)]
        if len(last_matches) == 1:
            return last_matches.iloc[0]

    return None


def load_preset_roster(preset_name: str, roster_size: int, player_df: pd.DataFrame):
    loaded = {}
    missing = []

    for slot, player_name in PRESET_ROSTERS[preset_name][:roster_size]:
        row = find_player_row(player_name, player_df)

        if row is None:
            missing.append(player_name)
            continue

        player = row.to_dict()
        player["Slot"] = slot

        fit, notes = calculate_position_fit(pd.Series(player), slot)
        player["Fit_Adjustment"] = fit
        player["Fit_Notes"] = "; ".join(notes)

        loaded[slot] = player

    return loaded, missing



# ============================================================
# BASIC HELPERS
# ============================================================

def money(x) -> str:
    try:
        return f"${float(x) / 1_000_000:.1f}M"
    except Exception:
        return "$0.0M"


def pct(x) -> str:
    try:
        return f"{float(x) * 100:.1f}%"
    except Exception:
        return "0.0%"


def normalize(value, low, high) -> float:
    if high == low:
        return 50.0
    return max(0.0, min(100.0, ((value - low) / (high - low)) * 100.0))


def score_to_grade(score: float) -> str:
    if score >= 97:
        return "A+"
    if score >= 92:
        return "A"
    if score >= 87:
        return "A-"
    if score >= 82:
        return "B+"
    if score >= 77:
        return "B"
    if score >= 72:
        return "B-"
    if score >= 67:
        return "C+"
    if score >= 62:
        return "C"
    return "D"



def wins_to_grade(wins: int) -> str:
    if wins >= 78:
        return "A+"
    if wins >= 70:
        return "A"
    if wins >= 62:
        return "A-"
    if wins >= 55:
        return "B+"
    if wins >= 50:
        return "B"
    if wins >= 45:
        return "B-"
    if wins >= 40:
        return "C+"
    if wins >= 35:
        return "C"
    return "D"


def get_slot_role(slot: str) -> str:
    if slot == "Starting PG":
        return "PG"
    if slot == "Starting SG":
        return "SG"
    if slot == "Starting SF":
        return "SF"
    if slot == "Starting PF":
        return "PF"
    if slot == "Starting C":
        return "C"
    if "Two-Way" in slot:
        return "TWO_WAY"
    return "BENCH"


# ============================================================
# ARCHETYPES / FIT ENGINE
# ============================================================

def is_floor_spacer(row) -> bool:
    return row["3P%"] >= 0.37 and row["3PA"] >= 4


def is_reliable_shooter(row) -> bool:
    return row["3P%"] >= 0.35 and row["3PA"] >= 3


def is_point_forward(row) -> bool:
    return row["Pos"] in ["SF", "PF", "C"] and row["AST"] >= 4.5 and row["BPM"] >= 2


def is_small_ball_forward(row) -> bool:
    # No height column needed: rebounding + defensive value + wing/guard classification.
    return (
        row["Pos"] in ["SG", "SF"] and
        row["TRB"] >= 6.5 and
        row["DBPM"] >= 0.5
    )


def is_big_with_guard_skills(row) -> bool:
    return row["Pos"] in ["PF", "C"] and row["AST"] >= 4.0 and row["OBPM"] >= 1.5


def custom_defense_score(row) -> float:
    """
    Defensive model that balances:
    - production: steals, blocks, rebounds
    - advanced signal: DBPM
    - role context: wing stopper, rim protector, guard defender
    - minutes: avoids low-minute players winning best defender
    - manual real-world correction for elite defenders

    This prevents DBPM/rebounding-only cases like Jokic beating Kawhi/Giannis
    as the best defender on a stacked roster.
    """
    name = str(row["Player"]).lower()
    pos = str(row["Pos"])
    mp = float(row.get("MP", 0))
    dbpm = float(row.get("DBPM", 0))
    stl = float(row.get("STL", 0))
    blk = float(row.get("BLK", 0))
    trb = float(row.get("TRB", 0))

    # Base production/advanced blend
    score = (
        dbpm * 4.5 +
        stl * 5.0 +
        blk * 5.5 +
        trb * 0.60 +
        mp * 0.18
    )

    # Defensive role bonuses
    if pos in ["SG", "SF"] and stl >= 1.2 and mp >= 24:
        score += 5.0  # wing/POA stopper signal

    if pos in ["PF", "C"] and blk >= 1.2 and trb >= 7:
        score += 5.5  # rim protector / backline signal

    if pos in ["PF", "C"] and stl >= 1.0 and blk >= 1.0:
        score += 3.5  # versatile frontcourt disruption

    if pos in ["PG", "SG"] and stl >= 1.2 and dbpm >= 0:
        score += 3.0  # guard pressure

    # Minutes reliability: prevent low-minute defensive noise
    if mp < 15:
        score -= 10
    elif mp < 20:
        score -= 5

    # Real-world defender correction
    elite_defender_bonus = {
        "victor wembanyama": 12.0,
        "anthony davis": 10.5,
        "giannis antetokounmpo": 10.0,
        "kawhi leonard": 10.0,
        "bam adebayo": 9.5,
        "rudy gobert": 9.5,
        "jrue holiday": 8.5,
        "alex caruso": 8.0,
        "evan mobley": 8.0,
        "jaden mcdaniels": 7.5,
        "herb jones": 7.5,
        "og anunoby": 7.5,
        "draymond green": 7.0,
        "jarrett allen": 6.5,
        "lu dort": 6.5,
        "isaac okoro": 5.0,
        "derrick white": 5.5,
        "jaylen brown": 4.0,
    }

    for player_name, bonus in elite_defender_bonus.items():
        if player_name in name:
            score += bonus
            break

    # Jokic is smart and strong defensively, but he should not be treated as a
    # better pure defender than elite stoppers/rim protectors.
    if "nikola jokic" in name:
        score -= 8.0

    return round(score, 2)


def defender_leader_score(row) -> float:
    """
    Used only for the 'Best Defender' card.
    This values actual defensive responsibility and minutes more than box-score noise.
    """
    name = str(row["Player"]).lower()
    pos = str(row["Pos"])
    score = custom_defense_score(row)

    score += float(row.get("MP", 0)) * 0.35
    score += float(row.get("STL", 0)) * 3.5
    score += float(row.get("BLK", 0)) * 4.0
    score += float(row.get("TRB", 0)) * 0.75

    # Prefer proven defensive archetypes.
    if pos in ["SF", "PF"] and float(row.get("MP", 0)) >= 25:
        score += 4.0
    if pos == "C" and float(row.get("BLK", 0)) >= 1.0:
        score += 4.0

    # Strong manual leader boost for known top defenders.
    leader_bonus = {
        "victor wembanyama": 15,
        "anthony davis": 13,
        "giannis antetokounmpo": 12,
        "kawhi leonard": 12,
        "bam adebayo": 11,
        "rudy gobert": 11,
        "jrue holiday": 9,
        "alex caruso": 9,
        "evan mobley": 9,
        "og anunoby": 8,
        "herb jones": 8,
        "jaden mcdaniels": 8,
        "lu dort": 7,
    }

    for player_name, bonus in leader_bonus.items():
        if player_name in name:
            score += bonus
            break

    if "nikola jokic" in name:
        score -= 12

    return round(score, 2)


def calculate_position_fit(row, slot: str) -> tuple[int, list[str]]:
    """
    Allows any player at any slot, then rewards or penalizes fit.
    Fit range is capped from -12 to +12.
    """
    slot_role = get_slot_role(slot)
    pos = row["Pos"]

    ast = float(row["AST"])
    trb = float(row["TRB"])
    stl = float(row["STL"])
    blk = float(row["BLK"])
    three_pct = float(row["3P%"])
    three_pa = float(row["3PA"])
    ts = float(row["TS%"])
    obpm = float(row["OBPM"])
    dbpm = float(row["DBPM"])
    bpm = float(row["BPM"])
    pts = float(row["PTS"])
    tov = float(row["TOV"])

    fit = 0
    notes = []

    # ----------------------------
    # STARTING PG
    # ----------------------------
    if slot_role == "PG":
        if ast >= 7:
            fit += 5
            notes.append("elite lead-guard playmaking")
        elif ast >= 5:
            fit += 3
            notes.append("strong creation for PG duties")
        elif ast < 3:
            fit -= 6
            notes.append("low assist profile for a lead guard")

        if obpm >= 3:
            fit += 3
            notes.append("high-end offensive engine")

        if is_point_forward(row):
            fit += 4
            notes.append("point-forward boost")

        if is_big_with_guard_skills(row):
            fit += 2
            notes.append("big with unusual passing skill")

        if pos == "C" and ast < 4:
            fit -= 9
            notes.append("center with limited guard skills at PG")

        if pos in ["PF", "C"] and three_pct < 0.32 and three_pa >= 1.5:
            fit -= 3
            notes.append("spacing concern at PG")

        if tov >= 3.5 and ast < 6:
            fit -= 2
            notes.append("turnover concern for lead-handler role")

    # ----------------------------
    # STARTING SG
    # ----------------------------
    elif slot_role == "SG":
        if is_floor_spacer(row):
            fit += 5
            notes.append("elite shooting guard spacing")
        elif is_reliable_shooter(row):
            fit += 3
            notes.append("reliable wing shooting")

        if pts >= 20:
            fit += 3
            notes.append("high-level scoring punch")
        elif pts >= 15:
            fit += 2
            notes.append("secondary scoring")

        if obpm >= 2:
            fit += 2
            notes.append("positive offensive creation")

        if three_pct < 0.32 and three_pa >= 2:
            fit -= 5
            notes.append("poor shooting fit at SG")

        if pos == "C":
            fit -= 8
            notes.append("center playing far out of position at SG")

        if pos == "PF" and ast < 3 and three_pa < 2:
            fit -= 5
            notes.append("limited guard skill fit at SG")

    # ----------------------------
    # STARTING SF
    # ----------------------------
    elif slot_role == "SF":
        if bpm >= 3:
            fit += 3
            notes.append("high-impact wing fit")
        if dbpm >= 1:
            fit += 2
            notes.append("plus defensive wing profile")
        if is_reliable_shooter(row):
            fit += 2
            notes.append("keeps spacing viable at SF")
        if pts >= 18:
            fit += 2
            notes.append("strong wing scoring")

        if pos == "PG" and dbpm < 0 and trb < 5:
            fit -= 5
            notes.append("small guard size/defense concern at SF")

        if pos == "C" and three_pa < 2 and ast < 4:
            fit -= 5
            notes.append("limited perimeter skill at SF")

    # ----------------------------
    # STARTING PF
    # ----------------------------
    elif slot_role == "PF":
        if trb >= 7:
            fit += 3
            notes.append("strong forward rebounding")
        if dbpm >= 1:
            fit += 3
            notes.append("plus frontcourt defense")
        if ts >= 0.60:
            fit += 2
            notes.append("efficient frontcourt scoring")

        if is_small_ball_forward(row):
            fit += 4
            notes.append("small-ball PF rebounding/defense boost")

        if pos == "SF" and trb >= 6 and dbpm >= 0.5:
            fit += 2
            notes.append("wing-to-PF versatility")

        if pos == "PG":
            fit -= 7
            notes.append("small guard playing PF")
        elif pos == "SG" and not is_small_ball_forward(row):
            fit -= 4
            notes.append("guard lacks PF rebounding/defensive profile")

        if trb < 5 and pos in ["PG", "SG"]:
            fit -= 4
            notes.append("low rebounding for PF role")

    # ----------------------------
    # STARTING C
    # ----------------------------
    elif slot_role == "C":
        if trb >= 9:
            fit += 5
            notes.append("elite center rebounding")
        elif trb >= 7:
            fit += 3
            notes.append("solid center rebounding")

        if blk >= 1.5:
            fit += 4
            notes.append("strong rim protection")
        elif blk >= 1.0:
            fit += 2
            notes.append("useful shot blocking")

        if dbpm >= 1.5:
            fit += 3
            notes.append("plus interior defense")

        if pos in ["PG", "SG"]:
            fit -= 10
            notes.append("guard playing center")
        elif pos == "SF" and trb < 7:
            fit -= 6
            notes.append("wing lacks center rebounding profile")

        if trb < 5:
            fit -= 5
            notes.append("low rebounding for center")
        if blk < 0.5 and dbpm < 0:
            fit -= 3
            notes.append("limited rim protection")

    # ----------------------------
    # BENCH 1 / PRIMARY BENCH
    # ----------------------------
    elif slot == "Bench 1":
        if pts >= 15:
            fit += 4
            notes.append("bench scoring punch")
        if obpm >= 1.5:
            fit += 3
            notes.append("second-unit creator")
        if is_reliable_shooter(row):
            fit += 2
            notes.append("bench spacing")
        if bpm >= 2:
            fit += 2
            notes.append("starter-quality primary bench")
        if pts < 8 and obpm < 0:
            fit -= 3
            notes.append("limited primary bench offense")

    # ----------------------------
    # BENCH
    # ----------------------------
    elif slot_role == "BENCH":
        if bpm >= 1:
            fit += 3
            notes.append("positive bench impact")
        if is_reliable_shooter(row):
            fit += 2
            notes.append("bench shooting value")
        if dbpm >= 1:
            fit += 2
            notes.append("defensive bench value")
        if pts >= 12:
            fit += 2
            notes.append("bench scoring")
        if bpm < -3:
            fit -= 4
            notes.append("weak rotation impact")

    # ----------------------------
    # TWO-WAY
    # ----------------------------
    elif slot_role == "TWO_WAY":
        # Two-way slots should not carry the team. Reward cheap value/developmental depth.
        if row["Salary"] <= 5_000_000:
            fit += 3
            notes.append("low-cost two-way depth")
        if bpm >= 0:
            fit += 2
            notes.append("positive depth impact")
        if row["MP"] <= 18 and row["Salary"] <= 8_000_000:
            fit += 2
            notes.append("realistic low-minute roster slot")
        if row["Salary"] >= 20_000_000:
            fit -= 5
            notes.append("expensive player in two-way slot")
        if bpm < -4:
            fit -= 3
            notes.append("poor two-way impact")

    fit = int(max(-12, min(12, fit)))

    if not notes:
        notes.append("neutral positional fit")

    return fit, notes[:3]



def calculate_player_quality_score(row) -> float:
    """
    Determines player quality without over-relying on BPM.
    BPM is useful, but it can be affected by team context and role.
    This score leans on production, efficiency, impact score, defense, minutes, and role.
    """
    score = 0.0

    score += normalize(row["Impact_Score"], 20, 95) * 0.28
    score += normalize(row["PTS"], 5, 32) * 0.17
    score += normalize(row["AST"], 1, 10) * 0.12
    score += normalize(row["TRB"], 2, 13) * 0.11
    score += normalize(row["TS%"], 0.50, 0.68) * 0.11
    score += normalize(custom_defense_score(row), 0, 30) * 0.10
    score += normalize(row["MP"], 12, 36) * 0.07
    score += normalize(row["BPM"], -2, 10) * 0.04

    # Penalize statistical noise from tiny roles.
    if row["MP"] < 15:
        score -= 14
    elif row["MP"] < 20:
        score -= 7

    # A role player can be valuable, but should not be labeled the best player
    # over true franchise-level players unless the full profile supports it.
    if row["USG%"] < 16 and row["PTS"] < 12 and row["AST"] < 4:
        score -= 8

    # Manual star correction for players whose box/advanced stats may be affected
    # by team context, role, injuries, or roster environment.
    star_names = {
        "nikola jokic": 9,
        "shai gilgeous-alexander": 9,
        "luka doncic": 9,
        "giannis antetokounmpo": 9,
        "jayson tatum": 8,
        "anthony edwards": 8,
        "victor wembanyama": 8,
        "lebron james": 7,
        "stephen curry": 7,
        "kevin durant": 7,
        "anthony davis": 7,
        "joel embiid": 7,
        "kawhi leonard": 6,
        "devin booker": 6,
        "donovan mitchell": 6,
        "jalen brunson": 6,
        "jaylen brown": 5,
        "bam adebayo": 5,
        "cade cunningham": 5,
        "ja morant": 5,
        "lamelo ball": 4,
        "paolo banchero": 5,
        "tyrese haliburton": 6,
        "trae young": 5,
        "damian lillard": 5,
        "kyrie irving": 5,
        "jaren jackson jr": 5,
        "jaren jackson jr.": 5,
    }

    name = str(row["Player"]).lower()
    for star_name, bonus in star_names.items():
        if star_name in name:
            score += bonus
            break

    return round(max(0, min(100, score)), 2)


def get_player_role(row) -> str:
    roles = []
    quality = row.get("Player_Quality", calculate_player_quality_score(row))

    if quality >= 82:
        roles.append("MVP-Level Star")
    elif quality >= 72:
        roles.append("All-NBA Caliber")
    elif quality >= 62:
        roles.append("All-Star Caliber")
    elif quality >= 52:
        roles.append("High-Level Starter")
    elif quality >= 42:
        roles.append("Rotation Contributor")

    if is_floor_spacer(row):
        roles.append("Elite Floor Spacer")
    elif is_reliable_shooter(row):
        roles.append("Reliable Shooter")

    if row["AST"] >= 7:
        roles.append("Primary Playmaker")
    elif row["AST"] >= 5:
        roles.append("Secondary Playmaker")
    elif row["AST"] >= 4 and row["Pos"] in ["PF", "C"]:
        roles.append("Frontcourt Connector")

    if custom_defense_score(row) >= 25:
        roles.append("Defensive Anchor")
    elif custom_defense_score(row) >= 18 or row["DBPM"] >= 1:
        roles.append("Plus Defender")

    if row["TRB"] >= 9:
        roles.append("High-End Rebounder")
    elif row["TRB"] >= 7:
        roles.append("Rebounder")

    if not roles:
        roles.append("Depth Piece")

    return ", ".join(roles[:3])

def fit_label(fit: int) -> str:
    if fit >= 5:
        return "Great Fit"
    if fit >= 1:
        return "Good Fit"
    if fit >= -2:
        return "Neutral Fit"
    if fit >= -6:
        return "Poor Fit"
    return "Bad Fit"


def fit_color_class(fit: int) -> str:
    if fit >= 1:
        return "fit-good"
    if fit <= -3:
        return "fit-bad"
    return "fit-neutral"


def get_roster_talent_context(roster_df: pd.DataFrame) -> dict:
    """
    Uses current-season stats only to identify when a roster is historically stacked.
    """
    df = roster_df.copy()
    if "Player_Quality" not in df.columns:
        df["Player_Quality"] = df.apply(calculate_player_quality_score, axis=1)

    elite = int((df["Player_Quality"] >= 78).sum())
    stars = int((df["Player_Quality"] >= 68).sum())
    high_level = int((df["Player_Quality"] >= 56).sum())
    twenty_ppg = int((df["PTS"] >= 20).sum())
    top5_quality = float(df["Player_Quality"].nlargest(5).mean())
    top8_quality = float(df["Player_Quality"].nlargest(8).mean())

    is_historic = elite >= 4 or stars >= 7 or (top5_quality >= 72 and high_level >= 8)
    is_superteam = elite >= 3 or stars >= 5 or top5_quality >= 68

    return {
        "elite_count": elite,
        "star_count": stars,
        "high_level_count": high_level,
        "twenty_ppg_count": twenty_ppg,
        "top5_quality": round(top5_quality, 1),
        "top8_quality": round(top8_quality, 1),
        "is_superteam": is_superteam,
        "is_historic": is_historic,
    }


def talent_adjusted_fit(raw_fit: int, roster_df: pd.DataFrame) -> int:
    """
    On normal teams, fit matters a lot.
    On absurd superstar teams, one weird slot should not crater the projection.
    """
    context = get_roster_talent_context(roster_df)

    if raw_fit >= 0:
        return raw_fit

    if context["is_historic"]:
        return int(round(raw_fit * 0.35))
    if context["is_superteam"]:
        return int(round(raw_fit * 0.55))
    return raw_fit


def build_unique_fit_note(row, slot: str, raw_fit: int, adjusted_fit: int, roster_df: pd.DataFrame | None = None) -> str:
    """
    More human-readable, player/context-aware fit notes for the table.
    """
    name = row["Player"]
    pos = row["Pos"]
    slot_role = get_slot_role(slot)
    pts = float(row["PTS"])
    ast = float(row["AST"])
    trb = float(row["TRB"])
    three_pct = float(row["3P%"])
    three_pa = float(row["3PA"])
    quality = row.get("Player_Quality", calculate_player_quality_score(row))

    context = get_roster_talent_context(roster_df) if roster_df is not None else {
        "is_superteam": False,
        "is_historic": False,
        "star_count": 0,
        "elite_count": 0,
    }

    notes = []

    if slot_role == "PG":
        if ast >= 7:
            notes.append(f"{name} gives this slot real lead-guard creation and control.")
        elif ast >= 5:
            notes.append(f"{name} can handle secondary creation duties without breaking the offense.")
        elif pos in ["SF", "PF", "C"] and ast >= 4:
            notes.append(f"{name} is more of a point-forward hub than a traditional guard.")
        else:
            notes.append(f"{name} is not a natural table-setter, so this slot asks a lot of his decision-making.")

    elif slot_role == "SG":
        if pts >= 22:
            notes.append(f"{name} brings star-level scoring pressure next to the primary initiator.")
        elif three_pct >= 0.37 and three_pa >= 4:
            notes.append(f"{name} fits cleanly as a spacing guard who keeps driving lanes open.")
        else:
            notes.append(f"{name} can function here, but the value depends on shooting and off-ball discipline.")

    elif slot_role == "SF":
        if pts >= 20 and trb >= 5:
            notes.append(f"{name} gives the wing spot scoring punch with enough size/activity to survive bigger matchups.")
        elif three_pct >= 0.36 and three_pa >= 3:
            notes.append(f"{name} provides useful wing spacing and does not crowd the floor.")
        else:
            notes.append(f"{name} is playable at the wing, though the team may need stronger creation or defense elsewhere.")

    elif slot_role == "PF":
        if trb >= 7 and quality >= 55:
            notes.append(f"{name} has enough rebounding and talent to work as a modern frontcourt piece.")
        elif pos in ["SG", "SF"] and trb >= 6:
            notes.append(f"{name} profiles as a small-ball forward who can help on the glass.")
        else:
            notes.append(f"{name} is a creative PF choice and needs surrounding size to protect the matchup.")

    elif slot_role == "C":
        if pos in ["PG", "SG"] and context["is_historic"]:
            notes.append(f"{name} is obviously undersized at center, but this historic talent base can hide the mismatch in many lineups.")
        elif pos in ["PG", "SG"] and context["is_superteam"]:
            notes.append(f"{name} is not a real center, but the surrounding stars reduce how damaging the mismatch is.")
        elif pos in ["PG", "SG"]:
            notes.append(f"{name} at center is a major size and rebounding risk.")
        elif trb >= 8 or row["BLK"] >= 1:
            notes.append(f"{name} gives the center spot legitimate interior presence.")
        else:
            notes.append(f"{name} can fill center minutes, but the team may need more rim protection around him.")

    elif slot == "Bench 1":
        if quality >= 65:
            notes.append(f"{name} as primary bench is a luxury; he can tilt bench minutes like a starter.")
        elif pts >= 15:
            notes.append(f"{name} gives the second unit scoring punch.")
        else:
            notes.append(f"{name} gives the bench a defined role, but not a true carry option.")

    elif slot_role == "BENCH":
        if quality >= 70:
            notes.append(f"{name} coming off the bench is an overwhelming depth advantage.")
        elif quality >= 55:
            notes.append(f"{name} gives the bench starter-level stability.")
        elif three_pct >= 0.37 and three_pa >= 3:
            notes.append(f"{name} adds useful shooting to stabilize reserve groups.")
        else:
            notes.append(f"{name} is best used as a matchup-dependent rotation piece.")

    elif slot_role == "TWO_WAY":
        if row["Salary"] >= 20_000_000 and context["is_historic"]:
            notes.append(f"{name} is far too talented for a two-way slot, but this roster is so loaded that stars are being squeezed down the depth chart.")
        elif row["Salary"] >= 20_000_000:
            notes.append(f"{name} is too expensive and too important for a two-way role.")
        elif quality >= 45:
            notes.append(f"{name} is strong developmental/depth value for this slot.")
        else:
            notes.append(f"{name} fits as a low-cost depth piece.")

    if raw_fit < -3 and adjusted_fit > raw_fit:
        notes.append("Penalty softened because the roster has enough top-end talent to cover some role awkwardness.")

    return " ".join(notes[:2])



# ============================================================
# ROLE-WEIGHTED TEAM SCORING
# ============================================================

ROLE_WEIGHTS = {
    "Starting PG": 1.45,
    "Starting SG": 1.35,
    "Starting SF": 1.35,
    "Starting PF": 1.35,
    "Starting C": 1.45,
    "Bench 1": 1.05,
    "Bench 2": 0.85,
    "Bench 3": 0.75,
    "Bench 4": 0.65,
    "Bench 5": 0.55,
    "Bench 6": 0.45,
    "Bench 7": 0.35,
    "Bench 8": 0.30,
    "Two-Way 1": 0.15,
    "Two-Way 2": 0.15,
}


def add_role_weights(roster_df: pd.DataFrame) -> pd.DataFrame:
    roster_df = roster_df.copy()
    roster_df["Role_Weight"] = roster_df["Slot"].map(ROLE_WEIGHTS).fillna(0.5)
    return roster_df


def weighted_average(roster_df: pd.DataFrame, col: str) -> float:
    weights = roster_df["Role_Weight"]
    if weights.sum() == 0:
        return float(roster_df[col].mean())
    return float((roster_df[col] * weights).sum() / weights.sum())


def calculate_rebounding_score(roster_df: pd.DataFrame) -> float:
    return (
        normalize(weighted_average(roster_df, "TRB"), 3, 12) * 0.72 +
        normalize(weighted_average(roster_df, "BLK"), 0.1, 2.2) * 0.13 +
        normalize(weighted_average(roster_df, "Custom_Defense"), 2, 30) * 0.15
    )


def calculate_versatility_score(roster_df: pd.DataFrame) -> float:
    """
    Measures how many different roster problems the team can solve.
    This helps teams like OKC/Orlando/Miami that win with two-way depth,
    defense, switchability, shooting, and role clarity.
    """
    versatile = 0
    for _, row in roster_df.iterrows():
        skill_count = 0

        if row["PTS"] >= 15:
            skill_count += 1
        if row["AST"] >= 4:
            skill_count += 1
        if row["TRB"] >= 6:
            skill_count += 1
        if row["3P%"] >= 0.36 and row["3PA"] >= 3:
            skill_count += 1
        if row["Custom_Defense"] >= 16 or row["DBPM"] >= 1:
            skill_count += 1
        if row["TS%"] >= 0.58:
            skill_count += 1
        if row["Fit_Adjustment"] >= 2:
            skill_count += 1

        if skill_count >= 4:
            versatile += 1.00
        elif skill_count == 3:
            versatile += 0.65
        elif skill_count == 2:
            versatile += 0.35

    base = normalize(versatile, 2, 8)

    # Extra reward for having competent two-way pieces in the actual rotation.
    rotation = roster_df[~roster_df["Slot"].str.contains("Two-Way", na=False)]
    positive_rotation = len(rotation[(rotation["Player_Quality"] >= 48) & (rotation["Fit_Adjustment"] >= 0)])
    base += normalize(positive_rotation, 4, 10) * 0.25

    return max(0, min(100, base))


def calculate_star_power_score(roster_df: pd.DataFrame) -> float:
    """
    Star power should not only mean MVP candidates.
    It should also reward All-Star level players, high-end starters,
    strong scoring options, and players who can realistically carry parts of a season.
    This helps teams like Miami where Bam, Herro, and Powell provide real star/near-star value
    without being Jokic/Luka/Giannis-level superstars.
    """
    top1 = roster_df["Player_Quality"].nlargest(1).mean()
    top3 = roster_df["Player_Quality"].nlargest(3).mean()
    top5 = roster_df["Player_Quality"].nlargest(5).mean()

    elite_count = len(roster_df[roster_df["Player_Quality"] >= 78])
    star_count = len(roster_df[roster_df["Player_Quality"] >= 66])
    high_level_count = len(roster_df[roster_df["Player_Quality"] >= 56])

    twenty_ppg_count = len(roster_df[roster_df["PTS"] >= 20])
    eighteen_ppg_count = len(roster_df[roster_df["PTS"] >= 18])

    # Two-way frontcourt stars/near-stars can be underrated by scoring-only formulas.
    two_way_bigs = len(
        roster_df[
            (roster_df["Pos"].isin(["PF", "C"])) &
            (roster_df["PTS"] >= 16) &
            (roster_df["TRB"] >= 7) &
            ((roster_df["Custom_Defense"] >= 18) | (roster_df["DBPM"] >= 1))
        ]
    )

    score = (
        normalize(top1, 48, 88) * 0.20 +
        normalize(top3, 42, 82) * 0.28 +
        normalize(top5, 36, 76) * 0.20 +
        normalize(star_count, 0, 4) * 0.12 +
        normalize(high_level_count, 1, 7) * 0.08 +
        normalize(twenty_ppg_count, 0, 4) * 0.06 +
        normalize(eighteen_ppg_count, 1, 6) * 0.04 +
        normalize(two_way_bigs, 0, 2) * 0.02
    )

    # Slight bump for teams with several credible top options but no MVP-level superstar.
    if elite_count == 0 and high_level_count >= 3:
        score += 8
    elif elite_count == 1 and high_level_count >= 3:
        score += 5

    return round(max(0, min(100, score)), 1)


def calculate_depth_score(roster_df: pd.DataFrame) -> float:
    bench_df = roster_df[~roster_df["Slot"].isin([
        "Starting PG", "Starting SG", "Starting SF", "Starting PF", "Starting C"
    ])]

    if len(bench_df) == 0:
        return 50

    # Bench 1-8 matter far more than two-way slots.
    bench_df = add_role_weights(bench_df)
    quality = weighted_average(bench_df, "Player_Quality")
    impact = weighted_average(bench_df, "Impact_Score")
    fit = weighted_average(bench_df, "Fit_Adjustment")
    shooting = weighted_average(bench_df, "TS%")

    return (
        normalize(quality, 28, 72) * 0.43 +
        normalize(impact, 20, 75) * 0.24 +
        normalize(fit, -4, 8) * 0.18 +
        normalize(shooting, 0.50, 0.65) * 0.15
    )


def roster_pillar_identity(metrics: dict) -> str:
    wins = metrics["projected_wins"]
    if wins >= 78:
        return "All-Time Superteam"
    if wins >= 70:
        return "Championship Favorite"
    if wins >= 58:
        return "Elite Contender"
    if wins >= 50:
        return "Strong Playoff Contender"
    if wins >= 43:
        return "Playoff-Level Team"
    if wins >= 36:
        return "Play-In Team"
    return "Developmental Roster"


# ============================================================
# TEAM METRICS
# ============================================================

def calculate_team_metrics(roster_df: pd.DataFrame, salary_cap: int) -> dict:
    roster_df = roster_df.copy()

    fit_results = roster_df.apply(
        lambda row: calculate_position_fit(row, row["Slot"]),
        axis=1
    )
    roster_df["Raw_Fit_Adjustment"] = [x[0] for x in fit_results]
    roster_df["Custom_Defense"] = roster_df.apply(custom_defense_score, axis=1)
    roster_df["Player_Quality"] = roster_df.apply(calculate_player_quality_score, axis=1)

    talent_context = get_roster_talent_context(roster_df)

    roster_df["Fit_Adjustment"] = roster_df["Raw_Fit_Adjustment"].apply(
        lambda x: talent_adjusted_fit(int(x), roster_df)
    )
    roster_df["Fit_Notes"] = roster_df.apply(
        lambda row: build_unique_fit_note(
            row,
            row["Slot"],
            int(row["Raw_Fit_Adjustment"]),
            int(row["Fit_Adjustment"]),
            roster_df
        ),
        axis=1
    )

    roster_df = add_role_weights(roster_df)
    payroll = roster_df["Salary"].sum()

    # Pillar 1: Creation
    creation_score = (
        normalize(weighted_average(roster_df, "AST"), 1.5, 8.5) * 0.33 +
        normalize(weighted_average(roster_df, "PTS"), 7, 29) * 0.22 +
        normalize(weighted_average(roster_df, "Impact_Score"), 25, 92) * 0.20 +
        normalize(weighted_average(roster_df, "TS%"), 0.52, 0.68) * 0.15 +
        normalize(weighted_average(roster_df, "TOV") * -1, -4, -1) * 0.10
    )

    # Pillar 2: Shooting
    shooting_score = (
        normalize(weighted_average(roster_df, "3P%"), 0.30, 0.42) * 0.38 +
        normalize(weighted_average(roster_df, "3PA"), 1.5, 7.5) * 0.24 +
        normalize(weighted_average(roster_df, "TS%"), 0.52, 0.68) * 0.24 +
        normalize(weighted_average(roster_df, "eFG%"), 0.48, 0.62) * 0.14
    )

    # Pillar 3: Defense
    defense_score = (
        normalize(weighted_average(roster_df, "Custom_Defense"), 2, 30) * 0.42 +
        normalize(weighted_average(roster_df, "STL"), 0.3, 1.8) * 0.15 +
        normalize(weighted_average(roster_df, "BLK"), 0.1, 2.4) * 0.17 +
        normalize(weighted_average(roster_df, "TRB"), 3, 12) * 0.16 +
        normalize(weighted_average(roster_df, "DBPM"), -2, 4) * 0.10
    )

    # Pillar 4: Rebounding
    rebounding_score = calculate_rebounding_score(roster_df)

    # Pillar 5: Star / top-end talent
    star_power_score = calculate_star_power_score(roster_df)

    # Additional talent concentration score using only current-season stats.
    top5_quality = roster_df["Player_Quality"].nlargest(5).mean()
    top8_quality = roster_df["Player_Quality"].nlargest(8).mean()
    top5_impact = roster_df["Impact_Score"].nlargest(5).mean()
    top8_impact = roster_df["Impact_Score"].nlargest(8).mean()

    talent_concentration_score = (
        normalize(top5_quality, 50, 88) * 0.36 +
        normalize(top8_quality, 42, 82) * 0.24 +
        normalize(top5_impact, 45, 92) * 0.24 +
        normalize(top8_impact, 36, 85) * 0.16
    )

    # Pillar 6: Depth
    depth_score = calculate_depth_score(roster_df)

    # Pillar 7: Fit
    fit_score = 50 + (weighted_average(roster_df, "Fit_Adjustment") * 4.5)
    fit_score = max(0, min(100, fit_score))

    # Pillar 8: Versatility
    versatility_score = calculate_versatility_score(roster_df)

    weighted_quality = weighted_average(roster_df, "Player_Quality")
    value_score = normalize(weighted_average(roster_df, "Value_Score"), 3, 16)


    # ============================================================
    # FINAL TEAM SCORING MODEL WITH CUMULATIVE BPM
    # ============================================================

    elite_count = talent_context["elite_count"]
    star_count = talent_context["star_count"]
    high_level_count = talent_context["high_level_count"]

    # Team cumulative BPM:
    # Rewards rosters with multiple positive-impact players.
    cumulative_bpm = roster_df["BPM"].sum()
    cumulative_bpm_score = normalize(cumulative_bpm, -10, 45)

    # Final basketball-first model.
    # Talent, star power, and cumulative impact should drive wins.
    overall_score = (
        talent_concentration_score * 0.24 +
        star_power_score * 0.21 +
        cumulative_bpm_score * 0.13 +
        creation_score * 0.14 +
        defense_score * 0.13 +
        depth_score * 0.07 +
        shooting_score * 0.04 +
        rebounding_score * 0.02 +
        fit_score * 0.015 +
        versatility_score * 0.005
    )

    # More realistic contender curve.
    projected_wins = round(20 + (overall_score / 100) * 62)

    # Talent floors
    if talent_context["is_historic"]:
        projected_wins = max(projected_wins, 78)
        overall_score = max(overall_score, 95)

    elif elite_count >= 3 or star_count >= 6:
        projected_wins = max(projected_wins, 72)
        overall_score = max(overall_score, 90)

    elif star_count >= 4 and high_level_count >= 7:
        projected_wins = max(projected_wins, 66)
        overall_score = max(overall_score, 84)

    elif star_count >= 3 and high_level_count >= 5:
        projected_wins = max(projected_wins, 60)
        overall_score = max(overall_score, 80)

    elif star_count >= 2 and high_level_count >= 5 and depth_score >= 50:
        projected_wins = max(projected_wins, 55)
        overall_score = max(overall_score, 76)

    elif high_level_count >= 4 and depth_score >= 55:
        projected_wins = max(projected_wins, 50)
        overall_score = max(overall_score, 72)

    # Balanced-team boost
    pillar_scores = [
        creation_score,
        shooting_score,
        defense_score,
        rebounding_score,
        depth_score,
        fit_score,
        versatility_score
    ]

    if min(pillar_scores) >= 55 and defense_score >= 65 and depth_score >= 60:
        projected_wins += 5
        overall_score += 2.0

    elif min(pillar_scores) >= 50 and depth_score >= 55 and fit_score >= 60:
        projected_wins += 3
        overall_score += 1.0

    # Star trio / offensive core bonus
    if star_count >= 3 and creation_score >= 55:
        projected_wins += 5
        overall_score += 1.8

    elif star_count >= 2 and creation_score >= 60 and depth_score >= 50:
        projected_wins += 3
        overall_score += 1.0

    # Elite balanced contender boost
    top4_quality = roster_df["Player_Quality"].nlargest(4).mean()
    top6_quality = roster_df["Player_Quality"].nlargest(6).mean()
    strong_rotation_count = len(roster_df[roster_df["Player_Quality"] >= 50])
    high_minutes_quality = len(
        roster_df[
            (roster_df["Player_Quality"] >= 55) &
            (roster_df["MP"] >= 24)
        ]
    )

    if top4_quality >= 66 and top6_quality >= 58 and strong_rotation_count >= 7:
        projected_wins = max(projected_wins, 64)
        overall_score = max(overall_score, 86)

    elif top4_quality >= 62 and top6_quality >= 55 and strong_rotation_count >= 6:
        projected_wins = max(projected_wins, 60)
        overall_score = max(overall_score, 82)

    elif top4_quality >= 58 and strong_rotation_count >= 6 and defense_score >= 55:
        projected_wins = max(projected_wins, 56)
        overall_score = max(overall_score, 78)

    # Extra reward for elite two-way cores
    if high_minutes_quality >= 4 and defense_score >= 60 and creation_score >= 58:
        projected_wins += 3
        overall_score += 1.2

    # Cumulative BPM bonuses
    if cumulative_bpm >= 35:
        projected_wins += 6
        overall_score += 2.0

    elif cumulative_bpm >= 28:
        projected_wins += 4
        overall_score += 1.4

    elif cumulative_bpm >= 22:
        projected_wins += 3
        overall_score += 1.0

    elif cumulative_bpm >= 16:
        projected_wins += 2
        overall_score += 0.6

    elif cumulative_bpm < 0:
        projected_wins -= 4
        overall_score -= 1.5

    # Cap penalty
    if payroll > salary_cap:
        if talent_context["is_historic"]:
            penalty = min(3, int((payroll - salary_cap) / 75_000_000))
        elif talent_context["is_superteam"]:
            penalty = min(5, int((payroll - salary_cap) / 50_000_000))
        elif star_count >= 3:
            penalty = min(5, int((payroll - salary_cap) / 45_000_000))
        else:
            penalty = min(7, int((payroll - salary_cap) / 30_000_000))

        projected_wins -= max(0, penalty - 1)
        overall_score -= penalty * 0.25

    # Conditional calibration boost.
    # Strong teams get corrected upward without giving weak teams a free +20.
    if overall_score >= 88:
        projected_wins += 12
        overall_score += 4.0

    elif overall_score >= 82:
        projected_wins += 10
        overall_score += 3.0

    elif overall_score >= 76:
        projected_wins += 8
        overall_score += 2.2

    elif overall_score >= 70:
        projected_wins += 6
        overall_score += 1.5

    elif overall_score >= 64:
        projected_wins += 4
        overall_score += 1.0

    elif overall_score >= 58:
        projected_wins += 2
        overall_score += 0.5

    projected_wins = round(projected_wins * 1.25)

    # ============================================================
    # EXTREME-TEAM REALISM CAP
    # ============================================================
    # Only touches teams that are already projecting as all-time great.
    # Mid-level and normal contender teams are intentionally unaffected.
    #
    # 82-0 should be possible only for a nearly perfect roster: elite talent,
    # elite fit, elite creation/defense/depth, strong cumulative impact,
    # and no cap overage. Otherwise, the best teams settle around 79-81 wins.
    if projected_wins >= 80:
        perfect_team_case = (
            talent_context["is_historic"] and
            overall_score >= 97 and
            fit_score >= 76 and
            creation_score >= 76 and
            defense_score >= 74 and
            depth_score >= 68 and
            cumulative_bpm >= 42 and
            payroll <= salary_cap
        )

        if projected_wins >= 82 and not perfect_team_case:
            projected_wins = 80
            overall_score -= 1.0
        elif projected_wins == 81 and not perfect_team_case:
            projected_wins = 80
            overall_score -= 0.5

        # Slight extra friction for superteams with role/cap issues.
        # This keeps stacked but awkward rosters from automatically hitting 82-0.
        elite_friction = 0
        if payroll > salary_cap:
            elite_friction += 1
        if fit_score < 70:
            elite_friction += 1
        if depth_score < 62:
            elite_friction += 1
        if min(pillar_scores) < 58:
            elite_friction += 1
        if star_count >= 7 and fit_score < 78:
            elite_friction += 1

        if projected_wins >= 80 and elite_friction > 0:
            projected_wins -= min(2, elite_friction)
            overall_score -= min(1.0, elite_friction * 0.35)

    projected_wins = max(15, min(82, projected_wins))
    overall_score = max(0, min(100, overall_score))

    # Best Shooter should reward both efficiency and volume.
    # This prevents low-volume high-percentage players from beating true high-gravity shooters.
    roster_df["Shooter_Score"] = (
        roster_df["3P%"] * 100 * 0.62
        + roster_df["3PA"] * 4.75
        + roster_df["TS%"] * 100 * 0.14
        + roster_df["PTS"] * 0.20
    )

    qualified_shooters = roster_df[roster_df["3PA"] >= 3.0]
    if len(qualified_shooters) > 0:
        best_shooter = qualified_shooters.sort_values(
            "Shooter_Score",
            ascending=False
        ).iloc[0]
    else:
        best_shooter = roster_df.sort_values(
            "Shooter_Score",
            ascending=False
        ).iloc[0]

    best_contract = roster_df.sort_values("Value_Score", ascending=False).iloc[0]
    worst_contract = roster_df.sort_values("Value_Score", ascending=True).iloc[0]
    best_player = roster_df.sort_values("Player_Quality", ascending=False).iloc[0]
    roster_df["Defender_Leader_Score"] = roster_df.apply(defender_leader_score, axis=1)
    qualified_defenders = roster_df[roster_df["MP"] >= 20]
    if len(qualified_defenders) > 0:
        best_defender = qualified_defenders.sort_values("Defender_Leader_Score", ascending=False).iloc[0]
    else:
        best_defender = roster_df.sort_values("Defender_Leader_Score", ascending=False).iloc[0]
    worst_fit = roster_df.sort_values("Fit_Adjustment", ascending=True).iloc[0]
    best_fit = roster_df.sort_values("Fit_Adjustment", ascending=False).iloc[0]

    identity = roster_pillar_identity({"projected_wins": projected_wins})
    if talent_context["is_historic"]:
        identity = "Historic Superteam"

    return {
        "payroll": payroll,
        "remaining_cap": salary_cap - payroll,
        "salary_cap": salary_cap,
        "overall_score": round(overall_score, 1),
        "grade": wins_to_grade(projected_wins),
        "projected_wins": projected_wins,
        "creation_score": round(creation_score, 1),
        "offense_score": round(creation_score, 1),
        "defense_score": round(defense_score, 1),
        "shooting_score": round(shooting_score, 1),
        "playmaking_score": round(creation_score, 1),
        "rebounding_score": round(rebounding_score, 1),
        "star_power": round(star_power_score, 1),
        "star_power_score": round(star_power_score, 1),
        "talent_concentration_score": round(talent_concentration_score, 1),
        "depth_score": round(depth_score, 1),
        "fit_score": round(fit_score, 1),
        "versatility_score": round(versatility_score, 1),
        "value_score": round(value_score, 1),
        "weighted_quality": round(weighted_quality, 1),
        "identity": identity,
        "cumulative_bpm": round(cumulative_bpm, 1),
        "cumulative_bpm_score": round(cumulative_bpm_score, 1),
        "avg_ts": weighted_average(roster_df, "TS%"),
        "avg_3p": weighted_average(roster_df, "3P%"),
        "avg_bpm": weighted_average(roster_df, "BPM"),
        "avg_obpm": weighted_average(roster_df, "OBPM"),
        "avg_dbpm": weighted_average(roster_df, "DBPM"),
        "total_vorp": roster_df["VORP"].sum(),
        "elite_count": elite_count,
        "star_count": star_count,
        "high_level_count": high_level_count,
        "twenty_ppg_count": talent_context["twenty_ppg_count"],
        "best_contract": best_contract["Player"],
        "worst_contract": worst_contract["Player"],
        "best_player": best_player["Player"],
        "best_shooter": best_shooter["Player"],
        "best_defender": best_defender["Player"],
        "best_fit": best_fit["Player"],
        "worst_fit": worst_fit["Player"],
        "roster_with_fit": roster_df,
    }

def build_team_summary(roster_df: pd.DataFrame, metrics: dict) -> dict:
    roster_fit_df = metrics["roster_with_fit"].copy()

    players = []
    for _, row in roster_fit_df.iterrows():
        players.append({
            "name": row["Player"],
            "slot": row["Slot"],
            "slot_role": get_slot_role(row["Slot"]),
            "actual_position": row["Pos"],
            "team": row["Team"],
            "salary": money(row["Salary"]),
            "points": round(row["PTS"], 1),
            "assists": round(row["AST"], 1),
            "rebounds": round(row["TRB"], 1),
            "steals": round(row["STL"], 1),
            "blocks": round(row["BLK"], 1),
            "three_point_percentage": pct(row["3P%"]),
            "three_point_attempts": round(row["3PA"], 1),
            "true_shooting": pct(row["TS%"]),
            "PER": round(row["PER"], 1),
            "OBPM": round(row["OBPM"], 1),
            "DBPM": round(row["DBPM"], 1),
            "BPM": round(row["BPM"], 1),
            "VORP": round(row["VORP"], 1),
            "impact_score": round(row["Impact_Score"], 1),
            "value_score": round(row["Value_Score"], 1),
            "custom_defense_score": round(row["Custom_Defense"], 1),
            "player_quality_score": round(row.get("Player_Quality", calculate_player_quality_score(row)), 1),
            "fit_adjustment": int(row["Fit_Adjustment"]),
            "fit_label": fit_label(int(row["Fit_Adjustment"])),
            "fit_notes": row["Fit_Notes"],
            "role": get_player_role(row),
        })

    return {
        "team_metrics": {
            "salary_cap": money(metrics["salary_cap"]),
            "payroll": money(metrics["payroll"]),
            "remaining_cap": money(metrics["remaining_cap"]),
            "salary_cap_raw": metrics["salary_cap"],
            "payroll_raw": metrics["payroll"],
            "remaining_cap_raw": metrics["remaining_cap"],
            "projected_wins": metrics["projected_wins"],
            "overall_score": metrics["overall_score"],
            "grade": metrics["grade"],
            "identity": metrics["identity"],
            "creation_score": metrics["creation_score"],
            "offense_score": metrics["offense_score"],
            "defense_score": metrics["defense_score"],
            "shooting_score": metrics["shooting_score"],
            "playmaking_score": metrics["playmaking_score"],
            "rebounding_score": metrics["rebounding_score"],
            "star_power": metrics["star_power"],
            "talent_concentration_score": metrics.get("talent_concentration_score", 0),
            "top_end_score": metrics.get("top_end_score", metrics["star_power"]),
            "superstar_score": metrics.get("superstar_score", 50),
            "weighted_quality": metrics.get("weighted_quality", 0),
            "elite_count": metrics.get("elite_count", 0),
            "star_count": metrics.get("star_count", 0),
            "high_level_count": metrics.get("high_level_count", 0),
            "twenty_ppg_count": metrics.get("twenty_ppg_count", 0),
            "depth_score": metrics["depth_score"],
            "value_score": metrics["value_score"],
            "fit_score": metrics["fit_score"],
            "versatility_score": metrics["versatility_score"],
            "average_TS": pct(metrics["avg_ts"]),
            "average_3P": pct(metrics["avg_3p"]),
            "average_BPM": round(metrics["avg_bpm"], 2),
            "average_OBPM": round(metrics["avg_obpm"], 2),
            "average_DBPM": round(metrics["avg_dbpm"], 2),
            "total_VORP": round(metrics["total_vorp"], 2),
            "best_contract": metrics["best_contract"],
            "worst_contract": metrics["worst_contract"],
            "best_player": metrics["best_player"],
            "best_shooter": metrics["best_shooter"],
            "best_defender": metrics["best_defender"],
            "best_fit": metrics["best_fit"],
            "worst_fit": metrics["worst_fit"],
        },
        "players": players
    }



def build_report_groups(team_summary: dict) -> dict:
    """
    Creates roster-aware context so each AI report is unique.
    No hardcoded player examples. Everything comes from the drafted roster.
    """
    players = team_summary["players"]
    metrics = team_summary["team_metrics"]

    def sf(value):
        try:
            if isinstance(value, str):
                return float(value.replace("%", "").replace("$", "").replace("M", ""))
            return float(value)
        except Exception:
            return 0.0

    def top_by(key, n=5, reverse=True):
        return sorted(players, key=lambda p: sf(p.get(key, 0)), reverse=reverse)[:n]

    def pct_to_float(value):
        if isinstance(value, str):
            return sf(value.replace("%", ""))
        return sf(value) * 100

    core_players = top_by("player_quality_score", 6)

    creators = sorted(
        players,
        key=lambda p: (
            sf(p.get("assists", 0)) * 0.45 +
            sf(p.get("points", 0)) * 0.18 +
            sf(p.get("OBPM", 0)) * 0.17 +
            sf(p.get("player_quality_score", 0)) * 0.20
        ),
        reverse=True
    )[:6]

    shooters = sorted(
        [p for p in players if sf(p.get("three_point_attempts", 0)) >= 2.0],
        key=lambda p: (
            pct_to_float(p.get("three_point_percentage", "0%")) * 0.50 +
            sf(p.get("three_point_attempts", 0)) * 4.0 +
            sf(p.get("points", 0)) * 0.40
        ),
        reverse=True
    )[:6]

    defenders = sorted(
        players,
        key=lambda p: (
            sf(p.get("custom_defense_score", 0)) * 0.45 +
            sf(p.get("rebounds", 0)) * 1.5 +
            sf(p.get("blocks", 0)) * 4.0 +
            sf(p.get("steals", 0)) * 3.0 +
            sf(p.get("player_quality_score", 0)) * 0.15
        ),
        reverse=True
    )[:6]

    rebounders = sorted(players, key=lambda p: sf(p.get("rebounds", 0)), reverse=True)[:5]
    rim_protectors = sorted(players, key=lambda p: sf(p.get("blocks", 0)), reverse=True)[:5]
    value_players = sorted(players, key=lambda p: sf(p.get("value_score", 0)), reverse=True)[:5]
    best_fits = sorted(players, key=lambda p: sf(p.get("fit_adjustment", 0)), reverse=True)[:5]
    fit_concerns = sorted(players, key=lambda p: sf(p.get("fit_adjustment", 0)))[:5]

    starters = [p for p in players if p.get("slot", "").startswith("Starting")]
    bench = [p for p in players if p.get("slot_role") in ["BENCH", "BENCH", "TWO_WAY"]]
    two_way = [p for p in players if p.get("slot_role") == "TWO_WAY"]

    # Dynamic roster fingerprint.
    projected_wins = int(metrics.get("projected_wins", 0))
    offense = sf(metrics.get("offense_score", 0))
    defense = sf(metrics.get("defense_score", 0))
    shooting = sf(metrics.get("shooting_score", 0))
    playmaking = sf(metrics.get("playmaking_score", 0))
    depth = sf(metrics.get("depth_score", 0))
    fit = sf(metrics.get("fit_score", 0))
    star_count = int(metrics.get("star_count", 0))
    elite_count = int(metrics.get("elite_count", 0))

    if projected_wins >= 70 or elite_count >= 3:
        roster_type = "superteam"
    elif defense >= 68 and depth >= 55 and star_count < 3:
        roster_type = "defense-and-depth team"
    elif shooting >= 72 and offense >= 65:
        roster_type = "spacing-heavy offensive team"
    elif fit >= 68 and depth >= 60:
        roster_type = "balanced team built on fit and depth"
    elif offense >= 72 and defense < 55:
        roster_type = "offense-first team with defensive questions"
    elif defense >= 70 and offense < 58:
        roster_type = "defense-first team with creation concerns"
    elif projected_wins >= 43:
        roster_type = "competitive playoff-level roster"
    else:
        roster_type = "developmental or incomplete roster"

    # Dynamic strengths.
    strengths = []
    if offense >= 70:
        strengths.append("high-end offensive creation")
    if shooting >= 70:
        strengths.append("floor spacing")
    if defense >= 68:
        strengths.append("defensive versatility")
    if depth >= 60:
        strengths.append("rotation depth")
    if fit >= 65:
        strengths.append("lineup fit")
    if elite_count >= 3:
        strengths.append("overwhelming star power")
    if playmaking >= 65:
        strengths.append("multiple decision-makers")
    if not strengths:
        strengths = ["salary flexibility", "defined roles", "development upside"]

    # Dynamic concerns.
    concerns = []
    if offense < 58:
        concerns.append("lack of elite half-court creation")
    if defense < 58:
        concerns.append("defensive reliability")
    if shooting < 58:
        concerns.append("spacing consistency")
    if playmaking < 55:
        concerns.append("playmaking burden")
    if depth < 45:
        concerns.append("bench reliability")
    if fit < 55:
        concerns.append("positional fit")
    if star_count >= 6:
        concerns.append("role sacrifice among high-usage players")
    if not concerns:
        concerns = ["playoff matchup execution", "health", "late-game role clarity"]

    # Trait hints based only on actual selected players.
    trait_map = {}
    for p in players:
        traits = []
        pos = p.get("actual_position", "")
        slot = p.get("slot", "")
        pts = sf(p.get("points", 0))
        ast = sf(p.get("assists", 0))
        reb = sf(p.get("rebounds", 0))
        blk = sf(p.get("blocks", 0))
        stl = sf(p.get("steals", 0))
        three_pa = sf(p.get("three_point_attempts", 0))
        three_pct = pct_to_float(p.get("three_point_percentage", "0%"))
        fit_adj = sf(p.get("fit_adjustment", 0))

        if ast >= 7:
            traits.append("primary table-setter")
        elif ast >= 5:
            traits.append("secondary creator")
        if pts >= 25:
            traits.append("high-volume scorer")
        elif pts >= 18:
            traits.append("reliable scorer")
        if three_pct >= 37 and three_pa >= 5:
            traits.append("high-volume spacer")
        elif three_pct >= 36 and three_pa >= 3:
            traits.append("credible spacer")
        if reb >= 8:
            traits.append("strong rebounder")
        if blk >= 1.2:
            traits.append("rim protection presence")
        if stl >= 1.2:
            traits.append("active hands defensively")
        if fit_adj >= 5:
            traits.append("clean positional fit")
        elif fit_adj <= -3:
            traits.append("fit risk")
        if pos in ["C", "PF"] and ast >= 4:
            traits.append("frontcourt passer")
        if pos in ["SG", "SF"] and reb >= 6:
            traits.append("wing rebounding")
        if "Two-Way" in slot:
            traits.append("developmental/depth role")

        trait_map[p["name"]] = traits[:5] if traits else ["rotation piece"]

    return {
        "roster_type": roster_type,
        "dynamic_strengths": strengths[:5],
        "dynamic_concerns": concerns[:5],
        "trait_map": trait_map,
        "core_players": core_players,
        "primary_creators": creators,
        "spacing_group": shooters,
        "defensive_group": defenders,
        "rebounding_group": rebounders,
        "rim_protection_group": rim_protectors,
        "bench_unit": bench,
        "starters": starters,
        "two_way_slots": two_way,
        "best_fit_combinations": best_fits,
        "fit_concerns": fit_concerns,
        "best_value_contracts": value_players,
        "top_end_core": core_players[:6],
        "creation_spacing_pairs": {
            "creators": creators[:4],
            "spacers": shooters[:4]
        },
        "defense_frontcourt_pairs": {
            "defenders": defenders[:4],
            "frontcourt": rebounders[:5]
        }
    }


# ============================================================
# REPORT GENERATION
# ============================================================

def fallback_report(team_summary: dict) -> str:
    """
    Built-in non-AI report used only when no OpenAI API key is available.
    The true autonomous report requires the API key.
    """
    m = team_summary["team_metrics"]
    players = team_summary["players"]

    creators = sorted(players, key=lambda p: (p["assists"], p["points"]), reverse=True)[:4]
    shooters = sorted(
        [p for p in players if p["three_point_attempts"] >= 2],
        key=lambda p: (float(str(p["three_point_percentage"]).replace("%", "")), p["three_point_attempts"]),
        reverse=True
    )[:4]
    defenders = sorted(players, key=lambda p: (p["rebounds"] + p["blocks"] + p["steals"]), reverse=True)[:5]

    def names(group):
        return ", ".join([p["name"] for p in group]) if group else "no clear group"

    report = f"""
# Executive Summary

This roster projects as a **{m['identity']}** with a **{m['grade']}** grade and **{m['projected_wins']} projected wins**. Payroll sits at **{m['payroll']}** against a **{m['salary_cap']}** cap.

This built-in report is a basic fallback. For the full autonomous ChatGPT-style report, set your OpenAI API key and click Generate AI Report again.

# Offensive Identity

The primary offensive pressure comes from **{names(creators)}**. The key spacing pieces are **{names(shooters)}**.

This offense will work best when the creators force the defense to rotate and the shooters punish late closeouts.

# Defensive Blueprint

The defensive structure is most likely shaped by **{names(defenders)}**. The question is whether this group has enough point-of-attack resistance, rebounding, and back-line support to survive against better offenses.

# Final Verdict

The projection makes sense if the team's best traits show up consistently. If the roster lacks elite creation, rim protection, or role clarity, those weaknesses will show up quickly over a full season.
"""
    return report

def generate_ai_report(team_summary: dict) -> str:
    """
    AI report generation with real autonomy.

    The app provides:
    - full 13-man roster
    - selected role slots
    - clean player stats
    - team result metrics

    The model decides what actually matters.
    The only fixed structure is the four required headings.
    """
    api_key = OPENAI_API_KEY.strip()

    if OpenAI is None:
        return fallback_report(team_summary)

    if api_key == PLACEHOLDER_API_KEY or not api_key:
        return fallback_report(team_summary)

    client = OpenAI(api_key=api_key)

    # Keep the payload clean. Do not pre-label "top creators", "top defenders",
    # "best shooter", etc. Let the AI reason from the roster.
    ai_payload = {
        "team_result": {
            "draft_grade": team_summary["team_metrics"]["grade"],
            "projected_wins": team_summary["team_metrics"]["projected_wins"],
            "team_identity": team_summary["team_metrics"]["identity"],
            "payroll": team_summary["team_metrics"]["payroll"],
            "salary_cap": team_summary["team_metrics"]["salary_cap"],
            "remaining_cap": team_summary["team_metrics"].get("remaining_cap"),
            "salary_context": {
                "payroll_formatted": team_summary["team_metrics"]["payroll"],
                "salary_cap_formatted": team_summary["team_metrics"]["salary_cap"],
                "remaining_cap_formatted": team_summary["team_metrics"]["remaining_cap"],
                "payroll_raw": team_summary["team_metrics"].get("payroll_raw"),
                "salary_cap_raw": team_summary["team_metrics"].get("salary_cap_raw"),
                "remaining_cap_raw": team_summary["team_metrics"].get("remaining_cap_raw"),
                "format_rule": "Always write salaries like $211.7M, $222.0M, or $10.3M. Never write 211.7millionagainsta222 million cap."
            },
            "overall_score": team_summary["team_metrics"]["overall_score"],
            "category_scores": {
                "creation": team_summary["team_metrics"].get("creation_score", team_summary["team_metrics"].get("offense_score")),
                "shooting": team_summary["team_metrics"]["shooting_score"],
                "defense": team_summary["team_metrics"]["defense_score"],
                "rebounding": team_summary["team_metrics"].get("rebounding_score"),
                "star_power": team_summary["team_metrics"].get("star_power"),
                "depth": team_summary["team_metrics"]["depth_score"],
                "fit": team_summary["team_metrics"]["fit_score"],
                "versatility": team_summary["team_metrics"].get("versatility_score"),
                "talent_concentration": team_summary["team_metrics"].get("talent_concentration_score"),
            }
        },
        "roster": [
            {
                "slot": p["slot"],
                "player": p["name"],
                "listed_position": p["actual_position"],
                "team": p["team"],
                "salary": p["salary"],
                "ppg": p["points"],
                "apg": p["assists"],
                "rpg": p["rebounds"],
                "spg": p["steals"],
                "bpg": p["blocks"],
                "three_point_percentage": p["three_point_percentage"],
                "three_point_attempts": p["three_point_attempts"],
                "true_shooting": p["true_shooting"],
                "role": p["role"],
                "fit_label": p["fit_label"],
                "fit_notes": p["fit_notes"],
            }
            for p in team_summary["players"]
        ],
        "instructions": {
            "required_headings": [
                "Executive Summary",
                "Offensive Identity",
                "Defensive Blueprint",
                "Salary Cap Analysis",
                "Final Verdict"
            ],
            "autonomy": "You decide what the roster's real story is. Do not follow a hidden template.",
            "important": [
                "Only mention players on this roster.",
                "Do not mention outside examples.",
                "Do not use a generic report pattern.",
                "Do not force equal coverage of every stat category.",
                "Explain why the projected wins make sense.",
                "Use basketball language first and stats second.",
                "Use stats naturally and sparingly.",
                "Do not mention custom defensive score, BPM, DBPM, OBPM, player quality score, or fit adjustment numbers.",
                "Do not say the same phrases every report.",
                "Make the report feel like a fresh answer from ChatGPT to this specific roster."
            ]
        }
    }

    prompt = f"""
You are ChatGPT acting as an NBA front office analyst.

Write a fresh, original scouting report for the custom roster below.

You have autonomy. Think about the roster first, then write the report.
Do not simply fill in a template.
Do not write the same kind of report every time.
Do not just change the names from a previous report.

You must use exactly these five section headings and no others:

# Executive Summary
# Offensive Identity
# Defensive Blueprint
# Salary Cap Analysis
# Final Verdict

Within those four sections, you decide what matters most.

Before writing, silently identify the roster's biggest basketball story:
- Is this a defense-and-depth team?
- Is it a superteam or historic superteam?
- Is it a shooting-heavy team?
- Is it a team with good role players but no true offensive engine?
- Is it positionally weird?
- Is it deep but lacking top-end talent?
- Is it talented but poorly balanced?

Build the entire report around that specific story.

Strict rules:
- Only discuss players who are actually on the roster.
- Never mention outside player examples.
- Do not mention custom defensive score, BPM, DBPM, OBPM, player quality score, or fit adjustment numbers.
- You may mention normal basketball stats naturally, especially PPG/APG/RPG and shooting percentages.
- Do not overhype the team if the projected wins are low.
- If the projection is around 40 wins, write like this is a competitive but flawed team.
- If the projection is around 50 wins, write like this is a strong playoff team with limitations.
- If the projection is 60+ wins, write like this is a serious contender.
- If the projection is 70+ wins, write like this is a dominant superteam.
- If the identity says Historic Superteam, make the report feel like the roster has broken normal roster-building rules.
- Explain role fit using the actual selected slots: Starting PG, Starting SG, Starting SF, Starting PF, Starting C, Bench 1 through Bench 8, Two-Way.
- If a player is out of position, explain how that affects the roster.
- Avoid repetitive phrases like "the roster is built around" unless it truly fits.
- Sound like a real basketball analyst, not a spreadsheet.
- Evaluate the roster as both a basketball team and a front-office asset.
- In Salary Cap Analysis, discuss payroll, salary cap level, cap flexibility, luxury-tax/apron pressure, best-value contracts, and expensive contracts when relevant.
- Do not simply list salaries; explain what the financial structure means for team-building.
- Always format money cleanly, like "$211.7M payroll against a $222.0M cap."
- Never write salary text without spaces, such as "211.7millionagainsta222 million cap."

Roster and team data:
{json.dumps(ai_payload, indent=2)}
"""

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt,
        temperature=1.05
    )

    return response.output_text

def get_team_hash(team_summary: dict) -> str:
    raw = json.dumps(team_summary, sort_keys=True)
    return hashlib.md5(raw.encode()).hexdigest()


# ============================================================
# SESSION STATE
# ============================================================

if "roster" not in st.session_state:
    st.session_state.roster = {}

if "reports" not in st.session_state:
    st.session_state.reports = {}

if "player_select_reset" not in st.session_state:
    st.session_state.player_select_reset = 0

if "roster_size" not in st.session_state:
    st.session_state.roster_size = DEFAULT_ROSTER_SIZE

if "active_salary_cap" not in st.session_state:
    st.session_state.active_salary_cap = DEFAULT_SALARY_CAP

if "quick_add_slot" not in st.session_state:
    st.session_state.quick_add_slot = None

active_roster_slots = ROSTER_SLOTS[:st.session_state.roster_size]


# ============================================================
# SIMPLE UI HELPERS
# ============================================================

import base64


def image_to_base64(path: str) -> str:
    try:
        with open(path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except Exception:
        return ""


def clear_reports():
    st.session_state.reports = {}


def add_player_to_slot(player_row: pd.Series, slot: str):
    selected_player = player_row.to_dict()
    selected_player["Slot"] = slot

    fit, notes = calculate_position_fit(pd.Series(selected_player), slot)
    selected_player["Fit_Adjustment"] = fit
    selected_player["Fit_Notes"] = "; ".join(notes)

    st.session_state.roster[slot] = selected_player
    clear_reports()


def remove_player_from_slot(slot: str):
    if slot in st.session_state.roster:
        del st.session_state.roster[slot]
        clear_reports()


def roster_dataframe_for_display() -> pd.DataFrame:
    rows = []
    for slot in active_roster_slots:
        if slot in st.session_state.roster:
            p = st.session_state.roster[slot]
            rows.append({
                "Slot": slot,
                "Player": p["Player"],
                "Team": p["Team"],
                "Pos": p["Pos"],
                "Salary": money(p["Salary"]),
                "PPG": round(float(p["PTS"]), 1),
                "APG": round(float(p["AST"]), 1),
                "RPG": round(float(p["TRB"]), 1),
            })
        else:
            rows.append({
                "Slot": slot,
                "Player": "— Empty —",
                "Team": "",
                "Pos": "",
                "Salary": "",
                "PPG": "",
                "APG": "",
                "RPG": "",
            })
    return pd.DataFrame(rows)


# ============================================================
# SLEEK MOBILE-FIRST UI
# ============================================================

st.markdown(
    """
<style>
/* Hide Streamlit chrome for app-like feel */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

.block-container {
    padding-top: 0.8rem !important;
    padding-bottom: 6rem !important;
    max-width: 920px !important;
}

.app-topbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 18px;
}

.app-brand {
    display: flex;
    align-items: center;
    gap: 12px;
}

.app-logo-mark {
    width: 44px;
    height: 44px;
    border-radius: 14px;
    display: grid;
    place-items: center;
    background: rgba(14, 165, 233, .12);
    border: 1px solid rgba(56, 189, 248, .35);
    color: #0ea5e9;
    font-size: 26px;
}

.app-title {
    color: #f8fafc;
    font-size: 25px;
    line-height: 1.0;
    font-weight: 950;
    letter-spacing: -0.03em;
    text-transform: uppercase;
}

.app-subtitle {
    color: #38bdf8;
    font-size: 12px;
    font-weight: 900;
    letter-spacing: .30em;
    text-transform: uppercase;
    margin-top: 3px;
}

.app-topbar-left {
    display: flex;
    align-items: center;
    margin-bottom: 18px;
}

.app-logo-img {
    width: 54px;
    height: 54px;
    border-radius: 15px;
    object-fit: contain;
    background: rgba(14, 165, 233, .08);
    border: 1px solid rgba(56, 189, 248, .35);
    padding: 5px;
}

/* Functional hamburger menu button */
div[data-testid="stPopover"] button {
    min-height: 52px !important;
    border-radius: 16px !important;
    background: rgba(15, 23, 42, .82) !important;
    border: 1px solid rgba(148, 163, 184, .22) !important;
    color: #cbd5e1 !important;
    font-size: 25px !important;
    font-weight: 950 !important;
    text-align: center !important;
    box-shadow: none !important;
}

@media (max-width: 700px) {
    .app-logo-img {
        width: 48px;
        height: 48px;
        border-radius: 14px;
    }
}

.overview-card {
    background:
        radial-gradient(circle at top right, rgba(14, 165, 233, .18), transparent 38%),
        linear-gradient(145deg, rgba(15, 23, 42, .98), rgba(2, 6, 23, .98));
    border: 1px solid rgba(148, 163, 184, .22);
    border-radius: 28px;
    padding: 22px;
    box-shadow: 0 18px 55px rgba(0, 0, 0, .40);
    margin-bottom: 22px;
}

.card-heading {
    color: #b8c7de;
    font-size: 15px;
    font-weight: 950;
    text-transform: uppercase;
    letter-spacing: .08em;
    margin-bottom: 18px;
}

.overview-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 0;
    border-bottom: 1px solid rgba(148, 163, 184, .14);
    padding-bottom: 18px;
    margin-bottom: 20px;
}

.overview-metric {
    padding: 0 14px;
    border-right: 1px solid rgba(148, 163, 184, .16);
    min-height: 78px;
}

.overview-metric:last-child {border-right: none;}

.overview-label {
    color: #9fb0c8;
    font-size: 12px;
    font-weight: 900;
    text-transform: uppercase;
    letter-spacing: .04em;
    margin-bottom: 8px;
}

.overview-value {
    color: #f8fafc;
    font-size: 33px;
    line-height: 1;
    font-weight: 950;
    letter-spacing: -0.045em;
}

.overview-note {
    color: #0ea5e9;
    font-size: 15px;
    font-weight: 900;
    margin-top: 7px;
}

.good-note { color: #22c55e !important; }
.bad-note { color: #ef4444 !important; }

.cap-track {
    height: 15px;
    border-radius: 999px;
    background: rgba(51, 65, 85, .62);
    overflow: hidden;
    margin: 10px 0 18px 0;
    border: 1px solid rgba(148, 163, 184, .10);
}

.cap-fill {
    height: 100%;
    border-radius: 999px;
    background: linear-gradient(90deg, #22c55e 0%, #facc15 72%, #ef4444 100%);
}

.cap-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
}

.cap-label {
    color: #94a3b8;
    font-size: 12px;
    font-weight: 850;
    text-transform: uppercase;
}

.cap-value {
    color: #f8fafc;
    font-size: 18px;
    font-weight: 900;
    margin-top: 2px;
}

.section-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin: 22px 0 10px 0;
}

.section-heading-mobile {
    color: #cbd5e1;
    font-size: 22px;
    font-weight: 950;
    letter-spacing: -0.025em;
    text-transform: uppercase;
}

.section-action {
    color: #0ea5e9;
    font-size: 14px;
    font-weight: 900;
}

.roster-list {
    display: flex;
    flex-direction: column;
    gap: 10px;
}

.player-row-card {
    display: grid;
    grid-template-columns: 52px 62px 1fr 88px 18px;
    gap: 12px;
    align-items: center;
    background: linear-gradient(145deg, rgba(15, 23, 42, .96), rgba(3, 7, 18, .96));
    border: 1px solid rgba(148, 163, 184, .17);
    border-radius: 18px;
    padding: 10px 12px;
    box-shadow: 0 10px 28px rgba(0,0,0,.22);
}

.slot-pill {
    color: #0ea5e9;
    font-size: 19px;
    font-weight: 950;
    text-align: center;
}

.avatar-circle {
    width: 58px;
    height: 58px;
    border-radius: 18px;
    display: grid;
    place-items: center;
    background: radial-gradient(circle at 30% 20%, rgba(56, 189, 248, .28), rgba(15, 23, 42, .95));
    border: 1px solid rgba(56, 189, 248, .26);
    color: #f8fafc;
    font-weight: 950;
    font-size: 18px;
}

.player-headshot {
    width: 58px;
    height: 58px;
    border-radius: 18px;
    object-fit: cover;
    object-position: center top;
    background: radial-gradient(circle at 30% 20%, rgba(56, 189, 248, .22), rgba(15, 23, 42, .95));
    border: 1px solid rgba(56, 189, 248, .35);
    box-shadow: inset 0 0 22px rgba(14, 165, 233, .08);
}

.player-name-mobile {
    color: #f8fafc;
    font-size: 18px;
    font-weight: 950;
    line-height: 1.1;
}

.player-role-mobile {
    color: #94a3b8;
    font-size: 14px;
    margin-top: 4px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.player-right-mobile {
    text-align: right;
}

.player-ovr-mobile {
    color: #0ea5e9;
    font-size: 14px;
    font-weight: 950;
}

.player-salary-mobile {
    color: #f8fafc;
    font-size: 17px;
    font-weight: 900;
    margin-top: 4px;
}

.chev-mobile {
    color: #cbd5e1;
    font-size: 26px;
    font-weight: 200;
}

.add-player-hero {
    background: linear-gradient(135deg, #0284c7, #0ea5e9);
    color: white;
    border-radius: 18px;
    padding: 17px 18px;
    text-align: center;
    font-size: 19px;
    font-weight: 950;
    letter-spacing: .02em;
    margin: 18px 0;
    box-shadow: 0 16px 42px rgba(14, 165, 233, .28);
}

.empty-card {
    background: rgba(15, 23, 42, .62);
    border: 1px dashed rgba(148, 163, 184, .32);
    border-radius: 18px;
    padding: 16px;
    color: #94a3b8;
    text-align: center;
    font-weight: 800;
}


.empty-slot-link {
    display: block;
    text-decoration: none !important;
    color: inherit !important;
}

.empty-slot-link:hover {
    text-decoration: none !important;
}

.empty-player-card {
    opacity: .78;
    grid-template-columns: 52px 62px 1fr 88px 18px;
    cursor: pointer;
}

.empty-player-card:hover {
    opacity: 1;
    border-color: rgba(14, 165, 233, .42);
    transform: translateY(-1px);
}

.plus-box {
    width: 58px;
    height: 58px;
    border-radius: 18px;
    display: grid;
    place-items: center;
    background: radial-gradient(circle at 30% 20%, rgba(56, 189, 248, .24), rgba(15, 23, 42, .95));
    border: 1px solid rgba(14, 165, 233, .35);
    color: #cbd5e1;
    font-size: 26px;
    font-weight: 950;
    box-shadow: inset 0 0 22px rgba(14, 165, 233, .08);
}

.action-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
    margin: 18px 0 26px 0;
}

.action-tile-mobile {
    background: linear-gradient(145deg, rgba(15, 23, 42, .98), rgba(2, 6, 23, .98));
    border: 1px solid rgba(148, 163, 184, .18);
    border-radius: 18px;
    padding: 18px 8px;
    text-align: center;
    min-height: 92px;
}

.action-icon-mobile {
    font-size: 28px;
    color: #0ea5e9;
    margin-bottom: 8px;
}

.action-label-mobile {
    color: #cbd5e1;
    font-size: 12px;
    font-weight: 950;
    text-transform: uppercase;
}

.draft-card {
    background: linear-gradient(145deg, rgba(15, 23, 42, .98), rgba(2, 6, 23, .98));
    border: 1px solid rgba(148, 163, 184, .17);
    border-radius: 20px;
    padding: 16px;
    margin-bottom: 14px;
}

.small-muted {
    color: #94a3b8;
    font-size: 13px;
    line-height: 1.45;
}

/* Tabs as bottom-nav style */
div[data-testid="stTabs"] > div:first-child {
    position: sticky;
    bottom: 0;
    z-index: 999;
    background: rgba(2, 6, 23, .96);
    border: 1px solid rgba(148, 163, 184, .18);
    border-radius: 22px;
    padding: 8px;
    margin-top: 24px;
    backdrop-filter: blur(18px);
}

div[data-testid="stTabs"] button {
    border-radius: 16px !important;
    color: #94a3b8 !important;
    font-weight: 900 !important;
}

div[data-testid="stTabs"] button[aria-selected="true"] {
    background: rgba(14, 165, 233, .15) !important;
    color: #38bdf8 !important;
}

.stButton > button {
    border-radius: 15px !important;
    min-height: 46px;
    font-weight: 900 !important;
}

/* Mobile-safe empty roster-slot buttons */
div[data-testid="stButton"] > button {
    background: linear-gradient(145deg, rgba(15, 23, 42, .96), rgba(3, 7, 18, .96));
    border: 1px solid rgba(148, 163, 184, .17);
    color: #f8fafc;
    box-shadow: 0 10px 28px rgba(0,0,0,.22);
    text-align: left;
    white-space: pre-line;
    line-height: 1.35;
}

div[data-testid="stButton"] > button:hover {
    border-color: rgba(14, 165, 233, .48);
    background: linear-gradient(145deg, rgba(15, 23, 42, 1), rgba(7, 12, 25, 1));
    color: #f8fafc;
}

@media (max-width: 700px) {
    .block-container {
        padding-left: .75rem !important;
        padding-right: .75rem !important;
    }
    .app-title { font-size: 20px; }
    .app-subtitle { font-size: 10px; }
    .overview-card { padding: 18px; border-radius: 24px; }
    .overview-grid { grid-template-columns: repeat(2, 1fr); row-gap: 18px; }
    .overview-metric:nth-child(2) { border-right: none; }
    .overview-value { font-size: 31px; }
    .cap-grid { grid-template-columns: repeat(2, 1fr); }
    .player-row-card { grid-template-columns: 38px 48px 1fr 76px 12px; gap: 8px; padding: 9px 10px; }
    .empty-player-card { grid-template-columns: 38px 48px 1fr 76px 12px; }
    .plus-box { width: 46px; height: 46px; border-radius: 14px; font-size: 22px; }
    .avatar-circle { width: 46px; height: 46px; border-radius: 14px; font-size: 15px; }
    .player-headshot { width: 46px; height: 46px; border-radius: 14px; }
    .slot-pill { font-size: 16px; }
    .player-name-mobile { font-size: 15px; }
    .player-role-mobile { font-size: 12px; }
    .player-salary-mobile { font-size: 14px; }
    .action-grid { grid-template-columns: repeat(2, 1fr); }
}
</style>
""",
    unsafe_allow_html=True
)




st.markdown(
    """
<style>
/* ============================================================
   MODERN ADD PLAYER DIALOG
   ============================================================ */
div[role="dialog"] {
    background: radial-gradient(circle at top left, rgba(14, 165, 233, .12), transparent 32%),
                linear-gradient(145deg, #030712, #07111f 56%, #020617) !important;
    border: 1px solid rgba(148, 163, 184, .22) !important;
    border-radius: 26px !important;
    box-shadow: 0 24px 80px rgba(0, 0, 0, .58) !important;
}

.dialog-hero-title {
    color: #f8fafc;
    font-size: 28px;
    font-weight: 950;
    letter-spacing: -0.035em;
    margin: 4px 0 2px 0;
}

.dialog-hero-title span { color: #38bdf8; }

.dialog-hero-sub {
    color: #a8b3c7;
    font-size: 15px;
    margin-bottom: 18px;
}

.dialog-filter-shell {
    background: linear-gradient(145deg, rgba(15, 23, 42, .86), rgba(2, 6, 23, .78));
    border: 1px solid rgba(148, 163, 184, .20);
    border-radius: 18px;
    padding: 12px 13px 4px 13px;
    margin-bottom: 14px;
}

.dialog-search-shell {
    background: linear-gradient(145deg, rgba(15, 23, 42, .88), rgba(2, 6, 23, .80));
    border: 1px solid rgba(148, 163, 184, .20);
    border-radius: 18px;
    padding: 10px 13px 2px 13px;
    margin: 14px 0 16px 0;
}

.dialog-section-row {
    display:flex;
    align-items:flex-end;
    justify-content:space-between;
    margin: 14px 0 8px 0;
}

.dialog-section-title {
    color:#f8fafc;
    font-size:18px;
    font-weight:950;
    letter-spacing:-.02em;
}

.dialog-section-note {
    color:#94a3b8;
    font-size:12px;
    font-weight:750;
}

.suggest-card {
    min-height: 152px;
    background: radial-gradient(circle at top, rgba(56, 189, 248, .14), transparent 45%),
                linear-gradient(145deg, rgba(15, 23, 42, .96), rgba(2, 6, 23, .94));
    border: 1px solid rgba(148, 163, 184, .22);
    border-radius: 15px;
    padding: 10px 8px;
    text-align: center;
    box-shadow: 0 12px 30px rgba(0,0,0,.23);
    margin-bottom: 8px;
}

.suggest-pos {
    display:inline-block;
    color:#38bdf8;
    border:1px solid rgba(56,189,248,.45);
    border-radius: 8px;
    padding: 2px 6px;
    font-size: 10px;
    font-weight: 950;
    margin-bottom: 5px;
}

.suggest-img-wrap img, .suggest-img-wrap .avatar-circle {
    width: 50px !important;
    height: 50px !important;
    border-radius: 15px !important;
    margin: 0 auto 6px auto;
}

.suggest-name {
    color:#f8fafc;
    font-size:12px;
    line-height:1.15;
    font-weight:950;
    min-height: 28px;
}

.suggest-meta {
    color:#94a3b8;
    font-size:10px;
    margin-top:3px;
    white-space:nowrap;
    overflow:hidden;
    text-overflow:ellipsis;
}

.suggest-salary {
    color:#38bdf8;
    font-size:13px;
    font-weight:950;
    margin-top:4px;
}



/* Suggested player rail: always one horizontal row, including mobile. */
.suggest-rail {
    display: grid;
    grid-template-columns: repeat(5, minmax(0, 1fr));
    gap: 10px;
    overflow: hidden;
    padding: 4px 0 12px 0;
    margin-bottom: 10px;
}

.suggest-card-link {
    text-decoration: none !important;
    color: inherit !important;
    display: block;
    min-width: 0;
}

.suggest-card-link:hover .suggest-card {
    border-color: rgba(56, 189, 248, .65);
    transform: translateY(-2px);
}

.suggest-card-link .suggest-card {
    transition: transform .16s ease, border-color .16s ease, box-shadow .16s ease;
}

.suggest-add-mini {
    margin-top: 7px;
    border: 1px solid rgba(56, 189, 248, .55);
    background: rgba(14, 165, 233, .10);
    color: #38bdf8;
    border-radius: 10px;
    padding: 6px 8px;
    font-size: 12px;
    font-weight: 950;
}

@media (max-width: 700px) {
    .suggest-rail {
        grid-template-columns: repeat(5, minmax(0, 1fr));
        gap: 6px;
        padding-bottom: 8px;
        margin-left: 0;
        margin-right: 0;
    }

    .suggest-card {
        min-height: 132px !important;
        padding: 7px 4px !important;
        border-radius: 12px !important;
    }

    .suggest-pos {
        font-size: 8px !important;
        padding: 1px 4px !important;
        border-radius: 6px !important;
        margin-bottom: 4px !important;
    }

    .suggest-img-wrap img, .suggest-img-wrap .avatar-circle {
        width: 38px !important;
        height: 38px !important;
        border-radius: 11px !important;
        margin-bottom: 4px !important;
    }

    .suggest-name {
        font-size: 9px !important;
        line-height: 1.1 !important;
        min-height: 30px !important;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }

    .suggest-meta {
        font-size: 8px !important;
    }

    .suggest-salary {
        font-size: 10px !important;
        margin-top: 3px !important;
    }

    .suggest-add-mini {
        font-size: 9px !important;
        padding: 4px 3px !important;
        margin-top: 5px !important;
        border-radius: 8px !important;
    }
}

.player-result-card {
    display:grid;
    grid-template-columns: 64px 1fr 92px 80px;
    gap: 12px;
    align-items:center;
    background: linear-gradient(145deg, rgba(15,23,42,.96), rgba(2,6,23,.94));
    border: 1px solid rgba(148,163,184,.18);
    border-radius: 17px;
    padding: 10px 12px;
    margin-bottom: 8px;
    box-shadow: 0 8px 24px rgba(0,0,0,.20);
}

.result-name {
    color:#f8fafc;
    font-size:17px;
    font-weight:950;
    line-height:1.1;
}

.result-meta {
    color:#94a3b8;
    font-size:13px;
    margin-top:3px;
    line-height:1.35;
}

.result-salary {
    color:#f8fafc;
    font-size:19px;
    font-weight:950;
    text-align:right;
}

.result-salary-label {
    color:#94a3b8;
    font-size:12px;
    text-align:right;
}

@media (max-width: 700px) {
    .dialog-hero-title { font-size: 25px; }
    .dialog-hero-sub { font-size: 14px; }
    .player-result-card { grid-template-columns: 50px 1fr 70px; gap: 8px; padding: 9px 10px; }
    .player-result-card .player-headshot, .player-result-card .avatar-circle { width: 48px !important; height: 48px !important; border-radius: 14px !important; }
    .result-name { font-size: 14px; }
    .result-meta { font-size: 11px; }
    .result-salary { font-size: 14px; }
    .result-salary-label { font-size: 10px; }
}



</style>
""",
    unsafe_allow_html=True
)


# ----------------------------
# UI helpers
# ----------------------------

def slot_short(slot: str) -> str:
    mapping = {
        "Starting PG": "PG",
        "Starting SG": "SG",
        "Starting SF": "SF",
        "Starting PF": "PF",
        "Starting C": "C",
        "Bench 1": "B1",
        "Bench 2": "B2",
        "Bench 3": "B3",
        "Bench 4": "B4",
        "Bench 5": "B5",
        "Two-Way 1": "2W1",
        "Two-Way 2": "2W2",
        "Bench 6": "B6",
        "Bench 7": "B7",
        "Bench 8": "B8",
    }
    return mapping.get(slot, slot[:3].upper())


def initials(name: str) -> str:
    parts = str(name).replace(".", " ").split()
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()


def player_headshot_html(row) -> str:
    """Return a real NBA headshot when HeadshotURL exists; otherwise show initials."""
    try:
        name = str(row.get("Player", ""))
        url = str(row.get("HeadshotURL", "") or "").strip()
    except Exception:
        name = ""
        url = ""

    if url and url.lower() not in {"nan", "none", "null"} and url.startswith("http"):
        return f'<img class="player-headshot" src="{url}" />'

    return f'<div class="avatar-circle">{initials(name)}</div>'


def compact_role(row: dict) -> str:
    try:
        role = get_player_role(pd.Series(row))
    except Exception:
        role = "Rotation Piece"
    return role.split(",")[0]


def roster_to_df() -> pd.DataFrame:
    rows = []
    for slot in active_roster_slots:
        if slot in st.session_state.roster:
            p = st.session_state.roster[slot].copy()
            p["Slot"] = slot
            rows.append(p)
    return pd.DataFrame(rows)


def current_metrics(salary_cap: int):
    r_df = roster_to_df()
    if len(r_df) >= MIN_RESULTS_PLAYERS:
        return calculate_team_metrics(r_df, salary_cap)
    return None


def render_topbar():
    """Top app bar with real logo + functional hamburger menu."""
    logo_b64 = image_to_base64(LOGO_PATH)

    if logo_b64:
        logo_html = f'<img class="app-logo-img" src="data:image/png;base64,{logo_b64}" />'
    else:
        logo_html = '<div class="app-logo-mark">🏀</div>'

    brand_col, menu_col = st.columns([0.84, 0.16], vertical_alignment="center")

    with brand_col:
        st.markdown(
            f"""
            <div class="app-topbar-left">
                <div class="app-brand">
                    {logo_html}
                    <div>
                        <div class="app-title">Front Office</div>
                        <div class="app-subtitle">Simulator</div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with menu_col:
        with st.popover("☰", use_container_width=True):
            st.markdown("### Menu")
            st.caption("Quick controls for roster setup and app navigation.")

            if st.button("🆕 New Team", use_container_width=True):
                st.session_state.roster = {}
                st.session_state.reports = {}
                st.rerun()

            st.divider()

            preset_options = ["New Team"] + sorted(PRESET_ROSTERS.keys())
            preset_choice_menu = st.selectbox(
                "Preset Roster",
                preset_options,
                index=0,
                key="top_menu_preset_choice"
            )

            if st.button("Load Preset", type="primary", use_container_width=True, key="top_menu_load_preset"):
                if preset_choice_menu == "New Team":
                    st.session_state.roster = {}
                    st.session_state.reports = {}
                else:
                    loaded, missing = load_preset_roster(
                        preset_choice_menu,
                        st.session_state.roster_size,
                        df
                    )
                    st.session_state.roster = loaded
                    st.session_state.reports = {}
                    if missing:
                        st.warning("Missing: " + ", ".join(missing))
                st.rerun()

            st.divider()

            new_roster_size = st.selectbox(
                "Roster Size",
                list(range(9, 16)),
                index=list(range(9, 16)).index(st.session_state.roster_size),
                key="top_menu_roster_size"
            )

            if new_roster_size != st.session_state.roster_size:
                st.session_state.roster_size = new_roster_size
                allowed_slots = ROSTER_SLOTS[:new_roster_size]
                for slot in list(st.session_state.roster.keys()):
                    if slot not in allowed_slots:
                        del st.session_state.roster[slot]
                st.session_state.reports = {}
                st.rerun()

            cap_choice_menu = st.selectbox(
                "Salary Level",
                list(SALARY_CAP_LEVELS.keys()),
                index=list(SALARY_CAP_LEVELS.values()).index(st.session_state.active_salary_cap)
                if st.session_state.active_salary_cap in SALARY_CAP_LEVELS.values()
                else list(SALARY_CAP_LEVELS.keys()).index("Second Apron"),
                key="top_menu_salary_choice"
            )

            if cap_choice_menu == "Custom":
                new_cap = st.number_input(
                    "Custom Salary Cap",
                    min_value=100_000_000,
                    max_value=700_000_000,
                    value=int(st.session_state.active_salary_cap),
                    step=5_000_000,
                    format="%d",
                    key="top_menu_custom_cap"
                )
            else:
                new_cap = SALARY_CAP_LEVELS[cap_choice_menu]

            if new_cap != st.session_state.active_salary_cap:
                st.session_state.active_salary_cap = int(new_cap)
                st.session_state.reports = {}
                st.rerun()

            st.divider()
            st.caption("Use the bottom tabs for Build, Players, Analysis, AI Report, and Settings.")


def render_overview(metrics, payroll: float, salary_cap: int):
    remaining = salary_cap - payroll
    if metrics:
        wins = metrics["projected_wins"]
        overall = metrics["overall_score"]
        identity = metrics["identity"]
        fit = metrics["fit_score"]
        grade = metrics["grade"]
    else:
        wins = "--"
        overall = "--"
        identity = f"Draft {MIN_RESULTS_PLAYERS}+ players"
        fit = "--"
        grade = "--"

    cap_pct = 0 if salary_cap <= 0 else min(max(payroll / salary_cap, 0), 1.25)
    fill_pct = min(cap_pct, 1.0) * 100
    rem_class = "good-note" if remaining >= 0 else "bad-note"
    rem_text = f"{money(abs(remaining))} {'under' if remaining >= 0 else 'over'}"

    st.markdown(
        f"""
        <div class="overview-card">
            <div class="card-heading">Team Overview</div>
            <div class="overview-grid">
                <div class="overview-metric">
                    <div class="overview-label">Projected Wins</div>
                    <div class="overview-value">{wins}</div>
                    <div class="overview-note">{identity}</div>
                </div>
                <div class="overview-metric">
                    <div class="overview-label">Grade</div>
                    <div class="overview-value">{grade}</div>
                    <div class="overview-note">OVR {overall}</div>
                </div>
                <div class="overview-metric">
                    <div class="overview-label">Payroll</div>
                    <div class="overview-value" style="font-size:29px;">{money(payroll)}</div>
                    <div class="overview-note {rem_class}">{rem_text}</div>
                </div>
                <div class="overview-metric">
                    <div class="overview-label">Chemistry</div>
                    <div class="overview-value">{fit}</div>
                    <div class="overview-note">Fit Score</div>
                </div>
            </div>
            <div class="card-heading" style="margin-bottom:8px;">Salary Cap Status</div>
            <div class="cap-track"><div class="cap-fill" style="width:{fill_pct:.1f}%;"></div></div>
            <div class="cap-grid">
                <div><div class="cap-label">Cap</div><div class="cap-value">$165.0M</div></div>
                <div><div class="cap-label">Tax</div><div class="cap-value">$201.0M</div></div>
                <div><div class="cap-label">1st Apron</div><div class="cap-value">$209.0M</div></div>
                <div><div class="cap-label">2nd Apron</div><div class="cap-value">$222.0M</div></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


@st.dialog("Add Player")
def salary_filter_label(value: float) -> str:
    if value < 5_000_000:
        return "Under $5M"
    if value < 15_000_000:
        return "$5M-$15M"
    if value < 30_000_000:
        return "$15M-$30M"
    return "$30M+"


def slot_target_positions(slot: str) -> list[str]:
    """Return the best position targets for this slot."""
    direct = {
        "Starting PG": ["PG"],
        "Starting SG": ["SG"],
        "Starting SF": ["SF"],
        "Starting PF": ["PF"],
        "Starting C": ["C"],
    }
    if slot in direct:
        return direct[slot]

    if "Two-Way" in slot:
        return ["PG", "SG", "SF", "PF", "C"]

    # Bench slots should fill positional needs from the current roster.
    ideal_counts = {"PG": 2, "SG": 2, "SF": 2, "PF": 2, "C": 2}
    current_counts = {k: 0 for k in ideal_counts}

    for player in st.session_state.roster.values():
        pos = str(player.get("Pos", ""))
        for p in current_counts:
            if p in pos:
                current_counts[p] += 1
                break

    needs = sorted(
        ideal_counts.keys(),
        key=lambda p: (current_counts[p] - ideal_counts[p], current_counts[p])
    )
    return needs[:3]


def player_matches_any_position(row, positions: list[str]) -> bool:
    pos = str(row.get("Pos", ""))
    return any(p in pos for p in positions)




st.markdown("""
<style>
/* FINAL MOBILE SUGGESTED PLAYER RAIL */
.suggest-scroll-row {
    display: flex !important;
    flex-direction: row !important;
    gap: 10px !important;
    overflow-x: auto !important;
    overflow-y: hidden !important;
    padding: 8px 0 14px 0 !important;
    margin: 0 0 12px 0 !important;
    scroll-snap-type: x mandatory;
    -webkit-overflow-scrolling: touch;
    width: 100%;
}
.suggest-card-link {
    flex: 0 0 132px !important;
    width: 132px !important;
    min-width: 132px !important;
    max-width: 132px !important;
    text-decoration: none !important;
    color: inherit !important;
    scroll-snap-align: start;
    display: block !important;
}
.suggest-card-link:visited, .suggest-card-link:hover, .suggest-card-link:active {
    color: inherit !important;
    text-decoration: none !important;
}
.suggest-scroll-row .suggest-card {
    height: 238px !important;
    min-height: 238px !important;
    box-sizing: border-box !important;
    background: radial-gradient(circle at top, rgba(14,165,233,.18), rgba(15,23,42,.96)) !important;
    border: 1px solid rgba(56,189,248,.28) !important;
    border-radius: 16px !important;
    padding: 10px 8px !important;
    text-align: center !important;
    margin: 0 !important;
    display: flex !important;
    flex-direction: column !important;
    align-items: center !important;
    box-shadow: 0 12px 30px rgba(0,0,0,.23) !important;
}
.suggest-scroll-row .suggest-pos {
    display: inline-block !important;
    color: #38bdf8 !important;
    border: 1px solid rgba(56,189,248,.55) !important;
    border-radius: 8px !important;
    padding: 2px 7px !important;
    font-size: 11px !important;
    font-weight: 950 !important;
    margin-bottom: 7px !important;
}
.suggest-scroll-row .suggest-img-wrap img, .suggest-scroll-row .suggest-img-wrap .avatar-circle {
    width: 52px !important;
    height: 52px !important;
    border-radius: 14px !important;
    margin: 0 auto 8px auto !important;
}
.suggest-scroll-row .suggest-name {
    color: #f8fafc !important;
    font-size: 13px !important;
    font-weight: 950 !important;
    line-height: 1.15 !important;
    min-height: 34px !important;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
}
.suggest-scroll-row .suggest-meta {
    color: #94a3b8 !important;
    font-size: 11px !important;
    margin-top: 7px !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
}
.suggest-scroll-row .suggest-salary {
    color: #38bdf8 !important;
    font-size: 14px !important;
    font-weight: 950 !important;
    margin-top: 7px !important;
}
.suggest-scroll-row .suggest-add-mini {
    margin-top: auto !important;
    width: 100% !important;
    box-sizing: border-box !important;
    border: 1px solid rgba(56,189,248,.58) !important;
    background: rgba(14,165,233,.10) !important;
    border-radius: 10px !important;
    padding: 6px 0 !important;
    color: #38bdf8 !important;
    font-weight: 950 !important;
    font-size: 12px !important;
}
@media (max-width: 700px) {
    .suggest-scroll-row { gap: 9px !important; padding-bottom: 12px !important; }
    .suggest-card-link { flex-basis: 118px !important; width: 118px !important; min-width: 118px !important; max-width: 118px !important; }
    .suggest-scroll-row .suggest-card { height: 228px !important; min-height: 228px !important; padding: 9px 7px !important; }
    .suggest-scroll-row .suggest-img-wrap img, .suggest-scroll-row .suggest-img-wrap .avatar-circle { width: 46px !important; height: 46px !important; }
    .suggest-scroll-row .suggest-name { font-size: 12px !important; min-height: 32px !important; }
}
</style>
""", unsafe_allow_html=True)

def dialog_sort_pool(player_pool: pd.DataFrame, sort_label: str) -> pd.DataFrame:
    if len(player_pool) == 0:
        return player_pool

    if sort_label == "Salary High-Low":
        return player_pool.sort_values(["Salary", "PTS"], ascending=[False, False])
    if sort_label == "Salary Low-High":
        return player_pool.sort_values(["Salary", "PTS"], ascending=[True, False])
    if sort_label == "APG":
        return player_pool.sort_values(["AST", "PTS", "MP"], ascending=[False, False, False])
    if sort_label == "RPG":
        return player_pool.sort_values(["TRB", "PTS", "MP"], ascending=[False, False, False])
    if sort_label == "TS%":
        # Require some usage so tiny-minute efficiency does not dominate.
        return player_pool.sort_values(["TS%", "PTS", "MP"], ascending=[False, False, False])

    # Default: PPG
    return player_pool.sort_values(["PTS", "AST", "TRB", "MP"], ascending=[False, False, False, False])


def base_available_player_pool() -> pd.DataFrame:
    player_pool = df.copy()
    selected_players = [p["Player"] for p in st.session_state.roster.values()]
    return player_pool[~player_pool["Player"].isin(selected_players)].copy()


def apply_dialog_filters(player_pool: pd.DataFrame, team_filter: str, position_filter: str, salary_filter: str, search_query: str) -> pd.DataFrame:
    if team_filter != "All Teams":
        player_pool = player_pool[player_pool["Team"] == team_filter]

    if position_filter != "All Positions":
        player_pool = player_pool[player_pool["Pos"].astype(str).str.contains(position_filter, na=False)]

    if salary_filter != "All Salaries":
        if salary_filter == "Under $5M":
            player_pool = player_pool[player_pool["Salary"] < 5_000_000]
        elif salary_filter == "$5M-$15M":
            player_pool = player_pool[(player_pool["Salary"] >= 5_000_000) & (player_pool["Salary"] < 15_000_000)]
        elif salary_filter == "$15M-$30M":
            player_pool = player_pool[(player_pool["Salary"] >= 15_000_000) & (player_pool["Salary"] < 30_000_000)]
        elif salary_filter == "$30M+":
            player_pool = player_pool[player_pool["Salary"] >= 30_000_000]

    q = str(search_query or "").strip()
    if q:
        q_norm = normalize_name_for_match(q)
        name_norm = player_pool["Player"].apply(normalize_name_for_match)
        team_norm = player_pool["Team"].astype(str).str.lower()
        pos_norm = player_pool["Pos"].astype(str).str.lower()
        profile_norm = player_pool.get(
            "PlayerProfile",
            pd.Series([""] * len(player_pool), index=player_pool.index)
        ).astype(str).str.lower()

        player_pool = player_pool[
            name_norm.str.contains(q_norm, na=False) |
            team_norm.str.contains(q.lower(), na=False) |
            pos_norm.str.contains(q.lower(), na=False) |
            profile_norm.str.contains(q.lower(), na=False)
        ].copy()

        if len(player_pool) > 0:
            name_norm_after = player_pool["Player"].apply(normalize_name_for_match)
            player_pool["Search_Priority"] = 3
            player_pool.loc[name_norm_after == q_norm, "Search_Priority"] = 0
            player_pool.loc[name_norm_after.str.startswith(q_norm, na=False), "Search_Priority"] = 1
            player_pool.loc[name_norm_after.str.contains(q_norm, na=False), "Search_Priority"] = 2

    return player_pool


def build_dialog_player_pool(slot: str, team_filter: str, position_filter: str, salary_filter: str, search_query: str, sort_label: str) -> pd.DataFrame:
    """Modern dialog player search with normalized search and clean sort options."""
    player_pool = base_available_player_pool()
    player_pool = apply_dialog_filters(player_pool, team_filter, position_filter, salary_filter, search_query)

    if len(player_pool) == 0:
        return player_pool

    if str(search_query or "").strip():
        # Search relevance first, then chosen basketball sort.
        sorted_pool = dialog_sort_pool(player_pool, sort_label)
        if "Search_Priority" in sorted_pool.columns:
            if sort_label == "Salary High-Low":
                sorted_pool = sorted_pool.sort_values(["Search_Priority", "Salary", "PTS"], ascending=[True, False, False])
            elif sort_label == "Salary Low-High":
                sorted_pool = sorted_pool.sort_values(["Search_Priority", "Salary", "PTS"], ascending=[True, True, False])
            elif sort_label == "APG":
                sorted_pool = sorted_pool.sort_values(["Search_Priority", "AST", "PTS", "MP"], ascending=[True, False, False, False])
            elif sort_label == "RPG":
                sorted_pool = sorted_pool.sort_values(["Search_Priority", "TRB", "PTS", "MP"], ascending=[True, False, False, False])
            elif sort_label == "TS%":
                sorted_pool = sorted_pool.sort_values(["Search_Priority", "TS%", "PTS", "MP"], ascending=[True, False, False, False])
            else:
                sorted_pool = sorted_pool.sort_values(["Search_Priority", "PTS", "AST", "TRB", "MP"], ascending=[True, False, False, False, False])
        return sorted_pool

    return dialog_sort_pool(player_pool, sort_label)



def current_roster_payroll() -> float:
    return float(sum(float(p.get("Salary", 0) or 0) for p in st.session_state.roster.values()))


def open_slots_after_filling(slot: str) -> list[str]:
    return [
        s for s in active_roster_slots
        if s != slot and s not in st.session_state.roster
    ]


def salary_room_for_suggestion(slot: str) -> dict:
    """
    Suggested players should be realistic, not just the best player available.
    This caps suggestions so the player:
    - does not put the team over the selected salary cap
    - leaves a minimum-salary buffer for every remaining empty slot
    """
    salary_cap = int(st.session_state.get("active_salary_cap", DEFAULT_SALARY_CAP))
    payroll = current_roster_payroll()
    open_after = open_slots_after_filling(slot)

    # Conservative placeholder for the cost of filling future open spots.
    # This prevents suggestions from burning the final cap room on one player.
    min_future_slot_cost = 2_000_000
    future_buffer = len(open_after) * min_future_slot_cost

    cap_room_now = salary_cap - payroll
    preferred_max_salary = cap_room_now - future_buffer

    return {
        "salary_cap": salary_cap,
        "payroll": payroll,
        "cap_room_now": cap_room_now,
        "open_after_count": len(open_after),
        "future_buffer": future_buffer,
        "preferred_max_salary": preferred_max_salary,
        "min_future_slot_cost": min_future_slot_cost,
    }


def roster_position_counts() -> dict:
    """Count the current roster by primary NBA position."""
    positions = ["PG", "SG", "SF", "PF", "C"]
    counts = {p: 0 for p in positions}

    for player in st.session_state.roster.values():
        pos_text = str(player.get("Pos", ""))
        matched = False
        for pos in positions:
            # Works for both "PG" and values like "PG, SG".
            if pos in pos_text:
                counts[pos] += 1
                matched = True
                break
        if not matched:
            continue

    return counts


def roster_role_needs() -> list[str]:
    """Lightweight role-needs signal used only for suggestions."""
    if not st.session_state.roster:
        return []

    roster = pd.DataFrame(list(st.session_state.roster.values()))
    needs = []

    try:
        shooters = roster[(roster["3P%"] >= 0.36) & (roster["3PA"] >= 3)]
        if len(shooters) < 4:
            needs.append("shooting")
    except Exception:
        pass

    try:
        defenders = roster[
            (roster["DBPM"] >= 1) |
            (roster["STL"] >= 1.1) |
            (roster["BLK"] >= 1.0)
        ]
        if len(defenders) < 5:
            needs.append("defense")
    except Exception:
        pass

    try:
        creators = roster[roster["AST"] >= 4.5]
        if len(creators) < 3:
            needs.append("creation")
    except Exception:
        pass

    return needs[:2]


def dynamic_slot_target_positions(slot: str) -> tuple[list[str], dict]:
    """
    Starter slots use the exact starter position.
    Bench/two-way slots use current roster balance.

    Example:
    If the user already has 3 PG, 3 SG, 2 SF, 3 PF, and 1 C,
    this returns C first because the roster only has one center.
    """
    direct = {
        "Starting PG": ["PG"],
        "Starting SG": ["SG"],
        "Starting SF": ["SF"],
        "Starting PF": ["PF"],
        "Starting C": ["C"],
    }

    if slot in direct:
        counts = roster_position_counts()
        return direct[slot], counts

    counts = roster_position_counts()

    # Core 15-man roster balance target.
    # This intentionally keeps at least 2 centers available across the roster.
    ideal_counts = {
        "PG": 2,
        "SG": 3,
        "SF": 3,
        "PF": 3,
        "C": 2,
    }

    shortages = {
        pos: ideal_counts[pos] - counts.get(pos, 0)
        for pos in ideal_counts
    }

    ordered = []

    # Hard minimum: do not let the roster sit with only one true center.
    if counts.get("C", 0) < 2:
        ordered.append("C")

    # Then fill the biggest remaining shortages.
    shortage_order = sorted(
        ideal_counts.keys(),
        key=lambda pos: (shortages[pos], -counts.get(pos, 0)),
        reverse=True
    )

    for pos in shortage_order:
        if pos not in ordered and shortages[pos] > 0:
            ordered.append(pos)

    # If the roster is already balanced, suggest the least-common positions.
    if len(ordered) < 3:
        fallback = sorted(ideal_counts.keys(), key=lambda pos: counts.get(pos, 0))
        for pos in fallback:
            if pos not in ordered:
                ordered.append(pos)
            if len(ordered) >= 3:
                break

    if "Two-Way" in slot:
        # Two-way slots can be any position, but still start with the roster needs.
        for pos in ["PG", "SG", "SF", "PF", "C"]:
            if pos not in ordered:
                ordered.append(pos)

    return ordered[:3], counts


def build_suggested_players_for_slot(slot: str, team_filter: str, position_filter: str, salary_filter: str) -> tuple[pd.DataFrame, str]:
    """
    Dynamic, cap-aware suggestions.

    Suggestions now consider:
    - exact starter slot need
    - bench/two-way positional balance
    - current roster position counts
    - selected salary cap
    - room needed to fill remaining empty slots
    - light role needs such as shooting, defense, and creation
    """
    pool = base_available_player_pool()
    pool = apply_dialog_filters(pool, team_filter, position_filter, salary_filter, "")

    if len(pool) == 0:
        return pool, "No suggestions match the current filters."

    target_positions, position_counts = dynamic_slot_target_positions(slot)
    cap_context = salary_room_for_suggestion(slot)
    role_needs = roster_role_needs()

    cap_room_now = float(cap_context["cap_room_now"])
    preferred_max_salary = float(cap_context["preferred_max_salary"])

    # First try the responsible version: leave room for every remaining open slot.
    pool = pool.copy()
    responsible_pool = pool[pool["Salary"] <= preferred_max_salary].copy()

    # If the roster is tight against the cap, still never suggest a player who puts
    # the team over the current cap. Fall back to players that fit the immediate room.
    if len(responsible_pool) == 0:
        responsible_pool = pool[pool["Salary"] <= cap_room_now].copy()

    # If the team is already over the cap, suggestions should be low-cost only.
    if len(responsible_pool) == 0:
        responsible_pool = pool.sort_values("Salary", ascending=True).head(40).copy()

    def pos_need_bonus(row) -> float:
        pos_text = str(row.get("Pos", ""))
        bonus = 0.0
        for rank, target in enumerate(target_positions):
            if target in pos_text:
                bonus += max(18, 55 - (rank * 14))

        # Hard center need boost: this is the user's example case.
        if position_counts.get("C", 0) < 2 and "C" in pos_text:
            bonus += 42

        return bonus

    def role_need_bonus(row) -> float:
        bonus = 0.0
        if "shooting" in role_needs and float(row.get("3P%", 0)) >= 0.36 and float(row.get("3PA", 0)) >= 3:
            bonus += 14
        if "defense" in role_needs and (
            float(row.get("DBPM", 0)) >= 1 or
            float(row.get("STL", 0)) >= 1.1 or
            float(row.get("BLK", 0)) >= 1.0
        ):
            bonus += 12
        if "creation" in role_needs and float(row.get("AST", 0)) >= 4.5:
            bonus += 12
        return bonus

    def cap_fit_bonus(row) -> float:
        salary = float(row.get("Salary", 0))
        bonus = 0.0

        if salary <= preferred_max_salary:
            bonus += 18
        if preferred_max_salary > 0:
            # Prefer players that fit without using all remaining move flexibility.
            usage_ratio = salary / preferred_max_salary
            if usage_ratio <= 0.45:
                bonus += 16
            elif usage_ratio <= 0.70:
                bonus += 10
            elif usage_ratio <= 0.90:
                bonus += 4
            else:
                bonus -= 8

        # Bench and two-way recommendations should be more financially careful.
        if slot.startswith("Bench"):
            if salary <= 8_000_000:
                bonus += 10
            elif salary >= 30_000_000:
                bonus -= 18
        if "Two-Way" in slot:
            if salary <= 5_000_000:
                bonus += 24
            elif salary >= 12_000_000:
                bonus -= 28

        return bonus

    def score_row(row):
        score = 0.0

        score += pos_need_bonus(row)
        score += role_need_bonus(row)
        score += cap_fit_bonus(row)

        # Basketball quality, but not enough to overpower position/cap need.
        score += float(row.get("Impact_Score", 0)) * 0.18
        score += float(row.get("PTS", 0)) * 0.65
        score += float(row.get("AST", 0)) * 0.55
        score += float(row.get("TRB", 0)) * 0.55
        score += float(row.get("TS%", 0)) * 12
        score += float(row.get("MP", 0)) * 0.10

        pos_match = player_matches_any_position(row, target_positions)

        # Starter slots should not suggest random off-position stars.
        if slot.startswith("Starting") and not pos_match:
            score -= 80

        return score

    responsible_pool["Suggestion_Score"] = responsible_pool.apply(score_row, axis=1)

    # Prioritize exact need and cap fit, then quality.
    suggested = responsible_pool.sort_values(
        ["Suggestion_Score", "Salary", "PTS", "MP"],
        ascending=[False, True, False, False]
    ).head(5)

    if slot.startswith("Starting"):
        reason = f"Suggested because this slot needs a true {target_positions[0]} and must fit your cap room."
    elif "Two-Way" in slot:
        reason = "Suggested for low-cost depth, roster balance, and future cap flexibility."
    else:
        need_text = ", ".join(target_positions)
        role_text = f" with added {', '.join(role_needs)} value" if role_needs else ""
        room_text = money(max(0, preferred_max_salary))
        reason = f"Suggested based on your bench position needs: {need_text}{role_text}. Target max salary: {room_text}."

    return suggested, reason

def add_dialog_player(row: pd.Series, slot: str):
    player = row.to_dict()
    player["Slot"] = slot
    fit, notes = calculate_position_fit(pd.Series(player), slot)
    player["Fit_Adjustment"] = fit
    player["Fit_Notes"] = "; ".join(notes)
    st.session_state.roster[slot] = player
    st.session_state.reports = {}
    st.session_state.quick_add_slot = None



def suggested_player_card_html(row: pd.Series, slot: str) -> str:
    """Compact visual card for native Streamlit suggestion buttons."""
    player_name = str(row.get("Player", ""))
    return f"""
    <div class="suggest-native-card">
        <div class="suggest-pos">{row["Pos"]}</div>
        <div class="suggest-img-wrap">{player_headshot_html(row)}</div>
        <div class="suggest-name">{player_name}</div>
        <div class="suggest-meta">{row["Team"]} • {row["Pos"]}</div>
        <div class="suggest-salary">{money(row["Salary"])}</div>
    </div>
    """


def render_suggested_players_row(slot: str, suggested_players: pd.DataFrame):
    """
    Render all 5 suggestions in one true horizontal row.

    Important:
    - This does NOT use st.columns, because Streamlit columns stack vertically
      inside mobile dialogs.
    - It uses one compact HTML component with five thin cards.
    - Card/Add clicks update the SAME Streamlit app tab using query params.
      process_query_param_add() handles the actual roster update.
    """
    if suggested_players is None or len(suggested_players) == 0:
        return

    import html

    shown = suggested_players.head(5).reset_index(drop=True)
    card_html = ""

    for _, row in shown.iterrows():
        player_name = str(row.get("Player", ""))
        safe_name = html.escape(player_name)
        team = html.escape(str(row.get("Team", "")))
        pos = html.escape(str(row.get("Pos", "")))
        salary = money(row.get("Salary", 0))
        salary_safe = html.escape(salary)

        display_name = player_name
        if len(display_name) > 15:
            display_name = display_name[:14].rstrip() + "…"
        display_name_safe = html.escape(display_name)

        headshot_url = str(row.get("HeadshotURL", "") or "").strip()
        if headshot_url and headshot_url.lower() not in {"nan", "none", "null"} and headshot_url.startswith("http"):
            avatar_html = f'<img class="suggest-img" src="{html.escape(headshot_url)}" />'
        else:
            avatar_html = f'<div class="suggest-avatar">{html.escape(initials(player_name))}</div>'

        add_url = f"?add_slot={quote(slot)}&add_player={quote(player_name)}"

        card_html += f"""
        <button class="suggest-card" onclick="addPlayer('{add_url}')" type="button" aria-label="Add {safe_name}">
            <div class="suggest-pos">{pos}</div>
            <div class="suggest-img-wrap">{avatar_html}</div>
            <div class="suggest-name">{display_name_safe}</div>
            <div class="suggest-meta">{team} • {pos}</div>
            <div class="suggest-salary">{salary_safe}</div>
            <div class="suggest-add-mini">Add</div>
        </button>
        """

    component_html = f"""
    <!doctype html>
    <html>
    <head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        html, body {{
            margin: 0;
            padding: 0;
            background: transparent;
            overflow: hidden;
            font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        }}

        .suggest-row {{
            display: flex;
            flex-direction: row;
            flex-wrap: nowrap;
            gap: 6px;
            width: 100%;
            box-sizing: border-box;
            padding: 4px 0 2px 0;
            overflow: hidden;
        }}

        .suggest-card {{
            flex: 1 1 0;
            min-width: 0;
            height: 156px;
            box-sizing: border-box;
            background:
                radial-gradient(circle at top, rgba(14,165,233,.22), transparent 48%),
                linear-gradient(145deg, rgba(8, 33, 61, .98), rgba(7, 21, 41, .98));
            border: 1px solid rgba(56,189,248,.65);
            border-radius: 13px;
            padding: 6px 3px 5px 3px;
            display: flex;
            flex-direction: column;
            align-items: center;
            text-align: center;
            color: #f8fafc;
            cursor: pointer;
            box-shadow: 0 10px 24px rgba(0,0,0,.22);
            outline: none;
            overflow: hidden;
        }}

        .suggest-card:active {{
            transform: scale(.98);
            border-color: rgba(125,211,252,.95);
        }}

        .suggest-pos {{
            color: #38bdf8;
            border: 1px solid rgba(56,189,248,.75);
            background: rgba(14,165,233,.12);
            border-radius: 7px;
            padding: 1px 5px;
            font-size: 9px;
            line-height: 1.2;
            font-weight: 950;
            margin-bottom: 5px;
            max-width: 100%;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}

        .suggest-img-wrap {{
            height: 34px;
            width: 34px;
            margin-bottom: 5px;
            flex: 0 0 auto;
        }}

        .suggest-img, .suggest-avatar {{
            width: 34px;
            height: 34px;
            border-radius: 10px;
            object-fit: cover;
            object-position: center top;
            border: 1px solid rgba(56,189,248,.45);
            background: rgba(15,23,42,.95);
            box-sizing: border-box;
        }}

        .suggest-avatar {{
            display: grid;
            place-items: center;
            font-size: 11px;
            font-weight: 950;
            color: #f8fafc;
        }}

        .suggest-name {{
            color: #f8fafc;
            font-size: 9.5px;
            font-weight: 950;
            line-height: 1.05;
            height: 21px;
            max-height: 21px;
            overflow: hidden;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            word-break: normal;
        }}

        .suggest-meta {{
            color: #a8b3c7;
            font-size: 8px;
            line-height: 1.1;
            margin-top: 5px;
            width: 100%;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}

        .suggest-salary {{
            color: #38bdf8;
            font-size: 10.5px;
            line-height: 1.1;
            font-weight: 950;
            margin-top: 4px;
            white-space: nowrap;
        }}

        .suggest-add-mini {{
            margin-top: auto;
            width: 100%;
            box-sizing: border-box;
            border: 1px solid rgba(56,189,248,.72);
            background: rgba(14,165,233,.10);
            border-radius: 8px;
            padding: 4px 0;
            color: #38bdf8;
            font-weight: 950;
            font-size: 10px;
            line-height: 1;
        }}

        @media (max-width: 420px) {{
            .suggest-row {{ gap: 5px; }}
            .suggest-card {{ height: 148px; border-radius: 12px; padding: 5px 2px 4px 2px; }}
            .suggest-pos {{ font-size: 8px; padding: 1px 4px; margin-bottom: 4px; }}
            .suggest-img-wrap {{ width: 30px; height: 30px; margin-bottom: 4px; }}
            .suggest-img, .suggest-avatar {{ width: 30px; height: 30px; border-radius: 9px; }}
            .suggest-name {{ font-size: 8.7px; height: 20px; max-height: 20px; }}
            .suggest-meta {{ font-size: 7.4px; margin-top: 4px; }}
            .suggest-salary {{ font-size: 9.6px; margin-top: 4px; }}
            .suggest-add-mini {{ font-size: 9.2px; padding: 3px 0; border-radius: 7px; }}
        }}
    </style>
    </head>
    <body>
        <div class="suggest-row">
            {card_html}
        </div>
        <script>
            function addPlayer(url) {{
                try {{
                    const target = new URL(url, window.parent.location.href);
                    window.parent.location.href = target.href;
                }} catch (e) {{
                    window.top.location.href = url;
                }}
            }}
        </script>
    </body>
    </html>
    """

    components.html(component_html, height=164, scrolling=False)

def process_query_param_add():
    """Handles clicks from the HTML suggested-player cards."""
    try:
        slot = st.query_params.get("add_slot", "")
        player_name = st.query_params.get("add_player", "")
    except Exception:
        return

    if not slot or not player_name:
        return

    if slot not in ROSTER_SLOTS:
        st.query_params.clear()
        st.rerun()

    if slot in st.session_state.roster:
        st.query_params.clear()
        st.rerun()

    selected_players = [p["Player"] for p in st.session_state.roster.values()]
    pool = df[~df["Player"].isin(selected_players)].copy()
    player_norm = normalize_name_for_match(player_name)
    matches = pool[pool["Player"].apply(normalize_name_for_match) == player_norm]

    if len(matches) > 0:
        add_dialog_player(matches.iloc[0], slot)

    st.query_params.clear()
    st.rerun()


@st.dialog("Add Player")
def open_player_search_dialog(slot: str):
    short = slot_short(slot)

    st.markdown(
        f"""
        <div class="dialog-hero-title">Add player to <span>{slot}</span></div>
        <div class="dialog-hero-sub">Find the perfect fit for your roster.</div>
        """,
        unsafe_allow_html=True
    )

    st.markdown('<div class="dialog-filter-shell">', unsafe_allow_html=True)
    f_team, f_pos, f_salary = st.columns(3)
    with f_team:
        team_filter = st.selectbox(
            "Team",
            ["All Teams"] + sorted(df["Team"].dropna().astype(str).unique().tolist()),
            key=f"dialog_team_filter_{slot}"
        )
    with f_pos:
        position_filter = st.selectbox(
            "Position",
            ["All Positions"] + ["PG", "SG", "SF", "PF", "C"],
            key=f"dialog_pos_filter_{slot}"
        )
    with f_salary:
        salary_filter = st.selectbox(
            "Salary",
            ["All Salaries", "Under $5M", "$5M-$15M", "$15M-$30M", "$30M+"],
            key=f"dialog_salary_filter_{slot}"
        )
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="dialog-search-shell">', unsafe_allow_html=True)
    search_query = st.text_input(
        "Search players",
        placeholder="Search players by name...",
        key=f"dialog_search_{slot}"
    )
    st.markdown('</div>', unsafe_allow_html=True)

    suggested_players, suggestion_reason = build_suggested_players_for_slot(slot, team_filter, position_filter, salary_filter)

    st.markdown(
        f"""
        <div class="dialog-section-row">
            <div>
                <div class="dialog-section-title">Suggested For This Spot</div>
                <div class="dialog-section-note">{suggestion_reason}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    if len(suggested_players) > 0:
        # HTML rail keeps all suggestions in one horizontal row on mobile.
        # Clicks are handled by process_query_param_add() using same-tab query params.
        render_suggested_players_row(slot, suggested_players)
    else:
        st.info("No suggested players available with these filters.")

    all_left, sort_right = st.columns([0.55, 0.45], vertical_alignment="bottom")
    with all_left:
        st.markdown('<div class="dialog-section-title">All Players</div>', unsafe_allow_html=True)
    with sort_right:
        sort_label = st.selectbox(
            "Sort by",
            ["Salary High-Low", "Salary Low-High", "PPG", "APG", "RPG", "TS%"],
            index=2,
            key=f"dialog_sort_{slot}"
        )

    player_pool = build_dialog_player_pool(slot, team_filter, position_filter, salary_filter, search_query, sort_label)

    if len(player_pool) == 0:
        st.warning("No players found. Try clearing a filter or searching by last name.")
        if st.button("Cancel", use_container_width=True, key=f"dialog_cancel_empty_{slot}"):
            st.session_state.quick_add_slot = None
            st.rerun()
        return

    st.caption(f"{len(player_pool)} players found")

    # Vertical player result list. The dialog itself scrolls naturally on mobile.
    for idx, (_, prow) in enumerate(player_pool.head(20).iterrows()):
        card_col, add_col = st.columns([0.78, 0.22], vertical_alignment="center")
        with card_col:
            st.markdown(
                f"""
                <div class="player-result-card">
                    {player_headshot_html(prow)}
                    <div>
                        <div class="result-name">{prow['Player']}</div>
                        <div class="result-meta">{prow['Team']} • {prow['Pos']}<br>{prow['PTS']:.1f} PPG • {prow['AST']:.1f} APG • {prow['TRB']:.1f} RPG • {pct(prow['TS%'])} TS</div>
                    </div>
                    <div>
                        <div class="result-salary">{money(prow['Salary'])}</div>
                        <div class="result-salary-label">Salary</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
        with add_col:
            if st.button("Add", use_container_width=True, key=f"dialog_result_add_{slot}_{idx}_{prow['Player']}"):
                add_dialog_player(prow, slot)
                st.rerun()

    if len(player_pool) > 20:
        st.caption("Showing top 20 matches. Use search or filters to narrow the list.")

    if st.button("Cancel", use_container_width=True, key=f"dialog_cancel_{slot}"):
        st.session_state.quick_add_slot = None
        st.rerun()


def render_roster_list(show_remove: bool = False):
    """
    Mobile-safe roster list.

    Important design choice:
    - Filled slots are rendered as sleek HTML cards.
    - Empty slots are rendered as ONE native Streamlit button styled as a full card.
      This keeps the + action fully responsive on phones and opens the player-search dialog
      instead of relying on fake HTML links/buttons.
    """
    st.markdown('<div class="roster-list">', unsafe_allow_html=True)

    for slot in active_roster_slots:
        short = slot_short(slot)

        if slot in st.session_state.roster:
            p = st.session_state.roster[slot]
            quality = p.get("Player_Quality")
            if quality is None:
                try:
                    quality = calculate_player_quality_score(pd.Series(p))
                except Exception:
                    quality = 0

            player_profile = p.get("PlayerProfile", "Depth Contributor")

            st.markdown(
                f"""
                <div class="player-row-card">
                    <div class="slot-pill">{short}</div>
                    {player_headshot_html(p)}
                    <div>
                        <div class="player-name-mobile">{p['Player']}</div>
                        <div class="player-role-mobile">{compact_role(p)}</div>
                    </div>
                    <div class="player-right-mobile">
                        <div class="player-ovr-mobile">{player_profile}</div>
                        <div class="player-salary-mobile">{money(p['Salary'])}</div>
                    </div>
                    <div class="chev-mobile">›</div>
                </div>
                """,
                unsafe_allow_html=True
            )

            if show_remove:
                if st.button(
                    f"Remove {p['Player']}",
                    key=f"remove_{slot}_{p['Player']}",
                    use_container_width=True
                ):
                    remove_player_from_slot(slot)
                    st.rerun()

        else:
            # One native button = responsive, clickable, and dialog-safe.
            # The label is intentionally compact so it stays horizontal on mobile.
            empty_label = f"{short}    ＋    Empty Slot                         OPEN\nAdd a player to fill this role                         --"
            if st.button(
                empty_label,
                key=f"add_slot_{slot}",
                use_container_width=True,
                help=f"Add player to {slot}"
            ):
                open_player_search_dialog(slot)

    st.markdown('</div>', unsafe_allow_html=True)


# ----------------------------
# Session defaults
# ----------------------------
if "active_salary_cap" not in st.session_state:
    st.session_state.active_salary_cap = DEFAULT_SALARY_CAP

if "quick_add_slot" not in st.session_state:
    st.session_state.quick_add_slot = None

salary_cap = st.session_state.active_salary_cap
active_roster_slots = ROSTER_SLOTS[:st.session_state.roster_size]
process_query_param_add()
roster_df_now = roster_to_df()
payroll_now = float(roster_df_now["Salary"].sum()) if len(roster_df_now) else 0.0
metrics_now = current_metrics(salary_cap)

render_topbar()
render_overview(metrics_now, payroll_now, salary_cap)


def app_h2h_team_strength(roster_list):
    """Use the app's existing basketball model as the H2H rating source."""
    try:
        r_df = pd.DataFrame(roster_list)
        if len(r_df) < MIN_RESULTS_PLAYERS:
            raise ValueError("Not enough players")
        metrics = calculate_team_metrics(r_df, st.session_state.active_salary_cap)
        return {
            "overall": float(metrics.get("overall_score", 50)),
            "offense": float(metrics.get("creation_score", metrics.get("offense_score", 50))),
            "defense": float(metrics.get("defense_score", 50)),
            "shooting": float(metrics.get("shooting_score", 50)),
            "playmaking": float(metrics.get("playmaking_score", metrics.get("creation_score", 50))),
            "rebounding": float(metrics.get("rebounding_score", 50)),
            "star_power": float(metrics.get("star_power_score", metrics.get("star_power", 50))),
            "depth": float(metrics.get("depth_score", 50)),
            "clutch": float(metrics.get("star_power_score", metrics.get("star_power", 50))) * 0.55 + float(metrics.get("creation_score", 50)) * 0.25 + float(metrics.get("shooting_score", 50)) * 0.20,
        }
    except Exception:
        # Fall back to the module's internal model if this roster is missing app-only columns.
        from head_to_head_7_game_mode_fixed import default_team_strength
        return default_team_strength(roster_list)

# Bottom-nav inspired tabs
tab_build, tab_players, tab_analysis, tab_h2h, tab_report, tab_settings = st.tabs([
    "📋 Build", "🔎 Players", "📊 Analysis", "⚔️ H2H", "🧠 AI Report", "⚙️ Settings"
])


# ============================================================
# BUILD TAB
# ============================================================
with tab_build:
    left_title, right_title = st.columns([1, 1])
    with left_title:
        st.markdown(
            f'<div class="section-heading-mobile">Roster ({len(st.session_state.roster)}/15)</div>',
            unsafe_allow_html=True
        )
    with right_title:
        st.markdown('<div class="section-action">Edit Roster ✎</div>', unsafe_allow_html=True)

    render_roster_list(show_remove=True)

    st.markdown('<div class="add-player-hero">＋ ADD PLAYER</div>', unsafe_allow_html=True)
    st.caption("Open the Players tab to search and add players. Results unlock once you draft at least 9 players.")

    st.markdown(
        """
        <div class="action-grid">
            <div class="action-tile-mobile"><div class="action-icon-mobile">🔎</div><div class="action-label-mobile">Players</div></div>
            <div class="action-tile-mobile"><div class="action-icon-mobile">📊</div><div class="action-label-mobile">Analysis</div></div>
            <div class="action-tile-mobile"><div class="action-icon-mobile">🧠</div><div class="action-label-mobile">AI Report</div></div>
            <div class="action-tile-mobile"><div class="action-icon-mobile">⚙️</div><div class="action-label-mobile">Settings</div></div>
        </div>
        """,
        unsafe_allow_html=True
    )


# ============================================================
# PLAYERS TAB
# ============================================================
with tab_players:
    st.markdown('<div class="section-heading-mobile">Add Player</div>', unsafe_allow_html=True)
    st.markdown('<div class="small-muted">Search, filter, choose a slot, then add the player to your roster.</div>', unsafe_allow_html=True)

    with st.container():
        st.markdown('<div class="draft-card">', unsafe_allow_html=True)
        search = st.text_input("Search player", placeholder="Type a name, team, or position")

        f1, f2 = st.columns(2)
        with f1:
            selected_positions = st.multiselect("Position", sorted(df["Pos"].unique()), default=[])
        with f2:
            selected_teams = st.multiselect("Team", sorted(df["Team"].unique()), default=[])

        f3, f4 = st.columns(2)
        with f3:
            min_minutes = st.slider("Minimum MPG", 0, 40, 10)
        with f4:
            sort_label = st.selectbox("Sort by", ["PPG", "APG", "RPG", "3P%", "TS%", "Salary"], index=0)
        st.markdown('</div>', unsafe_allow_html=True)

    SORT_MAP = {
        "PPG": "PTS",
        "APG": "AST",
        "RPG": "TRB",
        "3P%": "3P%",
        "TS%": "TS%",
        "Salary": "Salary",
    }
    sort_by = SORT_MAP[sort_label]

    player_pool = df.copy()
    if search:
        player_pool = player_pool[
            player_pool["Player"].str.contains(search, case=False, na=False) |
            player_pool["Team"].str.contains(search, case=False, na=False) |
            player_pool["Pos"].str.contains(search, case=False, na=False)
        ]
    if selected_positions:
        player_pool = player_pool[player_pool["Pos"].isin(selected_positions)]
    if selected_teams:
        player_pool = player_pool[player_pool["Team"].isin(selected_teams)]

    selected_players = [v["Player"] for v in st.session_state.roster.values()]
    player_pool = player_pool[
        (player_pool["MP"] >= min_minutes) &
        (~player_pool["Player"].isin(selected_players))
    ].sort_values(sort_by, ascending=False)

    open_slots = [slot for slot in active_roster_slots if slot not in st.session_state.roster]

    if not open_slots:
        st.success("Roster full. Remove a player from the Build tab to add someone else.")
    elif len(player_pool) == 0:
        st.warning("No available players match your filters.")
    else:
        add_col1, add_col2 = st.columns([1, 1])
        with add_col1:
            selected_slot = st.selectbox("Roster Slot", open_slots)
        with add_col2:
            selected_player_name = st.selectbox("Player", player_pool["Player"].head(250).tolist())

        preview = player_pool[player_pool["Player"] == selected_player_name].iloc[0]
        st.markdown(
            f"""
            <div class="player-row-card" style="margin:14px 0;">
                <div class="slot-pill">{preview['Pos']}</div>
                {player_headshot_html(preview)}
                <div>
                    <div class="player-name-mobile">{preview['Player']}</div>
                    <div class="player-role-mobile">{preview['Team']} • {preview['PPG']:.1f} PPG • {preview['APG']:.1f} APG • {preview['RPG']:.1f} RPG</div>
                </div>
                <div class="player-right-mobile">
                    <div class="player-ovr-mobile">BPM {float(preview['BPM']):.1f}</div>
                    <div class="player-salary-mobile">{money(preview['Salary'])}</div>
                </div>
                <div class="chev-mobile">›</div>
            </div>
            """,
            unsafe_allow_html=True
        )

        if st.button("＋ Add Player", type="primary", use_container_width=True):
            selected_player = preview.to_dict()
            selected_player["Slot"] = selected_slot
            fit, notes = calculate_position_fit(pd.Series(selected_player), selected_slot)
            selected_player["Fit_Adjustment"] = fit
            selected_player["Fit_Notes"] = "; ".join(notes)
            st.session_state.roster[selected_slot] = selected_player
            st.session_state.reports = {}
            st.rerun()

    st.markdown('<div class="section-heading-mobile" style="margin-top:22px;">Top Available</div>', unsafe_allow_html=True)
    board_cols = ["Player", "Team", "Pos", "Salary Display", "PPG", "APG", "RPG", "3P% Display", "TS% Display"]
    st.dataframe(player_pool[board_cols].head(35), use_container_width=True, hide_index=True, height=420)


# ============================================================
# ANALYSIS TAB
# ============================================================
with tab_analysis:
    st.markdown('<div class="section-heading-mobile">Team Analysis</div>', unsafe_allow_html=True)

    if metrics_now is None:
        st.warning(f"Draft at least {MIN_RESULTS_PLAYERS} players to unlock analysis. Current roster: {len(st.session_state.roster)}/15 MAX.")
    else:
        a, b, c = st.columns(3)
        with a:
            st.metric("Projected Wins", metrics_now["projected_wins"])
        with b:
            st.metric("Overall", metrics_now["overall_score"])
        with c:
            st.metric("Grade", metrics_now["grade"])

        grade_df = pd.DataFrame({
            "Category": [
                "Creation", "Shooting", "Defense", "Rebounding",
                "Star Power", "Talent", "Depth", "Fit", "Versatility"
            ],
            "Score": [
                metrics_now["creation_score"], metrics_now["shooting_score"], metrics_now["defense_score"],
                metrics_now["rebounding_score"], metrics_now["star_power_score"], metrics_now["talent_concentration_score"],
                metrics_now["depth_score"], metrics_now["fit_score"], metrics_now["versatility_score"]
            ]
        })
        st.bar_chart(grade_df.set_index("Category"))

        k1, k2 = st.columns(2)
        with k1:
            st.info(f"Best Player: {metrics_now['best_player']}")
            st.info(f"Best Shooter: {metrics_now['best_shooter']}")
        with k2:
            st.info(f"Best Defender: {metrics_now['best_defender']}")
            st.info(f"Best Contract: {metrics_now['best_contract']}")

        st.markdown('<div class="section-heading-mobile">Role & Fit</div>', unsafe_allow_html=True)
        roster_fit_df = metrics_now["roster_with_fit"]
        role_data = []
        for _, row in roster_fit_df.iterrows():
            role_data.append({
                "Slot": row["Slot"],
                "Player": row["Player"],
                "Listed Pos": row["Pos"],
                "Role": get_player_role(row),
                "Salary": money(row["Salary"]),
                "Fit": f"{fit_label(int(row['Fit_Adjustment']))} ({int(row['Fit_Adjustment']):+d})",
                "Fit Notes": row["Fit_Notes"],
            })
        st.dataframe(pd.DataFrame(role_data), use_container_width=True, hide_index=True, height=420)


# ============================================================
# HEAD-TO-HEAD TAB
# ============================================================
with tab_h2h:
    if render_head_to_head_mode is None:
        st.error("Head-to-head module not found. Put head_to_head_7_game_mode.py in the same folder as this app.")
    else:
        render_head_to_head_mode(
            current_roster=st.session_state.roster,
            salary_cap=salary_cap,
            calculate_team_strength=app_h2h_team_strength,
        )


# ============================================================
# AI REPORT TAB
# ============================================================
with tab_report:
    st.markdown('<div class="section-heading-mobile">AI Scouting Report</div>', unsafe_allow_html=True)

    if metrics_now is None:
        st.warning(f"Draft at least {MIN_RESULTS_PLAYERS} players to generate an AI report.")
    else:
        team_summary = build_team_summary(roster_df_now, metrics_now)
        team_hash = get_team_hash(team_summary)

        if st.button("Generate AI Report", type="primary", use_container_width=True):
            with st.spinner("Generating scouting report..."):
                st.session_state.reports[team_hash] = generate_ai_report(team_summary)

        if team_hash in st.session_state.reports:
            st.markdown(st.session_state.reports[team_hash])
        else:
            st.caption("Tap Generate AI Report to create a front-office scouting report for this exact roster.")


# ============================================================
# SETTINGS TAB
# ============================================================
with tab_settings:
    st.markdown('<div class="section-heading-mobile">Settings</div>', unsafe_allow_html=True)

    st.markdown('<div class="draft-card">', unsafe_allow_html=True)
    roster_size = st.selectbox(
        "Roster Size",
        list(range(9, 16)),
        index=list(range(9, 16)).index(st.session_state.roster_size),
        help="Results unlock at 9 players. You can build up to 15."
    )
    if roster_size != st.session_state.roster_size:
        st.session_state.roster_size = roster_size
        active_roster_slots = ROSTER_SLOTS[:st.session_state.roster_size]
        for slot in list(st.session_state.roster.keys()):
            if slot not in active_roster_slots:
                del st.session_state.roster[slot]
        st.session_state.reports = {}
        st.rerun()

    cap_choice = st.selectbox(
        "Salary Level",
        list(SALARY_CAP_LEVELS.keys()),
        index=list(SALARY_CAP_LEVELS.keys()).index("Second Apron")
    )

    if cap_choice == "Custom":
        salary_cap_new = st.number_input(
            "Custom Salary Cap",
            min_value=100_000_000,
            max_value=700_000_000,
            value=int(st.session_state.active_salary_cap),
            step=5_000_000,
            format="%d"
        )
    else:
        salary_cap_new = SALARY_CAP_LEVELS[cap_choice]

    if salary_cap_new != st.session_state.active_salary_cap:
        st.session_state.active_salary_cap = salary_cap_new
        st.session_state.reports = {}
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-heading-mobile">Preset Rosters</div>', unsafe_allow_html=True)
    preset_options = ["New Team"] + sorted(PRESET_ROSTERS.keys())
    preset_choice = st.selectbox("Load Preset Current Roster", preset_options, index=0)

    p1, p2 = st.columns([1, 1])
    with p1:
        if st.button("Load Preset", type="primary", use_container_width=True):
            if preset_choice == "New Team":
                st.session_state.roster = {}
                st.session_state.reports = {}
                st.success("Started a new team.")
            else:
                loaded, missing = load_preset_roster(preset_choice, st.session_state.roster_size, df)
                st.session_state.roster = loaded
                st.session_state.reports = {}
                if missing:
                    st.warning("Preset loaded, but these players were not found: " + ", ".join(missing))
                else:
                    st.success(f"{preset_choice} loaded successfully.")
            st.rerun()

    with p2:
        if st.button("Clear Roster", use_container_width=True):
            st.session_state.roster = {}
            st.session_state.reports = {}
            st.rerun()

    st.markdown('<div class="section-heading-mobile">App Status</div>', unsafe_allow_html=True)
    if OPENAI_API_KEY.strip() != PLACEHOLDER_API_KEY and OPENAI_API_KEY.strip():
        st.success("OpenAI API key loaded. AI reports are enabled.")
    else:
        st.warning("OpenAI API key not found. AI reports will use the fallback report.")
