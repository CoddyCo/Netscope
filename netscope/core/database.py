"""
SQLite Database for Historical Trace Storage

Persists trace results for:
- Trend analysis (how has routing to X changed over time?)
- Routing regression detection (did latency increase?)
- Recent search history
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from netscope.core.models import TraceSummary


class NetScopeDB:
    """SQLite database for storing trace history."""

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            # Default: ~/.netscope/history.db
            db_dir = Path.home() / ".netscope"
            db_dir.mkdir(parents=True, exist_ok=True)
            db_path = str(db_dir / "history.db")

        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        """Create tables if they don't exist."""
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS traces (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target TEXT NOT NULL,
                resolved_ip TEXT,
                total_hops INTEGER,
                avg_latency REAL,
                max_latency REAL,
                min_latency REAL,
                packet_loss REAL,
                health_score INTEGER,
                countries TEXT,
                cloud_providers TEXT,
                timestamp TEXT NOT NULL,
                full_data TEXT
            );

            CREATE TABLE IF NOT EXISTS recent_searches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target TEXT NOT NULL UNIQUE,
                resolved_ip TEXT,
                total_hops INTEGER,
                avg_latency REAL,
                last_searched TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_traces_target
                ON traces(target);

            CREATE INDEX IF NOT EXISTS idx_traces_timestamp
                ON traces(timestamp);
        """)
        self._conn.commit()

    def save_trace(self, summary: TraceSummary):
        """Save a completed trace to the database."""
        self._conn.execute(
            """INSERT INTO traces
               (target, resolved_ip, total_hops, avg_latency, max_latency,
                min_latency, packet_loss, health_score, countries,
                cloud_providers, timestamp, full_data)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                summary.target,
                summary.resolved_ip,
                summary.total_hops,
                summary.avg_latency,
                summary.max_latency,
                summary.min_latency,
                summary.packet_loss,
                summary.health.score if summary.health else 0,
                json.dumps(summary.countries),
                json.dumps(summary.cloud_providers),
                summary.timestamp or datetime.now().isoformat(),
                summary.to_json(),
            )
        )

        # Update recent searches
        self._conn.execute(
            """INSERT OR REPLACE INTO recent_searches
               (target, resolved_ip, total_hops, avg_latency, last_searched)
               VALUES (?, ?, ?, ?, ?)""",
            (
                summary.target,
                summary.resolved_ip,
                summary.total_hops,
                summary.avg_latency,
                datetime.now().isoformat(),
            )
        )

        self._conn.commit()

    def get_recent_searches(self, limit: int = 10) -> list[dict]:
        """Get the most recent unique searches."""
        cursor = self._conn.execute(
            """SELECT target, resolved_ip, total_hops, avg_latency, last_searched
               FROM recent_searches
               ORDER BY last_searched DESC
               LIMIT ?""",
            (limit,)
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_trace_history(self, target: str, limit: int = 30) -> list[dict]:
        """Get historical traces for a specific target (for trend analysis)."""
        cursor = self._conn.execute(
            """SELECT id, target, avg_latency, max_latency, packet_loss,
                      health_score, total_hops, timestamp
               FROM traces
               WHERE target = ?
               ORDER BY timestamp DESC
               LIMIT ?""",
            (target, limit)
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_full_trace(self, trace_id: int) -> Optional[TraceSummary]:
        """Load a full trace by ID."""
        cursor = self._conn.execute(
            "SELECT full_data FROM traces WHERE id = ?", (trace_id,)
        )
        row = cursor.fetchone()
        if row and row["full_data"]:
            return TraceSummary.from_json(row["full_data"])
        return None

    def detect_regression(self, target: str) -> Optional[dict]:
        """Check if routing has gotten worse recently compared to historical average."""
        history = self.get_trace_history(target, limit=14)
        if len(history) < 3:
            return None  # Not enough data

        # Compare last trace to average of previous traces
        latest = history[0]
        previous = history[1:]
        avg_historical = sum(h["avg_latency"] for h in previous) / len(previous)
        latest_latency = latest["avg_latency"]

        if latest_latency > avg_historical * 1.5:  # 50% increase
            return {
                "detected": True,
                "current_latency": latest_latency,
                "historical_avg": round(avg_historical, 1),
                "increase_pct": round(
                    (latest_latency - avg_historical) / avg_historical * 100, 1
                ),
                "message": (
                    f"Latency to {target} has increased by "
                    f"{(latest_latency - avg_historical):.0f}ms "
                    f"({((latest_latency - avg_historical) / avg_historical * 100):.0f}% above average)"
                ),
            }

        return {"detected": False}

    def close(self):
        """Close the database connection."""
        self._conn.close()
