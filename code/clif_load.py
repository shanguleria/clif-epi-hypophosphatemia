"""DuckDB views over CLIF tables, named and shaped by definitions.yaml.

Each view exposes only the declared columns under their logical names. Naive timestamps are read
as site-local time (config `timezone`); the session runs in UTC so interval math is unambiguous.
"""
from pathlib import Path

import duckdb

READERS = {"parquet": "read_parquet", "csv": "read_csv_auto"}
NAIVE_TS = {"TIMESTAMP", "TIMESTAMP_NS", "TIMESTAMP_MS", "TIMESTAMP_S"}


def _quote(s):
    return "'" + str(s).replace("'", "''") + "'"


def connect(cfg, defs, tables):
    reader = READERS.get(cfg["filetype"])
    if reader is None:
        raise ValueError(f"filetype must be one of {sorted(READERS)}, got {cfg['filetype']!r}")
    con = duckdb.connect()
    con.execute("SET TimeZone = 'UTC'")
    for table in tables:
        spec = defs(f"tables.{table}")
        path = Path(cfg["data_directory"]) / f"clif_{spec['file']}.{cfg['filetype']}"
        if not path.is_file():
            raise FileNotFoundError(f"{table}: expected {path}")
        src = f"{reader}({_quote(path)})"
        types = dict(con.execute(f"SELECT column_name, column_type FROM (DESCRIBE SELECT * FROM {src})").fetchall())
        rename = spec.get("rename") or {}
        physical = {col: rename.get(col, col) for col in spec["columns"]}
        missing = [p for p in physical.values() if p not in types]
        if missing:
            raise KeyError(f"{path.name} lacks columns {missing} (has {sorted(types)})")
        select = []
        for col, phys in physical.items():
            expr = f'"{phys}"'
            if types[phys] in NAIVE_TS:
                expr = f"timezone({_quote(cfg['timezone'])}, CAST({expr} AS TIMESTAMP))"
            select.append(f"{expr} AS {col}")
        con.execute(f"CREATE VIEW {table} AS SELECT {', '.join(select)} FROM {src}")
    return con
