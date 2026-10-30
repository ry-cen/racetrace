import re
from importlib.resources import files

import psycopg
from psycopg import sql


def connect(database_url, schema=None):
    schema = schema if schema is not None else "public"
    if not re.fullmatch(r"[a-z_][a-z0-9_]{0,62}", schema):
        raise ValueError("invalid database schema")
    conn = psycopg.connect(
        database_url,
        autocommit=True,
        connect_timeout=5,
        options="-cstatement_timeout=5000",
    )
    conn.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
    return conn


def migrate(database_url, variant, schema=None):
    with connect(database_url, schema) as conn:
        for name in (
            ["001_init.sql", "002_idempotency.sql"]
            if variant == "safe"
            else ["001_init.sql"]
        ):
            conn.execute(files("refworker").joinpath("schema", name).read_text())
