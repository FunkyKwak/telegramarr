# app/api.py

import os
import sqlite3
from flask import Flask, jsonify


SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", "/app/data/telegramarr.db")

app = Flask(__name__)

@app.route("/")
def index():
    return jsonify({"status": "ok"})

@app.route("/requests")
def get_requests():
    conn = sqlite3.connect(SQLITE_DB_PATH)
    c = conn.cursor()

    rows = c.execute("""
    SELECT title, year, status, poster_url
    FROM requests
    ORDER BY inserted_at DESC
    """).fetchall()

    result = []

    for r in rows:
        result.append({
            "title": r[0],
            "year": r[1],
            "status": r[2],
            "poster": r[3]
        })

    return jsonify(result)

#app.run(host="0.0.0.0", port=8000)