"""Explicit, transactional setup of the local SQLite foundation.

HTTP upload/query operations are intentionally not implemented by this module.
"""
import sqlite3
from contextlib import contextmanager
from importlib.resources import files
from pathlib import Path
from typing import Iterator

SCHEMA_VERSION = 1


class SchemaError(RuntimeError):
    pass


@contextmanager
def connect_database(path: Path) -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(path, timeout=5, isolation_level=None)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
    finally:
        connection.close()


def _statements(script: str) -> Iterator[str]:
    statement = ""
    for line in script.splitlines(keepends=True):
        statement += line
        if sqlite3.complete_statement(statement):
            yield statement
            statement = ""
    if statement.strip():
        raise SchemaError("Incomplete SQL migration")


def initialize_database(path: Path) -> int:
    """Create v1 atomically, or keep an already initialized v1 unchanged.

    Refuse unknown/unversioned existing databases instead of adopting or wiping
    them. BEGIN IMMEDIATE serializes simultaneous initialization attempts.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with connect_database(path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        try:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            tables = {
                row[0] for row in connection.execute(
                    "SELECT name FROM sqlite_master "
                    "WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                )
            }
            if version == SCHEMA_VERSION:
                if not {"inspections", "analyses"}.issubset(tables):
                    raise SchemaError("Versioned database is missing required tables")
            elif version != 0:
                raise SchemaError(f"Unsupported database schema version: {version}")
            elif tables:
                raise SchemaError("Existing unversioned database requires explicit migration")
            else:
                script = files("vm_server.migrations").joinpath("001_initial.sql").read_text(encoding="utf-8")
                for statement in _statements(script):
                    connection.execute(statement)
                connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
    return SCHEMA_VERSION
