# app/api.py

import logging
import os
import sqlite3
from flask import Flask, jsonify, request

import worker


SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", "/app/data/telegramarr.db")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

app = Flask(__name__)

@app.route("/")
def index():
    return jsonify({"status": "ok"})

@app.route("/requests")
def get_requests():
    conn = sqlite3.connect(SQLITE_DB_PATH)
    c = conn.cursor()

    rows = c.execute("""
    SELECT
        tmdbId,
        imdbId,
        tvdbId,
        title,
        year,
        status,
        poster_url,
        release_count,
        releases
    FROM requests
    ORDER BY inserted_at DESC
    """).fetchall()

    result = []

    for r in rows:
        result.append({
            "tmdbId": r[0],
            "imdbId": r[1],
            "tvdbId": r[2],
            "title": r[3],
            "year": r[4],
            "status": r[5],
            "poster": r[6],
            "release_count": r[7],
            "releases": r[8]
        })

    return jsonify({"data": result})


@app.route("/seerr-webhook", methods=["POST"])
def seerr_webhook():
    data = request.json
    logging.info(f"Nouvelle requête Seerr : {data}")

    worker.do_work()

    return {"status": "ok"}

#app.run(host="0.0.0.0", port=8000)