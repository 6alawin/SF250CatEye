"""Match Openplay player IDs to Transfermarkt birth and profile attributes."""
import json
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / ".audit_deps"))
import duckdb
import pandas as pd

OPENPLAY_PLAYERS = Path(r"D:\Openplay\Openplay_Event\players.parquet")
TRANSFERMARKT_PLAYERS = ROOT / "transfermarkt_players.csv.gz"


def normalize_name(value):
    text = unicodedata.normalize("NFKD", str(value).casefold())
    return " ".join("".join(c for c in text if not unicodedata.combining(c) and (c.isalnum() or c.isspace())).split())


players = duckdb.sql(
    f"SELECT player_id, player, height_cm FROM read_parquet('{str(OPENPLAY_PLAYERS).replace(chr(39), chr(39)*2)}')"
).df()
tm = pd.read_csv(
    TRANSFERMARKT_PLAYERS,
    usecols=["name", "date_of_birth", "height_in_cm", "foot", "country_of_citizenship"],
)
players["name_key"] = players.player.map(normalize_name)
tm = tm.dropna(subset=["name", "date_of_birth", "height_in_cm"]).copy()
tm["name_key"] = tm.name.map(normalize_name)
tm["dob"] = tm.date_of_birth.astype(str).str[:10]
tm = tm[tm.dob.str.fullmatch(r"\d{4}-\d{2}-\d{2}")]
players = players[players.name_key.ne("") & players.height_cm.notna()]
players = players[~players.name_key.duplicated(keep=False)]
tm = tm[~tm.name_key.duplicated(keep=False)]
matched = players.merge(tm, on="name_key")
matched = matched[(matched.height_cm - matched.height_in_cm).abs() <= 3]

def text_or_none(value):
    return None if pd.isna(value) else str(value).strip() or None


birthdays = {}
profiles = {}
for row in matched.itertuples():
    player_id = str(int(row.player_id))
    birthdays[player_id] = row.dob
    profiles[player_id] = {
        "date_of_birth": row.dob,
        "preferred_foot": text_or_none(row.foot),
        "height_cm": int(row.height_in_cm),
        "nationality": text_or_none(row.country_of_citizenship),
    }

(ROOT / "player_birthdays.json").write_text(
    json.dumps(birthdays, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
)
(ROOT / "player_profiles.json").write_text(
    json.dumps(profiles, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
)
print(f"Matched {len(profiles)} Openplay player profiles")
print(f"With preferred-foot data: {sum(bool(p['preferred_foot']) for p in profiles.values())}")
print(f"With height data: {sum(bool(p['height_cm']) for p in profiles.values())}")
