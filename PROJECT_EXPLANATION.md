# Walmart sales analytics: how the project works

This project takes a CSV file of weekly sales for 45 Walmart stores, cleans it with pandas, and shows it in a Streamlit dashboard: number cards, charts, a store ranking and a sales forecast. The same cleaned data can also be loaded into PostgreSQL or MySQL, and the `sql/` folder has the tables, indexes, views and analysis queries for both.

Every number in this document was checked by running the project on 21 and 22 September 2026. Section 10 lists what was run, what came out, and what was not run.

## 1. How the data moves

```text
data/raw/walmart_real_sales.csv          (6,435 rows, 8 columns)
            |
            v
src/transform.py      rename columns, fix dates and numbers, drop broken rows
            |
            +--------------------------------+
            |                                |
            v                                v
app.py  (the dashboard)              src/etl.py  (load into a database)
  summaries: src/transform.py                |
  forecast:  src/forecasting.py              v
            ^                        PostgreSQL or MySQL
            |                        tables, indexes, views, queries: sql/
            |                                |
            +------ "Database" mode ---------+
```

The CSV is the starting point for everything. `src/transform.py` is the one place where raw data becomes clean data, and both the dashboard and the database loader go through it. That is why the dashboard shows the same totals whether it reads the CSV or the database.

## 2. What is in the folder

| Path | What it does |
| --- | --- |
| `run.py` | The runner. One command that checks the setup and starts the dashboard. It can also run the tests and build and load a database (section 9). |
| `run.command`, `run.bat` | Double-click launchers for Mac and Windows. On the first run they make a project-local Python in `.venv`, then they hand over to `run.py`. |
| `HOW_TO_RUN.md` | The step-by-step guide for macOS and Windows: Python, the launcher, the same steps by hand, PostgreSQL, MySQL, VS Code, troubleshooting. |
| `.gitattributes` | Keeps `run.bat` in Windows line endings and the scripts and CSV files in Unix line endings on every checkout. |
| `app.py` | The dashboard. Builds the sidebar, loads the chosen data, draws the tabs. |
| `src/transform.py` | Cleaning rules and the summary functions (KPIs, monthly totals, store ranking, holiday gap, correlations). |
| `src/data_loader.py` | Three small loaders: weekly CSV, POS CSV, SQL query. |
| `src/forecasting.py` | The forecast: a trend line plus a fixed amount per calendar month. |
| `src/etl.py` | Command-line script that loads a CSV into PostgreSQL or MySQL. |
| `src/download_dataset.py` | Optional. Downloads the dataset again from Hugging Face and overwrites the bundled CSV. |
| `src/generate_assets.py` | Optional. Writes two SVG pictures, two PNG pictures and a 4-slide PowerPoint into `docs/` and `reports/`. |
| `src/__init__.py` | Marks `src` as a package so `from src.transform import ...` works. |
| `sql/postgres/`, `sql/mysql/` | Four numbered SQL files per database: schema, indexes, views, analysis queries. |
| `data/raw/walmart_real_sales.csv` | The main dataset. |
| `data/sample/walmart_sales_sample.csv` | A 10-row sample of receipt-level (POS) data. |
| `tests/test_transform.py` | Four tests for the cleaning, the summaries and the forecast. |
| `tests/test_run.py` | 17 tests for the runner and the launchers: the SQL splitter, the check on DROP statements, the password masking, the CSV reader, the choice of error line, the package version check, and the launcher files. |
| `requirements.txt` | The Python packages to install. |

The code is commented line by line. In the Python files the comment sits above the line it explains. In the SQL files, column comments sit to the right of the column.

## 3. The two datasets

### Weekly store sales

`data/raw/walmart_real_sales.csv` has one row per store per week. There are 45 stores and 143 weeks, which gives 45 x 143 = 6,435 rows. The first week is 5 February 2010 and the last is 26 October 2012. Every date is a Friday, and no cell is empty.

| Column | Meaning | Example |
| --- | --- | --- |
| `Store` | Store number, 1 to 45 | `1` |
| `Date` | The sales week, written day-month-year | `05-02-2010` |
| `Weekly_Sales` | Sales of that store in that week, in dollars | `1643690.9` |
| `Holiday_Flag` | 1 for a holiday week, 0 for a normal week | `0` |
| `Temperature` | Temperature for that store and week | `42.31` |
| `Fuel_Price` | Cost of fuel in the store's region | `2.572` |
| `CPI` | Consumer Price Index | `211.0963582` |
| `Unemployment` | Unemployment rate in percent | `8.106` |

The file comes from the public Hugging Face dataset `Ammok/walmart_sales_prediction`, whose dataset card gives the license as MIT.

Ten weeks carry the holiday flag: the weeks of 12 Feb, 10 Sep, 26 Nov and 31 Dec in 2010, the matching weeks in 2011, and 10 Feb and 7 Sep in 2012. With 45 stores that makes 450 holiday rows.

### POS sample

`data/sample/walmart_sales_sample.csv` is a different kind of data. One row is one receipt, with 17 columns such as invoice ID, branch, city, product line, quantity, total, payment method and rating. It has 10 rows from January to March 2019, three branches (A in Yangon, B in Mandalay, C in Naypyitaw) and $4,176 in total sales. It is an excerpt of a public supermarket sales sample and is not Walmart data. It is there to show the second dashboard layout. Ten rows are too few to draw conclusions from.

## 4. What happens when you run the dashboard

The command is `streamlit run app.py`. Streamlit then runs `app.py` from top to bottom, and it does so again after every click. The steps for the default mode:

1. `main()` calls `load_dashboard_data()`, which draws the sidebar with four radio buttons. "Real weekly CSV" is selected when the page opens.
2. For that choice it calls `cached_weekly("data/raw/walmart_real_sales.csv")`. The `@st.cache_data` line above the function makes Streamlit remember the result, so the file is read from disk once and later clicks reuse it.
3. `cached_weekly` calls `load_weekly_csv` in `src/data_loader.py`. That runs `pd.read_csv` and passes the raw table to `normalize_weekly_columns` in `src/transform.py` (section 5).
4. The cleaned table comes back together with the label `"weekly"`. `main()` sees the label and calls `weekly_dashboard(df)`. For the label `"pos"` it would call `pos_dashboard(df)`.
5. `weekly_dashboard` draws the title, four number cards and six tabs. Each tab calls one or two functions from `src/transform.py` or `src/forecasting.py` and gives the result to a Plotly chart or a table.

The other three modes change step 2 only. "Sample POS CSV" reads the 10-row file. "Upload CSV" and "Database" do not know in advance what kind of data they will get, so they call `detect_dataset_type`, which answers "weekly" when the columns include `weekly_sales` and `store`, and "pos" otherwise. Both modes show a hint and stop the run with `st.stop()` until a file or a URL has been given.

| Tab | Function behind it | What you see |
| --- | --- | --- |
| Overview | `monthly_sales` | Line chart of sales per month, and a box plot of holiday weeks against normal weeks |
| Stores | `store_performance` | Table of all 45 stores by rank, and a bar chart of the top 15 |
| Economic Signals | `economic_correlations` | Correlation table, and four scatter plots of sales against each signal |
| Forecast | `forecast_weekly_sales` | Slider for 4 to 26 weeks, the forecast table, and a chart with actual and forecast lines |
| Insights | `holiday_uplift`, `store_performance`, `economic_correlations` | Three sentences built from the numbers |
| Data | none | The cleaned table |

The POS page has four tabs: Overview (sales per day and per branch), Products (sales per product line), Customers (two pie charts: customer type and payment method) and Data.

## 5. The cleaning rules

`normalize_weekly_columns` does six things, in this order.

It renames the columns with `WEEKLY_COLUMN_MAP`, so `Weekly_Sales` becomes `weekly_sales`. Lowercase names with underscores are easier to type and they match the column names in the SQL tables.

It checks that all eight columns exist. If one is missing it raises `ValueError` and names the missing columns. Without this check, a wrong file would fail much later inside a chart with an error that is hard to read.

It converts the date text to real dates with `dayfirst=True`. This matters more than it looks. The file writes `05-02-2010` for 5 February 2010, and without `dayfirst=True` pandas reads that as 2 May. Monthly totals and the forecast would then be wrong without any error message. The first test in `tests/` exists to protect this line.

It converts the seven number columns with `errors="coerce"`, which turns text that is not a number into an empty value.

It drops rows that have no store, no date or no sales. In the bundled file this removes nothing, because no cell is empty. The rule is there for uploaded files.

It stores `store` and `holiday_flag` as whole numbers, sorts by date and then store, and renumbers the rows from 0.

`normalize_pos_columns` follows the same pattern for receipt data. It needs six columns (`invoice_id`, `branch`, `product_line`, `total`, `date`, `payment`) and treats the rest as optional.

## 6. What the numbers say

These are the results for the bundled file. They are the same in pandas, in PostgreSQL and in MySQL.

Total sales are $6,737,218,987 over 6,435 rows, so the average store sells $1,046,965 in a week. All 45 stores together average $47.1 million per week.

Store 20 sold the most with $301.4 million, followed by store 4 with $299.5 million and store 14 with $289.0 million. Store 33 sold the least, $37.2 million. The best store sold about eight times as much as the weakest one.

December is the strongest month of both 2010 and 2011 (the 2012 data ends in October): $288.8 million in December 2010 and $288.1 million in December 2011. The weakest month is January 2011 with $163.7 million.

Holiday weeks average $1,122,888 per store and normal weeks $1,041,256. `holiday_uplift` turns that into (1,122,888 - 1,041,256) / 1,041,256 x 100 = 7.84%. One detail weakens this number. The biggest week in the whole file is the week of 24 December 2010 with $80.9 million, and that week is flagged as a normal week, because the flag marks the week of 31 December. The Christmas shopping peak therefore counts on the "normal" side, and 7.84% understates how much the holiday season lifts sales.

The four economic columns barely move with sales. The correlations are -0.106 for unemployment, -0.073 for CPI, -0.064 for temperature and 0.009 for fuel price. Correlation runs from -1 to 1, and values this close to 0 mean that none of these columns explains weekly sales in a useful way. The Insights tab reports unemployment as the "strongest" relationship, which is true and still describes a weak link. The fuel price query in `sql/postgres/04_analytics_queries.sql` agrees: average sales are $1,039,929 in the low bucket, $1,063,514 in the medium one and $1,042,901 in the high one, all within 2.3% of each other.

## 7. How the forecast works

`forecast_weekly_sales` predicts the total of all stores, week by week.

First it adds the 45 stores together, which leaves 143 rows, one per week. Each row gets two inputs: a week counter from 0 to 142, and the month number. The month is then turned into 12 yes/no columns (`month_1` to `month_12`) with `pd.get_dummies`. A row in March has `month_3 = 1` and zeros in the other eleven. Feeding the month in as a plain number would tell the model that month 12 is "twelve times" month 1, which makes no sense for calendar months.

The model itself is one line of NumPy, `np.linalg.lstsq`. It finds 14 numbers: a base level, an amount to add per week (the trend), and one amount per calendar month. It picks them so that the predicted sales are as close as possible to the real sales over the 143 weeks. A prediction is then: base + trend x week number + the amount for that month.

For the future, the function builds the next Fridays after 26 October 2012, gives them the same inputs, multiplies, and lifts any negative result to 0. The output table has the 143 real weeks with an empty forecast column, followed by the future weeks with an empty actual column. Plotly draws that as two lines: the real sales up to 26 October 2012, and the forecast starting one week later.

With the default of 12 weeks the forecast is about $52.2 million per week for November 2012, $58.3 million for December and $42.2 million for January 2013. Inside one month the values rise by about $8,058 per week, which is the trend.

The limits are easy to name. Every week of a month gets the same monthly amount, so the model cannot produce a spike like the $80.9 million Christmas week. It ignores the holiday flag and the economic columns. It forecasts the chain as a whole and says nothing about single stores. And it has never been scored against weeks it did not see during fitting, so its error is unknown. It is a baseline: the first thing to build, and the thing a better model has to beat.

## 8. The database side

### Tables

`01_schema.sql` creates six tables. `weekly_store_sales` holds the Walmart data and is the only one the ETL script fills from the main CSV. It allows one row per store and date (`unique (store, date)`).

The other five tables are a design for receipt data in normalized form, meaning each fact is stored once and tables point to each other by id:

```text
stores    1 --- many  transactions  1 --- many  transaction_line_items  many --- 1  products
customers 1 --- many  transactions
```

### Loading data

```bash
python -m src.etl --dataset-type weekly --csv data/raw/walmart_real_sales.csv --db "DATABASE_URL"
```

ETL stands for extract, transform, load. In `load_weekly` the extract step is `pd.read_csv`, the transform step is `normalize_weekly_columns`, and the load step is `df.to_sql(..., if_exists="append")`, which adds the rows to `weekly_store_sales`.

With `--dataset-type pos` the script writes to two other tables, which pandas creates when they do not exist: `branches` (one row per branch and city) and `pos_sales_staging` (every cleaned receipt row). A staging table is a holding area where rows wait until SQL moves them into the final tables.

### Indexes, views and queries

`02_indexes.sql` adds six indexes on the columns that queries filter and group by: date, store and holiday flag on the weekly table, and date, payment method and product on the receipt tables. With 6,435 rows you will not feel a difference. Indexes start to pay off when a table has millions of rows.

`03_views.sql` creates three views. A view is a saved query with a name. `vw_monthly_sales`, `vw_store_rankings` and `vw_holiday_uplift` return the same results as `monthly_sales`, `store_performance` and `holiday_uplift` in Python, which makes them a good cross-check.

`04_analytics_queries.sql` has three queries to run by hand. The first uses a CTE and `lag()` for month-over-month growth. The second uses a window with `rows between 3 preceding and current row` for a 4-week moving average per store. The third differs by database: fuel price buckets on PostgreSQL, holiday comparison on MySQL.

### PostgreSQL and MySQL side by side

| Topic | PostgreSQL | MySQL |
| --- | --- | --- |
| Auto-numbered id | `serial` | `int auto_increment` |
| Exact decimal type | `numeric(14, 2)` | `decimal(14, 2)` |
| Foreign keys | Written on the column: `references stores(store_id)` | Separate lines: `foreign key (...) references ...` |
| First day of the month | `date_trunc('month', date)::date`, a real date | `date_format(date, '%Y-%m-01')`, text |
| Running `02_indexes.sql` twice | Works, because of `if not exists` | Fails with "Duplicate key name". Run `01_schema.sql` first. |
| Driver in the URL | `postgresql+psycopg2://` | `mysql+pymysql://` |
| Window functions | Supported | Need MySQL 8.0 or newer |

## 9. How to run everything

### The short way: run.py

```bash
python run.py
```

Pressing the Run button on `run.py` in VS Code does the same. So does a double-click on `run.command` (Mac) or `run.bat` (Windows), with one addition: on the first run those two make a project-local Python in the folder `.venv` and start `run.py` with it, so the packages land inside the project folder and nowhere else. [HOW_TO_RUN.md](HOW_TO_RUN.md) has the step-by-step version for both systems. Where the shell has no `python` command (a Mac or Linux without conda or an active virtual environment), type `python3 run.py`. The runner prints which Python is running it, checks that pandas, numpy, streamlit, plotly and sqlalchemy are installed, counts the rows of the CSV, starts Streamlit on the first free port from 8501 to 8510 and opens the browser. Ctrl+C stops the dashboard and leaves nothing running.

| Command | What it does |
| --- | --- |
| `python run.py` | Packages, data file, dashboard. It never touches a database. |
| `python run.py check` | A report only: Python, packages with versions, data files, the port it would use. It changes nothing. |
| `python run.py test` | Runs pytest without leaving cache folders behind. |
| `python run.py database` | Builds the tables from `sql/`, loads the weekly CSV, and compares the database with the CSV. |
| `python run.py all` | Tests, then database, then dashboard. It stops at the first step that fails. |

Two options exist. `--no-browser` starts the dashboard without opening a tab. `--reset` belongs to `database` and is explained below.

The runner uses one Python for everything: the one that started it. If a package is missing, or older than `requirements.txt` allows, it names the package, shows the exact `pip install` command, and installs only after you type `y`. Any other answer ends the run with a short list of next steps. This matters when VS Code and the terminal use different Pythons. On the machine this was tested on, the Python selected in VS Code (3.14) had no plotly, while `python` in the terminal was a conda Python with all five dashboard packages.

The `database` action asks for the address without the password, then asks for the password with hidden typing. The address is not an option on the command line, because a password typed there ends up in the shell history. For runs where nobody can type, put the full address into the environment variable `WALMART_DB_URL`. The runner never prints the address. It shows the target in words, such as `PostgreSQL database "walmart_sales" on localhost:5432 as user postgres`, and it removes the password from every error message.

`01_schema.sql` deletes tables, so the runner looks before it acts:

| What it finds in the six project tables | What it does |
| --- | --- |
| All empty or missing | Runs 01, 02 and 03, loads the CSV, checks the result |
| The weekly table already matches the CSV, views included | Checks the result, says so, changes nothing |
| The weekly rows match, but views or tables are missing | Shows what is missing, changes nothing, points at `--reset` |
| Anything else | Lists the tables with their row counts and changes nothing |

`python run.py database --reset` is the only way to wipe tables that hold rows, and it asks you to type the database name first. On PostgreSQL the three SQL files run in one transaction, so a failing statement undoes the drops before it. MySQL cannot undo a drop. There a failed rebuild leaves empty tables, and the next run builds them again. The runner does not create the database itself. If it is missing, the message shows the `CREATE DATABASE` line to run.

Before it drops anything, the runner lets the project's own cleaning code read the CSV. If that code refuses the file, or would keep fewer rows than the file has, the run stops with the database untouched. Without this step a confirmed `--reset` could delete good rows and then fail to load new ones.

The SQL files go through a small splitter inside `run.py` instead of the `psql` or `mysql` program. The splitter removes comments first, because the comments in these files contain semicolons, and it keeps quoted text such as `'%Y-%m-01'` unchanged. It stops with a line number when it meets SQL it does not understand. From the setup files it sends only `CREATE` statements and `DROP` statements that name a view or one of the six project tables. A `drop database`, or a drop of a seventh table, is refused, because the row counts shown before a reset only cover those six tables. The check at the end compares the database with numbers that the runner works out from the CSV with Python's `csv` and `decimal` modules. pandas is not involved in that side, so a mistake in the pandas code cannot hide itself.

The rest of this section shows the same steps done by hand.

### Dashboard and tests by hand

macOS or Linux:

```bash
cd walmart-sales-analytics        # the folder you cloned or unpacked
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

On Windows the third line is `.venv\Scripts\activate`. The dashboard opens at http://localhost:8501. Stop it with Ctrl + C.

`.venv` is your local copy of the packages. It can be several hundred megabytes. Leave it out when you zip or share the project, since anyone can rebuild it from `requirements.txt`.

`requirements.txt` asks for Streamlit 1.51 or newer. `app.py` passes `width="stretch"` to its charts and tables, and `st.plotly_chart` accepts that option from 1.51 on. Streamlit 1.51 in turn needs Python 3.10 or newer, which is why the runner refuses older Pythons. With an older Streamlit every chart would fail, so the runner reports it as TOO OLD and offers the upgrade.

Run the tests from the project folder:

```bash
python -m pytest
```

The expected last line is `21 passed`.

### PostgreSQL

```bash
psql -U postgres -c "CREATE DATABASE walmart_sales;"
psql -U postgres -d walmart_sales -f sql/postgres/01_schema.sql
psql -U postgres -d walmart_sales -f sql/postgres/02_indexes.sql
psql -U postgres -d walmart_sales -f sql/postgres/03_views.sql
python -m src.etl --dataset-type weekly --csv data/raw/walmart_real_sales.csv \
  --db "postgresql+psycopg2://postgres:YOUR_PASSWORD@localhost:5432/walmart_sales"
psql -U postgres -d walmart_sales -c "select count(*), sum(weekly_sales) from weekly_store_sales;"
```

The last command should print `6435` and `6737218987.11`.

### MySQL

```bash
mysql -u root -p -e "CREATE DATABASE walmart_sales;"
mysql -u root -p walmart_sales < sql/mysql/01_schema.sql
mysql -u root -p walmart_sales < sql/mysql/02_indexes.sql
mysql -u root -p walmart_sales < sql/mysql/03_views.sql
python -m src.etl --dataset-type weekly --csv data/raw/walmart_real_sales.csv \
  --db "mysql+pymysql://root:YOUR_PASSWORD@localhost:3306/walmart_sales"
```

`requirements.txt` also lists `cryptography`, because PyMySQL uses it for some MySQL 8 logins and stops with an error when it is missing.

### Dashboard on top of the database

Start the dashboard, choose "Database" in the sidebar, paste the same URL you gave to `src.etl`, and keep the query `select * from weekly_store_sales`. The page should show the same four numbers as the CSV mode.

The URL contains your password. The sidebar box hides it and the app does not store it. Keep real passwords out of files in this folder.

### Loading the data a second time

`weekly_store_sales` accepts one row per store and date, so a second run of the weekly ETL stops with a duplicate key error. That protects the totals from being doubled. To reload, run `01_schema.sql`, `02_indexes.sql` and `03_views.sql` again in that order, then the ETL. `01_schema.sql` deletes all rows in the six tables.

### The two optional scripts

`python -m src.generate_assets` writes `docs/dashboard_overview.svg`, `docs/project_architecture.svg`, two PNG files in `docs/screenshots/` and `reports/walmart_sales_analytics.pptx`. It creates the folders itself, and you can delete them afterwards.

`python -m src.download_dataset` needs internet and replaces `data/raw/walmart_real_sales.csv` with a fresh download. The bundled file already has all 6,435 rows, so there is no need to run it.

## 10. What was run, and the result

All of this was done on 21 and 22 September 2026 with Python 3.13.5, pandas 2.2.3, Streamlit 1.58.0, Plotly 6.7.0 and SQLAlchemy 2.0.49. The databases were a temporary PostgreSQL 15.15 and a temporary MySQL 8.4.11 in Docker. Both were deleted afterwards.

| What | Result |
| --- | --- |
| `python -m pytest` | 21 passed (4 before the runner's tests were added) |
| `streamlit run app.py` | Server started on port 8501 and answered its health check |
| Dashboard, "Real weekly CSV" | No errors. Cards: $6,737,218,987 / $1,046,965 / 6,435 / 45. Six tabs. |
| Forecast slider moved to 26 | No errors |
| Dashboard, "Sample POS CSV" | No errors. Cards: $4,176 / $418 / 10 / 3. Four tabs. |
| Dashboard, "Upload CSV" and "Database" with nothing entered | Hint message shown, no errors |
| PostgreSQL: schema, indexes, views | All three ran without errors |
| PostgreSQL: weekly ETL | 6,435 rows, 45 stores, sum 6,737,218,987.11 |
| PostgreSQL: three views and the query file | 33 months; stores 20, 4, 14 on top; holiday average 1,122,888 against 1,041,256; all three queries ran |
| Dashboard, "Database" mode on PostgreSQL | Same four cards as CSV mode |
| PostgreSQL: POS ETL | 3 rows in `branches`, 10 in `pos_sales_staging` |
| PostgreSQL: run 01, 02, 03 again, then ETL again | Worked, 6,435 rows |
| MySQL: schema, indexes, views, weekly ETL, POS ETL, query file | All ran. 6,435 rows, sum 6,737,218,987.11 |
| MySQL: run 01, 02, 03 again, then ETL again | Worked |
| MySQL: `02_indexes.sql` a second time without 01 | Fails with "Duplicate key name", as the file's comment says |
| Weekly ETL a second time without a reset | Fails with a duplicate key error, by design |
| `python -m src.generate_assets` (in a scratch copy) | Wrote 2 SVG, 2 PNG and 1 PPTX |
| `python run.py test` on Python 3.13 and 3.14 | 21 passed on both |
| `run.command` in a copy whose path has a space: only Python 3.9 on the PATH; first run with 3.13; second run; a `.venv` made with 3.9; a `.venv` whose Python was removed; a `.venv` without pip; a link to the file started elsewhere | Refused with exit 1; made `.venv` and ran `--help`; reused `.venv`; refused with exit 1; rebuilt; rebuilt; refused with exit 1 |
| `run.command` under a fake terminal: `check`, `test` with `y`, the dashboard with `y` then Ctrl+C, the dashboard again | Pause shown and exit 1; 21 passed; dashboard up, stopped cleanly, pause shown, exit 0; no question the second time |
| `run.bat` | Not run. Windows was not available. Reviewed by reading only. |
| Streamlit 1.40 simulated, no keyboard | Reported as TOO OLD (needs 1.51 or newer), pip command shown, nothing installed, exit code 2 |
| `python run.py check` on Python 3.9 | "This project needs Python 3.10 or newer", exit code 2 |
| `python run.py check` | Python 3.14: plotly reported missing, exit code 1. Python 3.13: ready, exit code 0. |
| `python run.py` on Python 3.14 without a keyboard | Named plotly, showed the pip command, installed nothing, exit code 2 |
| `python run.py` with port 8501 taken | Moved to 8502, health check ok, Streamlit started with the same Python |
| Stopping the runner: Ctrl+C, Ctrl+C twice, SIGTERM, SIGHUP | Exit code 0 each time, port free again, no process left, no traceback |
| Start again right after a stop | Same port again |
| `python run.py database` on PostgreSQL and MySQL, first run | 24 and 21 statements, 6,435 rows loaded, all nine checks ok |
| The same command a second time | "already loaded and correct", nothing changed |
| One extra row in the table, no `--reset` | Refused, exit code 2, rows untouched |
| `--reset` with a wrong name, with no input, with the right name | Cancelled, cancelled, rebuilt and verified |
| A broken `03_views.sql` on PostgreSQL | Stopped at the broken statement, and all 6,435 rows were still there |
| Typed address with hidden password, and a wrong password | Connected. With the wrong password: a three-line message, exit code 1 |
| Password `S3cr@t:/pw` searched for in all captured output | Not found, in any spelling |
| `python run.py all` | Tests, database, dashboard in that order. With an unreachable database it stopped before the tests. |
| Weekly rows loaded but the three views dropped by hand | Four lines marked DIFFERENT, exit code 2, message points at `--reset`, nothing changed |
| CSV with an upper-case header, then a confirmed `--reset` | Stopped by the loader check before any drop. All 6,435 rows were still there. |
| CSV with a cut-off last line | "line 6: this line does not have exactly 8 values", exit code 1, no traceback |
| Ctrl+D at the hidden password prompt | "No password given. Nothing was changed.", exit code 2 |
| Password equal to the user name | The target line shows the user name in full. Before the fix it was starred out, which gave the password away. |
| `python run.py check \| head -2` | Exit code 0. Before the fix a closed pipe turned it into 120. |
| `nohup python run.py --no-browser &`, then SIGHUP, then SIGTERM | Survived the hangup, stopped cleanly on SIGTERM, port free |
| `run.py` on Windows | Not run. The Windows parts (`taskkill` for the process tree, the `& ` prefix for PowerShell, exit code 0xC000013A) have never been executed. |
| `python -m src.download_dataset` | Not run. It needs internet and overwrites the bundled CSV. |

## 11. Known gaps

The five receipt tables stay empty. No code moves rows from `pos_sales_staging` into `stores`, `customers`, `products`, `transactions` and `transaction_line_items`. The SQL that does this is the missing piece of the POS pipeline, and writing it would be the most useful next step on the data engineering side.

The POS load is safe to repeat for `pos_sales_staging`, which is replaced each time. It is not safe for `branches`: a second load left 6 rows where there should be 3, because the rows are appended and the table has no unique rule. `01_schema.sql` does not drop these two tables either, since it does not know about them.

The dashboard mock-up in `src/generate_assets.py` has its numbers typed in by hand. Three of them match the data ($1.05M average week, 45 stores, +7.8% holiday uplift). The total of "$85.2M" does not. The real total is $6.74 billion. The two PNG files are placeholder charts and not screenshots of the app.

"Database" mode runs whatever SQL is typed into the sidebar, with the rights of the database user in the URL. On your own laptop that is fine. Before putting the app somewhere others can reach it, connect with a database user that can only read.

The tests cover the cleaning, the ranking, the monthly total, the holiday percentage, the row count of the forecast, and five parts of the runner: the SQL splitter with its DROP check, the password masking, the CSV reader, the choice of error line and the package version check, plus the presence and line endings of the two launcher files. Nothing tests `app.py`, `src/etl.py` or the POS cleaning with pytest. The SQL files are only tested for how they split into statements. Whether they run is checked by `python run.py database`, which needs a live server.

## 12. Describing the project to someone else

A description that matches what the code does:

> I built a sales analytics project on three years of weekly data from 45 Walmart stores. A pandas cleaning layer fixes column names, day-first dates and number types. A Streamlit dashboard sits on top of it with KPIs, a monthly trend, a store ranking, holiday and economic analysis, and a baseline forecast made with least squares on a trend and month columns. An ETL script loads the same cleaned data into PostgreSQL or MySQL, where I wrote the schema, indexes, views and window-function queries. The totals match between pandas and both databases.

Questions this tends to raise, with the answers the project supports:

- Why `dayfirst=True`? The file writes 05-02-2010 for 5 February. Without the flag pandas reads 2 May, and nothing crashes, so the mistake would go unnoticed.
- Why does the second ETL run fail? The table has `unique (store, date)`. Failing is better than doubling every total.
- Why 12 month columns and not one month number? A single number would claim that December is twelve times January.
- How good is the forecast? Unknown, because it was never scored on held-out weeks. It also cannot reproduce the Christmas week. Both are the first things to fix.
- Do fuel price or unemployment drive sales? Not in this data. The strongest correlation is -0.106.
- Why is the database address not an option of `run.py`? It contains the password, and the shell history keeps whatever is typed on a command line. The runner asks for it, with the password hidden, or reads an environment variable.
- What is unfinished? The step from `pos_sales_staging` into the five normalized tables.

## 13. Short glossary

| Term | Meaning |
| --- | --- |
| DataFrame | The pandas word for a table with named columns |
| KPI | Key performance indicator. Here: the four numbers at the top of the dashboard |
| ETL | Extract, transform, load: read data, clean it, write it somewhere else |
| Schema | The list of tables and columns in a database, with their types and rules |
| Primary key | The column that identifies a row, such as `store_id` |
| Foreign key | A column that must match a primary key in another table |
| Index | A lookup structure that lets the database find rows without reading the whole table |
| View | A saved query that can be used like a table |
| CTE | Common table expression: `with name as (...)`, a named sub-result inside one query |
| Window function | A function such as `rank()`, `lag()` or a moving `avg()` that looks at neighbouring rows without collapsing them into one |
| Staging table | A table that holds freshly loaded rows before they are moved to their final tables |
| Correlation | A number from -1 to 1 that says how closely two columns move together |
| Least squares | A way to fit a model by making the squared gaps between prediction and reality as small as possible |
| Baseline | The simplest reasonable model, used as the mark that a better model has to beat |
