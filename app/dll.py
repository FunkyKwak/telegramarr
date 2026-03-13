import datetime
from sqlite3 import Connection, Cursor


def init_db(conn: Connection, c: Cursor):
    c.execute("""
    CREATE TABLE IF NOT EXISTS requests (
        seerr_id INTEGER PRIMARY KEY,
        tmdbId INTEGER,
        imdbId TEXT,
        tvdbId INTEGER,
              
        mediaType TEXT,

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
    c.execute("""
    CREATE TABLE IF NOT EXISTS seer_status (
        seerr_status_id INTEGER PRIMARY KEY,
        value TEXT,
        value_fr TEXT
    );
    """)
    c.execute("""INSERT OR REPLACE INTO seer_status (seerr_status_id, value, value_fr) VALUES (1, "pending", "En attente");""")
    c.execute("""INSERT OR REPLACE INTO seer_status (seerr_status_id, value, value_fr) VALUES (2, "approved", "Approuvé");""")
    c.execute("""INSERT OR REPLACE INTO seer_status (seerr_status_id, value, value_fr) VALUES (3, "declined", "Refusé");""")
    c.execute("""INSERT OR REPLACE INTO seer_status (seerr_status_id, value, value_fr) VALUES (4, "processing", "En cours de traitement");""")
    c.execute("""INSERT OR REPLACE INTO seer_status (seerr_status_id, value, value_fr) VALUES (5, "available", "Disponible");""")
    c.execute("""INSERT OR REPLACE INTO seer_status (seerr_status_id, value, value_fr) VALUES (6, "failed", "Échec");""")
    conn.commit()



def load_seerr_status_maps(c: Cursor):
    c.execute("SELECT seerr_status_id, value FROM seer_status")
    rows = c.fetchall()
    id_to_name = {row[0]: row[1] for row in rows}
    name_to_id = {row[1]: row[0] for row in rows}
    return id_to_name, name_to_id



def get_request(c: Cursor, seerr_id):
    c.execute("SELECT mediaType, title, original_title, year, overview, poster_url, backdrop_url, last_search, available_at FROM requests WHERE seerr_id=?", (seerr_id,))
    return c.fetchone()

def update_last_search(conn: Connection, c: Cursor,
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
    
    date: datetime):
    c.execute("""
        INSERT OR REPLACE INTO requests (
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

            status,

            inserted_at,
            last_search,

            release_count
        )
        VALUES (
            ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?
        )
        """, (
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

            "pending",

            date.isoformat(),
            date.isoformat(),

            0
        )
    )
    conn.commit()
    
def update_request_found(conn: Connection, c: Cursor,
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
    
    date: datetime,
    
    release_count,
    releases_list):
    c.execute("""
        INSERT OR REPLACE INTO requests (
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

            status,

            inserted_at,
            last_search,
            available_at,

            release_count,
            releases
        )
        VALUES (
            ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?
        );
        """, (
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

            "available",

            date.isoformat(),
            date.isoformat(),
            date.isoformat(),

            release_count,
            releases_list
        )
    )
    conn.commit()


def delete_request(conn: Connection, c: Cursor, seerr_id):
    c.execute("DELETE FROM requests WHERE seerr_id=?", (seerr_id,))
    conn.commit()

def delete_removed_requests(conn: Connection, c: Cursor, seerr_requests):
    seerr_ids = [req["id"] for req in seerr_requests]

    if seerr_ids:
        placeholders = ",".join("?" * len(seerr_ids))
        c.execute(f"""
            DELETE FROM requests
            WHERE seerr_id NOT IN ({placeholders})
        """, seerr_ids)
    conn.commit()