"""Tiny SQLite layer for user-reported incidents."""
import sqlite3

from ml.common import ROOT

DB_PATH = ROOT / "data" / "saferoute.db"
INCIDENT_TYPES = ["Theft", "Harassment", "Assault", "Snatching", "Stalking",
                  "Poor lighting", "Other"]


def _connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS incidents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lat REAL NOT NULL,
                lon REAL NOT NULL,
                incident_type TEXT NOT NULL,
                description TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )""")


def add_incident(lat, lon, incident_type, description=""):
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO incidents (lat, lon, incident_type, description) VALUES (?, ?, ?, ?)",
            (lat, lon, incident_type, description[:300]))
        return cur.lastrowid


def list_incidents(limit=200):
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, lat, lon, incident_type, description, created_at "
            "FROM incidents ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]
