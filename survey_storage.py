from __future__ import annotations

from datetime import datetime, timezone
import os
from pathlib import Path
import sqlite3
from uuid import uuid4


DEFAULT_DATABASE_PATH = Path(__file__).with_name("survey_responses.db")


def save_survey_response(
    role: str,
    usefulness: int,
    actionable: str,
    comments: str,
) -> str:
    database_path = Path(os.environ.get("SURVEY_DB_PATH", DEFAULT_DATABASE_PATH))
    database_path.parent.mkdir(parents=True, exist_ok=True)
    response_id = str(uuid4())

    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS survey_responses (
                response_id TEXT PRIMARY KEY,
                submitted_at TEXT NOT NULL,
                role TEXT NOT NULL,
                usefulness INTEGER NOT NULL CHECK (usefulness BETWEEN 1 AND 5),
                actionable TEXT NOT NULL,
                comments TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            INSERT INTO survey_responses (
                response_id, submitted_at, role, usefulness, actionable, comments
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                response_id,
                datetime.now(timezone.utc).isoformat(),
                role,
                usefulness,
                actionable,
                comments,
            ),
        )
    return response_id
