# Walmart sales analytics

A pandas and Streamlit dashboard on three years of weekly sales from 45 Walmart stores, with an ETL script and SQL files for PostgreSQL and MySQL.

The full walkthrough is in [PROJECT_EXPLANATION.md](PROJECT_EXPLANATION.md): how the data moves, what each file does, how the forecast works, the database setup, the results, and what is still unfinished.

## Run it

```bash
git clone https://github.com/analyticsdurgesh/walmart-sales-analytics.git
cd walmart-sales-analytics
python run.py
```

If the shell answers `command not found: python` (a Mac or Linux without conda or an active virtual environment), type `python3 run.py`. The project needs Python 3.10 or newer.

Or press the Run button on [run.py](run.py) in VS Code. The runner checks the packages and the data file, starts the dashboard on the first free port from 8501 and opens the browser. If a package is missing or too old it shows the exact `pip install` command and asks before it installs anything. Ctrl+C stops the dashboard.

`python run.py test` runs the tests. `python run.py database` builds and loads PostgreSQL or MySQL and compares the result with the CSV. `python run.py all` runs the tests, then the database step, then the dashboard. `python run.py --help` lists the actions and options.

To set things up by hand in a fresh environment:

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Started this way, the dashboard opens at http://localhost:8501. It reads `data/raw/walmart_real_sales.csv`, and a database is optional.

Run the tests by hand with:

```bash
python -m pytest
```

## What is in the folder

| Path | Contents |
| --- | --- |
| `run.py` | One command that runs the project: dashboard, tests, database |
| `app.py` | The Streamlit dashboard |
| `src/` | Cleaning and summaries (`transform.py`), loaders, the forecast, the ETL script, two optional helper scripts |
| `sql/postgres/`, `sql/mysql/` | Schema, indexes, views and analysis queries for each database |
| `data/raw/` | The weekly dataset: 6,435 rows, February 2010 to October 2012 |
| `data/sample/` | A 10-row sample of receipt-level data |
| `tests/` | 20 pytest tests |

## The data in four numbers

Total sales are $6,737,218,987. The average store sells $1,046,965 a week. Store 20 leads with $301.4 million. Holiday weeks run 7.84% above normal weeks.

## Loading a database

Create the database once yourself (the first line below). `python run.py database` then does the other steps for you, and it refuses to overwrite tables that hold rows. By hand, on PostgreSQL:

```bash
psql -U postgres -c "CREATE DATABASE walmart_sales;"
psql -U postgres -d walmart_sales -f sql/postgres/01_schema.sql
psql -U postgres -d walmart_sales -f sql/postgres/02_indexes.sql
psql -U postgres -d walmart_sales -f sql/postgres/03_views.sql
python -m src.etl --dataset-type weekly --csv data/raw/walmart_real_sales.csv \
  --db "postgresql+psycopg2://postgres:YOUR_PASSWORD@localhost:5432/walmart_sales"
```

For MySQL, use the files in `sql/mysql/` and a URL that starts with `mysql+pymysql://`. Then pick "Database" in the dashboard sidebar and paste the same URL.

The weekly dataset comes from Hugging Face: `Ammok/walmart_sales_prediction`. Its dataset card gives the license as MIT. The 10-row receipt sample is an excerpt of a public supermarket sales sample with three branches in Myanmar. It is not Walmart data and is only there to show the second dashboard layout.
