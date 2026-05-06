"""Persistent storage for recorded robot runs.

Supports two backends, selected automatically:
  - Supabase (PostgreSQL) — when DATABASE_URL is set in environment or
    Streamlit secrets. Used in production and on Streamlit Cloud.
  - SQLite — local fallback when DATABASE_URL is not set.

The public API (save_run, load_run, list_runs) is identical for both.
Calling code never needs to know which backend is active.
"""
from __future__ import annotations

import json
import logging
import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from data_acquisition.rtde_client import RobotSample

log = logging.getLogger(__name__)


@dataclass
class RunMetadata:
    run_id: str
    started_at_unix: float
    ended_at_unix: float
    pipeline: str
    host: str
    trajectory_name: str
    aas_params_used: dict | None


# ---------------------------------------------------------------------------
# Backend detection
# ---------------------------------------------------------------------------

def _get_database_url() -> str | None:
    """Return the PostgreSQL connection URL if configured, else None."""
    # 1. Plain environment variable (local dev with .env, CI, etc.)
    url = os.environ.get("DATABASE_URL")
    if url:
        return url
    # 2. Streamlit secrets (production on Streamlit Cloud)
    try:
        import streamlit as st
        return st.secrets.get("DATABASE_URL")
    except Exception:
        return None


def _use_supabase() -> bool:
    return bool(_get_database_url())


# ---------------------------------------------------------------------------
# PostgreSQL helpers (Supabase)
# ---------------------------------------------------------------------------

_PG_DDL = """
CREATE TABLE IF NOT EXISTS runs (
    run_id            TEXT PRIMARY KEY,
    started_at_unix   DOUBLE PRECISION NOT NULL,
    ended_at_unix     DOUBLE PRECISION NOT NULL,
    pipeline          TEXT NOT NULL,
    host              TEXT NOT NULL,
    trajectory_name   TEXT NOT NULL,
    aas_params_json   TEXT
);

CREATE TABLE IF NOT EXISTS samples (
    run_id                  TEXT    NOT NULL,
    sample_idx              INTEGER NOT NULL,
    wall_time               DOUBLE PRECISION NOT NULL,
    controller_timestamp    DOUBLE PRECISION NOT NULL,
    actual_q_json           TEXT NOT NULL,
    actual_qd_json          TEXT NOT NULL,
    actual_tcp_pose_json    TEXT NOT NULL,
    actual_tcp_speed_json   TEXT NOT NULL,
    actual_current_json     TEXT NOT NULL,
    target_q_json           TEXT NOT NULL,
    runtime_state           INTEGER NOT NULL,
    PRIMARY KEY (run_id, sample_idx),
    FOREIGN KEY (run_id) REFERENCES runs(run_id)
);

CREATE INDEX IF NOT EXISTS idx_samples_run_id ON samples(run_id);
"""


def _pg_conn():
    try:
        import psycopg2
    except ImportError as exc:
        raise ImportError(
            "psycopg2-binary is required for Supabase. Run: pip install psycopg2-binary"
        ) from exc
    return psycopg2.connect(_get_database_url())


def _pg_init() -> None:
    with _pg_conn() as conn:
        with conn.cursor() as cur:
            for stmt in _PG_DDL.strip().split(";"):
                stmt = stmt.strip()
                if stmt:
                    cur.execute(stmt)
        conn.commit()


def _pg_save_run(metadata: RunMetadata, samples: list[RobotSample]) -> None:
    _pg_init()
    with _pg_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO runs
                    (run_id, started_at_unix, ended_at_unix, pipeline,
                     host, trajectory_name, aas_params_json)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (run_id) DO NOTHING
                """,
                (
                    metadata.run_id,
                    metadata.started_at_unix,
                    metadata.ended_at_unix,
                    metadata.pipeline,
                    metadata.host,
                    metadata.trajectory_name,
                    json.dumps(metadata.aas_params_used) if metadata.aas_params_used is not None else None,
                ),
            )
            cur.executemany(
                """
                INSERT INTO samples
                    (run_id, sample_idx, wall_time, controller_timestamp,
                     actual_q_json, actual_qd_json, actual_tcp_pose_json,
                     actual_tcp_speed_json, actual_current_json, target_q_json,
                     runtime_state)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
                """,
                [
                    (
                        metadata.run_id, idx,
                        s.wall_time, s.controller_timestamp,
                        json.dumps(s.actual_q), json.dumps(s.actual_qd),
                        json.dumps(s.actual_tcp_pose), json.dumps(s.actual_tcp_speed),
                        json.dumps(s.actual_current), json.dumps(s.target_q),
                        s.runtime_state,
                    )
                    for idx, s in enumerate(samples)
                ],
            )
        conn.commit()


def _pg_load_run(run_id: str) -> tuple[RunMetadata, list[RobotSample]]:
    with _pg_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT run_id, started_at_unix, ended_at_unix, pipeline, host, "
                "trajectory_name, aas_params_json FROM runs WHERE run_id = %s",
                (run_id,),
            )
            row = cur.fetchone()
            if row is None:
                raise ValueError(f"Run not found: {run_id!r}")
            meta = RunMetadata(
                run_id=row[0], started_at_unix=row[1], ended_at_unix=row[2],
                pipeline=row[3], host=row[4], trajectory_name=row[5],
                aas_params_used=json.loads(row[6]) if row[6] else None,
            )
            cur.execute(
                "SELECT wall_time, controller_timestamp, actual_q_json, actual_qd_json, "
                "actual_tcp_pose_json, actual_tcp_speed_json, actual_current_json, "
                "target_q_json, runtime_state "
                "FROM samples WHERE run_id = %s ORDER BY sample_idx",
                (run_id,),
            )
            samples = [
                RobotSample(
                    wall_time=r[0], controller_timestamp=r[1],
                    actual_q=json.loads(r[2]), actual_qd=json.loads(r[3]),
                    actual_tcp_pose=json.loads(r[4]), actual_tcp_speed=json.loads(r[5]),
                    actual_current=json.loads(r[6]), target_q=json.loads(r[7]),
                    runtime_state=r[8],
                )
                for r in cur.fetchall()
            ]
    return meta, samples


def _pg_list_runs(pipeline: str | None) -> list[RunMetadata]:
    with _pg_conn() as conn:
        with conn.cursor() as cur:
            if pipeline:
                cur.execute(
                    "SELECT run_id, started_at_unix, ended_at_unix, pipeline, host, "
                    "trajectory_name, aas_params_json FROM runs WHERE pipeline = %s "
                    "ORDER BY started_at_unix DESC",
                    (pipeline,),
                )
            else:
                cur.execute(
                    "SELECT run_id, started_at_unix, ended_at_unix, pipeline, host, "
                    "trajectory_name, aas_params_json FROM runs ORDER BY started_at_unix DESC"
                )
            return [
                RunMetadata(
                    run_id=r[0], started_at_unix=r[1], ended_at_unix=r[2],
                    pipeline=r[3], host=r[4], trajectory_name=r[5],
                    aas_params_used=json.loads(r[6]) if r[6] else None,
                )
                for r in cur.fetchall()
            ]


# ---------------------------------------------------------------------------
# SQLite helpers (local fallback)
# ---------------------------------------------------------------------------

_SQLITE_DDL = """
CREATE TABLE IF NOT EXISTS runs (
    run_id            TEXT PRIMARY KEY,
    started_at_unix   REAL NOT NULL,
    ended_at_unix     REAL NOT NULL,
    pipeline          TEXT NOT NULL,
    host              TEXT NOT NULL,
    trajectory_name   TEXT NOT NULL,
    aas_params_json   TEXT
);
CREATE TABLE IF NOT EXISTS samples (
    run_id                  TEXT    NOT NULL,
    sample_idx              INTEGER NOT NULL,
    wall_time               REAL    NOT NULL,
    controller_timestamp    REAL    NOT NULL,
    actual_q_json           TEXT    NOT NULL,
    actual_qd_json          TEXT    NOT NULL,
    actual_tcp_pose_json    TEXT    NOT NULL,
    actual_tcp_speed_json   TEXT    NOT NULL,
    actual_current_json     TEXT    NOT NULL,
    target_q_json           TEXT    NOT NULL,
    runtime_state           INTEGER NOT NULL,
    PRIMARY KEY (run_id, sample_idx),
    FOREIGN KEY (run_id) REFERENCES runs(run_id)
);
CREATE INDEX IF NOT EXISTS idx_samples_run_id ON samples(run_id);
"""


def init_db(db_path: Path) -> None:
    """Create SQLite tables if missing. Idempotent."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.executescript(_SQLITE_DDL)


# ---------------------------------------------------------------------------
# Public API — auto-selects backend
# ---------------------------------------------------------------------------

def save_run(db_path: Path, metadata: RunMetadata, samples: list[RobotSample]) -> None:
    if _use_supabase():
        log.info("Saving run %s to Supabase", metadata.run_id)
        _pg_save_run(metadata, samples)
    else:
        init_db(db_path)
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                "INSERT INTO runs (run_id, started_at_unix, ended_at_unix, pipeline, "
                "host, trajectory_name, aas_params_json) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    metadata.run_id, metadata.started_at_unix, metadata.ended_at_unix,
                    metadata.pipeline, metadata.host, metadata.trajectory_name,
                    json.dumps(metadata.aas_params_used) if metadata.aas_params_used is not None else None,
                ),
            )
            conn.executemany(
                "INSERT INTO samples (run_id, sample_idx, wall_time, controller_timestamp, "
                "actual_q_json, actual_qd_json, actual_tcp_pose_json, actual_tcp_speed_json, "
                "actual_current_json, target_q_json, runtime_state) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        metadata.run_id, idx, s.wall_time, s.controller_timestamp,
                        json.dumps(s.actual_q), json.dumps(s.actual_qd),
                        json.dumps(s.actual_tcp_pose), json.dumps(s.actual_tcp_speed),
                        json.dumps(s.actual_current), json.dumps(s.target_q),
                        s.runtime_state,
                    )
                    for idx, s in enumerate(samples)
                ],
            )


def load_run(db_path: Path, run_id: str) -> tuple[RunMetadata, list[RobotSample]]:
    if _use_supabase():
        return _pg_load_run(run_id)
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT run_id, started_at_unix, ended_at_unix, pipeline, host, "
            "trajectory_name, aas_params_json FROM runs WHERE run_id = ?",
            (run_id,),
        ).fetchone()
        if row is None:
            raise ValueError(f"Run not found: {run_id!r}")
        meta = RunMetadata(
            run_id=row[0], started_at_unix=row[1], ended_at_unix=row[2],
            pipeline=row[3], host=row[4], trajectory_name=row[5],
            aas_params_used=json.loads(row[6]) if row[6] else None,
        )
        sample_rows = conn.execute(
            "SELECT wall_time, controller_timestamp, actual_q_json, actual_qd_json, "
            "actual_tcp_pose_json, actual_tcp_speed_json, actual_current_json, "
            "target_q_json, runtime_state "
            "FROM samples WHERE run_id = ? ORDER BY sample_idx",
            (run_id,),
        ).fetchall()
        return meta, [
            RobotSample(
                wall_time=r[0], controller_timestamp=r[1],
                actual_q=json.loads(r[2]), actual_qd=json.loads(r[3]),
                actual_tcp_pose=json.loads(r[4]), actual_tcp_speed=json.loads(r[5]),
                actual_current=json.loads(r[6]), target_q=json.loads(r[7]),
                runtime_state=r[8],
            )
            for r in sample_rows
        ]


def list_runs(db_path: Path, pipeline: str | None = None) -> list[RunMetadata]:
    if _use_supabase():
        return _pg_list_runs(pipeline)
    if not db_path.exists():
        return []
    with sqlite3.connect(db_path) as conn:
        if pipeline:
            rows = conn.execute(
                "SELECT run_id, started_at_unix, ended_at_unix, pipeline, host, "
                "trajectory_name, aas_params_json FROM runs WHERE pipeline = ? "
                "ORDER BY started_at_unix DESC",
                (pipeline,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT run_id, started_at_unix, ended_at_unix, pipeline, host, "
                "trajectory_name, aas_params_json FROM runs ORDER BY started_at_unix DESC",
            ).fetchall()
    return [
        RunMetadata(
            run_id=r[0], started_at_unix=r[1], ended_at_unix=r[2],
            pipeline=r[3], host=r[4], trajectory_name=r[5],
            aas_params_used=json.loads(r[6]) if r[6] else None,
        )
        for r in rows
    ]
