import logging
import os
import sqlite3
import time
import requests
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


# --- CONFIGURATION ---
SEERR_HOST = os.getenv("SEERR_HOST", "seerr")
SEERR_PORT = os.getenv("SEERR_PORT", "5055")
SEERR_API_KEY = os.getenv("SEERR_API_KEY")
SEERR_BASE = f"http://{SEERR_HOST}:{SEERR_PORT}/api/v1"

PROWLARR_HOST = os.getenv("PROWLARR_HOST", "prowlarr")
PROWLARR_PORT = os.getenv("PROWLARR_PORT", "9696")
PROWLARR_API_KEY = os.getenv("PROWLARR_API_KEY")
PROWLARR_BASE = f"http://{PROWLARR_HOST}:{PROWLARR_PORT}/api/v1"

TMDB_API_KEY = os.getenv("TMDB_API_KEY")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", "/app/data/telegramarr.db")

LOOP_INTERVAL_HOURS = int(os.getenv("LOOP_INTERVAL_HOURS", "1"))
SEARCH_INTERVAL_HOURS_PER_MOVIE = int(os.getenv("SEARCH_INTERVAL_HOURS_PER_MOVIE", "6"))

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
    original_title TEXT,
    year INTEGER,
    overview TEXT,

    poster_url TEXT,
    backdrop_url TEXT,

    status TEXT,

    inserted_at TEXT,
    last_search TEXT,
    available_at TEXT,

    release_count INTEGER,
    releases TEXT
)
""")
c.execute("""
CREATE INDEX IF NOT EXISTS idx_status ON requests(status);""")
conn.commit()

# --- FONCTIONS UTILES ---
def wait_for_service(url, timeout=60):
    start = time.time()
    while True:
        try:
            r = requests.get(url, timeout=5)
            if r.ok:
                return
        except:
            pass
        if time.time() - start > timeout:
            raise RuntimeError(f"Service not ready: {url}")
        time.sleep(2)


def api_get_request(session: requests.Session, url: str, headers:dict = None, params: dict = None, max_retries: int = 3) -> requests.Response:
    time.sleep(0.5)
    for attempt in range(1, max_retries + 1):
        try:
            return session.get(url, headers=headers, params=params, timeout=(5 * attempt, 30 * attempt))
        except Exception as e:
            if attempt == max_retries:
                raise
            logging.warning(f"Connection error on attempt {attempt} for {url} : {e}")
            time.sleep(1)


def get_seerr_requests(session: requests.Session, filter : str = "all"):
    url = f"{SEERR_BASE}/request"
    resp = requests.get(url, )
    resp = api_get_request(session, url, 
        headers={"X-Api-Key": SEERR_API_KEY},
        params={"filter": filter}
    )
    resp.raise_for_status()
    return resp.json()["results"]


def get_tmdb_data(session: requests.Session, tmdbId):
    url = f"https://api.themoviedb.org/3/movie/{tmdbId}"
    resp = api_get_request(session, url, 
        params = {"api_key": TMDB_API_KEY, "language": "fr-FR", "append_to_response": "external_ids"}
    )
    resp.raise_for_status()
    return resp.json()

def search_prowlarr(session: requests.Session, imdbId):
    url = f"{PROWLARR_BASE}/search"
    resp = api_get_request(session, url, 
        headers={"X-Api-Key": PROWLARR_API_KEY},
        params={"query": imdbId}
    )
    resp.raise_for_status()
    return resp.json()

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

# --- LOGIQUE PRINCIPALE ---
def main():
    now = datetime.now()
    httpSession = requests.Session()

    seerr_requests = get_seerr_requests(httpSession) #"approved,pending,processing,unavailable,failed"
    
    for req in seerr_requests:
        seerr_id = req["id"]
        tmdbId = req["media"]["tmdbId"]
        imdbId = req["media"]["imdbId"]
        tvdbId = req["media"]["tvdbId"]
        title = None
        original_title = None
        year = None
        overview = None
        poster_url = None
        backdrop_url = None
        
        # vérifier si déjà en base
        c.execute("SELECT title, original_title, year, overview, poster_url, backdrop_url, last_search, available_at FROM requests WHERE seerr_id=?", (seerr_id,))
        row = c.fetchone()
        
        search_needed = True
        if row:
            title, original_title, year, overview, poster_url, backdrop_url, last_search, available_at = row
            if last_search:
                last_search_dt = datetime.fromisoformat(last_search)
                if now - last_search_dt < timedelta(hours=SEARCH_INTERVAL_HOURS_PER_MOVIE):
                    search_needed = False  # déjà recherché récemment
            if available_at:
                search_needed = False  # déjà disponible

        if search_needed:
            try:
                if (not imdbId and tmdbId) or not title or not original_title or not year or not overview or not poster_url or not backdrop_url:
                    data = get_tmdb_data(httpSession, tmdbId)
                    if not imdbId and tmdbId:
                        imdbId = data.get("external_ids", {}).get("imdb_id")
                    if not title:
                        title = data.get("title")
                    if not original_title:
                        original_title = data.get("original_title")
                    if not year:
                        year = data.get("release_date")[:4] if data.get("release_date") else None
                    if not overview:
                        overview = data.get("overview")
                    if not poster_url:
                        poster_url = f"https://image.tmdb.org/t/p/w500{data.get('poster_path')}" if data.get('poster_path') else None
                    if not backdrop_url:
                        backdrop_url = f"https://image.tmdb.org/t/p/w500{data.get('backdrop_path')}" if data.get('backdrop_path') else None

                releases = search_prowlarr(httpSession, imdbId)
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
                    INSERT OR REPLACE INTO requests (
                        seerr_id,
                        tmdbId,
                        imdbId,
                        tvdbId,

                        title,
                        original_title,
                        year,
                        overview,

                        poster_url,
                        backdrop_url,

                        status,

                        inserted_at,
                        last_search,
                        available_at,

                        release_count,
                        releases
                    )
                    VALUES (
                        ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?
                    );
                    """, (
                        seerr_id,
                        tmdbId,
                        imdbId,
                        tvdbId,

                        title,
                        original_title,
                        year,
                        overview,

                        poster_url,
                        backdrop_url,

                        "available",

                        now.isoformat(),
                        now.isoformat(),
                        now.isoformat(),

                        len(releases),
                        release_list
                    ))
            else:
                # update last_search                
                c.execute("""
                    INSERT OR REPLACE INTO requests (
                        seerr_id,
                        tmdbId,
                        imdbId,
                        tvdbId,

                        title,
                        original_title,
                        year,
                        overview,

                        poster_url,
                        backdrop_url,

                        status,

                        inserted_at,
                        last_search,

                        release_count
                    )
                    VALUES (
                        ?,?,?,?,?,?,?,?,?,?,?,?,?,?
                    )
                    """, (
                        seerr_id,
                        tmdbId,
                        imdbId,
                        tvdbId,

                        title,
                        original_title,
                        year,
                        overview,

                        poster_url,
                        backdrop_url,

                        "pending",

                        now.isoformat(),
                        now.isoformat(),

                        0
                    ))
            
            conn.commit()

    # --- suppression des films disponibles dans Plex ---
    # Ici tu peux vérifier via l'API Plex ou autre si le film est dispo, puis :
    # c.execute("DELETE FROM requests WHERE seerr_id=?", (seerr_id,))
    # conn.commit()

if __name__ == "__main__":
    wait_for_service(f"{SEERR_BASE}/request")
    wait_for_service(f"{PROWLARR_BASE}/indexer")

    logging.info(f"starting loop with interval {LOOP_INTERVAL_HOURS} hours")
    send_telegram_message("Telegramarr démarré !")
    while True:
        main()
        logging.info(f"loop finished, sleeping for {LOOP_INTERVAL_HOURS} hours...")
        time.sleep(LOOP_INTERVAL_HOURS * 3600)
