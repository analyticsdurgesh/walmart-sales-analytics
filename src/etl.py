# Keep type hints as plain text, so newer hint syntax also works on older Python.
from __future__ import annotations

# argparse reads the options typed after the command, such as --csv and --db.
import argparse

# pandas reads the CSV and writes the rows to the database.
import pandas as pd
# create_engine sets up the database connection from a URL.
from sqlalchemy import create_engine

# The cleaning step, the T in ETL. Extract is read_csv and Load is to_sql.
from src.transform import normalize_pos_columns, normalize_weekly_columns


# Weekly CSV into the weekly_store_sales table.
def load_weekly(csv_path: str, db_url: str) -> None:
    # Extract and transform: read the file, then clean it.
    df = normalize_weekly_columns(pd.read_csv(csv_path))
    # Works for PostgreSQL and MySQL alike. The start of the URL decides which one.
    engine = create_engine(db_url)
    # Load. "append" adds rows to the table that 01_schema.sql created.
    # index=False leaves out the pandas row numbers.
    # The table allows one row per store and date, so loading the same file twice fails
    # with a duplicate key error. Run 01_schema.sql again first to start from empty tables.
    df.to_sql("weekly_store_sales", engine, if_exists="append", index=False)


# POS CSV into two tables: branches and pos_sales_staging.
def load_pos(csv_path: str, db_url: str) -> None:
    # Read the file, then clean it with the POS rules.
    df = normalize_pos_columns(pd.read_csv(csv_path))
    # Set up the connection.
    engine = create_engine(db_url)
    # Keep the branch and city columns, drop repeated pairs, and rename branch to branch_code.
    # The 10-row sample gives 3 rows: A Yangon, B Mandalay, C Naypyitaw.
    branches = df[["branch", "city"]].drop_duplicates().rename(columns={"branch": "branch_code"})
    # Add them to a table called branches. pandas creates the table if it is not there.
    branches.to_sql("branches", engine, if_exists="append", index=False)
    # Put every cleaned row into pos_sales_staging. "replace" deletes the old table first,
    # so this step can be repeated safely. A staging table is a holding area:
    # the rows wait here until SQL moves them into the final tables.
    df.to_sql("pos_sales_staging", engine, if_exists="replace", index=False)


# Defines the three options the script accepts.
def parse_args() -> argparse.Namespace:
    # The description is printed when someone runs the script with --help.
    parser = argparse.ArgumentParser(description="Load Walmart CSV data into PostgreSQL or MySQL.")
    # --dataset-type must be the word weekly or the word pos. Anything else is rejected.
    parser.add_argument("--dataset-type", choices=["weekly", "pos"], required=True)
    # --csv is the path to the file to load.
    parser.add_argument("--csv", required=True)
    # --db is the database URL, e.g. postgresql+psycopg2://user:password@localhost:5432/walmart_sales
    parser.add_argument("--db", required=True)
    # Read what was typed. The values come back as args.dataset_type, args.csv and args.db.
    return parser.parse_args()


# Picks the right loader.
def main() -> None:
    # Get the three options.
    args = parse_args()
    # argparse turns the dash in --dataset-type into an underscore.
    if args.dataset_type == "weekly":
        # Load into weekly_store_sales.
        load_weekly(args.csv, args.db)
    # The only other allowed value is pos.
    else:
        # Load into branches and pos_sales_staging.
        load_pos(args.csv, args.db)
    # Reaching this line means no error was raised.
    print("ETL load complete.")


# True when started with: python -m src.etl ...
if __name__ == "__main__":
    # Run the load.
    main()
