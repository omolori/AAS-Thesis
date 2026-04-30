"""Persistent storage for recorded robot runs.

Saves RunMetadata and RobotSample lists to a SQLite database at
data/runs.db. SQLite ships with Python; no extra dependency needed.

Maps to thesis §3.x (data pipeline): raw RTDE samples are stored here
and later loaded by comparator.py to compute the comparison metrics.
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from data_acquisition.rtde_client import RobotSample


@dataclass
class RunMetadata:
    run_id: str
    started_at_unix: float
    ended_at_unix: float
    pipeline: str           # 'real', 'sim_no_aas', 'sim_aas'
    host: str
    trajectory_name: str
    aas_params_used: dict | None  # None for non-AAS runs


_DDL = """
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
    """Create tables if missing. Idempotent."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.executescript(_DDL)


def save_run(
    db_path: Path,
    metadata: RunMetadata,
    samples: list[RobotSample],
) -> None:
    """Insert a run and all its samples. Raises if run_id already exists."""
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO runs
                (run_id, started_at_unix, ended_at_unix, pipeline,
                 host, trajectory_name, aas_params_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
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
        conn.executemany(
            """
            INSERT INTO samples
                (run_id, sample_idx, wall_time, controller_timestamp,
                 actual_q_json, actual_qd_json, actual_tcp_pose_json,
                 actual_tcp_speed_json, actual_current_json, target_q_json,
                 runtime_state)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    metadata.run_id,
                    idx,
                    s.wall_time,
                    s.controller_timestamp,
                    json.dumps(s.actual_q),
                    json.dumps(s.actual_qd),
                    json.dumps(s.actual_tcp_pose),
                    json.dumps(s.actual_tcp_speed),
                    json.dumps(s.actual_current),
                    json.dumps(s.target_q),
                    s.runtime_state,
                )
                for idx, s in enumerate(samples)
            ],
        )


def load_run(db_path: Path, run_id: str) -> tuple[RunMetadata, list[RobotSample]]:
    """Load a run and all its samples by run_id. Raises if not found."""
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT run_id, started_at_unix, ended_at_unix, pipeline, host, "
            "trajectory_name, aas_params_json FROM runs WHERE run_id = ?",
            (run_id,),
        ).fetchone()
        if row is None:
            raise ValueError(f"Run not found: {run_id!r}")
        meta = RunMetadata(
            run_id=row[0],
            started_at_unix=row[1],
            ended_at_unix=row[2],
            pipeline=row[3],
            host=row[4],
            trajectory_name=row[5],
            aas_params_used=json.loads(row[6]) if row[6] is not None else None,
        )
        sample_rows = conn.execute(
            "SELECT wall_time, controller_timestamp, actual_q_json, actual_qd_json, "
            "actual_tcp_pose_json, actual_tcp_speed_json, actual_current_json, "
            "target_q_json, runtime_state "
            "FROM samples WHERE run_id = ? ORDER BY sample_idx",
            (run_id,),
        ).fetchall()
        samples = [
            RobotSample(
                wall_time=r[0],
                controller_timestamp=r[1],
                actual_q=json.loads(r[2]),
                actual_qd=json.loads(r[3]),
                actual_tcp_pose=json.loads(r[4]),
                actual_tcp_speed=json.loads(r[5]),
                actual_current=json.loads(r[6]),
                target_q=json.loads(r[7]),
                runtime_state=r[8],
            )
            for r in sample_rows
        ]
    return meta, samples


def list_runs(db_path: Path, pipeline: str | None = None) -> list[RunMetadata]:
    """Return all run metadata, optionally filtered by pipeline name."""
    if not db_path.exists():
        return []
    with sqlite3.connect(db_path) as conn:
        if pipeline is not None:
            rows = conn.execute(
                "SELECT run_id, started_at_unix, ended_at_unix, pipeline, host, "
                "trajectory_name, aas_params_json FROM runs WHERE pipeline = ? "
                "ORDER BY started_at_unix",
                (pipeline,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT run_id, started_at_unix, ended_at_unix, pipeline, host, "
                "trajectory_name, aas_params_json FROM runs ORDER BY started_at_unix",
            ).fetchall()
    return [
        RunMetadata(
            run_id=r[0],
            started_at_unix=r[1],
            ended_at_unix=r[2],
            pipeline=r[3],
            host=r[4],
            trajectory_name=r[5],
            aas_params_used=json.loads(r[6]) if r[6] is not None else None,
        )
        for r in rows
    ]
