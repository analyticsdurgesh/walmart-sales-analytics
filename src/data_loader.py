# Keep type hints as plain text, so newer hint syntax also works on older Python.
from __future__ import annotations

# pandas reads CSV files and SQL results into tables.
import pandas as pd
# create_engine opens the door to a database. text() wraps a SQL string so SQLAlchemy accepts it.
from sqlalchemy import create_engine, text

# The two cleaning functions. Every loader below hands its raw table to one of them.
from src.transform import normalize_pos_columns, normalize_weekly_columns


# Weekly CSV in, cleaned table out.
def load_weekly_csv(path: str) -> pd.DataFrame:
    # pd.read_csv reads the file. normalize_weekly_columns renames columns and fixes dates and numbers.
    return normalize_weekly_columns(pd.read_csv(path))


# POS CSV in, cleaned table out.
def load_pos_csv(path: str) -> pd.DataFrame:
    # Same two steps, with the POS cleaning rules.
    return normalize_pos_columns(pd.read_csv(path))


# Runs a SQL query and returns the rows as a table. The caller cleans them afterwards.
def load_from_database(db_url: str, query: str) -> pd.DataFrame:
    # The URL says which database, which user, which host. The engine keeps those details.
    engine = create_engine(db_url)
    # Open a connection. "with" closes it again, even if the query fails.
    with engine.connect() as conn:
        # Send the query and turn the result into a DataFrame.
        return pd.read_sql_query(text(query), conn)
