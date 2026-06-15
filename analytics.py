"""Lightweight analytics — SQLite-backed, zero dependencies."""
from __future__ import annotations

import json
import sqlite3
import os
from datetime import date
from typing import Any

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "analytics.db")


def _get_db() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    _migrate(conn)
    return conn


def _migrate(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            data TEXT DEFAULT '{}',
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS daily_stats (
            date TEXT PRIMARY KEY,
            page_views INTEGER DEFAULT 0,
            calculations INTEGER DEFAULT 0,
            checkouts INTEGER DEFAULT 0,
            purchases INTEGER DEFAULT 0,
            revenue_cents INTEGER DEFAULT 0,
            referral_leads INTEGER DEFAULT 0
        );
    """)
    conn.commit()


def log_event(event_type: str, data: dict[str, Any] | None = None) -> None:
    """Record an analytics event."""
    conn = _get_db()
    today = date.today().isoformat()
    try:
        conn.execute(
            "INSERT INTO events (event_type, data) VALUES (?, ?)",
            (event_type, json.dumps(data or {})),
        )
        col_map = {
            "page_view": "page_views",
            "calculation": "calculations",
            "checkout": "checkouts",
            "purchase": "purchases",
            "referral_lead": "referral_leads",
        }
        col = col_map.get(event_type)
        if col:
            revenue = data.get("revenue_cents", 0) if event_type == "purchase" else 0
            conn.execute(
                f"INSERT INTO daily_stats (date, {col}, revenue_cents) VALUES (?, 1, ?) "
                f"ON CONFLICT(date) DO UPDATE SET {col} = {col} + 1, "
                f"revenue_cents = revenue_cents + ?",
                (today, revenue, revenue),
            )
        conn.commit()
    finally:
        conn.close()


def get_stats(days: int = 30) -> dict[str, Any]:
    """Return aggregate stats for the last N days."""
    conn = _get_db()
    try:
        # Daily stats
        rows = conn.execute(
            """SELECT * FROM daily_stats WHERE date >= date('now', ?)
               ORDER BY date DESC""",
            (f"-{days} days",),
        ).fetchall()

        totals = {
            "page_views": 0,
            "calculations": 0,
            "checkouts": 0,
            "purchases": 0,
            "revenue_cents": 0,
            "referral_leads": 0,
        }
        daily = []
        for r in rows:
            d = dict(r)
            daily.append(d)
            for k in totals:
                totals[k] += d.get(k, 0)

        # Conversion rates
        calc_to_purchase = 0
        if totals["calculations"] > 0:
            calc_to_purchase = round(totals["purchases"] / totals["calculations"] * 100, 1)

        # Top industries
        top_industries = conn.execute(
            """SELECT json_extract(data, '$.business_type') AS industry, COUNT(*) AS cnt
               FROM events
               WHERE event_type = 'calculation' AND created_at >= date('now', ?)
                 AND json_extract(data, '$.business_type') IS NOT NULL
               GROUP BY industry ORDER BY cnt DESC LIMIT 5""",
            (f"-{days} days",),
        ).fetchall()

        # Avg refund calculated
        avg_refund = conn.execute(
            """SELECT AVG(CAST(json_extract(data, '$.refund_amount') AS REAL)) AS avg_ref
               FROM events
               WHERE event_type = 'calculation' AND created_at >= date('now', ?)
                 AND json_extract(data, '$.refund_amount') IS NOT NULL""",
            (f"-{days} days",),
        ).fetchone()

        return {
            "period_days": days,
            "totals": totals,
            "daily": daily,
            "conversion_rate": calc_to_purchase,
            "top_industries": [dict(r) for r in top_industries],
            "avg_refund": round(avg_refund["avg_ref"] or 0, 2),
        }
    finally:
        conn.close()
