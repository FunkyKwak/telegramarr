import logging
import os
import time
import requests


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

SEERR_STATUS_MAP = {
    1: "pending",
    2: "approved",
    3: "declined",
    4: "processing",
    5: "available",
    6: "failed"
}


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



def wait_for_service(url, api_key, timeout_minutes=10):
    start = time.time()
    while True:
        try:
            r = requests.get(url, headers={"X-Api-Key": api_key}, timeout=5)
            if r.ok:
                logging.info(f"Service ready: {url}")
                return
        except:
            pass
        if time.time() - start > timeout_minutes * 60:
            raise RuntimeError(f"Service not ready: {url}")
        time.sleep(5)

        
def wait_for_services():
    wait_for_service(f"{SEERR_BASE}/request", api_key=SEERR_API_KEY)
    wait_for_service(f"{PROWLARR_BASE}/indexer", api_key=PROWLARR_API_KEY)

