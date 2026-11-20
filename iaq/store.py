"""Load readings into SQLite and run the analysis queries in sql/analysis.sql."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Dict

import pandas as pd

SQL_FILE = Path(__file__).resolve().parent.parent / "sql" / "analysis.sql"


def to_sqlite(df: pd.DataFrame, path: str | Path = ":memory:") -> sqlite3.Connection:
    con = sqlite3.connect(str(path))
    out = df.reset_index()
    out["timestamp"] = out["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
    out.to_sql("readings", con, if_exists="replace", index=False)
    con.execute("CREATE INDEX IF NOT EXISTS idx_ts ON readings(timestamp)")
    return con


def load_queries(sql_path: str | Path = SQL_FILE) -> Dict[str, str]:
    """Split a .sql file into named queries using '-- name: <query_name>' markers."""
    queries, name, buf = {}, None, []
    for line in Path(sql_path).read_text().splitlines():
        if line.strip().lower().startswith("-- name:"):
            if name:
                queries[name] = "\n".join(buf).strip()
            name, buf = line.split(":", 1)[1].strip(), []
        elif name:
            buf.append(line)
    if name:
        queries[name] = "\n".join(buf).strip()
    return queries


def run_all(con: sqlite3.Connection) -> Dict[str, pd.DataFrame]:
    return {name: pd.read_sql_query(q, con) for name, q in load_queries().items()}
