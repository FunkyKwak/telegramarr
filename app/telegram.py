


import logging
import os
import requests

# --- CONFIGURATION ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

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


def build_and_send_telegram_message(title: str, imdbId: str, tmdbId: str, new_seerr_request: bool, mediaType: str, releases: list, release_list: str = None):
    msg_html = f"<b>{title}</b>"
    msg_html += f" ("
    if imdbId:
        msg_html += f"<a href='https://www.imdb.com/title/{imdbId}'>imdb</a> - "
    msg_html += f"<a href='https://www.themoviedb.org/{mediaType}/{tmdbId}'>tmdb</a>)"
    
    if new_seerr_request:
        msg_html += "\nNouvelle demande !"
        
    if releases:
        msg_html += "\n\nDisponible au téléchargement !"
        for r in releases:
            release_title = r.get("title")
            msg_html += f"\n- <i>{release_title}</i>"
            if release_list is not None:
                release_list += f"- {release_title}\n"
    else:
        if mediaType == "movie":
            msg_html += "\n\n<i>Pas encore disponible en téléchargement</i>"
        else:
            msg_html += "\n\n<i>La recherche de release est désactivée pour les séries, impossible de vérifier la disponibilité dans Prowlarr</i>"

    send_telegram_message(msg_html)