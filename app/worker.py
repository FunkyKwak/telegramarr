import logging
import os
import sqlite3
import time
import requests
from datetime import datetime, timedelta
import telegram
import ext_api
import dll

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


# --- CONFIGURATION ---
SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", "/app/data/telegramarr.db")

LOOP_INTERVAL_HOURS = int(os.getenv("LOOP_INTERVAL_HOURS", "1"))
SEARCH_INTERVAL_HOURS_PER_MOVIE = int(os.getenv("SEARCH_INTERVAL_HOURS_PER_MOVIE", "6"))

# --- BASE DE DONNEES ---
conn = sqlite3.connect(SQLITE_DB_PATH)
c = conn.cursor()

dll.init_db(conn, c)

SEERR_STATUS_ID_TO_NAME, SEERR_STATUS_NAME_TO_ID = dll.load_seerr_status_maps(c)


# --- LOGIQUE PRINCIPALE ---
def do_work():
    now = datetime.now()
    httpSession = requests.Session()

    seerr_requests = ext_api.get_seerr_requests(httpSession)
    
    for req in seerr_requests:
        seerr_id = req["id"]
        tmdbId = req["media"]["tmdbId"]
        imdbId = req["media"]["imdbId"]
        tvdbId = req["media"]["tvdbId"]
        mediaType = req["media"]["mediaType"]  # movie ou tv
        title = None
        original_title = None
        year = None
        overview = None
        poster_url = None
        backdrop_url = None

        releases = None
        
        # vérifier si déjà en base
        row = dll.get_request(c, seerr_id)
        
        search_needed = True
        new_seerr_request = True
        if row:
            new_seerr_request = False
            mediaType, title, original_title, year, overview, poster_url, backdrop_url, last_search, available_at = row
            if last_search:
                last_search_dt = datetime.fromisoformat(last_search)
                if now - last_search_dt < timedelta(hours=SEARCH_INTERVAL_HOURS_PER_MOVIE):
                    search_needed = False  # déjà recherché récemment
            if available_at:
                search_needed = False  # déjà disponible
            if SEERR_STATUS_ID_TO_NAME[req["status"]] == "available":
                search_needed = False  # Requête déjà traitée, on peut la sortir de la base
                dll.delete_request(conn, c, seerr_id)  # supprimer de la DB pour ne pas garder les films refusés

        if search_needed:
            try:
                if (not imdbId and tmdbId) or not title or not original_title or not year or not overview or not poster_url or not backdrop_url:
                    data = ext_api.get_tmdb_data(httpSession, tmdbId, mediaType)
                    if not imdbId and tmdbId:
                        imdbId = data.get("external_ids", {}).get("imdb_id")
                    if not title:
                        if mediaType == "movie":
                            title = data.get("title")
                        else:
                            title = data.get("name")
                    if not original_title:
                        if mediaType == "movie":
                            original_title = data.get("original_title")
                        else:
                            original_title = data.get("original_name")
                    if not year:
                        if mediaType == "movie":
                            year = data.get("release_date")[:4] if data.get("release_date") else None
                        else:
                            year = data.get("first_air_date")[:4] if data.get("first_air_date") else None
                    if not overview:
                        overview = data.get("overview")
                    if not poster_url:
                        poster_url = f"https://image.tmdb.org/t/p/w500{data.get('poster_path')}" if data.get('poster_path') else None
                    if not backdrop_url:
                        backdrop_url = f"https://image.tmdb.org/t/p/w500{data.get('backdrop_path')}" if data.get('backdrop_path') else None

                if mediaType == "movie":
                    if not imdbId:
                        logging.warning(f"Le film {title} ({tmdbId}) n'a pas d'imdbId, impossible de le rechercher dans Prowlarr")
                    else:
                        releases = ext_api.search_prowlarr(httpSession, imdbId)
            except Exception as e:
                logging.error(f"Erreur Prowlarr pour seerr_id {seerr_id} (imdbId {imdbId}, tmdbId {tmdbId}, tvdbId {tvdbId}): {e}")
                continue

            if releases:               
                # message Telegram
                logging.info(f"Film disponible ! \"{title}\" a {len(releases)} nouvelles releases")

                release_list = [""]  # Utiliser une liste pour stocker la liste des releases trouvées, afin de pouvoir la passer par référence à la fonction de message Telegram
                telegram.build_and_send_telegram_message(title, imdbId, tmdbId, new_seerr_request, mediaType, releases, release_list)
                
                # update DB
                dll.update_request_found(conn, c,
                    seerr_id,
                    tmdbId,
                    imdbId,
                    tvdbId,

                    mediaType,
                    title,
                    original_title,
                    year,
                    overview,

                    poster_url,
                    backdrop_url,
                    
                    now,

                    len(releases),
                    release_list[0]
                )
            else:
                dll.update_last_search(conn, c,
                    seerr_id,
                    tmdbId,
                    imdbId,
                    tvdbId,

                    mediaType,
                    title,
                    original_title,
                    year,
                    overview,

                    poster_url,
                    backdrop_url,
                    now)
                if new_seerr_request:
                    telegram.build_and_send_telegram_message(title, imdbId, tmdbId, new_seerr_request, mediaType, releases)

            
    dll.delete_removed_requests(conn, c, seerr_requests)

if __name__ == "__main__":
    ext_api.wait_for_services()

    logging.info(f"starting loop with interval {LOOP_INTERVAL_HOURS} hours")
    while True:
        do_work()
        logging.info(f"loop finished, sleeping for {LOOP_INTERVAL_HOURS} hours...")
        time.sleep(LOOP_INTERVAL_HOURS * 3600)
