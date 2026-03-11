import logging
import os
import sqlite3
import requests
from datetime import datetime, timedelta

# --- CONFIGURATION ---
RADARR_HOST = os.getenv("RADARR_HOST", "radarr")
RADARR_PORT = os.getenv("RADARR_PORT", "7878")
RADARR_API_KEY = os.getenv("RADARR_API_KEY")

SEERR_HOST = os.getenv("SEERR_HOST", "seerr")
SEERR_PORT = os.getenv("SEERR_PORT", "5055")
SEERR_API_KEY = os.getenv("SEERR_API_KEY")

PROWLARR_HOST = os.getenv("PROWLARR_HOST", "prowlarr")
PROWLARR_PORT = os.getenv("PROWLARR_PORT", "9696")
PROWLARR_API_KEY = os.getenv("PROWLARR_API_KEY")

TMDB_API_KEY = os.getenv("TMDB_API_KEY")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

SEERR_BASE = f"http://{SEERR_HOST}:{SEERR_PORT}/api/v1"
RADARR_BASE = f"http://{RADARR_HOST}:{RADARR_PORT}/api/v3"
PROWLARR_BASE = f"http://{PROWLARR_HOST}:{PROWLARR_PORT}/api/v1"

SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", "/app/data/telegramarr.db")

SEARCH_INTERVAL_HOURS = int(os.getenv("SEARCH_INTERVAL_HOURS", "6"))

# --- BASE DE DONNEES ---
conn = sqlite3.connect(SQLITE_DB_PATH)
c = conn.cursor()
c.execute("""
CREATE TABLE IF NOT EXISTS requests (
    seerr_id INTEGER PRIMARY KEY,
    tmdbId INTEGER,
    imdbId TEXT,
    tvdbId INTEGER,
    title TEXT,
    inserted_at TEXT,
    last_search TEXT,
    available_at TEXT,
    releases TEXT
)
""")
conn.commit()

# --- FONCTIONS UTILES ---
def get_seerr_requests(filter : str = "all"):
    url = f"{SEERR_BASE}/request"
    resp = requests.get(url, headers={"X-Api-Key": SEERR_API_KEY})
    #resp = requests.get(url, headers={"X-Api-Key": SEERR_API_KEY}, params={"filter": filter})
    resp.raise_for_status()
    return resp.json()["results"]


def send_telegram_message(text: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logging.warning("Telegram credentials not provided, skipping notification")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    resp = requests.post(url, data=data)
    if not resp.ok:
        logging.error(f"Telegram API returned {resp.status_code}: {resp.text}")

def get_tmdb_data(tmdbId):
    url = f"https://api.themoviedb.org/3/movie/{tmdbId}"
    params = {"api_key": TMDB_API_KEY, "language": "fr-FR", "append_to_response": "external_ids"}
    resp = requests.get(url, params=params)
    resp.raise_for_status()
    return resp.json()

def search_prowlarr(imdbId):
    url = f"{PROWLARR_BASE}/search"
    resp = requests.get(url, headers={"X-Api-Key": PROWLARR_API_KEY}, params={"query": imdbId})
    resp.raise_for_status()
    return resp.json()

# --- LOGIQUE PRINCIPALE ---
def main():
    now = datetime.now()

    logging.info(f"starting loop with interval {SEARCH_INTERVAL_HOURS} hours")
    send_telegram_message("Telegramarr démarré !")

    seerr_requests = get_seerr_requests("approved,pending,processing,unavailable,failed")
    
    for req in seerr_requests:
        seerr_id = req["id"]
        tmdbId = req["media"]["tmdbId"]
        imdbId = req["media"]["imdbId"]
        tvdbId = req["media"]["tvdbId"]
        title = None
        
        # vérifier si déjà en base
        c.execute("SELECT last_search, available_at FROM requests WHERE seerr_id=?", (seerr_id,))
        row = c.fetchone()
        
        search_needed = True
        if row:
            last_search_str, available_at, title = row
            if last_search_str:
                last_search_dt = datetime.fromisoformat(last_search_str)
                if now - last_search_dt < timedelta(hours=SEARCH_INTERVAL_HOURS):
                    search_needed = False  # déjà recherché récemment
            if available_at:
                search_needed = False  # déjà disponible

        if search_needed:
            try:
                if (not imdbId and tmdbId) or not title:
                    data = get_tmdb_data(tmdbId)
                    if not imdbId and tmdbId:
                        imdbId = data.get("external_ids", {}).get("imdb_id")
                    if not title:
                        title = data.get("title")
                releases = search_prowlarr(imdbId)
            except Exception as e:
                logging.error(f"Erreur Prowlarr pour seerr_id {seerr_id} (imdbId {imdbId}, tmdbId {tmdbId}, tvdbId {tvdbId}): {e}")
                continue

            if releases:               
                # message Telegram
                logging.info(f"Film disponible ! \"{title}\" a {len(releases)} nouvelles releases")

                msg_html = f"<b>{title}</b>"
                msg_html += f" (<a href='https://www.imdb.com/title/{imdbId}'>imdb</a> - <a href='https://www.themoviedb.org/movie/{tmdbId}'>tmdb</a>)"
                msg_html += "\nDisponible au téléchargement !"
                release_list = ""
                for r in releases:
                    release_title = r.get("title")
                    msg_html += f"\n- <i>{release_title}</i>"
                    release_list += f"- {release_title}\n"

                send_telegram_message(msg_html)
                
                # update DB
                c.execute("""
                    INSERT OR REPLACE INTO requests
                    (seerr_id, tmdbId, imdbId, title, inserted_at, last_search, available_at, releases)
                    VALUES (?, ?, ?, ?, COALESCE((SELECT inserted_at FROM requests WHERE seerr_id=?), ?), ?, ?, ?)
                """, (seerr_id, tmdbId, imdbId, title, seerr_id, now.isoformat(), now.isoformat(), now.isoformat(), release_list))
            else:
                # update last_search
                c.execute("""
                    INSERT OR REPLACE INTO requests
                    (seerr_id, tmdbId, imdbId, title, inserted_at, last_search)
                    VALUES (?, ?, ?, ?, COALESCE((SELECT inserted_at FROM requests WHERE seerr_id=?), ?), ?)
                """, (seerr_id, tmdbId, imdbId, title, seerr_id, now.isoformat(), now.isoformat()))
            
            conn.commit()

    # --- suppression des films disponibles dans Plex ---
    # Ici tu peux vérifier via l'API Plex ou autre si le film est dispo, puis :
    # c.execute("DELETE FROM requests WHERE seerr_id=?", (seerr_id,))
    # conn.commit()

if __name__ == "__main__":
    main()
