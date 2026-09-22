# One file that runs the whole project.
#
#   python run.py             check packages and data, start the dashboard, open the browser
#   python run.py check       only report what is installed and which port is free
#   python run.py test        run the automated tests
#   python run.py database    build the tables in PostgreSQL or MySQL, load the CSV, compare totals
#   python run.py all         test, then database, then dashboard
#
# Pressing the Run button in VS Code is the same as the first line.

# Keep type hints as plain text, so newer hint syntax also works on older Python.
from __future__ import annotations

# Everything imported up here ships with Python itself. pandas, streamlit and the other
# project packages are only touched further down, after the runner has checked for them.
# That is why this file can start, and say what is missing, on a Python with nothing installed.
# argparse reads the word typed after "python run.py", such as test or database.
import argparse
# csv reads the data file without needing pandas.
import csv
# getpass asks for a password without showing it on screen.
import getpass
# importlib can make Python notice packages that were installed a moment ago.
import importlib
# importlib.util can tell whether a package is installed without importing it.
import importlib.util
# os gives access to environment variables and tells Windows apart from macOS and Linux.
import os
# re matches text against a pattern. It is used to check the DROP statements in the SQL files.
import re
# shlex writes a command the way a macOS or Linux shell expects it, quotes included.
import shlex
# signal lets the runner react when the terminal window is closed.
import signal
# socket is used to test whether a port is already taken.
import socket
# subprocess starts other programs: pip, pytest and Streamlit.
import subprocess
# sys knows which Python is running this file.
import sys
# time is used for short waits.
import time
# urllib.request asks the dashboard "are you up yet?".
import urllib.request
# webbrowser opens the dashboard in the default browser.
import webbrowser
# datetime turns the text 05-02-2010 into a real date.
from datetime import datetime
# Decimal adds money values without the tiny rounding errors that float has.
from decimal import Decimal, InvalidOperation
# Path builds file paths that work on Windows, macOS and Linux.
from pathlib import Path
# quote and quote_plus write special characters the way a URL needs them, for example @ as %40.
# unquote and unquote_plus turn that writing back into the plain characters.
from urllib.parse import quote, quote_plus, unquote, unquote_plus

# Tell Python not to write __pycache__ folders. It has to happen before anything from src/ is imported.
sys.dont_write_bytecode = True

# The folder this file sits in. Every other path is built from it, so the runner works
# no matter which folder the terminal happens to be in.
PROJECT = Path(__file__).resolve().parent
# The main data file.
CSV_PATH = PROJECT / "data" / "raw" / "walmart_real_sales.csv"
# The small receipt sample. Only the check action looks at it.
POS_CSV_PATH = PROJECT / "data" / "sample" / "walmart_sales_sample.csv"
# The eight columns the weekly CSV must have, in lowercase.
CSV_COLUMNS = ["store", "date", "weekly_sales", "holiday_flag", "temperature", "fuel_price", "cpi", "unemployment"]
# True on Windows. A few things work differently there.
IS_WINDOWS = os.name == "nt"
# One address for the dashboard: where it listens, its health check and the link that is printed.
# The port test looks at this address and at its IPv6 twin, see port_in_use().
HOST = "127.0.0.1"
# The dashboard takes the first free port from 8501 to 8510.
PORTS = range(8501, 8511)
# Environment variable that may hold the database address for runs where nobody can type.
ENV_NAME = "WALMART_DB_URL"
# The SQL files that build the database, in the order they must run.
# 04_analytics_queries.sql is a set of queries to run by hand, so it is left out on purpose.
SETUP_FILES = ("01_schema.sql", "02_indexes.sql", "03_views.sql")
# The six tables that 01_schema.sql drops and rebuilds.
PROJECT_TABLES = ("transaction_line_items", "transactions", "customers", "products", "stores", "weekly_store_sales")
# Packages the dashboard needs. The names are the ones used in "import ...".
DASHBOARD_NEEDS = ["pandas", "numpy", "streamlit", "plotly", "sqlalchemy"]
# Packages the tests need.
TEST_NEEDS = ["pandas", "numpy", "pytest"]
# The database driver depends on the kind of database. pymysql uses the cryptography package
# for some MySQL 8 logins, and fails with a confusing error when it is missing, so it is listed too.
DRIVER_NEEDS = {"postgres": ["psycopg2"], "mysql": ["pymysql", "cryptography"]}
# pip knows psycopg2 under a different name than the one used in "import psycopg2".
PIP_NAMES = {"psycopg2": "psycopg2-binary"}
# Address beginnings the runner accepts, and the kind of database each one means.
ACCEPTED_PREFIXES = {"postgresql+psycopg2://": "postgres", "postgresql://": "postgres", "mysql+pymysql://": "mysql"}
# Common wrong beginnings, with the right one to use.
PREFIX_FIXES = {"postgres://": "postgresql+psycopg2://", "mysql://": "mysql+pymysql://"}
# Signals that mean "please stop" on the systems that have them. SIGBREAK only exists on Windows.
STOP_SIGNALS = [getattr(signal, name) for name in ("SIGTERM", "SIGHUP", "SIGBREAK") if hasattr(signal, name)]
# Exit codes of Streamlit that only mean "stopped with Ctrl+C". The last one is how Windows reports it.
CTRL_C_CODES = (0, 130, -2, 0xC000013A)

# The only DROP statements the runner sends: "drop table" or "drop view", with or without
# "if exists", followed by one plain name. group(1) is the word table or view, group(2) is the name.
DROP_PATTERN = re.compile(r"drop\s+(table|view)\s+(?:if\s+exists\s+)?([a-z_][a-z0-9_]*)$", re.IGNORECASE)

# Shown whenever a database address cannot be used. It never repeats what was typed.
ADDRESS_HELP = (
    "That does not look like a database address I can use. It should look like one of these:\n"
    "  postgresql+psycopg2://postgres@localhost:5432/walmart_sales\n"
    "  mysql+pymysql://root@localhost:3306/walmart_sales"
)


# The one way to end early. code becomes the exit code and text is printed first.
class Stop(Exception):
    # Keep both values so main() can use them.
    def __init__(self, code: int, text: str) -> None:
        # Let Exception do its normal setup.
        super().__init__(text)
        # 1 means something failed. 2 means the user has to decide or fix something.
        self.code = code
        # The message for the user.
        self.text = text


# Raised by the signal handler below when the terminal window is closed or the runner is killed.
# It is a BaseException, like KeyboardInterrupt, so that no "except Exception" can swallow it by accident.
class StopRequested(BaseException):
    # pass means: do nothing. The class only needs its own name.
    pass


# Python calls this when one of STOP_SIGNALS arrives.
def on_stop_signal(signum, frame) -> None:
    # Turn the signal into an exception, so the normal clean-up code runs.
    raise StopRequested()


# All output goes through here.
def say(text: str = "") -> None:
    # Printing can fail in three ways. Each one is handled below.
    try:
        # flush=True shows the line at once, so it lands above Streamlit's own lines.
        print(text, flush=True)
    # The terminal cannot show one of the characters, for example an accented letter in a folder name.
    # This case has to come before ValueError, because UnicodeEncodeError is a kind of ValueError.
    except UnicodeEncodeError:
        # Print the line again with "?" in place of each such character.
        try:
            # encode(..., "replace") swaps what ASCII cannot hold for "?".
            print(text.encode("ascii", "replace").decode("ascii"), flush=True)
        # Give up on this one line.
        except (OSError, ValueError):
            pass
    # The terminal or the pipe on the other end is gone.
    except OSError:
        # Point the output at "nowhere". Without this, Python's own last write at exit fails too
        # and turns the exit code into 120.
        try:
            # os.devnull is the system's "nowhere" file. dup2 makes the output channel point at it.
            os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        # Nothing more can be done.
        except (OSError, ValueError, AttributeError):
            pass
    # The output was closed.
    except ValueError:
        pass


# True when a person can type an answer. False for pipes and for output panels without a keyboard.
def can_ask() -> bool:
    # sys.stdin is None when there is no input at all. A closed input raises ValueError on isatty().
    try:
        # isatty() is True when the input is a real terminal.
        return sys.stdin is not None and sys.stdin.isatty()
    # Treat every problem as "nobody can answer".
    except (AttributeError, ValueError):
        # Nobody can answer.
        return False


# The environment for programs this runner starts.
def child_env() -> dict:
    # Start from a copy of the current environment.
    env = dict(os.environ)
    # No __pycache__ folders from pytest or Streamlit.
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    # Show the child's output line by line, not in delayed blocks.
    env["PYTHONUNBUFFERED"] = "1"
    # The tests and the dashboard have no use for the database password.
    env.pop(ENV_NAME, None)
    # Hand the finished environment back.
    return env


# Turns a command list into text that can be pasted into a terminal.
def shown_command(parts: list) -> str:
    # macOS and Linux.
    if not IS_WINDOWS:
        # shlex.join adds quotes wherever bash or zsh need them.
        return shlex.join(parts)
    # Windows: double quotes around parts with a space or a character the shell would act on.
    quoted = ['"' + part + '"' if any(char in part for char in " <>=&|()'") else part for part in parts]
    # Join the parts with spaces.
    text = " ".join(quoted)
    # PowerShell needs "& " in front when the program path is in quotes.
    if quoted[0].startswith('"'):
        # Add it.
        text = "& " + text
    # The finished line.
    return text


# The command as an indented line, plus a note for the Windows shells that do not know "& ".
def command_lines(parts: list) -> str:
    # Four spaces make the command stand out.
    text = "    " + shown_command(parts)
    # Only PowerShell understands the "& " prefix.
    if text.startswith("    & "):
        # Tell users of the other Windows shells what to do.
        text += '\n    (In Command Prompt or Anaconda Prompt leave out the "& " at the start.)'
    # One or two lines.
    return text


# Returns the installed version of a package, or None when it is missing.
def package_version(module: str):
    # find_spec looks the package up without importing it.
    try:
        # None from find_spec means "not installed".
        found = importlib.util.find_spec(module) is not None
    # A half-removed package can raise here. Count it as missing.
    except (ImportError, ValueError):
        # Missing.
        found = False
    # Not installed.
    if not found:
        # None tells the caller that the package is missing.
        return None
    # importlib.metadata reads the version number that pip recorded.
    try:
        # Imported here because very old Python does not have it.
        import importlib.metadata as metadata
    # Very old Python has no importlib.metadata.
    except ImportError:
        # The package is there, only its version is unknown.
        return "installed"
    # Try the pip name first, then the import name.
    for name in (PIP_NAMES.get(module, module), module):
        # version() raises when it has no record under this name.
        try:
            # The version text, for example "2.2.3".
            return metadata.version(name)
        # No record under this name. Try the next one.
        except metadata.PackageNotFoundError:
            # On to the next name.
            continue
    # Installed, but no version on record.
    return "installed"


# Finds the line for one package in requirements.txt, for example "plotly>=5.20".
def requirement_text(pip_name: str) -> str:
    # Compare in lowercase, and treat "_" and "-" as the same.
    wanted = pip_name.lower().replace("_", "-")
    # Read the file. A missing file is fine, the plain name works too.
    try:
        # One list entry per line of the file.
        lines = (PROJECT / "requirements.txt").read_text(encoding="utf-8").splitlines()
    # The file is missing, cannot be read, or is not saved as UTF-8.
    except (OSError, UnicodeError):
        # The plain name works with pip too.
        return pip_name
    # Go through the file line by line.
    for line in lines:
        # Cut off the comment and the spaces around what is left.
        line = line.split("#", 1)[0].strip()
        # The package name ends at the first of these characters.
        name = line
        # Try each of those characters.
        for mark in "<>=!~[; ":
            # Keep only what stands before it.
            name = name.split(mark, 1)[0]
        # Found the line for this package.
        if name and name.lower().replace("_", "-") == wanted:
            # The whole line, version rule included.
            return line
    # Not listed. Use the plain name.
    return pip_name


# Turns version text into numbers that can be compared: "1.58.0" becomes (1, 58, 0).
def version_numbers(text: str) -> tuple:
    # re.findall picks out the groups of digits. Only the first three count.
    return tuple(int(part) for part in re.findall(r"\d+", text)[:3])


# The oldest version that requirements.txt allows for a package, for example "1.51". None when it names no such limit.
def oldest_allowed(module: str):
    # The line from requirements.txt, such as "streamlit>=1.51".
    line = requirement_text(PIP_NAMES.get(module, module))
    # Every limit in that file is written with ">=".
    if ">=" not in line:
        # No limit.
        return None
    # The text after ">=", up to a comma or a space if one follows.
    return line.split(">=", 1)[1].split(",")[0].split()[0]


# Says what is wrong with a package: "MISSING", "TOO OLD", or None when it is fine.
def package_problem(module: str):
    # None means not installed.
    version = package_version(module)
    # Not installed.
    if version is None:
        # The caller offers to install it.
        return "MISSING"
    # The oldest version that works, if requirements.txt names one.
    floor = oldest_allowed(module)
    # "installed" means the version is unknown, so there is nothing to compare.
    if floor and version != "installed" and version_numbers(version) < version_numbers(floor):
        # The caller offers to upgrade it.
        return "TOO OLD"
    # Nothing wrong.
    return None


# Prints one line per package and returns the ones that are missing or too old.
def show_packages(modules: list) -> list:
    # Collect the names that need attention here.
    missing = []
    # One line per package.
    for module in modules:
        # "MISSING", "TOO OLD" or None.
        problem = package_problem(module)
        # Not installed.
        if problem == "MISSING":
            # Remember it for the caller.
            missing.append(module)
            # ":<13" pads the name to 13 characters, so the columns line up.
            say(f"  {module:<13} MISSING")
        # Installed, but older than requirements.txt allows.
        elif problem == "TOO OLD":
            # Remember it for the caller.
            missing.append(module)
            # Show the version that is there and the one that is needed.
            say(f"  {module:<13} {package_version(module):<11} TOO OLD (needs {oldest_allowed(module)} or newer)")
        # Fine.
        else:
            # Name, version, and the word ok.
            say(f"  {module:<13} {package_version(module):<11} ok")
    # The names that need attention.
    return missing


# Makes sure the packages for one action are there. Offers to install what is missing.
# what is the start of the sentence shown to the user, such as "The dashboard".
def ensure_packages(what: str, modules: list) -> None:
    # Show the list of packages.
    missing = show_packages(modules)
    # Nothing missing.
    if not missing:
        # Done.
        return
    # The exact text to hand to pip, with the version rule from requirements.txt.
    specs = [requirement_text(PIP_NAMES.get(module, module)) for module in missing]
    # Use the Python that runs this file, so the packages land where they are needed.
    command = [sys.executable, "-m", "pip", "install"] + specs
    # Pick singular or plural words.
    one = len(missing) == 1
    # An empty line for readability.
    say()
    # Name what is missing.
    say(f"{what} cannot start yet: {'1 package is' if one else str(len(missing)) + ' packages are'} missing or too old ({', '.join(missing)}).")
    # Offer to install.
    say(f"I can install {'it' if one else 'them'} for you. This is the exact command I would run:")
    # The command, indented so it stands out.
    say(command_lines(command))
    # Say where the download comes from.
    say(f"It downloads {', '.join(missing)} (and the packages {'it needs' if one else 'they need'}) from pypi.org")
    # Say what gets changed and what does not.
    say("and adds them to the Python shown at the top. The project's own files are not changed.")
    # Without a keyboard there is nobody to say yes, so the answer is no.
    answer = ""
    # Nobody can type.
    if not can_ask():
        # Explain why no question follows.
        say("I cannot ask questions in this window.")
    # Somebody can type.
    else:
        # Wait for the answer. Closing the input counts as no.
        try:
            # input() shows the question and returns what was typed.
            answer = input("Install now? Type y and press Enter. Anything else means no: ")
        # The input was closed before an answer came.
        except EOFError:
            # Count it as no.
            answer = ""
    # Only y or yes installs.
    if answer.strip().lower() not in ("y", "yes"):
        # End the run and list what the user can do next.
        raise Stop(2, (
            "Nothing was installed.\n"
            "What to do next - pick one:\n"
            "  1. Run this file again in a terminal and answer y.\n"
            "  2. Or paste the command above into a terminal yourself, then run this file again.\n"
            "  3. Or, if another Python on your computer already has what is missing, select it in VS Code\n"
            "     (click the Python version at the bottom right) and run this file again.\n"
            "  4. Or start the project with run.command (Mac) or run.bat (Windows). They make a\n"
            "     project-local Python in the folder .venv, where installs are always allowed."
        ))
    # pip itself can be missing on some Python installs.
    if importlib.util.find_spec("pip") is None:
        # Show the command that adds pip.
        raise Stop(1, "This Python has no pip. Add it with:\n" + command_lines([sys.executable, "-m", "ensurepip", "--upgrade"]))
    # Run pip and let its output go straight to the terminal.
    result = subprocess.run(command, env=child_env())
    # pip prints its own reason when it fails.
    if result.returncode != 0:
        # End the run with the usual reasons. Some Pythons refuse installs on purpose (pip then says
        # "externally-managed-environment"), and a project-local Python is the way around that.
        raise Stop(1, (
            f"The install did not work (pip ended with code {result.returncode}). pip's own message above says why.\n"
            "The usual reasons are no internet connection, or a Python that does not allow installs.\n"
            "In the second case start the project with run.command (Mac) or run.bat (Windows) instead:\n"
            "they make a project-local Python in the folder .venv, where installs are always allowed."
        ))
    # Make Python notice the packages that were just added.
    importlib.invalidate_caches()
    # Check again.
    if [module for module in missing if package_problem(module)]:
        # Still not visible from this run. A fresh start will see it.
        raise Stop(2, "The install finished. Run this file once more.")
    # All there now.
    say("Installed. Carrying on.")


# Stops early when run.py was moved away from the rest of the project, or when the data file is gone.
def check_project_files() -> None:
    # app.py and the src folder must sit next to run.py.
    for needed in (PROJECT / "app.py", PROJECT / "src"):
        # One of them is not there.
        if not needed.exists():
            # Say where the runner looked.
            raise Stop(1, f"run.py must stay in the project's top folder, next to app.py. I looked in: {PROJECT}")
    # The data file has its own message, because the fix is a different one.
    if not CSV_PATH.exists():
        # Name the file and the script that can fetch it again.
        raise Stop(1, (
            "The data file is missing: data/raw/walmart_real_sales.csv\n"
            "Put it back, or download it again with: python -m src.download_dataset\n"
            "(that script needs the datasets package and an internet connection)"
        ))


# Reads text such as "1", "01" or "1.0" as the whole number 1. Raises ValueError for anything else.
def whole_number(text: str) -> int:
    # Decimal reads the text exactly. For junk it raises InvalidOperation, which the caller catches.
    value = Decimal(text)
    # "NaN" and "Infinity" are accepted by Decimal, and 1.5 is a number but not a whole one.
    if not value.is_finite() or value != value.to_integral_value():
        # Refuse.
        raise ValueError(text)
    # A normal Python whole number.
    return int(value)


# Reads the weekly CSV with the standard library only and returns the facts about it.
# The database check compares against these numbers. They do not come from pandas,
# so a mistake in the pandas code cannot hide itself.
def read_csv_facts() -> dict:
    # The file name as it is shown in messages.
    shown = "data/raw/walmart_real_sales.csv"
    # Reading fails with UnicodeDecodeError or csv.Error when the file is not UTF-8 text or not a proper CSV.
    try:
        # utf-8-sig also copes with files that Excel saved with a hidden marker at the start.
        with open(CSV_PATH, newline="", encoding="utf-8-sig") as handle:
            # DictReader gives each row as a dictionary keyed by column name.
            reader = csv.DictReader(handle)
            # Map lowercase names to the names as written in the file.
            actual = {name.strip().lower(): name for name in (reader.fieldnames or [])}
            # All eight columns must be there.
            absent = [column for column in CSV_COLUMNS if column not in actual]
            # At least one column is missing.
            if absent:
                # Name the missing columns.
                raise Stop(1, f"{shown} is missing these columns: {', '.join(absent)}")
            # Running totals.
            rows, total = 0, Decimal(0)
            # Sets keep each different value once.
            stores, flags, months = set(), set(), set()
            # The dates that could be read.
            dates = []
            # Becomes False when a date is not written day-month-year.
            dates_ok = True
            # Go through the file row by row.
            for row in reader:
                # reader.line_num is the line of the file that was just read.
                where = f"{shown}, line {reader.line_num}"
                # A line with too few values gets None as a value. Too many values land under the key None.
                if None in row or None in row.values():
                    # A cut-off last line is the usual cause.
                    raise Stop(1, f"{where}: this line does not have exactly {len(reader.fieldnames)} values.")
                # Count the row.
                rows += 1
                # "1", "01" and "1.0" all mean store 1, the same way the project's loader reads them.
                try:
                    # Remember the store number.
                    stores.add(whole_number(row[actual["store"]].strip()))
                # Not a whole number.
                except (InvalidOperation, ValueError):
                    # "from None" hides the inner error.
                    raise Stop(1, f"{where}: the store number is not a whole number.") from None
                # An empty holiday flag counts as 0. src/transform.py has the same rule.
                try:
                    # Remember the flag.
                    flags.add(whole_number(row[actual["holiday_flag"]].strip() or "0"))
                # Not a whole number.
                except (InvalidOperation, ValueError):
                    # Stop with the line number.
                    raise Stop(1, f"{where}: the holiday flag is not a whole number.") from None
                # Read the sales value.
                try:
                    # Decimal keeps every cent exact.
                    value = Decimal(row[actual["weekly_sales"]].strip())
                # The text is not a number.
                except InvalidOperation:
                    # Stop with the line number.
                    raise Stop(1, f"{where}: the sales value is not a number.") from None
                # Decimal accepts "NaN" and "Infinity", but those are not amounts of money.
                if not value.is_finite():
                    # Same message as for other junk.
                    raise Stop(1, f"{where}: the sales value is not a number.")
                # Add it to the total.
                total += value
                # The bundled file writes 05-02-2010 for 5 February 2010.
                try:
                    # strptime reads the text with the pattern day-month-year.
                    day = datetime.strptime(row[actual["date"]].strip(), "%d-%m-%Y").date()
                    # Keep the date.
                    dates.append(day)
                    # Keep its year and month as a pair.
                    months.add((day.year, day.month))
                # A file in another date style still counts. Only the date checks get skipped.
                except ValueError:
                    # Remember that the dates cannot be trusted.
                    dates_ok = False
    # Not UTF-8 text, or broken in a way the csv module refuses.
    except (UnicodeDecodeError, csv.Error):
        # Say what kind of file is expected.
        raise Stop(1, f"{shown} cannot be read. It has to be a comma-separated text file saved as UTF-8.") from None
    # A header with nothing under it.
    if rows == 0:
        # An empty table would make every later check pass with 0 equal to 0.
        raise Stop(1, f"{shown} has a header but no rows.")
    # Hand everything back in one dictionary.
    return {
        # Number of data rows.
        "rows": rows,
        # Number of different stores.
        "stores": len(stores),
        # All sales added up.
        "total": total,
        # Number of different holiday flags, normally 2.
        "flags": len(flags),
        # Number of different months.
        "months": len(months),
        # Earliest week, or None when the dates could not be read.
        "first": min(dates) if dates and dates_ok else None,
        # Latest week, or None.
        "last": max(dates) if dates and dates_ok else None,
    }


# Prints the three header lines.
def show_header() -> None:
    # Title.
    say("Walmart Sales - project runner")
    # This is the Python that runs everything below. No other Python is looked for.
    say(f"Python  : {sys.executable}  (version {sys.version_info[0]}.{sys.version_info[1]}.{sys.version_info[2]})")
    # The project folder.
    say(f"Project : {PROJECT}")
    # An empty line.
    say()


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------


# True when something already listens on the port.
def port_in_use(port: int) -> bool:
    # Try the IPv4 and the IPv6 form of "this computer".
    for host in ("127.0.0.1", "::1"):
        # A connection that works means somebody is there.
        try:
            # Connect, then close again at once.
            socket.create_connection((host, port), timeout=0.5).close()
            # Somebody answered, so the port is taken.
            return True
        # Refused or timed out: nobody on this one.
        except OSError:
            pass
    # Nobody answered on either address.
    return False


# The first free port, or None when all ten are taken.
def first_free_port():
    # Try 8501, then 8502, and so on.
    for port in PORTS:
        # Free.
        if not port_in_use(port):
            # Use this one.
            return port
    # All ten are taken.
    return None


# True once the dashboard answers on its health page.
def dashboard_is_healthy(port: int) -> bool:
    # The empty ProxyHandler keeps a company proxy out of a call to this computer.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    # Any problem just means "not ready yet".
    try:
        # Streamlit answers on this page as soon as it is up.
        with opener.open(f"http://{HOST}:{port}/_stcore/health", timeout=2) as reply:
            # 200 is the web's code for "fine".
            return reply.status == 200
    # Connection refused, timeout, broken reply and so on.
    except Exception:
        # Not ready yet.
        return False


# False on a Linux machine without a desktop, for example over SSH. There Python would start a
# text browser inside this terminal, and the runner would hang until that browser is closed.
def has_desktop() -> bool:
    # macOS and Windows always have a way to open a page.
    if not sys.platform.startswith("linux"):
        # Nothing to check.
        return True
    # On Linux one of these variables is set when a desktop or a chosen browser exists.
    return any(os.environ.get(name) for name in ("DISPLAY", "WAYLAND_DISPLAY", "BROWSER"))


# Waits until the child program has ended, but no longer than the given seconds.
def wait_until_gone(proc, seconds: float) -> None:
    # time.monotonic() is a clock that never jumps backwards.
    deadline = time.monotonic() + seconds
    # poll() is None while the program is still running.
    while proc.poll() is None and time.monotonic() < deadline:
        # Look again in a fifth of a second.
        time.sleep(0.2)


# Stops Streamlit: first politely, then firmly.
def stop_child(proc, child_got_ctrl_c: bool) -> None:
    # A second stop signal must not interrupt the clean-up.
    for sig in STOP_SIGNALS:
        # SIG_IGN means "ignore this signal from now on".
        signal.signal(sig, signal.SIG_IGN)
    # The polite part.
    try:
        # Ctrl+C in a terminal reaches Streamlit too. Give it 5 seconds to close by itself.
        if child_got_ctrl_c:
            # Wait for it.
            wait_until_gone(proc, 5)
        # Still running: ask it to end. On Windows terminate() is already the hard way, see below.
        if proc.poll() is None and not IS_WINDOWS:
            # Send the "please end" signal.
            proc.terminate()
            # Give it 5 seconds.
            wait_until_gone(proc, 5)
    # A second Ctrl+C means "stop waiting".
    except KeyboardInterrupt:
        pass
    # Still running: end it for good.
    if proc.poll() is None:
        # On Windows python.exe inside a venv is only a launcher, so end the whole process tree.
        if IS_WINDOWS:
            # /T ends the child processes too, /F forces it.
            subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True)
        # macOS and Linux.
        else:
            # kill() cannot be ignored by the child.
            proc.kill()
        # Wait until it is really gone.
        wait_until_gone(proc, 10)


# Starts Streamlit, opens the browser and waits until the user stops it. Returns the exit code.
def run_dashboard(open_browser: bool = True) -> int:
    # Nothing from here on needs the database address. Remove it, so that the browser helper,
    # which cannot be given a cleaned environment, does not inherit the password.
    os.environ.pop(ENV_NAME, None)
    # React to a closed terminal window the same way as to Ctrl+C.
    for sig in STOP_SIGNALS:
        # A signal that arrives set to "ignore" stays that way. That is how nohup keeps a program alive.
        if signal.getsignal(sig) is not signal.SIG_IGN:
            # From now on this signal calls on_stop_signal.
            signal.signal(sig, on_stop_signal)
    # Try the ports in order.
    for port in PORTS:
        # Whatever already listens there is left alone. It might be somebody else's work.
        if port_in_use(port):
            # Say so.
            say(f"Port {port} is already in use (maybe a dashboard you started earlier). Trying the next one.")
            # On to the next port.
            continue
        # The address the user will open.
        link = f"http://{HOST}:{port}"
        # "sys.executable -m streamlit" uses this Python, not whatever "streamlit" the terminal would find.
        # headless skips Streamlit's first-run e-mail question. This runner opens the browser itself.
        command = [
            sys.executable, "-m", "streamlit", "run", str(PROJECT / "app.py"),
            "--server.headless", "true",
            "--server.address", HOST,
            "--server.port", str(port),
            "--browser.gatherUsageStats", "false",
        ]
        # No child yet.
        proc = None
        # Everything from here on is watched, so Streamlit gets stopped whatever happens.
        try:
            # cwd matters: app.py opens data/raw/... relative to the project folder.
            proc = subprocess.Popen(command, cwd=str(PROJECT), env=child_env())
            # Note the start time. ready turns True once the health page answers.
            started, ready = time.monotonic(), False
            # Keep asking while Streamlit runs, is not ready, and 90 seconds are not over.
            while proc.poll() is None and not ready and time.monotonic() - started < 90:
                # Ask the health page.
                ready = dashboard_is_healthy(port)
                # Short pause before the next try.
                time.sleep(0.3)
            # Streamlit ended before it was ready.
            if proc.poll() is not None:
                # Another program took the port in the split second after the test.
                if port_in_use(port):
                    # Try the next port.
                    continue
                # A real failure. Streamlit printed the reason itself.
                say(f"The dashboard could not start (exit code {proc.returncode}). The reason is in the lines above.")
                # 1 means failed.
                return 1
            # An empty line after Streamlit's own start-up lines.
            say()
            # The link, or a note when the 90 seconds ran out while Streamlit is still starting.
            say(f"Dashboard is running: {link}" if ready else f"Still starting. Open this yourself in a moment: {link}")
            # How to stop it.
            say("Leave this window open. To stop the dashboard, click here and press Ctrl+C.")
            # Where to find the other actions.
            say("More    : python run.py --help   (check, test, database, all)")
            # Open the page once. webbrowser.open returns False when it found no browser.
            if ready and open_browser and not (has_desktop() and webbrowser.open(link)):
                # The user can still open the link by hand.
                say("I could not open a browser. Open the address above yourself.")
            # Wait until Streamlit ends.
            while proc.poll() is None:
                # Short sleeps keep Ctrl+C quick on Windows.
                time.sleep(0.5)
            # Streamlit ended without anyone pressing Ctrl+C in this window.
            if proc.returncode not in CTRL_C_CODES:
                # Point at Streamlit's own message.
                say(f"The dashboard ended by itself (exit code {proc.returncode}). The reason is in the lines above.")
                # 1 means failed.
                return 1
            # A normal end.
            return 0
        # Ctrl+C, or a stop signal from outside.
        except (KeyboardInterrupt, StopRequested) as why:
            # A child exists.
            if proc is not None:
                # Only a real Ctrl+C reached Streamlit as well.
                stop_child(proc, child_got_ctrl_c=isinstance(why, KeyboardInterrupt))
            # An empty line after the ^C that the terminal prints.
            say()
            # Confirm that nothing is left, when that is the case.
            say("Dashboard stopped. Nothing is left running." if proc is None or proc.poll() is not None else "Dashboard stopped.")
            # Stopping on purpose counts as success.
            return 0
        # Runs on every way out of the try block, so Streamlit never stays behind.
        finally:
            # A child exists and still runs.
            if proc is not None and proc.poll() is None:
                # It received no Ctrl+C on this path, so skip the first wait.
                stop_child(proc, child_got_ctrl_c=False)
    # All ten ports were taken.
    say("Ports 8501 to 8510 are all in use. Stop an old dashboard (Ctrl+C in its terminal), then run this again.")
    # 1 means failed.
    return 1


# The default action: packages, data file, dashboard.
def action_dashboard(open_browser: bool) -> int:
    # Step 1 heading.
    say("[1/3] Packages the dashboard needs")
    # Stops the run when a package is missing and the user does not want it installed.
    ensure_packages("The dashboard", DASHBOARD_NEEDS)
    # Step 2 heading.
    say("[2/3] Data file")
    # The row count is reported, not compared with 6,435, because download_dataset.py may replace the file.
    facts = read_csv_facts()
    # ":," adds the thousands comma.
    say(f"  data/raw/walmart_real_sales.csv   ok ({facts['rows']:,} rows)")
    # Step 3 heading.
    say("[3/3] Starting the dashboard")
    # Runs until the user stops it.
    return run_dashboard(open_browser)


# ---------------------------------------------------------------------------
# Tests and check
# ---------------------------------------------------------------------------


# Runs pytest with the Python that runs this file.
def action_test() -> int:
    # Heading.
    say("Packages the tests need")
    # pandas, numpy and pytest.
    ensure_packages("The tests", TEST_NEEDS)
    # Heading.
    say("Running the tests")
    # -q keeps the output short. "-p no:cacheprovider" stops pytest from creating a .pytest_cache folder.
    command = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", str(PROJECT / "tests")]
    # cwd matters here too: "python -m pytest" finds the src package through the current folder.
    return 1 if subprocess.run(command, cwd=str(PROJECT), env=child_env()).returncode else 0


# A report that changes nothing, asks nothing and starts nothing.
def action_check() -> int:
    # Heading.
    say("Packages the dashboard needs")
    # Only these five decide whether the dashboard can start.
    missing = show_packages(DASHBOARD_NEEDS)
    # Heading.
    say("Only needed for: python run.py test")
    # pytest.
    show_packages(["pytest"])
    # Heading.
    say("Only needed for: python run.py database  (one driver is enough)")
    # The PostgreSQL driver, the MySQL driver and its helper.
    show_packages(["psycopg2", "pymysql", "cryptography"])
    # Heading.
    say("Data files")
    # Stops with a message when the weekly file is broken.
    facts = read_csv_facts()
    # Rows and stores of the weekly file.
    say(f"  data/raw/walmart_real_sales.csv       ok ({facts['rows']:,} rows, {facts['stores']} stores)")
    # The sample file only has to exist.
    say(f"  data/sample/walmart_sales_sample.csv  {'ok' if POS_CSV_PATH.exists() else 'MISSING'}")
    # Heading.
    say("Port")
    # None when all ten ports are taken.
    port = first_free_port()
    # Name the port, or say that none is free.
    say(f"  The dashboard would use port {port}." if port else "  Ports 8501 to 8510 are all in use.")
    # An empty line.
    say()
    # Ready means: nothing missing and a port to use.
    ready = not missing and port is not None
    # The verdict in one line.
    say("Ready. Start the dashboard with: python run.py" if ready else "Not ready yet. Run python run.py and it will offer to fix what is missing.")
    # 0 when ready, 1 when not.
    return 0 if ready else 1


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------


# Replaces every secret in a message with ****.
def scrub(message: str, secrets: list) -> str:
    # The list is sorted longest first, so no half of a password is left over.
    for secret in secrets:
        # Swap this form of the secret for four stars.
        message = message.replace(secret, "****")
    # The cleaned message.
    return message


# Every form in which the password could show up in an error message.
def secret_forms(raw_address: str, password) -> list:
    # The password as it was typed inside the address: the text between the first ":" and the last "@".
    typed = raw_address.partition("://")[2].rpartition("@")[0].partition(":")[2]
    # The plain form plus three ways of writing special characters in a URL.
    forms = {
        form
        for secret in (password or "", typed)
        for form in (secret, unquote(secret), quote(secret, safe=""), quote_plus(secret))
        if form
    }
    # The whole address is secret as well when it carries a password.
    whole = [raw_address] if typed else []
    # A one-letter password would also mask harmless text. Too much masking is the safe direction.
    return whole + sorted(forms, key=len, reverse=True)


# The first line of an error message, with secrets removed.
def first_line(problem: Exception, secrets: list) -> str:
    # Split the message into lines. An empty message gets a placeholder.
    lines = str(problem).splitlines() or ["unknown error"]
    # PostgreSQL can report one line per address it tried. The line with FATAL is the server's own answer.
    # Without such a line the first line is shown. The later lines of database errors can be long.
    chosen = next((line for line in reversed(lines) if "FATAL:" in line), lines[0])
    # Without spaces around it, and with secrets removed.
    return scrub(chosen.strip(), secrets)


# Gets the database address: from the environment variable, or by asking.
# Returns the address and whether it was typed just now.
def get_address():
    # Look in the environment first. A missing variable counts as empty text.
    raw = os.environ.get(ENV_NAME, "").strip()
    # The variable is set.
    if raw:
        # Say where the address came from, but not what it is.
        say(f"Database address: taken from the {ENV_NAME} environment variable.")
        # False means: not typed just now, so no password question follows.
        return raw, False
    # Nobody can type, and the variable is not set.
    if not can_ask():
        # Show how to set the variable on both kinds of system.
        raise Stop(2, (
            "I need a database address and cannot ask for it in this window.\n"
            f"Run this in a terminal, or set {ENV_NAME} first:\n"
            f"  macOS or Linux : export {ENV_NAME}='postgresql+psycopg2://USER:PASSWORD@localhost:5432/walmart_sales'\n"
            f"  PowerShell     : $env:{ENV_NAME}='postgresql+psycopg2://USER:PASSWORD@localhost:5432/walmart_sales'\n"
            f"  Command Prompt : set \"{ENV_NAME}=postgresql+psycopg2://USER:PASSWORD@localhost:5432/walmart_sales\""
        ))
    # Explain what to type.
    say("Type the database address WITHOUT the password. The password is asked for next, hidden.")
    # Example for PostgreSQL.
    say("  PostgreSQL : postgresql+psycopg2://postgres@localhost:5432/walmart_sales")
    # Example for MySQL.
    say("  MySQL      : mysql+pymysql://root@localhost:3306/walmart_sales")
    # Read the address.
    try:
        # strip() removes spaces typed by accident.
        raw = input("Address: ").strip()
    # The input was closed.
    except EOFError:
        # Count it as nothing typed.
        raw = ""
    # Nothing typed.
    if not raw:
        # 2 means the user has to act.
        raise Stop(2, "No address given. Nothing was changed.")
    # True means: typed just now, so the password question follows.
    return raw, True


# "postgres" or "mysql", decided from the start of the address. sqlalchemy is not needed for this.
def backend_of(raw_address: str) -> str:
    # Go through the accepted beginnings.
    for prefix, backend in ACCEPTED_PREFIXES.items():
        # The address starts with this one.
        if raw_address.startswith(prefix):
            # The kind of database it means.
            return backend
    # A well-known wrong beginning gets a precise hint.
    for wrong, right in PREFIX_FIXES.items():
        # The address starts with the wrong form.
        if raw_address.startswith(wrong):
            # Name the right form.
            raise Stop(2, f"The address has to start with {right}")
    # Anything else gets the general help text.
    raise Stop(2, ADDRESS_HELP)


# Turns the address into a URL object, asks for the password and tests the connection.
# Returns a dictionary with everything the later steps need.
def open_database() -> dict:
    # The address, and whether it was typed just now.
    raw, typed_now = get_address()
    # With two "@" signs SQLAlchemy would read part of the password as the host name and print it.
    if raw.partition("://")[2].count("@") > 1:
        # Refuse, and say how to write an @ inside a password.
        raise Stop(2, "The address has more than one @ sign. Inside a password, write @ as %40.")
    # postgres or mysql.
    backend = backend_of(raw)
    # Heading.
    say("Packages the database step needs")
    # pandas and sqlalchemy for loading, plus the driver for this kind of database.
    ensure_packages("The database step", ["pandas", "sqlalchemy"] + DRIVER_NEEDS[backend])
    # Safe to import now. create_engine sets up the connection.
    from sqlalchemy import create_engine
    # make_url splits an address into user, password, host, port and database.
    from sqlalchemy.engine import make_url
    # make_url errors can repeat the whole address, so the error text is never shown.
    try:
        # Build the URL object.
        url = make_url(raw)
    # The address could not be read.
    except Exception:
        # Show the examples, and hide the inner error with "from None".
        raise Stop(2, ADDRESS_HELP) from None
    # No database name after the last "/".
    if not url.database:
        # Say what is missing.
        raise Stop(2, "The address has no database name at the end, such as /walmart_sales.")
    # The password as it is written inside the address: the text between the first ":" and the last "@".
    written = raw.partition("://")[2].rpartition("@")[0].partition(":")[2]
    # SQLAlchemy must have read the same password. If it did not, the address was split in the wrong
    # place, and a piece of the password could show up as the host or the database name.
    if (url.password or "") not in (unquote(written), unquote_plus(written)):
        # Refuse without repeating anything that was typed.
        raise Stop(2, ADDRESS_HELP)
    # The password that came inside the address, if any.
    password = url.password
    # Ask for the password when the address was typed without one.
    if password is None and typed_now:
        # Ctrl+D at the prompt closes the input.
        try:
            # getpass hides the typing. Enter alone gives "", which "or None" turns into None.
            password = getpass.getpass("Password (typing stays hidden, Enter for none): ") or None
        # The input was closed.
        except EOFError:
            # 2 means the user decided.
            raise Stop(2, "No password given. Nothing was changed.") from None
        # A password was typed.
        if password:
            # set() puts the password in as it is. Characters like @ or / need no special writing this way.
            url = url.set(password=password)
    # The target in plain words, built from the parts. The address itself is never printed.
    kind = "PostgreSQL" if backend == "postgres" else "MySQL"
    # The port from the address, or the usual one for this kind of database.
    port = url.port or (5432 if backend == "postgres" else 3306)
    # User, host, database and port are public. They are shown on purpose.
    public = [str(part) for part in (url.username, url.host, url.database, port) if part]
    # Every form of the password that has to stay off the screen. A form that is also part of a public
    # word is left out: masking the user name "postgres" would tell everyone that it is the password too.
    secrets = [secret for secret in secret_forms(raw, password) if not any(secret in part for part in public)]
    # Kind, database, host, port and user.
    label = f'{kind} database "{url.database}" on {url.host or "localhost"}:{port} as user {url.username or "(none)"}'
    # Show the target before anything is done to it.
    say(f"Target  : {label}")
    # Give up after 10 seconds when the server does not answer.
    engine = create_engine(url, connect_args={"connect_timeout": 10})
    # A tiny query proves that server, database, user and password all work.
    try:
        # "with" closes the connection again.
        with engine.connect() as conn:
            # exec_driver_sql sends the text to the database as it is.
            conn.exec_driver_sql("select 1")
    # pymysql can only send passwords made of Latin-1 characters. Its error names the character
    # and its position, which would give part of the password away, so a fixed sentence is shown.
    except UnicodeError:
        # 1 means failed.
        raise Stop(1, "The password holds a character that the database driver cannot send. Use a password made of plain letters, digits and signs.") from None
    # Any other problem while connecting.
    except Exception as problem:
        # First line of the driver's message, password removed.
        reason = first_line(problem, secrets)
        # The message: what failed, why, and the three usual causes.
        lines = [f"Could not connect to {label}.", "  " + reason, "Is the server running? Does the database exist? Is the password right?"]
        # A missing database gets the fix spelled out. The two texts are how PostgreSQL and MySQL put it.
        if ('database "' in reason and "does not exist" in reason) or "Unknown database" in reason:
            # The one SQL line that creates the database.
            lines.append(f"run.py does not create databases. Create it on the server with: CREATE DATABASE {url.database};")
        # PostgreSQL uses almost the same words when the user name is unknown.
        elif 'role "' in reason and "does not exist" in reason:
            # Point at the user name, not at the database.
            lines.append("The server has no user with that name. Check the user name in the address.")
        # 1 means failed.
        raise Stop(1, "\n".join(lines)) from None
    # The server's version as numbers, such as (8, 4, 11). Empty when unknown.
    version = engine.dialect.server_version_info or ()
    # The ranking view uses window functions, which MySQL only has from version 8.0.
    if backend == "mysql" and version and version[0] < 8:
        # Stop before anything is built.
        raise Stop(1, "This MySQL server is older than 8.0. The views in sql/mysql need 8.0 or newer.")
    # Everything the database action needs, in one dictionary.
    return {"engine": engine, "url": url, "label": label, "secrets": secrets, "backend": backend}


# Cuts the text of a SQL file into single statements.
# The comments in the sql/ files contain semicolons and quotes, so cutting at every ";" would be wrong.
# When the text holds something this function does not understand, it stops with the line number.
def split_sql(text: str, name: str) -> list:
    # Builds the error with file name and line number. at is the position in the text.
    def fail(why: str, at: int):
        # chr(10) is the line break. Counting the breaks before the position gives the line number.
        raise ValueError(f"{name}, line {text.count(chr(10), 0, at) + 1}: {why}")

    # statements collects the results. buf collects the characters of the current statement.
    statements, buf = [], []
    # i is the position in the text, n is its length.
    i, n = 0, len(text)
    # Walk through the text from start to end.
    while i < n:
        # The current character, and the current two characters.
        ch, two = text[i], text[i:i + 2]
        # Comments are tested FIRST, because they may hold ; ' and ".
        if two == "--":
            # "--x" is a comment in PostgreSQL but means "minus minus x" in MySQL.
            if text[i + 2:i + 3].strip():
                # Refuse to guess.
                fail('write a space after "--"', i)
            # Find the end of the line.
            j = text.find("\n", i)
            # Jump there. -1 means the comment runs to the end of the file.
            i = n if j == -1 else j
        # A /* ... */ comment.
        elif two == "/*":
            # Find where it closes.
            j = text.find("*/", i + 2)
            # It never closes.
            if j == -1:
                # Stop with the line number.
                fail("a /* comment is never closed", i)
            # PostgreSQL allows a comment inside a comment and MySQL does not, so the end would be a guess.
            if "/*" in text[i + 2:j]:
                # Refuse to guess.
                fail("a /* comment inside another /* comment is not supported", i)
            # A space keeps the words on both sides apart.
            buf.append(" ")
            # Continue after the closing */.
            i = j + 2
        # Quoted text is copied as it is, so '%Y-%m-01' arrives unchanged.
        elif ch in "'\"`":
            # Find the closing quote of the same kind.
            j = text.find(ch, i + 1)
            # A doubled quote inside quoted text is an escaped quote, not the end.
            while j != -1 and text[j:j + 2] == ch * 2:
                # Keep looking after it.
                j = text.find(ch, j + 2)
            # No closing quote.
            if j == -1:
                # Stop with the line number.
                fail("a quote is never closed", i)
            # MySQL and PostgreSQL read backslashes differently.
            if "\\" in text[i:j + 1]:
                # Refuse to guess.
                fail("a backslash inside quoted text is not supported", i)
            # Copy the quoted text, quotes included.
            buf.append(text[i:j + 1])
            # Continue after the closing quote.
            i = j + 1
        # In MySQL "#" starts a comment, in PostgreSQL it is part of some operators.
        elif ch == "#":
            # The project's SQL uses "-- " for comments, so refuse.
            fail('"#" is not supported here (in MySQL it starts a comment). Write "-- " for comments', i)
        # $$ ... $$ blocks hold semicolons that must not split the statement.
        elif ch == "$":
            # The project's SQL has none, so refuse.
            fail("dollar-quoted SQL is not supported", i)
        # A semicolon outside comments and quotes ends the statement.
        elif ch == ";":
            # Store the finished statement without spaces around it.
            statements.append("".join(buf).strip())
            # Start a new statement and step over the semicolon.
            buf, i = [], i + 1
        # Any other character belongs to the current statement.
        else:
            # Keep it.
            buf.append(ch)
            # Next character.
            i += 1
    # Whatever follows the last semicolon.
    statements.append("".join(buf).strip())
    # Leave out empty pieces.
    return [statement for statement in statements if statement]


# Reads and checks all three setup files BEFORE anything is sent to the database.
def read_setup_statements(sql_dir: Path) -> list:
    # One entry per statement: file name, number inside the file, SQL text.
    plan = []
    # 01, then 02, then 03.
    for name in SETUP_FILES:
        # The whole file as one text. utf-8-sig skips the hidden marker that Windows Notepad puts at the start.
        text = (sql_dir / name).read_text(encoding="utf-8-sig")
        # Number the statements from 1, so error messages can point at one.
        for number, statement in enumerate(split_sql(text, name), 1):
            # The first word of the statement, in lowercase.
            first_word = statement.split(None, 1)[0].lower()
            # The setup files only drop and create things. Anything else is refused.
            if first_word not in ("drop", "create"):
                # Show the first 40 characters of the statement.
                raise ValueError(f"{name}, statement {number}: run.py only runs DROP and CREATE, not: {statement[:40]} ...")
            # A DROP gets a closer look, because the row counts shown to the user only cover the six project tables.
            if first_word == "drop":
                # Put the statement on one line and hold it against the pattern.
                match = DROP_PATTERN.match(" ".join(statement.split()))
                # Refuse "drop database", "drop schema" and the like, and any table outside the fixed list.
                if match is None or (match.group(1).lower() == "table" and match.group(2).lower() not in PROJECT_TABLES):
                    # Say how to add a table the right way.
                    raise ValueError(f"{name}, statement {number}: run.py only drops views and the six project tables. To add a table, also add its name to PROJECT_TABLES in run.py.")
            # Accepted.
            plan.append((name, number, statement))
    # The full list, in running order.
    return plan


# Sends the setup statements to the database.
def run_setup(engine, plan: list, secrets: list) -> None:
    # One connection for all statements.
    with engine.connect() as conn:
        # no_parameters=True hands the text to the driver as it is.
        # Without it pymysql would treat the % in '%Y-%m-01' as a place for a value and fail.
        conn = conn.execution_options(no_parameters=True)
        # One transaction for all three files. When a statement fails, PostgreSQL undoes the earlier drops.
        # MySQL cannot undo drops. There the next run finds empty tables and builds them again.
        with conn.begin():
            # In file order.
            for name, number, statement in plan:
                # Send one statement.
                try:
                    # As it is, with no values filled in.
                    conn.exec_driver_sql(statement)
                # The database refused it.
                except Exception as problem:
                    # The first 50 characters of the statement, on one line.
                    short = " ".join(statement.split())[:50]
                    # Say which file and statement, and give the database's reason.
                    raise Stop(1, f"{name} stopped at statement {number} ({short} ...)\n  {first_line(problem, secrets)}") from None


# Row count for each of the six project tables. None means the table does not exist.
def table_counts(engine) -> dict:
    # inspect() can answer questions about the database, such as "is there a table called x?".
    from sqlalchemy import inspect
    # The object that answers them.
    inspector = inspect(engine)
    # Table name to row count.
    counts = {}
    # One connection for all six counts.
    with engine.connect() as conn:
        # The six tables that 01_schema.sql would drop.
        for table in PROJECT_TABLES:
            # The table names come from the fixed list above, never from user input.
            counts[table] = conn.exec_driver_sql(f"select count(*) from {table}").scalar() if inspector.has_table(table) else None
    # The counts.
    return counts


# Rows, stores, total, first and last week as the database sees them.
def database_facts(engine) -> dict:
    # One query gets all five numbers.
    with engine.connect() as conn:
        # .one() returns the single result row.
        row = conn.exec_driver_sql(
            "select count(*), count(distinct store), sum(weekly_sales), min(date), max(date) from weekly_store_sales"
        ).one()
    # An empty table has no sum. Count that as 0. Decimal(str(...)) works for every number type a driver may return.
    return {"rows": row[0], "stores": row[1], "total": Decimal(str(row[2] or 0)), "first": row[3], "last": row[4]}


# True when both money values are the same to the cent.
def same_money(left: Decimal, right: Decimal) -> bool:
    # One cent.
    cent = Decimal("0.01")
    # quantize rounds to two decimals.
    return left.quantize(cent) == right.quantize(cent)


# Compares the database with the CSV and prints one line per check. Returns the exit code.
def verify(engine, facts: dict, secrets: list) -> int:
    # Heading.
    say("Checking the database against the CSV")
    # Column titles. ":<26" pads to the left, ":>18" pads to the right.
    say(f"  {'what':<26} {'CSV':>18} {'database':>18}")
    # Each entry: name, value from the CSV, value from the database, and whether they agree.
    checks = []
    # Read the numbers from the database.
    try:
        # Rows, stores, total, first and last week.
        found = database_facts(engine)
    # The table is missing or cannot be read.
    except Exception as problem:
        # Say why, with the password removed.
        say("  could not read weekly_store_sales: " + first_line(problem, secrets))
        # 1 means failed.
        return 1
    # Row count.
    checks.append(("rows", f"{facts['rows']:,}", f"{found['rows']:,}", facts["rows"] == found["rows"]))
    # Number of stores.
    checks.append(("stores", str(facts["stores"]), str(found["stores"]), facts["stores"] == found["stores"]))
    # Total sales, compared to the cent.
    checks.append(("total sales", f"{facts['total']:,.2f}", f"{found['total']:,.2f}", same_money(facts["total"], found["total"])))
    # The dates of the CSV could not be read.
    if facts["first"] is None:
        # Nothing to compare.
        checks.append(("first and last week", "skipped", "skipped", True))
    # The date checks catch a day and month swap, which would leave counts and totals unchanged.
    else:
        # [:10] keeps the date part, in case a driver adds a time.
        checks.append(("first week", str(facts["first"]), str(found["first"])[:10], str(facts["first"]) == str(found["first"])[:10]))
        # The same for the last week.
        checks.append(("last week", str(facts["last"]), str(found["last"])[:10], str(facts["last"]) == str(found["last"])[:10]))
    # Each view must exist and have the expected number of rows: months, stores, holiday flags.
    expected_view_rows = [("vw_monthly_sales", facts["months"]), ("vw_store_rankings", facts["stores"]), ("vw_holiday_uplift", facts["flags"])]
    # One connection for the view checks.
    with engine.connect() as conn:
        # One view at a time.
        for view, expected in expected_view_rows:
            # No month count is known when the dates could not be read.
            if view == "vw_monthly_sales" and facts["first"] is None:
                # Skip this view.
                continue
            # Count the rows of the view.
            try:
                # The view names come from the fixed list above.
                got = conn.exec_driver_sql(f"select count(*) from {view}").scalar()
                # Compare with the expected count.
                checks.append((f"rows in {view}", str(expected), str(got), expected == got))
            # The view does not exist.
            except Exception:
                # Record it as a difference.
                checks.append((f"rows in {view}", str(expected), "view missing", False))
                # PostgreSQL refuses further queries on this connection until the failed one is rolled back.
                conn.rollback()
        # The first month as text proves that '%Y-%m-01' reached MySQL unchanged.
        if facts["first"] is not None:
            # The expected text, such as 2010-02-01.
            first_month = f"{facts['first'].year:04d}-{facts['first'].month:02d}-01"
            # Ask the monthly view for its earliest month.
            try:
                # PostgreSQL returns a date and MySQL returns text. str() and [:10] make both comparable.
                got = str(conn.exec_driver_sql("select min(month) from vw_monthly_sales").scalar())[:10]
            # The view does not exist.
            except Exception:
                # Shown in the table.
                got = "view missing"
            # Compare the two texts.
            checks.append(("first month in the view", first_month, got, first_month == got))
    # Print the table.
    for name, expected, got, same in checks:
        # One line per check, ending in ok or DIFFERENT.
        say(f"  {name:<26} {expected:>18} {got:>18}   {'ok' if same else 'DIFFERENT'}")
    # True when every check agreed. check[3] is the ok value.
    all_same = all(check[3] for check in checks)
    # The verdict in one line.
    say("The database matches the CSV." if all_same else "The database does NOT match the CSV. See the lines marked DIFFERENT.")
    # 0 when everything matched.
    return 0 if all_same else 1


# Prints the six tables with their row counts.
def show_tables(counts: dict) -> None:
    # One line per table.
    for table, count in counts.items():
        # format(count, ",") adds the thousands comma.
        say(f"  {table:<24} {'(no such table)' if count is None else format(count, ',') + ' rows'}")


# The database action. db is the dictionary from open_database().
def action_database(db: dict, reset: bool) -> int:
    # Shorter names for two values that are used often.
    engine, secrets = db["engine"], db["secrets"]
    # What the CSV says: rows, stores, total, dates.
    facts = read_csv_facts()
    # Read and check the SQL files first. Nothing has been sent at this point.
    try:
        # The folder names sql/postgres and sql/mysql match the two backend names.
        plan = read_setup_statements(PROJECT / "sql" / db["backend"])
    # A file is missing, or holds SQL the splitter refuses.
    except (ValueError, OSError) as problem:
        # Pass the reason on.
        raise Stop(1, f"{problem}\nNothing was sent to the database.") from None
    # Make "from src..." work from any folder.
    if str(PROJECT) not in sys.path:
        # Put the project folder first in Python's search list.
        sys.path.insert(0, str(PROJECT))
    # Let the project's own cleaning code read the CSV BEFORE anything is dropped.
    # It is stricter than read_csv_facts() about column names and dates.
    try:
        # pandas is installed. open_database() made sure of that.
        import pandas as pd
        # The cleaning function that src/etl.py uses.
        from src.transform import normalize_weekly_columns
        # Number of rows the loader would write.
        clean_rows = len(normalize_weekly_columns(pd.read_csv(CSV_PATH)))
    # The loader refuses the file.
    except Exception as problem:
        # Say why, and that the database is untouched.
        raise Stop(1, "The project's loader cannot read data/raw/walmart_real_sales.csv:\n  " + first_line(problem, secrets) + "\nNothing was sent to the database.") from None
    # The loader drops rows without a store, a date or a sales value. Then the database could never match the CSV.
    if clean_rows != facts["rows"]:
        # Stop before anything is dropped.
        raise Stop(1, f"The project's loader would keep {clean_rows:,} of the {facts['rows']:,} rows in the CSV. Fix the CSV first.\nNothing was sent to the database.")
    # How many rows each of the six tables holds.
    try:
        # None for a table that does not exist.
        counts = table_counts(engine)
    # The database stopped answering.
    except Exception as problem:
        # One line instead of a traceback.
        raise Stop(1, "Could not look at the tables:\n  " + first_line(problem, secrets)) from None
    # Empty means: every table is missing or has no rows, so nothing can be lost.
    empty = all(not count for count in counts.values())
    # At least one table holds rows.
    if not empty:
        # Worth a closer look only when the weekly table has rows and no reset was asked for.
        loaded = counts["weekly_store_sales"] and not reset
        # The weekly table holds rows.
        if loaded:
            # Read its numbers.
            try:
                # Rows, stores, total, first and last week.
                found = database_facts(engine)
            # The table cannot be read.
            except Exception as problem:
                # One line instead of a traceback.
                raise Stop(1, "Could not read weekly_store_sales:\n  " + first_line(problem, secrets)) from None
            # Same rows, stores and total as the CSV.
            if found["rows"] == facts["rows"] and found["stores"] == facts["stores"] and same_money(found["total"], facts["total"]):
                # The rows are right. The full check also looks at the dates and the views.
                if verify(engine, facts, secrets) == 0:
                    # Everything is in place.
                    say("The data is already loaded and correct. Nothing was changed.")
                    # 0 means fine.
                    return 0
                # Right rows, but something else is missing. This happens after "python -m src.etl" without 01 to 03.
                raise Stop(2, (
                    "The weekly rows are right, but something else is missing (see the lines marked DIFFERENT). I changed nothing.\n"
                    "To rebuild everything: python run.py database --reset"
                ))
        # There are rows and no --reset: change nothing.
        if not reset:
            # Heading.
            say("These tables already hold rows:")
            # The six tables with their counts.
            show_tables(counts)
            # Explain why nothing was done, and name the way out.
            raise Stop(2, (
                "Loading the file again would stop with a duplicate key error, and rebuilding the tables\n"
                "would delete those rows. I changed nothing.\n"
                "To wipe the tables and load from scratch: python run.py database --reset"
            ))
        # --reset: show what will be deleted.
        say(f"--reset will DELETE every row in these tables of {db['label']}:")
        # The six tables with their counts.
        show_tables(counts)
        # Ask for the database name as confirmation.
        say(f"To go ahead, type the database name ({db['url'].database}) and press Enter. Anything else cancels.")
        # input() also reads a line from a pipe, which keeps this path testable.
        try:
            # What the user typed.
            typed = input("> ")
        # The input ended or is not there at all.
        except (EOFError, RuntimeError, OSError):
            # Count it as nothing typed.
            typed = ""
        # Anything but the exact name cancels.
        if typed.strip() != db["url"].database:
            # 2 means the user decided.
            raise Stop(2, "Cancelled. Nothing was changed.")
    # All six tables are empty or missing.
    else:
        # No question needed.
        say("The six project tables are empty or missing, so nothing can be lost.")
    # Announce the build.
    say(f"Building tables, indexes and views ({len(plan)} statements from sql/{db['backend']}/)")
    # Run 01, 02 and 03.
    run_setup(engine, plan, secrets)
    # Announce the load.
    say(f"Loading data/raw/walmart_real_sales.csv ({facts['rows']:,} rows)")
    # Reuse the project's own loader inside this process, so the password never lands on a command line.
    try:
        # The same function that "python -m src.etl" uses.
        from src.etl import load_weekly
        # It reads the CSV, cleans it and writes the rows into weekly_store_sales.
        load_weekly(str(CSV_PATH), db["url"])
    # Anything that goes wrong while loading.
    except Exception as problem:
        # First line only, password removed.
        raise Stop(1, "The load failed:\n  " + first_line(problem, secrets)) from None
    # Compare the result with the CSV.
    return verify(engine, facts, secrets)


# ---------------------------------------------------------------------------
# Start
# ---------------------------------------------------------------------------


# Reads the command line and runs the chosen action. Returns the exit code.
def main(argv=None) -> int:
    # Jupyter's Interactive window has no normal terminal, so Ctrl+C and questions do not work there.
    if "ipykernel" in sys.modules:
        # Say how to run the file properly.
        say("Run this file with the Run Python File button or in a terminal, not in the Interactive window.")
        # 2 means the user has to act.
        return 2
    # Streamlit 1.51, the oldest version that requirements.txt allows, needs Python 3.10 or newer.
    # This file itself still starts on Python 3.9, so that this message can be shown there.
    if sys.version_info < (3, 10):
        # Name the version in use.
        say(f"This project needs Python 3.10 or newer. You are using {sys.version_info[0]}.{sys.version_info[1]}.")
        # Say where to change it.
        say("In VS Code click the Python version at the bottom right and pick a newer one.")
        # The launchers look for a newer Python by themselves.
        say("Or start the project with run.command (Mac) or run.bat (Windows), which look for a newer Python.")
        # 2 means the user has to act.
        return 2
    # RawDescriptionHelpFormatter keeps the line breaks of the help text below.
    parser = argparse.ArgumentParser(
        prog="run.py",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=(
            "Runs the Walmart sales project. With no word after run.py it checks the packages\n"
            "and the data file, then opens the dashboard.\n\n"
            "  dashboard   check packages and data, start the dashboard, open the browser (the default)\n"
            "  check       only report: Python, packages, data files, free port. Changes nothing.\n"
            "  test        run the automated tests\n"
            "  database    build the tables in PostgreSQL or MySQL, load the weekly CSV, compare totals\n"
            "  all         test, then database, then dashboard"
        ),
        epilog=(
            "The database address is asked for when it is needed. It is not an option on the command\n"
            "line, because it contains a password. For runs where nobody can type, put the full address\n"
            f"into the environment variable {ENV_NAME}.\n\n"
            "examples:\n  python run.py\n  python run.py database"
        ),
    )
    # nargs="?" makes the word optional. Without it the action is dashboard.
    parser.add_argument("action", nargs="?", default="dashboard", choices=["dashboard", "check", "test", "database", "all"], help="what to run (default: dashboard)")
    # store_true makes --reset a switch: present means True.
    parser.add_argument("--reset", action="store_true", help="only with database: wipe the six project tables first. Asks for the database name before it does.")
    # Another switch.
    parser.add_argument("--no-browser", action="store_true", help="start the dashboard without opening a browser tab")
    # Read the command line. argv is None in normal use, which means "take what was typed".
    args = parser.parse_args(argv)
    # --reset with any other action makes no sense.
    if args.reset and args.action != "database":
        # parser.error prints the message and exits with code 2.
        parser.error("--reset only works like this: python run.py database --reset")
    # From here on a Stop ends the run with its message.
    try:
        # The three header lines.
        show_header()
        # run.py must sit next to app.py.
        check_project_files()
        # The report.
        if args.action == "check":
            # Its result is the exit code.
            return action_check()
        # The tests.
        if args.action == "test":
            # 0 when every test passed.
            return action_test()
        # The database.
        if args.action == "database":
            # Connect first, then build, load and check.
            return action_database(open_database(), args.reset)
        # Everything.
        if args.action == "all":
            # Ask every question first, so the long part runs without waiting for anyone.
            # First question: may missing packages for the tests and the dashboard be installed?
            say("Packages the tests and the dashboard need")
            # The five dashboard packages plus pytest.
            ensure_packages("The full run", DASHBOARD_NEEDS + ["pytest"])
            # An empty line between the steps.
            say()
            # Second and third question: the database address and its password.
            db = open_database()
            # An empty line between the steps.
            say()
            # Failing tests stop the run before the database is touched.
            if action_test() != 0:
                # 1 means failed.
                raise Stop(1, "The tests failed, so the database and the dashboard were not started.")
            # An empty line between the steps.
            say()
            # A database that does not match the CSV stops the run before the dashboard.
            if action_database(db, reset=False) != 0:
                # 1 means failed.
                raise Stop(1, "The database check failed, so the dashboard was not started.")
            # An empty line between the steps.
            say()
        # The default action, and the last step of "all".
        return action_dashboard(open_browser=not args.no_browser)
    # A planned early end.
    except Stop as stop:
        # Print the message.
        say(stop.text)
        # Use its exit code.
        return stop.code
    # Ctrl+C or a stop signal anywhere outside the dashboard wait.
    except (KeyboardInterrupt, StopRequested):
        # An empty line after the ^C that the terminal prints.
        say()
        # One word is enough.
        say("Stopped.")
        # 1, because the run did not finish.
        return 1


# True when the file is run directly. "import run" in the tests does not start anything.
if __name__ == "__main__":
    # Hand the exit code to the terminal.
    sys.exit(main())
