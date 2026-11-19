"""Build the four CatEye heatmap counts per player and pitch zone."""
import argparse
import gzip
import json
import re
from collections import defaultdict
from pathlib import Path

import duckdb

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("event_dir", type=Path)
parser.add_argument("output_dir", type=Path)
args = parser.parse_args()
pattern = re.compile(r"events_((?:eng|esp|fra|ger|ita)_[0-9]{4})\.parquet")
files = sorted(path for path in args.event_dir.glob("*.parquet") if pattern.fullmatch(path.name))
if len(files) != 60:
    parser.error("Expected 60 Big Five event files")
args.output_dir.mkdir(parents=True, exist_ok=True)

with duckdb.connect() as db:
    for source in files:
        counts = db.execute("""
            SELECT player_id,
                   LEAST(9, CAST(FLOOR(x / 10) AS INTEGER)) AS zone_x,
                   LEAST(9, CAST(FLOOR(y / 10) AS INTEGER)) AS zone_y,
                   COUNT(*),
                   COUNT(*) FILTER (WHERE is_touch = true),
                   COUNT(*) FILTER (WHERE is_shot = true),
                   COUNT(*) FILTER (WHERE type = 'Pass')
            FROM read_parquet(?)
            WHERE player_id IS NOT NULL AND x IS NOT NULL AND y IS NOT NULL
            GROUP BY 1, 2, 3
            ORDER BY 1, 2, 3
        """, [str(source)]).fetchall()
        players = defaultdict(list)
        for player_id, *bins in counts:
            players[player_id].append(bins)
        target = args.output_dir / f"heatmap_{pattern.fullmatch(source.name)[1]}.json.gz"
        payload = json.dumps(players, separators=(",", ":")).encode("utf-8")
        target.write_bytes(gzip.compress(payload, compresslevel=6, mtime=0))

print(f"Built {len(files)} heatmap files.")
