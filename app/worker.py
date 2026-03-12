import logging
import os
import sqlite3
import time
import requests
from datetime import datetime, timedelta
import ext_api
import dll

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


# --- CONFIGURATION ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", "/app/data/telegramarr.db")

LOOP_INTERVAL_HOURS = int(os.getenv("LOOP_INTERVAL_HOURS", "1"))
SEARCH_INTERVAL_HOURS_PER_MOVIE = int(os.getenv("SEARCH_INTERVAL_HOURS_PER_MOVIE", "6"))

# --- BASE DE DONNEES ---
conn = sqlite3.connect(SQLITE_DB_PATH)
c = conn.cursor()

dll.init_db(conn, c)

# --- FONCTIONS UTILES ---

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

    seerr_requests = ext_api.get_seerr_requests(httpSession) #"approved,pending,processing,unavailable,failed"
    
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
        row = dll.get_request(c, seerr_id)
        
        search_needed = True
        if row:
            title, original_title, year, overview, poster_url, backdrop_url, last_search, available_at = row
            if last_search:
                last_search_dt = datetime.fromisoformat(last_search)
                if now - last_search_dt < timedelta(hours=SEARCH_INTERVAL_HOURS_PER_MOVIE):
                    search_needed = False  # déjà recherché récemment
            if available_at:
                search_needed = False  # déjà disponible
            if req.status != "approved":
                search_needed = False  # pas encore approuvé sur Seerr
                dll.delete_request(conn, c, seerr_id)  # supprimer de la DB pour ne pas garder les films refusés

        if search_needed:
            try:
                if (not imdbId and tmdbId) or not title or not original_title or not year or not overview or not poster_url or not backdrop_url:
                    data = ext_api.get_tmdb_data(httpSession, tmdbId)
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

                releases = ext_api.search_prowlarr(httpSession, imdbId)
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
                dll.update_request_found(conn, c,
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
                    
                    now,

                    len(releases),
                    release_list)
            else:
                dll.update_last_search(conn, c,
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
                    now)
            
            

if __name__ == "__main__":
    ext_api.wait_for_services()

    logging.info(f"starting loop with interval {LOOP_INTERVAL_HOURS} hours")
    send_telegram_message("Telegramarr démarré !")
    while True:
        main()
        logging.info(f"loop finished, sleeping for {LOOP_INTERVAL_HOURS} hours...")
        time.sleep(LOOP_INTERVAL_HOURS * 3600)
