import os
import time
import sqlite3
import requests
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# environment configuration
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL_MINUTES", "120"))
RADARR_HOST = os.getenv("RADARR_HOST")
RADARR_PORT = os.getenv("RADARR_PORT")
RADARR_API_KEY = os.getenv("RADARR_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", "/app/data/telegramarr.db")

RADARR_BASE = f"http://{RADARR_HOST}:{RADARR_PORT}/api/v3"


def init_db(path: str):
    conn = sqlite3.connect(path)
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS seen_movies (
            movie_id INTEGER NOT NULL PRIMARY KEY,
            imdbId TEXT NOT NULL,
            tmdbId TEXT NOT NULL
        )
        """
    )
    conn.commit()
    return conn


def get_monitored_unfiled_movies():
    url = f"{RADARR_BASE}/movie"
    params = {"apikey": RADARR_API_KEY}
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    movies = resp.json()
    # filter monitored=true and hasFile=false
    return [m for m in movies if m.get("monitored") and not m.get("hasFile")]


def get_releases_for_movie(session: requests.Session, movie_id: int):
    url = f"{RADARR_BASE}/release"
    params = {"apikey": RADARR_API_KEY, "movieId": movie_id}
    resp = session.get(url, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def is_movie_seen(conn, movie_id: int) -> bool:
    c = conn.cursor()
    c.execute("SELECT 1 FROM seen_movies WHERE movie_id=?", (movie_id,))
    return c.fetchone() is not None


def mark_movie_seen(conn, movie_id: int, imdbId: str, tmdbId: str):
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO seen_movies(movie_id, imdbId, tmdbId) VALUES(?, ?, ?)", (movie_id, imdbId, tmdbId))
    conn.commit()


def send_telegram_message(text: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logging.warning("Telegram credentials not provided, skipping notification")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": text}
    resp = requests.post(url, data=data)
    if not resp.ok:
        logging.error(f"Telegram API returned {resp.status_code}: {resp.text}")


def main():
    conn = init_db(SQLITE_DB_PATH)
    logging.info(f"starting loop with interval {POLL_INTERVAL} minutes")
    send_telegram_message("Telegramarr démarré !")

    while True:
        movies = get_monitored_unfiled_movies()
        notifications_sent = 0
        logging.info(f"found {len(movies)} monitored/unfiled movies")

        httpSession = requests.Session()

        for movie in movies:
            movie_id = movie.get("id")
            imdbId = movie.get("imdbId")
            tmdbId = movie.get("tmdbId")
            if is_movie_seen(conn, movie_id):
                continue
            # check releases
            releases = get_releases_for_movie(httpSession,movie_id)
            # select those not rejected
            ok = [r for r in releases if not r.get("rejected")]
            if ok:
                mark_movie_seen(conn, movie_id, imdbId, tmdbId)
                title = movie.get("title")
                msg = f"Film disponible ! \"{title}\" a {len(ok)} nouvelles releases"
                logging.info(msg)
                send_telegram_message(msg)
                notifications_sent += 1
        logging.info(f"end of loop: processed {len(movies)}, sent {notifications_sent} notifications, sleeping for {POLL_INTERVAL} minutes")
        time.sleep(POLL_INTERVAL * 60)


if __name__ == "__main__":
    main()
