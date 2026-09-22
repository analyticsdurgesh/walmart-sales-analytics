# How to run the project on a Mac or on Windows

This guide takes you from an empty computer to a running dashboard, and on to the tests and the database, on macOS and on Windows. Every step has the exact command to type. If you only want to see the dashboard, section 2 is enough.

The launcher and `run.py` steps in sections 2, 3, 4.3, 4.4 and 4.7 were run on a Mac on 22 September 2026. The Python install, the download from GitHub and the Homebrew and Postgres.app commands in sections 4.1, 4.2, 4.5 and 4.6 follow the tools' documentation and were not run. The Windows steps were written from the documentation of Python, PostgreSQL and MySQL and reviewed by reading; nobody has run them on a Windows machine yet. Section 10 lists what was and was not run. If a Windows step does not work as written, please open an issue on GitHub.

## 1. What you need

- Python 3.10 or newer. Section 4.1 (Mac) and section 5.1 (Windows) show how to install it. Python 3.13 and 3.14 were used for testing.
- About 1 GB of free disk space. The dashboard packages take around 500 MB.
- Git, if you want to clone the project. Without git you can download it as a zip file.
- A database server only if you want the database part. The dashboard runs from the CSV file without one.

## 2. The quick way: one file that does everything

The project folder holds two launcher files next to `run.py`:

| File | For | What it does |
| --- | --- | --- |
| `run.command` | Mac (and Linux) | Double-click in Finder, or type `bash run.command` |
| `run.bat` | Windows | Double-click in Explorer, or type `.\run.bat` |

Both do the same three things:

1. On the first run they make a project-local Python in the folder `.venv` inside the project. That takes a few seconds and happens once. Packages installed later go into that folder and nowhere else on your computer.
2. They hand over to `run.py`, which checks the packages the dashboard needs. On the first run five are missing. It shows the exact `pip install` command and asks `Install now? Type y and press Enter.` Type `y`. The download takes one to three minutes.
3. `run.py` starts the dashboard on the first free port from 8501 to 8510 and opens it in your browser.

Leave the window open while you use the dashboard. To stop it, click the window and press Ctrl+C. The last line reads `Dashboard stopped. Nothing is left running.` On a Mac the launcher then shows `Press Enter to finish.`; after Enter, Terminal shows `[Process completed]` or closes the window, depending on its settings, and Command+W closes it. On Windows the console asks `Terminate batch job (Y/N)?` instead. Type `N`: the batch file then finishes and shows `Press any key to continue . . .`. `Y` also works, but it ends the batch file at once and a double-clicked window closes.

The launchers pass on any word you add. From a terminal in the project folder:

```bash
bash run.command test        # Mac
.\run.bat test               # Windows
```

The words are the same for both, and the same as for `run.py`:

| Word | What it does |
| --- | --- |
| none | Checks packages and the data file, then starts the dashboard and opens the browser |
| `check` | A report only: Python, package versions, data files, the port it would use. Changes nothing. |
| `test` | Runs the 21 automated tests |
| `database` | Builds the tables in PostgreSQL or MySQL, loads the CSV, compares the database with the CSV |
| `all` | Tests, then database, then dashboard |

Two options exist: `--no-browser` starts the dashboard without opening a tab, and `--reset` (only with `database`) wipes the six project tables after you confirm.

Two things that happen on the first double-click:

- Mac: if the project came from a zip download, the first double-click on `run.command` shows a dialog that says Apple could not verify it. Click Done, open System Settings, click Privacy & Security, scroll down to the line about `run.command` and click Open Anyway, then Open. On macOS 14 and older, right-click the file, choose Open, and click Open instead. Either is needed once. Or skip the dialog: open Terminal and type `bash run.command` inside the project folder. Projects that came through `git clone` do not have this problem.
- Windows: the first double-click on `run.bat` may show a window titled Open File - Security Warning. Click Run.

## 3. What run.py does behind the launchers

`run.py` is a plain Python file with no dependencies of its own. `python run.py` from a terminal is the same as the launcher, with one difference: it uses whatever Python you typed, not the `.venv` one. It prints the Python it uses in its second line, so there is never a doubt.

It never installs anything without a `y`. It never touches a database unless you type `database` or `all`. It never prints a database address or a password. `python run.py --help` lists the words and options. Section 9 of [PROJECT_EXPLANATION.md](PROJECT_EXPLANATION.md) explains the database action in detail.

## 4. macOS, step by step

All commands go into the Terminal app. Open it with Command+Space, type Terminal, press Enter. A line that starts with `#` is a comment, not something to type.

### 4.1 Install Python

Check what you have first:

```bash
python3 --version
```

You need 3.10 or newer. A fresh Mac answers with 3.9.6 or offers to install command line tools. In both cases install a newer Python in one of two ways.

Option A, the python.org installer: open https://www.python.org/downloads/, click the big download button, open the .pkg file and click through. Then close and reopen Terminal and check again:

```bash
python3 --version
# Python 3.14.x (any 3.10 or newer is fine)
```

Option B, Homebrew, if you already use it:

```bash
brew install python
python3 --version
```

### 4.2 Get the project

With git:

```bash
cd ~
git clone https://github.com/analyticsdurgesh/walmart-sales-analytics.git
cd walmart-sales-analytics
```

Without git: open https://github.com/analyticsdurgesh/walmart-sales-analytics, click the green Code button, click Download ZIP. Double-click the zip in Downloads. Then:

```bash
cd ~/Downloads/walmart-sales-analytics-main
```

### 4.3 Run it with the launcher

```bash
bash run.command
```

Or double-click `run.command` in Finder (section 2 explains the one-time Open dialog). The first run prints:

```text
Making a project-local Python in the folder .venv with python3 (3.14.x).
This happens once and takes a few seconds.
Walmart Sales - project runner
Python  : /Users/you/walmart-sales-analytics/.venv/bin/python  (version 3.14.x)
Project : /Users/you/walmart-sales-analytics

[1/3] Packages the dashboard needs
  pandas        MISSING
  numpy         MISSING
  streamlit     MISSING
  plotly        MISSING
  sqlalchemy    MISSING

The dashboard cannot start yet: 5 packages are missing or too old (pandas, numpy, streamlit, plotly, sqlalchemy).
I can install them for you. This is the exact command I would run:
    /Users/you/walmart-sales-analytics/.venv/bin/python -m pip install 'pandas>=2.1' 'numpy>=1.26' 'streamlit>=1.51' 'plotly>=5.20' 'sqlalchemy>=2.0'
...
Install now? Type y and press Enter. Anything else means no:
```

Type `y`. After the download the run continues:

```text
Installed. Carrying on.
[2/3] Data file
  data/raw/walmart_real_sales.csv   ok (6,435 rows)
[3/3] Starting the dashboard
...

Dashboard is running: http://127.0.0.1:8501
Leave this window open. To stop the dashboard, click here and press Ctrl+C.
More    : python run.py --help   (check, test, database, all)
```

The lines in place of the `...` come from Streamlit itself and start with `You can now view your Streamlit app`.

The browser opens the dashboard. Press Ctrl+C in Terminal to stop it. The tests and the other words work the same way:

```bash
bash run.command test
bash run.command check
```

### 4.4 The same steps by hand

This is what the launcher does for you, typed out. It is useful when you want to work with the code yourself.

```bash
cd ~/walmart-sales-analytics

# Make a project-local Python. The folder .venv appears inside the project.
python3 -m venv .venv

# Switch this terminal to it. The prompt now starts with (.venv).
source .venv/bin/activate

# Inside the .venv, "python" and "pip" are the project-local ones.
python --version

# Install every package the project can use. This takes a few minutes.
pip install -r requirements.txt

# Start the dashboard. Streamlit prints two URLs and opens a browser tab.
streamlit run app.py
```

On its very first start Streamlit may ask for an e-mail address. Press Enter to skip. Stop the dashboard with Ctrl+C.

The tests:

```bash
python -m pytest
# .....................
# 21 passed
```

When you are done, `deactivate` switches the terminal back to the normal Python. The `.venv` folder stays, and `source .venv/bin/activate` brings it back next time.

### 4.5 PostgreSQL on a Mac

Two easy ways to get a server. Postgres.app is a normal Mac app with an elephant icon and needs no password. Homebrew fits if you already use it.

Postgres.app: download it from https://postgresapp.com, move it to Applications, open it, click Initialize. Then give Terminal the `psql` command:

```bash
sudo mkdir -p /etc/paths.d && echo /Applications/Postgres.app/Contents/Versions/latest/bin | sudo tee /etc/paths.d/postgresapp
```

Close and reopen Terminal. The server listens on port 5432, the user is your Mac user name, and there is no password.

Homebrew:

```bash
brew install postgresql@17
brew services start postgresql@17
```

Homebrew's server also uses your Mac user name and no password. Homebrew keeps this version's programs out of the PATH (the formula is keg-only), so `psql` and `createdb` are not found until you add their folder once. On an Apple silicon Mac:

```bash
echo 'export PATH="/opt/homebrew/opt/postgresql@17/bin:$PATH"' >> ~/.zshrc
```

On an Intel Mac the folder is `/usr/local/opt/postgresql@17/bin`. Reopen Terminal.

Create the database once, with either server. `createdb` comes with PostgreSQL:

```bash
createdb walmart_sales
```

Now let the runner build the tables, load the CSV and check the result:

```bash
bash run.command database
```

It asks for the address without the password. Type it with your Mac user name, for example:

```text
postgresql+psycopg2://alice@localhost:5432/walmart_sales
```

Next it lists the packages the database step needs and asks `Install now?` for the PostgreSQL driver (and for pandas and sqlalchemy if the dashboard was never started). Type `y`. Then comes the password prompt; press Enter, because there is none. The runner then prints:

```text
Target  : PostgreSQL database "walmart_sales" on localhost:5432 as user alice
The six project tables are empty or missing, so nothing can be lost.
Building tables, indexes and views (24 statements from sql/postgres/)
Loading data/raw/walmart_real_sales.csv (6,435 rows)
Checking the database against the CSV
  what                                      CSV           database
  rows                                    6,435              6,435   ok
  stores                                     45                 45   ok
  total sales                  6,737,218,987.11   6,737,218,987.11   ok
  ...
The database matches the CSV.
```

To see the data in the dashboard, start it, pick Database in the sidebar, paste the same address with the password in it (`postgresql+psycopg2://alice@localhost:5432/walmart_sales` when there is no password), and keep the query `select * from weekly_store_sales`.

The same work by hand, inside the activated `.venv` from section 4.4:

```bash
psql -d walmart_sales -f sql/postgres/01_schema.sql
psql -d walmart_sales -f sql/postgres/02_indexes.sql
psql -d walmart_sales -f sql/postgres/03_views.sql
python -m src.etl --dataset-type weekly --csv data/raw/walmart_real_sales.csv --db "postgresql+psycopg2://alice@localhost:5432/walmart_sales"
psql -d walmart_sales -c "select count(*), sum(weekly_sales) from weekly_store_sales;"
# 6435 | 6737218987.11
```

`sql/postgres/04_analytics_queries.sql` holds three queries to look at by hand: `psql -d walmart_sales -f sql/postgres/04_analytics_queries.sql`.

### 4.6 MySQL on a Mac

```bash
brew install mysql
brew services start mysql
```

Homebrew's MySQL starts with the user `root` and no password. Create the database:

```bash
mysql -u root -e "CREATE DATABASE walmart_sales;"
```

Then:

```bash
bash run.command database
```

Address to type: `mysql+pymysql://root@localhost:3306/walmart_sales`. Next the runner asks `Install now?` for the MySQL driver and the cryptography package it needs; type `y`. Then press Enter at the password prompt. The runner builds 21 statements from `sql/mysql/`, loads the CSV and checks it, the same way as for PostgreSQL.

By hand, inside the activated `.venv`:

```bash
mysql -u root walmart_sales < sql/mysql/01_schema.sql
mysql -u root walmart_sales < sql/mysql/02_indexes.sql
mysql -u root walmart_sales < sql/mysql/03_views.sql
python -m src.etl --dataset-type weekly --csv data/raw/walmart_real_sales.csv --db "mysql+pymysql://root@localhost:3306/walmart_sales"
mysql -u root walmart_sales -e "select count(*), sum(weekly_sales) from weekly_store_sales;"
```

If you gave root a password, add `-p` to the `mysql` commands and type the password at the runner's prompt.

### 4.7 Stop and remove

Ctrl+C stops the dashboard. `brew services stop postgresql@17` and `brew services stop mysql` stop the servers; Postgres.app stops when you quit it. To remove the project, delete its folder. The `.venv` folder inside it is where the packages were installed. One thing stays behind: pip's download cache in your home folder (section 9 says where and how to empty it).

## 5. Windows, step by step

Commands go into PowerShell. Open it with the Start button, type PowerShell, press Enter. Windows Terminal works the same way. Where Command Prompt (cmd) differs, the difference is noted. Two differences hold everywhere: Command Prompt has no `~`, so type `cd %UserProfile%` where this guide says `cd ~`, and it adds a folder to the PATH with `set "PATH=%PATH%;C:\Program Files\PostgreSQL\17\bin"` where this guide says `$env:Path += ...`.

### 5.1 Install Python

Open https://www.python.org/downloads/. The big button gives the Python install manager, a small .msix file. Double-click it and click Install. Then open a new PowerShell and type `py --version`: the first time, this downloads Python 3.14.x (about a minute) and offers to add a folder to the PATH. Say yes.

If you prefer the classic installer, click the smaller link under the button, `Or get the standalone installer for Python 3.14.x`, run the .exe, tick `Add python.exe to PATH` on its first screen and click Install Now.

Either way, close and reopen PowerShell, then check:

```powershell
py --version
# Python 3.14.x (any 3.10 or newer is fine)
py -0
# lists every Python on the computer, the default one marked with *
```

`py` is the command that comes with both installers. `py -3` picks the newest Python 3 unless the variable `PY_PYTHON3` or the file `py.ini` says otherwise, which is why `run.bat` tries it first and then `python`. The plain `Python 3.x` apps in the Microsoft Store are not needed; the Python install manager from the Store is the same package as the python.org download and is fine.

If `python` on its own opens the Microsoft Store, Windows has a placeholder in the way. It does not matter for the launcher, which tries `py` first. To remove the placeholder: Start, type Manage app execution aliases, and switch off the entries `App Installer python.exe` and `App Installer python3.exe`. Leave `Python (default)`, `Python (default windowed)` and `Python install manager` on: those are the real commands.

### 5.2 Get the project

With git (https://gitforwindows.org if you do not have it):

```powershell
cd ~
git clone https://github.com/analyticsdurgesh/walmart-sales-analytics.git
cd walmart-sales-analytics
```

Without git: open https://github.com/analyticsdurgesh/walmart-sales-analytics, click the green Code button, click Download ZIP. In Downloads right-click the zip, choose Extract All, click Extract. Then:

```powershell
cd ~\Downloads\walmart-sales-analytics-main\walmart-sales-analytics-main
```

(Extract All puts a folder of the same name inside the folder it creates. If `dir` shows `run.bat`, you are in the right place.)

### 5.3 Run it with the launcher

Double-click `run.bat` in Explorer, or type in PowerShell:

```powershell
.\run.bat
```

In Command Prompt type `run.bat` without the `.\`. The first run prints:

```text
Making a project-local Python in the folder .venv with py -3. This happens once and takes a few seconds.
Walmart Sales - project runner
Python  : C:\Users\you\walmart-sales-analytics\.venv\Scripts\python.exe  (version 3.14.x)
Project : C:\Users\you\walmart-sales-analytics

[1/3] Packages the dashboard needs
  pandas        MISSING
  ...
The dashboard cannot start yet: 5 packages are missing or too old (pandas, numpy, streamlit, plotly, sqlalchemy).
I can install them for you. This is the exact command I would run:
    C:\Users\you\walmart-sales-analytics\.venv\Scripts\python.exe -m pip install "pandas>=2.1" "numpy>=1.26" "streamlit>=1.51" "plotly>=5.20" "sqlalchemy>=2.0"
...
Install now? Type y and press Enter. Anything else means no:
```

Type `y`. After the download the dashboard starts and the browser opens `http://127.0.0.1:8501`. To stop, click the window, press Ctrl+C, and answer `Y` to `Terminate batch job (Y/N)?`.

The other words:

```powershell
.\run.bat test
.\run.bat check
```

### 5.4 The same steps by hand

```powershell
cd ~\walmart-sales-analytics

# Make a project-local Python. The folder .venv appears inside the project.
py -3 -m venv .venv

# Switch this PowerShell window to it. The prompt now starts with (.venv).
.venv\Scripts\Activate.ps1

# Inside the .venv, "python" and "pip" are the project-local ones.
python --version

# Install every package the project can use. This takes a few minutes.
pip install -r requirements.txt

# Start the dashboard.
streamlit run app.py
```

Two Windows details:

- If `Activate.ps1` is refused with `running scripts is disabled on this system`, allow scripts for your user once, then try again:

  ```powershell
  Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
  ```

- In Command Prompt the activation command is `.venv\Scripts\activate.bat`, and no execution policy is involved.

On its very first start Streamlit may ask for an e-mail address. Press Enter to skip. Stop the dashboard with Ctrl+C.

The tests:

```powershell
python -m pytest
# 21 passed
```

`deactivate` switches the window back to the normal Python.

### 5.5 PostgreSQL on Windows

Download the installer from https://www.postgresql.org/download/windows/ (the EDB installer) and run it. Keep the default folder and port 5432. The installer asks for a password for the user `postgres`. Choose one and write it down. Stack Builder at the end can be skipped.

The installer adds SQL Shell (psql) to the Start menu. Open it. It asks five questions. Press Enter for Server, Database, Port and Username to accept the defaults, then type the password. At the `postgres=#` prompt:

```sql
CREATE DATABASE walmart_sales;
```

Back in PowerShell, in the project folder:

```powershell
.\run.bat database
```

Address to type: `postgresql+psycopg2://postgres@localhost:5432/walmart_sales`. Next the runner asks `Install now?` for the PostgreSQL driver (and for pandas and sqlalchemy if the dashboard was never started); type `y`. Then type the password at the hidden prompt. The runner builds the tables, loads the 6,435 rows and prints the comparison table that ends with `The database matches the CSV.`

To see the data in the dashboard, start it, pick Database in the sidebar, and paste the address with the password inside: `postgresql+psycopg2://postgres:YOUR_PASSWORD@localhost:5432/walmart_sales`.

By hand, inside the activated `.venv`: `psql` is not on the PATH by default. Either use the SQL Shell for the SQL files, or add the folder once (replace 17 with your version):

```powershell
$env:Path += ";C:\Program Files\PostgreSQL\17\bin"
```

Then:

```powershell
psql -U postgres -d walmart_sales -f sql/postgres/01_schema.sql
psql -U postgres -d walmart_sales -f sql/postgres/02_indexes.sql
psql -U postgres -d walmart_sales -f sql/postgres/03_views.sql
python -m src.etl --dataset-type weekly --csv data/raw/walmart_real_sales.csv --db 'postgresql+psycopg2://postgres:YOUR_PASSWORD@localhost:5432/walmart_sales'
psql -U postgres -d walmart_sales -c "select count(*), sum(weekly_sales) from weekly_store_sales;"
```

The address is in single quotes, so PowerShell leaves a `$` in the password alone. In Command Prompt use double quotes instead, because cmd does not treat single quotes as quotes. Each `psql` command asks for the password. The `src.etl` line has the password on the command line, which PowerShell keeps in its history file. `.\run.bat database` avoids that.

### 5.6 MySQL on Windows

Download the MSI from https://dev.mysql.com/downloads/mysql/ and run it. It installs the server and starts MySQL Configurator, which asks for a password for the user `root`. Choose one and write it down. Keep port 3306.

The installer adds MySQL Command Line Client to the Start menu (the name includes the version). Open it, type the root password, and at the `mysql>` prompt:

```sql
CREATE DATABASE walmart_sales;
```

Then in PowerShell:

```powershell
.\run.bat database
```

Address to type: `mysql+pymysql://root@localhost:3306/walmart_sales`. Next the runner asks `Install now?` for the MySQL driver and the cryptography package it needs; type `y`. Then type the password. The runner builds 21 statements from `sql/mysql/`, loads the CSV and checks it.

By hand, inside the activated `.venv`, with the `mysql` folder on the PATH (`$env:Path += ";C:\Program Files\MySQL\MySQL Server 8.4\bin"`, adjust the version):

```powershell
mysql -u root -p walmart_sales -e "source sql/mysql/01_schema.sql"
mysql -u root -p walmart_sales -e "source sql/mysql/02_indexes.sql"
mysql -u root -p walmart_sales -e "source sql/mysql/03_views.sql"
python -m src.etl --dataset-type weekly --csv data/raw/walmart_real_sales.csv --db 'mysql+pymysql://root:YOUR_PASSWORD@localhost:3306/walmart_sales'
mysql -u root -p walmart_sales -e "select count(*), sum(weekly_sales) from weekly_store_sales;"
```

The address is in single quotes for the same reason as in section 5.5; in Command Prompt use double quotes.

PowerShell does not allow `<` for reading a file into a command, which is why the Mac form `mysql ... < file.sql` is replaced by `-e "source file.sql"` here. It works in Command Prompt too.

### 5.7 Stop and remove

Ctrl+C stops the dashboard. The database servers run as Windows services; stop them in the Services app (`postgresql-x64-17`, `MySQL84`) or leave them. To remove the project, delete its folder. The `.venv` folder inside it is where the packages were installed. One thing stays behind: pip's download cache in your home folder (section 9 says where and how to empty it).

## 6. VS Code, on both systems

Open the project folder in VS Code. After the launcher has made the `.venv`, VS Code offers it as the interpreter; accept, or pick it with the Python version shown at the bottom right. Open `run.py` and click the Run button at the top right. The output appears in the terminal panel, questions included. Ctrl+C in that panel stops the dashboard.

Do not run `run.py` from the Interactive window or a notebook cell. It notices and asks for a terminal, because questions and Ctrl+C do not work there.

## 7. The database address and the password

The runner asks for the address without the password, then for the password with hidden typing. It shows the target in words, such as `PostgreSQL database "walmart_sales" on localhost:5432 as user postgres`, and it never prints the address itself. Every error message has the password removed.

For a run where nobody can type, put the full address into an environment variable first. Special characters in the password have to be written the URL way here, for example `@` as `%40`:

```bash
# Mac
export WALMART_DB_URL='postgresql+psycopg2://postgres:YOUR_PASSWORD@localhost:5432/walmart_sales'
```

```powershell
# Windows PowerShell
$env:WALMART_DB_URL = 'postgresql+psycopg2://postgres:YOUR_PASSWORD@localhost:5432/walmart_sales'
```

```bat
rem Windows Command Prompt
set "WALMART_DB_URL=postgresql+psycopg2://postgres:YOUR_PASSWORD@localhost:5432/walmart_sales"
```

The variable lives only in that terminal window. The Mac terminal and PowerShell save typed commands to a history file, so the prompt is the safer way on a shared computer.

The `database` word is safe to repeat. When the tables already hold the right rows it says so and changes nothing. When they hold other rows it lists them and stops. `database --reset` is the only way to wipe them, and it asks you to type the database name first.

## 8. Troubleshooting

| What you see | Why | What to do |
| --- | --- | --- |
| `command not found: python` (Mac) | Only `python3` exists outside a `.venv` | Type `python3`, or use `bash run.command` |
| `python` opens the Microsoft Store (Windows) | A Windows placeholder sits in front of Python | Use `py` or `run.bat`, or switch the aliases off (section 5.1) |
| `This project needs Python 3.10 or newer` | The Python that started `run.py` is too old | Install a newer Python, or use the launcher, which looks for one |
| `The folder .venv holds a Python older than 3.10` | The `.venv` was made before a newer Python was installed | Delete the `.venv` folder and run the launcher again |
| macOS says it could not verify `run.command` (or, on macOS 14 and older, that it is from an unidentified developer) | The file came from a downloaded zip | System Settings, Privacy & Security, Open Anyway (macOS 14 and older: right-click, Open, Open). Or `bash run.command` in Terminal |
| `running scripts is disabled on this system` | PowerShell blocks `Activate.ps1` | `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`, or use Command Prompt |
| pip says `externally-managed-environment` | A Homebrew or system Python refuses installs | Use the launcher, or make a `.venv` by hand (sections 4.4 and 5.4) |
| `streamlit ... TOO OLD (needs 1.51 or newer)` | An old Streamlit is installed | Answer `y`, the runner upgrades it |
| `Port 8501 is already in use ... Trying the next one.` | A dashboard from earlier is still running | Nothing. The runner takes 8502. Stop the old one with Ctrl+C in its window |
| `Ports 8501 to 8510 are all in use.` | Ten old dashboards are running | Close their windows, or restart the computer |
| `Could not connect to ... Is the server running?` | Server off, wrong port, wrong password, or the database does not exist | Start the server, check the address, create the database (sections 4.5, 4.6, 5.5, 5.6) |
| `role "postgres" does not exist` (Mac) | Postgres.app and Homebrew use your Mac user name, not `postgres` | Put your Mac user name in the address |
| `These tables already hold rows` | The database was loaded before | Nothing is wrong. Use `database --reset` only if you want to start over |
| `duplicate key value violates unique constraint` (PostgreSQL) or `Duplicate entry ... for key` (MySQL) | `src.etl` was run twice by hand | Run the three SQL files again, then the ETL once. Or use `run.py database` |
| `Terminate batch job (Y/N)?` (Windows) | Ctrl+C reached the batch file as well | Type `N` so the batch file can finish; `Y` closes a double-clicked window at once |
| The window closes at once (Windows) | `run.py` was double-clicked instead of `run.bat` | Double-click `run.bat`, which waits for a key press before it closes |
| Streamlit asks for an e-mail | First start of `streamlit run` | Press Enter. `run.py` skips the question |

## 9. Where things end up

| Thing | Place |
| --- | --- |
| The project | The folder you cloned or unpacked |
| Packages | `.venv` inside the project, and nowhere else |
| Python itself | Wherever the installer put it: `/Library/Frameworks/Python.framework` or Homebrew on a Mac, `%LocalAppData%\Programs\Python` (standalone installer) or `%LocalAppData%\Python` (install manager) on Windows |
| Database servers | Postgres.app in Applications, Homebrew under `/opt/homebrew` or `/usr/local`, `C:\Program Files\PostgreSQL` and `C:\Program Files\MySQL` on Windows |
| Streamlit's settings | `~/.streamlit` on a Mac, `%UserProfile%\.streamlit` on Windows |

Apart from pip's download cache and the Streamlit settings folder in the table, the project writes nothing outside its own folder. pip keeps the downloaded packages in `~/Library/Caches/pip` on a Mac and `%LocalAppData%\pip\Cache` on Windows; `python -m pip cache purge` from inside the `.venv` empties it. Streamlit writes its settings folder only when you start it by hand as in sections 4.4 and 5.4.

## 10. What was checked

On a Mac on 22 September 2026, in a copy of the project whose path contains a space: `run.command` with only Python 3.9 on the PATH (refuses, exit 1); first run with Python 3.13 (makes `.venv`, `--help` works); second run (reuses `.venv`); a `.venv` made with 3.9 (refuses); a `.venv` whose Python was removed and a `.venv` without pip (both rebuilt); a link to `run.command` started from another folder (refuses); under a fake terminal: `check` with the closing pause, `test` with the install question answered `y` (21 passed), the dashboard with the install question answered `y`, Ctrl+C and the closing pause, and a second dashboard start with nothing to install. The PostgreSQL and MySQL steps of `run.py database` were run against temporary servers on 21 and 22 September; PROJECT_EXPLANATION.md section 10 has the list.

Not run: `run.bat` and every command in section 5. They follow the documentation of the tools and were reviewed by reading. The Homebrew and Postgres.app commands in section 4.5 and 4.6 were taken from the tools' own documentation and not run on this Mac, which has other database servers on those ports.
