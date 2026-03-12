import datetime
from sqlite3 import Connection, Cursor


def init_db(conn: Connection, c: Cursor):
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


def get_request(c: Cursor, seerr_id):
    c.execute("SELECT title, original_title, year, overview, poster_url, backdrop_url, last_search, available_at FROM requests WHERE seerr_id=?", (seerr_id,))
    return c.fetchone()

def update_last_search(conn: Connection, c: Cursor,
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
    
    date: datetime):
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

