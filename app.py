import os
import re
import time
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from flask import Flask, Response, abort, request, send_file

app = Flask(__name__)
ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")
SUMMARY = "openplay_player_season_extended.json.gz"
DATASETS = {SUMMARY, "player_birthdays.json", "player_market_values.json", "player_profiles.json"}
HEATMAP_NAME = re.compile(r"heatmap_(?:eng|esp|fra|ger|ita)_[0-9]{4}\.json\.gz")
ASSET_CACHE = {}
CACHE_CONTROL = "public, max-age=300, stale-while-revalidate=3600"


@app.get("/")
@app.get("/index.html")
@app.get("/demo.html")
def demo():
    return send_file(ROOT / "index.html", max_age=0)


@app.get("/<name>")
def dataset(name):
    if name not in DATASETS:
        abort(404)
    return asset(name, "application/json", gzip=name == SUMMARY)


@app.get("/heatmap-data/<name>")
def heatmap_file(name):
    if not HEATMAP_NAME.fullmatch(name):
        abort(404)
    return asset(name, "application/json", gzip=True)


def asset(name, content_type, gzip=False):
    try:
        cached = ASSET_CACHE.get(name)
        if cached is None or time.monotonic() - cached[3] >= 300:
            with psycopg.connect(os.environ["DATABASE_URL"], connect_timeout=8) as db:
                metadata = db.execute(
                    "SELECT size_bytes, sha256 FROM cateye_assets WHERE name = %s", (name,)
                ).fetchone()
                if metadata is None:
                    abort(404)
                size, sha = metadata
                if cached is None or cached[0] != sha:
                    content = db.execute(
                        "SELECT content FROM cateye_assets WHERE name = %s", (name,)
                    ).fetchone()[0]
                else:
                    content = cached[2]
            cached = (sha, size, content, time.monotonic())
            ASSET_CACHE[name] = cached
        sha, size, content, _ = cached
        headers = {
            "Accept-Ranges": "bytes",
            "Cache-Control": CACHE_CONTROL,
            "ETag": f'"{sha}"',
        }
        if gzip:
            headers["Content-Encoding"] = "gzip"
        if request.if_none_match.contains(sha):
            return Response(status=304, headers=headers)
        start, end, status = 0, size, 200
        if request.headers.get("Range"):
            bounds = request.range
            result = bounds.range_for_length(size) if bounds and bounds.units == "bytes" else None
            if result is None:
                return Response(status=416, headers={"Content-Range": f"bytes */{size}"})
            start, end = result
            status = 206
            headers["Content-Range"] = f"bytes {start}-{end - 1}/{size}"
        body = content[start:end] if request.method != "HEAD" else b""
        response = Response(body, status, headers, content_type=content_type)
        response.content_length = end - start
        return response
    except (psycopg.Error, KeyError):
        return Response("CatEye data is temporarily unavailable.", status=503)
