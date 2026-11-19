"""Match Openplay player IDs to Transfermarkt market values by unique name."""
import json
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / ".audit_deps"))
import duckdb
import pandas as pd

OPENPLAY_PLAYERS = ROOT / "Openplay" / "Openplay_Event" / "players.parquet"
TRANSFERMARKT_PLAYERS = ROOT / "transfermarkt_players.csv.gz"

def normalize_name(value):
    text = unicodedata.normalize("NFKD", str(value).casefold())
    return " ".join("".join(c for c in text if not unicodedata.combining(c) and (c.isalnum() or c.isspace())).split())

players = duckdb.sql(f"SELECT player_id, player FROM read_parquet('{str(OPENPLAY_PLAYERS).replace(chr(39), chr(39)*2)}')").df()
tm = pd.read_csv(TRANSFERMARKT_PLAYERS, usecols=["name", "market_value_in_eur"])
players["name_key"] = players.player.map(normalize_name)
tm["name_key"] = tm.name.map(normalize_name)
players = players[players.name_key.ne("") & ~players.name_key.duplicated(keep=False)]
tm = tm[tm.name_key.ne("") & ~tm.name_key.duplicated(keep=False)].dropna(subset=["market_value_in_eur"])
matched = players.merge(tm, on="name_key")
values = {str(int(row.player_id)): int(row.market_value_in_eur) for row in matched.itertuples() if row.market_value_in_eur > 0}
(ROOT / "player_market_values.json").write_text(json.dumps(values, separators=(",", ":")), encoding="utf-8")
print(f"Matched {len(values)} Openplay market values")
