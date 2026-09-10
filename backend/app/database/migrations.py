"""
Additive schema changes for databases that already exist.

`Base.metadata.create_all()` creates missing *tables* but never adds columns to
tables that are already there — and the team's Supabase database already has
populated `patients` and `encounters` tables. These checks are idempotent and
only ever ADD nullable columns/indexes; nothing is dropped or rewritten.
"""
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

_COLUMNS = {
    "patients": {
        "aadhaar_hash": "VARCHAR",
        "aadhaar_last4": "VARCHAR(4)",
    },
    "encounters": {
        "queue_date": "VARCHAR(10)",
        "queue_token": "INTEGER",
    },
}

# (table, DDL). Existing rows have NULL tokens, which a unique index allows.
_INDEXES = (
    ("patients", "CREATE UNIQUE INDEX IF NOT EXISTS ix_patients_aadhaar_hash ON patients (aadhaar_hash)"),
    ("encounters", "CREATE INDEX IF NOT EXISTS ix_encounters_queue_date ON encounters (queue_date)"),
    ("encounters", "CREATE UNIQUE INDEX IF NOT EXISTS ix_encounters_queue_token "
                   "ON encounters (assigned_doctor_username, queue_date, queue_token)"),
)


def ensure_columns(engine: Engine) -> None:
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    with engine.begin() as conn:
        for table, columns in _COLUMNS.items():
            if table not in tables:
                continue
            existing = {column["name"] for column in inspector.get_columns(table)}
            for name, ddl in columns.items():
                if name not in existing:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))
        for table, ddl in _INDEXES:
            if table in tables:
                conn.execute(text(ddl))
