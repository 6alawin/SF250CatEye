"""Import the files required by CatEye into its Render PostgreSQL database."""
import argparse
import hashlib
import os
from pathlib import Path

import psycopg

from app import DATASETS, EVENT_NAME

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("data_dir", type=Path, help="Folder containing the three summary files")
parser.add_argument("event_dir", type=Path, help="Folder containing Openplay Parquet files")
args = parser.parse_args()
summary = [args.data_dir / name for name in sorted(DATASETS)]
events = sorted(path for path in args.event_dir.glob("*.parquet") if EVENT_NAME.fullmatch(path.name))
if len(events) != 61 or not any(path.name == "players.parquet" for path in events):
    parser.error("Expected 60 Big Five event files and players.parquet")
if any(not path.is_file() or path.stat().st_size == 0 for path in summary + events):
    parser.error("A required data file is missing or empty")

try:
    with psycopg.connect(os.environ["DATABASE_URL"], connect_timeout=12, autocommit=True) as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS cateye_assets (
                name text PRIMARY KEY,
                size_bytes integer NOT NULL,
                sha256 text NOT NULL,
                content bytea NOT NULL
            )
        """)
        for path in summary + events:
            content = path.read_bytes()
            sha = hashlib.sha256(content).hexdigest()
            current = db.execute(
                "SELECT sha256, octet_length(content) FROM cateye_assets WHERE name = %s",
                (path.name,),
            ).fetchone()
            if current == (sha, len(content)):
                print(f"Already present: {path.name}", flush=True)
                continue
            db.execute("""
                INSERT INTO cateye_assets (name, size_bytes, sha256, content)
                VALUES (%s, %s, %s, %b)
                ON CONFLICT (name) DO UPDATE SET size_bytes = EXCLUDED.size_bytes,
                  sha256 = EXCLUDED.sha256, content = EXCLUDED.content
            """, (path.name, len(content), sha, content))
            print(f"Uploaded {path.name}: {len(content):,} bytes", flush=True)
        expected = [path.name for path in summary + events]
        count, size = db.execute(
            "SELECT count(*), sum(octet_length(content)) FROM cateye_assets WHERE name = ANY(%s)",
            (expected,),
        ).fetchone()
        if count != len(expected) or size != sum(path.stat().st_size for path in summary + events):
            raise SystemExit("Database file count or size verification failed.")
        print(f"Verified {count} files and {size:,} bytes in PostgreSQL.")
except KeyError:
    raise SystemExit("Set DATABASE_URL in the local environment first.") from None
except psycopg.Error as exc:
    print(f"PostgreSQL import failed ({type(exc).__name__}, SQLSTATE {exc.sqlstate or 'n/a'}).")
    raise SystemExit(1) from None
