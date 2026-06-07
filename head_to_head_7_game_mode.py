# H2H MODULE VERSION: role_locked_team_name_only_v5_smart_autorefresh
from __future__ import annotations

import base64
import hashlib
import json
import math
import random
import time
import uuid
import zlib
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st

try:
    from streamlit_autorefresh import st_autorefresh
except Exception:
    st_autorefresh = None

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

ROOMS_FILE = Path("h2h_rooms.json")
MAX_GAMES = 7
MIN_H2H_PLAYERS = 9


# ============================================================
# STORAGE / BASIC HELPERS
# ============================================================

def _now() -> int:
    return int(time.time())


def _load_rooms() -> Dict[str, Any]:
    if not ROOMS_FILE.exists():
        return {}
    try:
        return json.loads(ROOMS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_rooms(rooms: Dict[str, Any]) -> None:
    ROOMS_FILE.write_text(json.dumps(rooms, indent=2), encoding="utf-8")


def _make_room_code() -> str:
    return uuid.uuid4().hex[:6].upper()


def _num(p: Dict[str, Any], *keys: str, default: float = 0.0) -> float:
    for key in keys:
        if key in p and p[key] not in (None, "", "nan", "None"):
            try:
                value = float(p[key])
                if math.isfinite(value):
                    return value
            except Exception:
                pass
    return default


def _player_name(p: Any) -> str:
    if isinstance(p, dict):
        return str(p.get("Player") or p.get("Name") or "Unknown")
    return str(getattr(p, "Player", getattr(p, "Name", "Unknown")))


def _safe_roster(roster: Any) -> List[Dict[str, Any]]:
    """Accepts Streamlit session_state.roster dict, list of dicts, or DataFrame rows."""
    if roster is None:
        return []

    if isinstance(roster, dict):
        items = []
        for slot, player in roster.items():
            if isinstance(player, dict):
                p = dict(player)
            elif hasattr(player, "to_dict"):
                p = player.to_dict()
            else:
                p = {"Player": str(player)}
            p["Slot"] = p.get("Slot", slot)
            items.append(p)
        return items

    safe = []
    for p in roster or []:
        if isinstance(p, dict):
            safe.append(dict(p))
        elif hasattr(p, "to_dict"):
            safe.append(p.to_dict())
        else:
            safe.append({"Player": str(p)})
    return safe


def _stable_seed(*parts: Any) -> int:
    raw = "|".join(str(p) for p in parts)
    return int(hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16], 16)


def _money(x: float) -> str:
    try:
        return f"${float(x) / 1_000_000:.1f}M"
    except Exception:
        return "$0.0M"


def _pct(x: float) -> str:
    try:
        return f"{float(x) * 100:.1f}%"
    except Exception:
        return "0.0%"


def encode_roster_payload(payload: Dict[str, Any]) -> str:
    raw = json.dumps(payload, separators=(",", ":"), default=str).encode("utf-8")
    compressed = zlib.compress(raw, level=9)
    return base64.urlsafe_b64encode(compressed).decode("utf-8").rstrip("=")


def decode_roster_payload(code: str) -> Dict[str, Any]:
    padded = code + "=" * (-len(code) % 4)
    raw = zlib.decompress(base64.urlsafe_b64decode(padded.encode("utf-8")))
    return json.loads(raw.decode("utf-8"))


# ============================================================
# TEAM RATINGS
# ============================================================

def default_team_strength(roster: List[Dict[str, Any]]) -> Dict[str, float]:
    if not roster:
        return {"overall": 0, "offense": 0, "defense": 0, "shooting": 0, "playmaking": 0, "rebounding": 0, "star_power": 0, "depth": 0, "clutch": 0}

    rows = roster[:15]
    rotation = rows[:10]

    def player_quality(p: Dict[str, Any]) -> float:
        impact = _num(p, "Impact_Score", "ImpactScore", "Impact Score", default=0)
        pts = _num(p, "PTS", default=0)
        ast = _num(p, "AST", default=0)
        reb = _num(p, "TRB", "REB", default=0)
        stl = _num(p, "STL", default=0)
        blk = _num(p, "BLK", default=0)
        ts = _num(p, "TS%", "TS", default=0.55)
        bpm = _num(p, "BPM", default=0)
        per = _num(p, "PER", default=0)
        mp = _num(p, "MP", default=18)
        base = impact * 0.40 + pts * 1.00 + ast * 1.25 + reb * 0.75 + stl * 2.2 + blk * 2.0 + bpm * 2.2 + per * 0.28 + ts * 10
        if mp < 15:
            base -= 8
        elif mp < 20:
            base -= 4
        return max(0, base)

    qualities = sorted([player_quality(p) for p in rows], reverse=True)
    top5 = sum(qualities[:5]) / max(1, min(5, len(qualities)))
    top8 = sum(qualities[:8]) / max(1, min(8, len(qualities)))
    depth = sum(qualities[5:10]) / max(1, len(qualities[5:10])) if len(qualities) > 5 else top5 * 0.70

    offense = sum(_num(p, "PTS", default=0) * 1.10 + _num(p, "AST", default=0) * 1.25 + _num(p, "OBPM", default=0) * 2.2 + _num(p, "TS%", default=0.55) * 18 for p in rotation) / max(1, len(rotation))
    shooting = sum(_num(p, "3P%", default=0.33) * 65 + _num(p, "3PA", default=1) * 2.4 + _num(p, "TS%", default=0.55) * 15 for p in rotation) / max(1, len(rotation))
    defense = sum(_num(p, "DBPM", default=0) * 2.6 + _num(p, "STL", default=0) * 3.2 + _num(p, "BLK", default=0) * 3.3 + _num(p, "TRB", "REB", default=0) * 0.75 for p in rotation) / max(1, len(rotation))
    playmaking = sum(_num(p, "AST", default=0) * 1.9 + _num(p, "BPM", default=0) * 0.55 for p in rotation) / max(1, len(rotation))
    rebounding = sum(_num(p, "TRB", "REB", default=0) * 1.35 + _num(p, "BLK", default=0) * 0.8 for p in rotation) / max(1, len(rotation))
    star_power = sum(qualities[:3]) / max(1, min(3, len(qualities)))

    clutch_names = {
        "lebron james", "stephen curry", "kevin durant", "nikola jokic", "luka doncic", "jalen brunson", "damian lillard",
        "kyrie irving", "jimmy butler", "shai gilgeous-alexander", "devin booker", "donovan mitchell", "anthony edwards",
        "jayson tatum", "kawhi leonard", "jamal murray", "de'aaron fox", "deaaron fox"
    }
    clutch = star_power * 0.55 + playmaking * 0.25 + shooting * 0.20
    for p in rows:
        name = _player_name(p).lower().replace("’", "'")
        if any(c in name for c in clutch_names):
            clutch += 2.8

    overall = top5 * 0.30 + top8 * 0.18 + offense * 0.17 + defense * 0.14 + shooting * 0.08 + playmaking * 0.06 + rebounding * 0.03 + depth * 0.04

    return {
        "overall": round(overall, 2),
        "offense": round(offense, 2),
        "defense": round(defense, 2),
        "shooting": round(shooting, 2),
        "playmaking": round(playmaking, 2),
        "rebounding": round(rebounding, 2),
        "star_power": round(star_power, 2),
        "depth": round(depth, 2),
        "clutch": round(clutch, 2),
    }


# ============================================================
# BOX SCORE ENGINE
# ============================================================

def _role_minutes(slot: str, player: Dict[str, Any], rng: random.Random, fatigue: float, injury_penalty: float) -> int:
    slot = str(slot)
    if slot.startswith("Starting"):
        base = rng.uniform(30, 38)
    elif slot == "Bench 1":
        base = rng.uniform(24, 32)
    elif slot in ["Bench 2", "Bench 3"]:
        base = rng.uniform(18, 27)
    elif slot in ["Bench 4", "Bench 5"]:
        base = rng.uniform(10, 20)
    elif slot.startswith("Bench"):
        base = rng.uniform(4, 13)
    else:
        base = rng.uniform(0, 6)

    quality_bump = min(4, max(-3, (_num(player, "BPM", default=0) / 2)))
    minutes = base + quality_bump - fatigue * rng.uniform(0.8, 2.2) - injury_penalty
    return int(max(0, min(44, round(minutes))))


def _normalize_minutes(box: List[Dict[str, Any]], target_total: int = 240) -> List[Dict[str, Any]]:
    current = sum(p["MIN"] for p in box)
    if current <= 0:
        return box
    factor = target_total / current
    for p in box:
        p["MIN"] = int(max(0, min(45, round(p["MIN"] * factor))))

    # final adjustment
    diff = target_total - sum(p["MIN"] for p in box)
    order = sorted(range(len(box)), key=lambda i: box[i]["MIN"], reverse=True)
    i = 0
    while diff != 0 and order:
        idx = order[i % len(order)]
        if diff > 0 and box[idx]["MIN"] < 45:
            box[idx]["MIN"] += 1
            diff -= 1
        elif diff < 0 and box[idx]["MIN"] > 0:
            box[idx]["MIN"] -= 1
            diff += 1
        i += 1
        if i > 1000:
            break
    return box


def _allocate_points(box: List[Dict[str, Any]], team_score: int, team_rating: Dict[str, float], opp_rating: Dict[str, float], rng: random.Random, clutch_bonus: float) -> List[Dict[str, Any]]:
    weights = []
    defensive_pressure = max(-8, min(10, opp_rating.get("defense", 0) - team_rating.get("offense", 0)))
    shooting_boost = max(-5, min(7, team_rating.get("shooting", 0) - opp_rating.get("defense", 0) * 0.35))

    for p in box:
        src = p["_src"]
        min_factor = max(0.05, p["MIN"] / 36)
        usage = _num(src, "USG%", default=20)
        pts = _num(src, "PTS", default=6)
        obpm = _num(src, "OBPM", default=0)
        three_pa = _num(src, "3PA", default=1)
        three_pct = _num(src, "3P%", default=0.33)
        star = _num(src, "BPM", default=0)

        weight = (pts * 1.3 + usage * 0.55 + obpm * 2.0 + star * 1.1 + three_pa * three_pct * 4.5) * min_factor
        weight += rng.uniform(-3, 5)
        weight += shooting_boost * 0.18
        weight -= defensive_pressure * 0.12
        if p.get("_clutch"):
            weight += clutch_bonus
        weights.append(max(0.2, weight))

    total_weight = sum(weights) or 1
    raw_points = [max(0, round(team_score * w / total_weight)) for w in weights]
    diff = team_score - sum(raw_points)
    order = sorted(range(len(raw_points)), key=lambda i: weights[i], reverse=True)
    i = 0
    while diff != 0 and order:
        idx = order[i % len(order)]
        if diff > 0:
            raw_points[idx] += 1
            diff -= 1
        elif raw_points[idx] > 0:
            raw_points[idx] -= 1
            diff += 1
        i += 1
        if i > 1000:
            break

    for p, pts in zip(box, raw_points):
        p["PTS"] = int(pts)
    return box


def generate_team_box_score(
    roster: List[Dict[str, Any]],
    team_score: int,
    team_rating: Dict[str, float],
    opp_rating: Dict[str, float],
    rng: random.Random,
    game_no: int,
    fatigue: float,
    injury_events: Dict[str, str],
    clutch_bonus: float,
) -> List[Dict[str, Any]]:
    box = []
    ordered = sorted(roster[:15], key=lambda p: list(_slot_order()).index(str(p.get("Slot", "Two-Way 2"))) if str(p.get("Slot", "Two-Way 2")) in _slot_order() else 99)

    for p in ordered:
        name = _player_name(p)
        injury_penalty = 0
        if name in injury_events:
            injury_penalty = 10 if "limited" in injury_events[name].lower() else 99

        slot = str(p.get("Slot", "Bench"))
        minutes = _role_minutes(slot, p, rng, fatigue, injury_penalty)
        box.append({
            "Player": name,
            "Slot": slot,
            "MIN": minutes,
            "PTS": 0,
            "REB": 0,
            "AST": 0,
            "STL": 0,
            "BLK": 0,
            "TOV": 0,
            "+/-": 0,
            "_src": p,
            "_clutch": False,
        })

    box = _normalize_minutes(box, 240)
    clutch_candidates = sorted(box, key=lambda x: (_num(x["_src"], "BPM", default=0), _num(x["_src"], "PTS", default=0), x["MIN"]), reverse=True)[:3]
    for p in clutch_candidates:
        p["_clutch"] = True

    box = _allocate_points(box, team_score, team_rating, opp_rating, rng, clutch_bonus)

    total_reb_target = int(rng.uniform(38, 53) + max(-5, min(6, team_rating.get("rebounding", 0) - opp_rating.get("rebounding", 0))) * 0.3)
    total_ast_target = int(max(16, min(37, team_score * rng.uniform(0.18, 0.28) + team_rating.get("playmaking", 0) * 0.22)))
    total_stl_target = int(max(3, min(13, rng.gauss(7, 2))))
    total_blk_target = int(max(1, min(12, rng.gauss(5, 2))))
    total_tov_target = int(max(7, min(20, rng.gauss(12, 3) - team_rating.get("playmaking", 0) * 0.05 + opp_rating.get("defense", 0) * 0.04)))

    def allocate_stat(target: int, weight_fn, key: str):
        weights = [max(0.05, weight_fn(p)) for p in box]
        total = sum(weights) or 1
        vals = [int(max(0, round(target * w / total))) for w in weights]
        diff = target - sum(vals)
        order = sorted(range(len(vals)), key=lambda i: weights[i], reverse=True)
        i = 0
        while diff != 0 and order:
            idx = order[i % len(order)]
            if diff > 0:
                vals[idx] += 1
                diff -= 1
            elif vals[idx] > 0:
                vals[idx] -= 1
                diff += 1
            i += 1
            if i > 1000:
                break
        for p, v in zip(box, vals):
            p[key] = int(v)

    allocate_stat(total_reb_target, lambda p: (p["MIN"] / 36) * (_num(p["_src"], "TRB", "REB", default=3) + _num(p["_src"], "BLK", default=0) * 0.8), "REB")
    allocate_stat(total_ast_target, lambda p: (p["MIN"] / 36) * (_num(p["_src"], "AST", default=1) + _num(p["_src"], "OBPM", default=0) * 0.35 + 0.3), "AST")
    allocate_stat(total_stl_target, lambda p: (p["MIN"] / 36) * (_num(p["_src"], "STL", default=0.5) + _num(p["_src"], "DBPM", default=0) * 0.08 + 0.2), "STL")
    allocate_stat(total_blk_target, lambda p: (p["MIN"] / 36) * (_num(p["_src"], "BLK", default=0.4) + (1.0 if str(p["_src"].get("Pos", "")) in ["PF", "C"] else 0.1)), "BLK")
    allocate_stat(total_tov_target, lambda p: (p["MIN"] / 36) * (_num(p["_src"], "TOV", default=1) + _num(p["_src"], "USG%", default=18) * 0.04), "TOV")

    for p in box:
        p.pop("_src", None)
        p.pop("_clutch", None)

    return sorted(box, key=lambda p: (p["MIN"], p["PTS"]), reverse=True)


def _slot_order() -> List[str]:
    return [
        "Starting PG", "Starting SG", "Starting SF", "Starting PF", "Starting C",
        "Bench 1", "Bench 2", "Bench 3", "Bench 4", "Bench 5", "Bench 6", "Bench 7", "Bench 8", "Two-Way 1", "Two-Way 2"
    ]


def _game_mvp(box: List[Dict[str, Any]]) -> Dict[str, Any]:
    return max(box, key=lambda p: p["PTS"] + p["REB"] * 1.2 + p["AST"] * 1.5 + p["STL"] * 3 + p["BLK"] * 3 - p["TOV"] * 1.5)


def _series_mvp(games: List[Dict[str, Any]], winner_key: str) -> Dict[str, Any]:
    totals: Dict[str, Dict[str, Any]] = {}
    box_key = "p1_box" if winner_key == "P1" else "p2_box"
    for g in games:
        for p in g[box_key]:
            name = p["Player"]
            t = totals.setdefault(name, {"Player": name, "PTS": 0, "REB": 0, "AST": 0, "STL": 0, "BLK": 0, "TOV": 0, "G": 0})
            for k in ["PTS", "REB", "AST", "STL", "BLK", "TOV"]:
                t[k] += p[k]
            t["G"] += 1
    winner = max(totals.values(), key=lambda p: p["PTS"] + p["REB"] * 1.1 + p["AST"] * 1.4 + p["STL"] * 3 + p["BLK"] * 3 - p["TOV"] * 1.2)
    g = max(1, winner["G"])
    for k in ["PTS", "REB", "AST", "STL", "BLK", "TOV"]:
        winner[f"{k}_AVG"] = round(winner[k] / g, 1)
    return winner


# ============================================================
# SERIES SIMULATION
# ============================================================

def _series_seed(room_code: str, p1_roster: List[Dict[str, Any]], p2_roster: List[Dict[str, Any]], run_id: str) -> int:
    joined = room_code + "|" + run_id + "|" + ",".join(_player_name(p) for p in p1_roster) + "|" + ",".join(_player_name(p) for p in p2_roster)
    return _stable_seed(joined)


def simulate_series(
    room_code: str,
    p1_roster: List[Dict[str, Any]],
    p2_roster: List[Dict[str, Any]],
    strength_fn: Optional[Callable[[List[Dict[str, Any]]], Dict[str, float]]] = None,
    run_id: Optional[str] = None,
    injuries_enabled: bool = True,
) -> Dict[str, Any]:
    strength_fn = strength_fn or default_team_strength
    s1 = strength_fn(p1_roster)
    s2 = strength_fn(p2_roster)
    run_id = run_id or uuid.uuid4().hex[:8]
    rng = random.Random(_series_seed(room_code, p1_roster, p2_roster, run_id))

    p1_wins = 0
    p2_wins = 0
    games = []
    home_pattern = ["P1", "P1", "P2", "P2", "P1", "P2", "P1"]
    p1_fatigue = 0.0
    p2_fatigue = 0.0
    p1_injuries: Dict[str, str] = {}
    p2_injuries: Dict[str, str] = {}

    for game_no in range(1, MAX_GAMES + 1):
        if p1_wins == 4 or p2_wins == 4:
            break

        home = home_pattern[game_no - 1]
        elimination_p1 = p2_wins == 3
        elimination_p2 = p1_wins == 3
        home_edge = 2.4

        clutch_gap = (s1.get("clutch", 0) - s2.get("clutch", 0)) * (0.07 + (0.09 if game_no >= 6 else 0))
        rating_gap = (s1["overall"] - s2["overall"]) * 0.50
        matchup_gap = (
            (s1["offense"] - s2["defense"]) * 0.12
            + (s1["defense"] - s2["offense"]) * 0.10
            + (s1["shooting"] - s2["defense"] * 0.35) * 0.05
            + (s1["rebounding"] - s2["rebounding"]) * 0.05
            + (s1["depth"] - s2["depth"]) * 0.03
        )
        fatigue_gap = (p2_fatigue - p1_fatigue) * 1.6
        elimination_boost = (1.8 if elimination_p1 else 0) - (1.8 if elimination_p2 else 0)
        p1_expected_margin = rating_gap + matchup_gap + clutch_gap + fatigue_gap + elimination_boost + (home_edge if home == "P1" else -home_edge)

        noise = rng.gauss(0, 8.2)
        margin = p1_expected_margin + noise
        pace_total = rng.randint(208, 236)
        pace_total += int((s1["offense"] + s2["offense"] - s1["defense"] - s2["defense"]) * 0.10)
        pace_total = max(188, min(252, pace_total))

        p1_score = int(round(pace_total / 2 + margin / 2))
        p2_score = int(round(pace_total / 2 - margin / 2))
        if p1_score == p2_score:
            if rng.random() < 0.5:
                p1_score += rng.choice([1, 2, 3])
            else:
                p2_score += rng.choice([1, 2, 3])

        winner = "P1" if p1_score > p2_score else "P2"
        if winner == "P1":
            p1_wins += 1
        else:
            p2_wins += 1

        # Injuries are rare and mostly create limited-minutes outcomes.
        game_injury_notes = []
        if injuries_enabled:
            for side, roster, injuries in [("P1", p1_roster, p1_injuries), ("P2", p2_roster, p2_injuries)]:
                if rng.random() < 0.055:
                    candidates = roster[:8]
                    injured = rng.choice(candidates)
                    name = _player_name(injured)
                    severity = "limited by a minor injury" if rng.random() < 0.75 else "out with an injury"
                    injuries[name] = severity
                    game_injury_notes.append(f"{name} was {severity}.")

        p1_clutch_bonus = 2.4 if (winner == "P1" and abs(p1_score - p2_score) <= 8) else 0.6
        p2_clutch_bonus = 2.4 if (winner == "P2" and abs(p1_score - p2_score) <= 8) else 0.6

        p1_box = generate_team_box_score(p1_roster, p1_score, s1, s2, rng, game_no, p1_fatigue, p1_injuries, p1_clutch_bonus)
        p2_box = generate_team_box_score(p2_roster, p2_score, s2, s1, rng, game_no, p2_fatigue, p2_injuries, p2_clutch_bonus)

        plus_margin = p1_score - p2_score
        for p in p1_box:
            p["+/-"] = int(round(plus_margin * (p["MIN"] / 240) + rng.gauss(0, 4)))
        for p in p2_box:
            p["+/-"] = int(round(-plus_margin * (p["MIN"] / 240) + rng.gauss(0, 4)))

        winning_box = p1_box if winner == "P1" else p2_box
        mvp = _game_mvp(winning_box)

        # Fatigue carries forward: heavy starter load increases fatigue, deep wins reduce it.
        p1_heavy = sum(1 for p in p1_box[:7] if p["MIN"] >= 36)
        p2_heavy = sum(1 for p in p2_box[:7] if p["MIN"] >= 36)
        p1_fatigue = max(0, min(5, p1_fatigue + p1_heavy * 0.45 - s1["depth"] * 0.006 + rng.uniform(-0.2, 0.4)))
        p2_fatigue = max(0, min(5, p2_fatigue + p2_heavy * 0.45 - s2["depth"] * 0.006 + rng.uniform(-0.2, 0.4)))

        games.append({
            "game": game_no,
            "home": home,
            "p1_score": p1_score,
            "p2_score": p2_score,
            "winner": winner,
            "series": f"{p1_wins}-{p2_wins}",
            "p1_box": p1_box,
            "p2_box": p2_box,
            "game_mvp": mvp,
            "injury_notes": game_injury_notes,
            "fatigue": {"P1": round(p1_fatigue, 1), "P2": round(p2_fatigue, 1)},
        })

    series_winner = "P1" if p1_wins > p2_wins else "P2"
    return {
        "run_id": run_id,
        "p1_strength": s1,
        "p2_strength": s2,
        "games": games,
        "p1_wins": p1_wins,
        "p2_wins": p2_wins,
        "series_winner": series_winner,
        "series_mvp": _series_mvp(games, series_winner),
    }


# ============================================================
# AI STORYLINES
# ============================================================

def fallback_series_storyline(result: Dict[str, Any], p1_name: str, p2_name: str) -> str:
    winner_name = p1_name if result["series_winner"] == "P1" else p2_name
    loser_name = p2_name if result["series_winner"] == "P1" else p1_name
    mvp = result["series_mvp"]
    close_games = [g for g in result["games"] if abs(g["p1_score"] - g["p2_score"]) <= 6]
    swing_game = max(result["games"], key=lambda g: abs(g["p1_score"] - g["p2_score"]))

    return f"""
### Series Headline
{winner_name} defeats {loser_name} {result['p1_wins']}-{result['p2_wins']} behind a stronger top-end performance and better late-series execution.

### Series MVP
**{mvp['Player']}** controlled the matchup, averaging **{mvp['PTS_AVG']} PPG, {mvp['REB_AVG']} RPG, and {mvp['AST_AVG']} APG**.

### Turning Point
Game {swing_game['game']} created the clearest separation: {winner_name if swing_game['winner'] == result['series_winner'] else loser_name} won {swing_game['p1_score']}-{swing_game['p2_score']}. The series had {len(close_games)} close game(s), so late-game shot creation and fatigue management mattered.

### What Decided It
The winning team got enough star production while avoiding long empty stretches from the rotation. The losing side had moments, but could not consistently match the combination of scoring pressure, matchup counters, and closing reliability.
"""


def generate_ai_series_storyline(result: Dict[str, Any], room: Dict[str, Any]) -> str:
    api_key = st.secrets.get("OPENAI_API_KEY", "").strip()
    p1_name = room.get("p1_name", "Player 1")
    p2_name = room.get("p2_name", "Player 2")

    if OpenAI is None or not api_key:
        return fallback_series_storyline(result, p1_name, p2_name)

    client = OpenAI(api_key=api_key)

    compact_games = []
    for g in result["games"]:
        p1_top = sorted(g["p1_box"], key=lambda p: p["PTS"] + p["REB"] + p["AST"], reverse=True)[:4]
        p2_top = sorted(g["p2_box"], key=lambda p: p["PTS"] + p["REB"] + p["AST"], reverse=True)[:4]
        compact_games.append({
            "game": g["game"],
            "score": f"{p1_name} {g['p1_score']}, {p2_name} {g['p2_score']}",
            "winner": p1_name if g["winner"] == "P1" else p2_name,
            "game_mvp": g["game_mvp"],
            "injuries": g.get("injury_notes", []),
            "fatigue": g.get("fatigue", {}),
            "top_p1": p1_top,
            "top_p2": p2_top,
        })

    payload = {
        "teams": {"P1": p1_name, "P2": p2_name},
        "series_result": {
            "winner": p1_name if result["series_winner"] == "P1" else p2_name,
            "p1_wins": result["p1_wins"],
            "p2_wins": result["p2_wins"],
            "series_mvp": result["series_mvp"],
            "team_ratings": {"P1": result["p1_strength"], "P2": result["p2_strength"]},
        },
        "games": compact_games,
        "instruction": "Write like an NBA playoff recap. Explain matchups, fatigue, clutch moments, injuries if present, and why the winning team advanced. Do not invent stats not in the payload."
    }

    prompt = f"""
You are an NBA playoff writer inside a roster simulator.

Write a fun but realistic head-to-head best-of-seven series recap using ONLY the data below.
Use these exact sections:

### Series Headline
### Series MVP
### Turning Point
### Matchup Story
### What The Losing Team Needs To Fix

Keep it concise, specific, and basketball-focused. Mention real player names from the box scores.
Do not say this was simulated by code.

DATA:
{json.dumps(payload, indent=2)}
"""
    try:
        response = client.responses.create(model="gpt-4.1-mini", input=prompt, temperature=0.95)
        return response.output_text
    except Exception:
        return fallback_series_storyline(result, p1_name, p2_name)


# ============================================================
# ROOM HELPERS
# ============================================================

def _upsert_player(room_code: str, slot: str, name: str, roster: List[Dict[str, Any]], salary_cap: int) -> None:
    rooms = _load_rooms()
    room = rooms.setdefault(room_code, {})
    room.setdefault("room_code", room_code)
    room.setdefault("created_at", _now())
    room.setdefault("status", "waiting")
    room[f"{slot}_name"] = name or ("Player 1" if slot == "p1" else "Player 2")
    room[f"{slot}_roster"] = _safe_roster(roster)
    room["salary_cap"] = salary_cap
    room["updated_at"] = _now()
    if room.get("p1_roster") and room.get("p2_roster"):
        room["status"] = "ready"
    room.pop("result", None)
    room.pop("storyline", None)
    rooms[room_code] = room
    _save_rooms(rooms)


def _render_roster_cards(title: str, roster: List[Dict[str, Any]]) -> None:
    st.markdown(f"**{title}**")
    if not roster:
        st.caption("No roster locked yet.")
        return
    for i, p in enumerate(roster[:15], 1):
        slot = p.get("Slot", "")
        pos = p.get("Pos", "")
        salary = _money(_num(p, "Salary", default=0))
        st.caption(f"{i}. {slot} — {pos} {_player_name(p)} ({salary})")


def _render_box_score(team_name: str, box: List[Dict[str, Any]]) -> None:
    show = pd.DataFrame(box)[["Player", "MIN", "PTS", "REB", "AST", "STL", "BLK", "TOV", "+/-"]]
    st.markdown(f"**{team_name} Box Score**")
    st.dataframe(show, use_container_width=True, hide_index=True, height=310)


# ============================================================
# STREAMLIT UI
# ============================================================

# ============================================================
# H2H ONLINE ROLE-LOCKED LIVE UI OVERRIDE
# ============================================================
# This final definition intentionally overrides the earlier render_head_to_head_mode
# while reusing the same simulation, box-score, storage, and AI helpers above.


def _h2h_session_id() -> str:
    if "h2h_session_id" not in st.session_state:
        st.session_state.h2h_session_id = uuid.uuid4().hex
    return st.session_state.h2h_session_id


def _team_label(room: Dict[str, Any], slot: str) -> str:
    team = str(room.get(f"{slot}_team_name") or "").strip()
    owner = str(room.get(f"{slot}_name") or ("Player 1" if slot == "p1" else "Player 2")).strip()
    return team or owner or ("Player 1" if slot == "p1" else "Player 2")


def _owner_label(room: Dict[str, Any], slot: str) -> str:
    return str(room.get(f"{slot}_name") or ("Player 1" if slot == "p1" else "Player 2"))


def _role_for_session(room: Dict[str, Any], session_id: str) -> Optional[str]:
    # Strict role locking:
    # - creator session is always Player 1
    # - first joiner session is always Player 2
    # - no browser can manually switch roles
    if room.get("p1_session") == session_id:
        return "p1"
    if room.get("p2_session") == session_id:
        return "p2"
    return None


def _upsert_player_v2(
    room_code: str,
    slot: str,
    owner_name: str,
    team_name: str,
    roster: List[Dict[str, Any]],
    salary_cap: int,
) -> None:
    rooms = _load_rooms()
    room = rooms.setdefault(room_code, {})
    room.setdefault("room_code", room_code)
    room.setdefault("created_at", _now())
    room.setdefault("status", "waiting")
    room[f"{slot}_name"] = owner_name or ("Player 1" if slot == "p1" else "Player 2")
    room[f"{slot}_team_name"] = team_name or owner_name or ("Player 1" if slot == "p1" else "Player 2")
    room[f"{slot}_roster"] = _safe_roster(roster)
    room[f"{slot}_locked"] = True
    room["salary_cap"] = int(salary_cap)
    room["updated_at"] = _now()
    if room.get("p1_roster") and room.get("p2_roster"):
        room["status"] = "ready"
    # Changing a locked roster invalidates any previous result.
    room.pop("result", None)
    room.pop("full_result", None)
    room.pop("visible_games", None)
    room.pop("storyline", None)
    rooms[room_code] = room
    _save_rooms(rooms)


def _visible_result(full_result: Dict[str, Any], visible_games: int) -> Dict[str, Any]:
    result = json.loads(json.dumps(full_result))
    games = result.get("games", [])[:max(0, int(visible_games))]
    p1_wins = sum(1 for g in games if g.get("winner") == "P1")
    p2_wins = sum(1 for g in games if g.get("winner") == "P2")
    result["games"] = games
    result["p1_wins"] = p1_wins
    result["p2_wins"] = p2_wins
    if p1_wins >= 4 or p2_wins >= 4:
        result["series_winner"] = "P1" if p1_wins > p2_wins else "P2"
        result["series_mvp"] = _series_mvp(games, result["series_winner"])
    else:
        result["series_winner"] = None
        result["series_mvp"] = {}
    return result


def _series_is_complete(result: Dict[str, Any]) -> bool:
    return int(result.get("p1_wins", 0)) >= 4 or int(result.get("p2_wins", 0)) >= 4


def _render_room_header(room: Dict[str, Any], role: Optional[str], room_code: str, salary_cap: int) -> None:
    role_text = "Player 1 / Host" if role == "p1" else "Player 2 / Guest" if role == "p2" else "Spectator"
    st.markdown(f"### Room Code: `{room_code}`")
    st.caption(f"You are locked in as **{role_text}** • Salary Cap: {_money(room.get('salary_cap', salary_cap))}")


def _render_roster_cards_v2(title: str, owner: str, roster: List[Dict[str, Any]], locked: bool = False) -> None:
    lock_text = " ✅ Locked" if locked and roster else ""
    st.markdown(f"#### {title}{lock_text}")
    st.caption(f"GM: {owner}")
    if not roster:
        st.info("Waiting for roster lock.")
        return
    for i, p in enumerate(roster, start=1):
        slot = p.get("Slot", f"Player {i}")
        pos = p.get("Pos", "")
        salary = _money(p.get("Salary", 0))
        st.caption(f"{i}. {slot} — {pos} {_player_name(p)} ({salary})")


def _render_result_tables(result: Dict[str, Any], p1_name: str, p2_name: str, complete: bool) -> None:
    if not result.get("games"):
        st.info("Series created. Player 1 can simulate Game 1.")
        return

    if complete:
        winner_name = p1_name if result["series_winner"] == "P1" else p2_name
        st.markdown(f"## {winner_name} wins the series {max(result['p1_wins'], result['p2_wins'])}-{min(result['p1_wins'], result['p2_wins'])}")
    else:
        leader = p1_name if result.get("p1_wins", 0) > result.get("p2_wins", 0) else p2_name if result.get("p2_wins", 0) > result.get("p1_wins", 0) else "Series tied"
        st.markdown(f"## Series in progress: {p1_name} {result.get('p1_wins', 0)} — {p2_name} {result.get('p2_wins', 0)}")
        st.caption(f"Current leader: {leader}")

    m1, m2, m3 = st.columns(3)
    m1.metric(p1_name, f"{result.get('p1_wins', 0)} wins", f"OVR {result.get('p1_strength', {}).get('overall', 0)}")
    m2.metric(p2_name, f"{result.get('p2_wins', 0)} wins", f"OVR {result.get('p2_strength', {}).get('overall', 0)}")
    if complete and result.get("series_mvp"):
        mvp = result.get("series_mvp", {})
        m3.metric("Series MVP", mvp.get("Player", "—"), f"{mvp.get('PTS_AVG', 0)} PPG")
    else:
        last = result["games"][-1]
        m3.metric("Latest Game MVP", last.get("game_mvp", {}).get("Player", "—"), f"Game {last.get('game')}")

    game_rows = []
    for g in result["games"]:
        game_rows.append({
            "Game": g["game"],
            "Home": p1_name if g["home"] == "P1" else p2_name,
            p1_name: g["p1_score"],
            p2_name: g["p2_score"],
            "Winner": p1_name if g["winner"] == "P1" else p2_name,
            "Game MVP": g["game_mvp"]["Player"],
            "Series": g["series"],
        })
    st.dataframe(pd.DataFrame(game_rows), use_container_width=True, hide_index=True)

    with st.expander("Game-by-game box scores", expanded=True):
        game_labels = [f"Game {g['game']} — {p1_name} {g['p1_score']}, {p2_name} {g['p2_score']}" for g in result["games"]]
        selected_label = st.selectbox("Choose game", game_labels, index=len(game_labels) - 1, key="h2h_box_game_live")
        selected_idx = game_labels.index(selected_label)
        g = result["games"][selected_idx]
        if g.get("injury_notes"):
            st.warning(" ".join(g["injury_notes"]))
        t1, t2 = st.tabs([f"{p1_name} Box", f"{p2_name} Box"])
        with t1:
            _render_box_score(p1_name, g["p1_box"])
        with t2:
            _render_box_score(p2_name, g["p2_box"])

    with st.expander("Team matchup ratings"):
        st.dataframe(pd.DataFrame([result["p1_strength"], result["p2_strength"]], index=[p1_name, p2_name]), use_container_width=True)


def render_head_to_head_mode(
    current_roster: Any,
    salary_cap: int,
    calculate_team_strength: Optional[Callable[[List[Dict[str, Any]]], Dict[str, float]]] = None,
) -> None:
    st.markdown('<div class="section-heading-mobile">Online Head-to-Head</div>', unsafe_allow_html=True)
    st.caption("Create a room, lock both rosters, then Player 1 controls the live best-of-seven simulation and AI storyline.")

    session_id = _h2h_session_id()
    current = _safe_roster(current_roster)
    enough_players = len(current) >= MIN_H2H_PLAYERS

    if "h2h_room_code" not in st.session_state:
        st.session_state.h2h_room_code = ""
    if "h2h_slot" not in st.session_state:
        st.session_state.h2h_slot = ""
    if "h2h_team_name" not in st.session_state:
        st.session_state.h2h_team_name = ""

    # URL challenge support: opening a challenge automatically joins as Player 2.
    challenge_code = st.query_params.get("challenge", "") if hasattr(st, "query_params") else ""
    if challenge_code and not st.session_state.h2h_room_code:
        try:
            payload = decode_roster_payload(challenge_code)
            code = _make_room_code()
            rooms = _load_rooms()
            rooms[code] = {
                "room_code": code,
                "created_at": _now(),
                "updated_at": _now(),
                "status": "waiting",
                "p1_session": payload.get("session", "challenge_host"),
                "p2_session": session_id,
                "p1_name": payload.get("name", "Player 1"),
                "p1_team_name": payload.get("team_name", payload.get("name", "Player 1")),
                "p2_team_name": st.session_state.h2h_team_name or "Player 2",
                "p2_name": st.session_state.h2h_team_name or "Player 2",
                "p1_roster": payload.get("roster", []),
                "p2_roster": [],
                "p1_locked": True,
                "p2_locked": False,
                "salary_cap": int(payload.get("salary_cap", salary_cap)),
            }
            _save_rooms(rooms)
            st.session_state.h2h_room_code = code
            st.session_state.h2h_slot = "p2"
            st.success(f"Challenge loaded. You joined as Player 2 in room {code}.")
            st.rerun()
        except Exception:
            st.warning("Challenge link could not be loaded. Create or join a room manually.")

    setup_col1, setup_col2 = st.columns(2)
    with setup_col1:
        st.session_state.h2h_team_name = st.text_input("Team name", value=st.session_state.h2h_team_name, placeholder="Dimitri Hoops", key="h2h_team_name_input")
        if st.button("Create New Room", use_container_width=True, key="h2h_create_room_v2"):
            code = _make_room_code()
            rooms = _load_rooms()
            team = st.session_state.h2h_team_name or "Player 1"
            owner = team
            rooms[code] = {
                "room_code": code,
                "created_at": _now(),
                "updated_at": _now(),
                "status": "waiting",
                "p1_session": session_id,
                "p2_session": "",
                "p1_name": owner,
                "p1_team_name": team,
                "p2_name": "Player 2",
                "p2_team_name": "Player 2",
                "p1_roster": [],
                "p2_roster": [],
                "p1_locked": False,
                "p2_locked": False,
                "salary_cap": int(salary_cap),
            }
            _save_rooms(rooms)
            st.session_state.h2h_room_code = code
            st.session_state.h2h_slot = "p1"
            st.success(f"Room created: {code}. You are locked in as Player 1.")
            st.rerun()

    with setup_col2:
        join_code = st.text_input("Room code", value=st.session_state.h2h_room_code, max_chars=6, key="h2h_join_code_v2").upper().strip()
        st.caption("Joiners are automatically locked as Player 2.")
        if st.button("Join Room", use_container_width=True, key="h2h_join_room_v2"):
            rooms = _load_rooms()
            if join_code not in rooms:
                st.error("Room not found. Check the code or create a new room.")
            else:
                room = rooms[join_code]
                if room.get("p1_session") == session_id:
                    st.warning("You created this room, so this browser is locked as Player 1.")
                    st.session_state.h2h_room_code = join_code
                    st.session_state.h2h_slot = "p1"
                    st.rerun()
                elif room.get("p2_session") and room.get("p2_session") != session_id:
                    st.error("This room already has a Player 2. Create a new room for a different matchup.")
                else:
                    room["p2_session"] = session_id
                    room["p2_team_name"] = st.session_state.h2h_team_name or "Player 2"
                    room["p2_name"] = room["p2_team_name"]
                    room["updated_at"] = _now()
                    rooms[join_code] = room
                    _save_rooms(rooms)
                    st.session_state.h2h_room_code = join_code
                    st.session_state.h2h_slot = "p2"
                    st.success(f"Joined room {join_code}. You are locked in as Player 2.")
                    st.rerun()

    room_code = st.session_state.h2h_room_code.upper().strip()

    with st.expander("Shareable challenge link", expanded=False):
        if enough_players:
            payload = {
                "name": st.session_state.h2h_team_name or "Player 1",
                "team_name": st.session_state.h2h_team_name or "Player 1",
                "roster": current,
                "salary_cap": salary_cap,
                "session": session_id,
            }
            challenge = encode_roster_payload(payload)
            st.code(f"?challenge={challenge}", language="text")
            st.caption("Send this query string to another player. Your roster loads as Player 1, and they join as Player 2.")
        else:
            st.info(f"Draft at least {MIN_H2H_PLAYERS} players to create a challenge link.")

    if not room_code:
        st.info("Create a room or join a room to start.")
        return

    rooms = _load_rooms()
    room = rooms.get(room_code)
    if not room:
        st.warning("This room does not exist anymore. Create a new room.")
        return

    role = _role_for_session(room, session_id)
    if role in {"p1", "p2"}:
        st.session_state.h2h_slot = role

    _render_room_header(room, role, room_code, salary_cap)

    # Smart sync.
    # This uses Streamlit's rerun-safe autorefresh component instead of a browser
    # meta-refresh. It only runs while the room series is active/in progress.
    # Manual Refresh stays available at all times as a fallback.
    sync_col1, sync_col2 = st.columns([0.55, 0.45])
    with sync_col1:
        live_sync = st.toggle(
            "Auto-refresh live series every 3 seconds",
            value=True,
            key="h2h_live_sync_v3",
            help="Only runs while the room status is in_progress. It stops automatically when the series is complete."
        )

        if live_sync and room.get("status") == "in_progress":
            if st_autorefresh is not None:
                st.caption("Live sync is active. Updates check every 3 seconds.")
                st_autorefresh(interval=3000, key=f"h2h_live_sync_{room_code}")
            else:
                st.warning(
                    "Auto-refresh requires streamlit-autorefresh. Add it to requirements.txt, "
                    "then redeploy. Manual Refresh still works."
                )
        elif live_sync:
            st.caption("Auto-refresh will start once Player 1 begins the series.")
        else:
            st.caption("Auto-refresh is off. Use Refresh Room to sync manually.")

    with sync_col2:
        if st.button("Refresh Room", use_container_width=True, key="h2h_refresh_v2"):
            st.rerun()

    if role not in {"p1", "p2"}:
        st.info("You are viewing this room as a spectator. Only the room creator is Player 1, and the first person to join is Player 2.")

    series_started = bool(room.get("full_result") or room.get("result"))
    my_roster_key = f"{role}_roster" if role in {"p1", "p2"} else None
    my_locked_key = f"{role}_locked" if role in {"p1", "p2"} else None

    if role in {"p1", "p2"}:
        if not enough_players:
            st.warning(f"Draft at least {MIN_H2H_PLAYERS} players before locking your roster. Current: {len(current)}")
        elif series_started:
            st.info("Series has started. Rosters are locked until Player 1 resets the room result.")
        else:
            own_locked = bool(room.get(my_locked_key)) and bool(room.get(my_roster_key))
            label = "Roster Locked ✅" if own_locked else f"Lock Current Roster as {'Player 1' if role == 'p1' else 'Player 2'}"
            if st.button(label, type="primary", use_container_width=True, key="h2h_lock_roster_v2", disabled=own_locked):
                _upsert_player_v2(
                    room_code,
                    role,
                    st.session_state.h2h_team_name or ("Player 1" if role == "p1" else "Player 2"),
                    st.session_state.h2h_team_name or ("Player 1" if role == "p1" else "Player 2"),
                    current,
                    salary_cap,
                )
                st.success("Roster locked.")
                st.rerun()

    # Reload after potential changes.
    room = _load_rooms().get(room_code, room)
    p1_label = _team_label(room, "p1")
    p2_label = _team_label(room, "p2")

    a, b = st.columns(2)
    with a:
        _render_roster_cards_v2(p1_label, _owner_label(room, "p1"), room.get("p1_roster", []), bool(room.get("p1_locked")))
    with b:
        _render_roster_cards_v2(p2_label, _owner_label(room, "p2"), room.get("p2_roster", []), bool(room.get("p2_locked")))

    ready = bool(room.get("p1_roster")) and bool(room.get("p2_roster"))
    if not ready:
        st.info("Waiting for both players to lock rosters.")
        return

    is_host = role == "p1"
    status = room.get("status", "ready")
    full_result = room.get("full_result") or room.get("result")
    visible_games = int(room.get("visible_games", len(full_result.get("games", [])) if full_result else 0))
    injuries_enabled = st.toggle("Enable injuries / fatigue storylines", value=True, key="h2h_injuries_v2", disabled=bool(full_result))

    control_col1, control_col2 = st.columns(2)
    if not full_result:
        with control_col1:
            if is_host:
                if st.button("Start Series: Simulate Game 1", type="primary", use_container_width=True, key="h2h_start_series_v2"):
                    full_result = simulate_series(
                        room_code,
                        room["p1_roster"],
                        room["p2_roster"],
                        calculate_team_strength,
                        run_id=uuid.uuid4().hex[:8],
                        injuries_enabled=injuries_enabled,
                    )
                    rooms = _load_rooms()
                    rooms[room_code]["full_result"] = full_result
                    rooms[room_code]["visible_games"] = 1
                    rooms[room_code]["storyline"] = ""
                    rooms[room_code]["status"] = "in_progress"
                    rooms[room_code]["updated_at"] = _now()
                    _save_rooms(rooms)
                    st.rerun()
            else:
                st.button("Waiting for Player 1 to start", use_container_width=True, disabled=True, key="h2h_wait_start_v2")
    else:
        visible_result = _visible_result(full_result, visible_games)
        complete = _series_is_complete(visible_result)
        next_game_no = visible_games + 1
        with control_col1:
            if is_host and not complete:
                if st.button(f"Simulate Game {next_game_no}", type="primary", use_container_width=True, key="h2h_next_game_v2"):
                    rooms = _load_rooms()
                    rooms[room_code]["visible_games"] = min(visible_games + 1, len(full_result.get("games", [])))
                    new_visible = _visible_result(full_result, rooms[room_code]["visible_games"])
                    rooms[room_code]["status"] = "complete" if _series_is_complete(new_visible) else "in_progress"
                    if _series_is_complete(new_visible):
                        rooms[room_code]["result"] = new_visible
                    rooms[room_code]["updated_at"] = _now()
                    _save_rooms(rooms)
                    st.rerun()
            elif not is_host and not complete:
                st.button("Waiting for Player 1 to simulate next game", use_container_width=True, disabled=True, key="h2h_wait_next_v2")
        with control_col2:
            if is_host and not complete:
                if st.button("Simulate Rest of Series", use_container_width=True, key="h2h_rest_series_v2"):
                    rooms = _load_rooms()
                    total_games = len(full_result.get("games", []))
                    rooms[room_code]["visible_games"] = total_games
                    final_result = _visible_result(full_result, total_games)
                    rooms[room_code]["result"] = final_result
                    rooms[room_code]["status"] = "complete"
                    rooms[room_code]["updated_at"] = _now()
                    _save_rooms(rooms)
                    st.rerun()

    room = _load_rooms().get(room_code, room)
    full_result = room.get("full_result") or room.get("result")
    if not full_result:
        st.info("Both rosters are ready. Player 1 must start the series.")
        return

    visible_games = int(room.get("visible_games", len(full_result.get("games", []))))
    result = _visible_result(full_result, visible_games)
    complete = _series_is_complete(result)
    _render_result_tables(result, p1_label, p2_label, complete)

    st.markdown("### AI Series Storyline")
    if complete:
        if is_host:
            if st.button("Generate AI Storyline", use_container_width=True, key="h2h_storyline_v2"):
                story_room = dict(room)
                story_room["p1_name"] = p1_label
                story_room["p2_name"] = p2_label
                story = generate_ai_series_storyline(result, story_room)
                rooms = _load_rooms()
                rooms[room_code]["storyline"] = story
                rooms[room_code]["updated_at"] = _now()
                _save_rooms(rooms)
                st.rerun()
        else:
            st.button("Waiting for Player 1 to generate storyline", use_container_width=True, disabled=True, key="h2h_wait_story_v2")
    else:
        st.caption("Storyline unlocks after the series is complete. Player 1 generates it, and Player 2 sees the same saved recap.")

    room = _load_rooms().get(room_code, room)
    if room.get("storyline"):
        st.markdown(room["storyline"])
    elif complete:
        st.caption("No storyline generated yet.")

    if is_host:
        if st.button("Reset This Room Result", use_container_width=True, key="h2h_reset_result_v2"):
            rooms = _load_rooms()
            if room_code in rooms:
                rooms[room_code].pop("result", None)
                rooms[room_code].pop("full_result", None)
                rooms[room_code].pop("visible_games", None)
                rooms[room_code].pop("storyline", None)
                rooms[room_code]["status"] = "ready"
                rooms[room_code]["updated_at"] = _now()
                _save_rooms(rooms)
            st.rerun()
