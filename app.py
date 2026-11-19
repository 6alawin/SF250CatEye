import os
import re
from pathlib import Path

import psycopg
from flask import Flask, Response, abort, request, send_file

app = Flask(__name__)
ROOT = Path(__file__).resolve().parent
SUMMARY = "openplay_player_season_extended.json.gz"
DATASETS = {SUMMARY, "player_birthdays.json", "player_market_values.json"}
EVENT_NAME = re.compile(r"(?:events_(?:eng|esp|fra|ger|ita)_[0-9]{4}|players)\.parquet")


@app.get("/")
@app.get("/demo.html")
def demo():
    return send_file(ROOT / "demo.html", max_age=0)


@app.get("/<name>")
def dataset(name):
    if name not in DATASETS:
        abort(404)
    return asset(name, "application/json", gzip=name == SUMMARY)


@app.get("/openplay-data/<name>")
def event_file(name):
    if not EVENT_NAME.fullmatch(name):
        abort(404)
    return asset(name, "application/octet-stream")


def asset(name, content_type, gzip=False):
    try:
        with psycopg.connect(os.environ["DATABASE_URL"], connect_timeout=8) as db:
            size_row = db.execute(
                "SELECT size_bytes FROM cateye_assets WHERE name = %s", (name,)
            ).fetchone()
            if size_row is None:
                abort(404)
            size = size_row[0]
            start, end, status = 0, size, 200
            headers = {"Accept-Ranges": "bytes", "Cache-Control": "no-store"}
            if request.headers.get("Range"):
                bounds = request.range
                result = bounds.range_for_length(size) if bounds and bounds.units == "bytes" else None
                if result is None:
                    return Response(status=416, headers={"Content-Range": f"bytes */{size}"})
                start, end = result
                status = 206
                headers["Content-Range"] = f"bytes {start}-{end - 1}/{size}"
            if gzip:
                headers["Content-Encoding"] = "gzip"
            body = b""
            if request.method != "HEAD":
                body = db.execute(
                    "SELECT substring(content FROM %s FOR %s) FROM cateye_assets WHERE name = %s",
                    (start + 1, end - start, name),
                ).fetchone()[0]
            response = Response(body, status, headers, content_type=content_type)
            response.content_length = end - start
            return response
    except (psycopg.Error, KeyError):
        return Response("CatEye data is temporarily unavailable.", status=503)
