# Path points at the real SQL files of the project.
from pathlib import Path

# pytest.raises checks that a piece of code stops with the expected error.
import pytest

# The runner under test. Importing it starts nothing, because all work sits in main().
import run

# The sql/ folder of the project.
SQL = run.PROJECT / "sql"


# The splitter must find the same statements in the real files as a person reading them would.
# If someone edits a SQL file in a way the splitter cannot handle, this test notices it first.
def test_split_sql_counts_statements_in_the_real_files():
    # Expected number of statements per file: schema, indexes, views, query pack.
    expected = {"postgres": [15, 6, 3, 3], "mysql": [12, 6, 3, 3]}
    # The four files in the order they are numbered.
    names = ["01_schema.sql", "02_indexes.sql", "03_views.sql", "04_analytics_queries.sql"]
    # Check both databases.
    for backend, counts in expected.items():
        # Split every file and count the pieces.
        found = [len(run.split_sql((SQL / backend / name).read_text(encoding="utf-8"), name)) for name in names]
        # The counts must match exactly.
        assert found == counts


# The comments in the SQL files contain semicolons and quotes. None of that may reach the database.
def test_split_sql_drops_comments_and_keeps_quoted_text():
    # Read the MySQL views, which hold the text '%Y-%m-01'.
    statements = run.split_sql((SQL / "mysql" / "03_views.sql").read_text(encoding="utf-8"), "03_views.sql")
    # No statement may still contain a comment.
    assert not any("--" in statement for statement in statements)
    # The first view uses the month text twice, and both must arrive unchanged.
    assert statements[0].count("'%Y-%m-01'") == 2


# A semicolon only ends a statement when it is outside comments and quotes.
def test_split_sql_only_cuts_at_real_semicolons():
    # Three real statements. The other semicolons sit inside a quote or a comment.
    text = "select 'a;b -- x'; -- c; d\nselect 'it''s; ok'; /* b; */ select 3"
    # Split it.
    statements = run.split_sql(text, "example.sql")
    # The quoted text must come through untouched, and the comments must be gone.
    assert statements == ["select 'a;b -- x'", "select 'it''s; ok'", "select 3"]


# When the splitter meets something it does not understand, it must stop and not guess.
def test_split_sql_refuses_what_it_cannot_read():
    # Six kinds of text the splitter does not handle. The last two are comment forms that
    # MySQL and PostgreSQL read differently, so a DROP could hide inside them.
    for bad in [
        "select 1 --no space after the dashes",
        "select 'never closed",
        "select $$ body; $$",
        "select 'back\\slash'",
        "create table t (id int) # todo; drop table stores\n;",
        "/* a /* b */ drop table stores; -- */",
    ]:
        # Each one must raise ValueError.
        with pytest.raises(ValueError):
            # The second argument is only the file name used in the error message.
            run.split_sql(bad, "bad.sql")


# The setup files may only drop and create things. Anything else must be refused before it is sent.
def test_read_setup_statements_refuses_other_commands(tmp_path: Path):
    # tmp_path is an empty folder that pytest creates and removes. Put three small SQL files in it.
    (tmp_path / "01_schema.sql").write_text("create table t (id int);", encoding="utf-8")
    # The second file holds a command that deletes rows.
    (tmp_path / "02_indexes.sql").write_text("delete from t;", encoding="utf-8")
    # The third file is fine.
    (tmp_path / "03_views.sql").write_text("create view v as select id from t;", encoding="utf-8")
    # Reading the folder must stop at the delete.
    with pytest.raises(ValueError):
        # Nothing is sent anywhere. The function only reads and checks.
        run.read_setup_statements(tmp_path)


# A DROP may only name a view or one of the six project tables. The row counts shown to the user
# cover those six tables, so a drop of anything else would delete rows nobody was told about.
def test_read_setup_statements_refuses_drops_outside_the_project(tmp_path: Path):
    # Four statements that start with the word drop and must still be refused.
    for bad in ["drop database walmart_sales;", "drop schema public cascade;", "drop table if exists store_notes;", "drop table stores, customers;"]:
        # The bad statement goes into the first file.
        (tmp_path / "01_schema.sql").write_text(bad, encoding="utf-8")
        # The other two files are harmless.
        (tmp_path / "02_indexes.sql").write_text("create index i on stores(city);", encoding="utf-8")
        # A view, so that all three files exist.
        (tmp_path / "03_views.sql").write_text("create view v as select 1;", encoding="utf-8")
        # Each one must be refused.
        with pytest.raises(ValueError):
            # Reading is enough to trigger the check.
            run.read_setup_statements(tmp_path)
    # A project table and a view are fine, in any mix of upper and lower case.
    (tmp_path / "01_schema.sql").write_text("DROP VIEW IF EXISTS vw_monthly_sales; drop table if exists Stores;", encoding="utf-8")
    # Two drops from 01, one create each from 02 and 03.
    assert len(run.read_setup_statements(tmp_path)) == 4


# A file saved by Windows Notepad starts with a hidden marker. It must not confuse the check.
def test_read_setup_statements_copes_with_a_hidden_marker(tmp_path: Path):
    # utf-8-sig writes that marker in front of the text.
    (tmp_path / "01_schema.sql").write_text("create table t (id int);", encoding="utf-8-sig")
    # The other two files are plain.
    (tmp_path / "02_indexes.sql").write_text("create index i on t(id);", encoding="utf-8")
    # A view, so that all three files exist.
    (tmp_path / "03_views.sql").write_text("create view v as select id from t;", encoding="utf-8")
    # All three statements are accepted.
    assert len(run.read_setup_statements(tmp_path)) == 3


# Reading the real setup files gives 24 statements for PostgreSQL and 21 for MySQL.
def test_read_setup_statements_accepts_the_real_files():
    # 15 + 6 + 3.
    assert len(run.read_setup_statements(SQL / "postgres")) == 24
    # 12 + 6 + 3.
    assert len(run.read_setup_statements(SQL / "mysql")) == 21


# A password must never show up in a message, in whichever form it was written.
# Each of the three parts below fails when one specific piece of secret_forms() is removed.
def test_scrub_hides_every_form_of_the_password():
    # Part 1: the password was typed at the hidden prompt, so the address holds none.
    # "p w@1" has a space, which the two URL spellings write differently: %20 and +.
    secrets = run.secret_forms("postgresql+psycopg2://postgres@localhost:5432/walmart_sales", "p w@1")
    # A made-up message that repeats the password in all three spellings.
    cleaned = run.scrub("tried p w@1 then p%20w%401 then p+w%401", secrets)
    # Nothing of it may be left.
    assert cleaned == "tried **** then **** then ****"
    # Part 2: the password only exists inside the address, written with %40 %3A %2F.
    address = "postgresql+psycopg2://postgres:S3cr%40t%3A%2Fpw@localhost:5432/walmart_sales"
    # No separate password is given this time.
    secrets = run.secret_forms(address, None)
    # Database drivers report the decoded form, which has to be hidden as well.
    assert run.scrub("login failed for S3cr@t:/pw", secrets) == "login failed for ****"
    # Part 3: a message that repeats the whole address must lose all of it, user and host included.
    cleaned = run.scrub(f"could not parse {address}", secrets)
    # The whole address became one ****.
    assert cleaned == "could not parse ****"


# An address typed without a password has nothing to hide, so messages stay as they are.
def test_scrub_leaves_messages_alone_when_there_is_no_password():
    # No password in the address and none typed.
    secrets = run.secret_forms("postgresql+psycopg2://postgres@localhost:5432/walmart_sales", None)
    # Nothing to hide.
    assert secrets == []
    # The message comes back unchanged.
    assert run.scrub("connection refused", secrets) == "connection refused"


# The facts about the CSV are worked out without pandas. Check them on a tiny file with known answers.
def test_read_csv_facts_on_a_small_file(tmp_path: Path, monkeypatch):
    # Three rows: two stores, two months, one holiday week. Dates are written day-month-year.
    text = (
        "Store,Date,Weekly_Sales,Holiday_Flag,Temperature,Fuel_Price,CPI,Unemployment\n"
        "1,05-02-2010,100.10,0,1,1,1,1\n"
        "2,05-02-2010,200.20,0,1,1,1,1\n"
        "1,12-03-2010,300.30,1,1,1,1,1\n"
    )
    # Write it into the temporary folder.
    small = tmp_path / "small.csv"
    # Save the three rows as UTF-8 text.
    small.write_text(text, encoding="utf-8")
    # Point the runner at this file for the length of the test. monkeypatch puts the old value back afterwards.
    monkeypatch.setattr(run, "CSV_PATH", small)
    # Read the facts.
    facts = run.read_csv_facts()
    # Three rows and two different stores.
    assert (facts["rows"], facts["stores"]) == (3, 2)
    # 100.10 + 200.20 + 300.30, exact to the cent because Decimal is used.
    assert str(facts["total"]) == "600.60"
    # 05-02-2010 must be read as 5 February, and 12-03-2010 as 12 March.
    assert (str(facts["first"]), str(facts["last"])) == ("2010-02-05", "2010-03-12")
    # February and March are two months. Flags 0 and 1 are two different values.
    assert (facts["months"], facts["flags"]) == (2, 2)


# A helper for the tests below: writes a small CSV and points the runner at it.
def use_csv(tmp_path: Path, monkeypatch, body: str) -> None:
    # The header every test file shares.
    header = "Store,Date,Weekly_Sales,Holiday_Flag,Temperature,Fuel_Price,CPI,Unemployment\n"
    # Write header and body into the temporary folder.
    small = tmp_path / "small.csv"
    # newline="" keeps the line ends exactly as written.
    small.write_text(header + body, encoding="utf-8", newline="")
    # Point the runner at this file for the length of one test.
    monkeypatch.setattr(run, "CSV_PATH", small)


# Broken files must end with a clear message and exit code 1, never with a Python traceback.
def test_read_csv_facts_stops_cleanly_on_broken_files(tmp_path: Path, monkeypatch):
    # A good row to put in front of each broken one.
    good = "1,05-02-2010,100.10,0,1,1,1,1\n"
    # A cut-off last line, a line of spaces, too many values, junk numbers, and a header with no rows.
    for body in [good + "45,26-10-20", good + "   \n", good + "1,05-02-2010,1,0,1,1,1,1,9\n", good + "1,05-02-2010,Infinity,0,1,1,1,1\n", good + "x,05-02-2010,1,0,1,1,1,1\n", ""]:
        # Use this file.
        use_csv(tmp_path, monkeypatch, body)
        # run.Stop is the runner's planned way to end early.
        with pytest.raises(run.Stop) as caught:
            # Read the facts.
            run.read_csv_facts()
        # 1 means something failed.
        assert caught.value.code == 1


# The message must name the real line of the file, also when blank lines come before it.
def test_read_csv_facts_reports_the_right_line(tmp_path: Path, monkeypatch):
    # Line 1 is the header, line 2 is good, lines 3 and 4 are blank, line 5 holds the bad sales value.
    use_csv(tmp_path, monkeypatch, "1,05-02-2010,100.10,0,1,1,1,1\n\n\n1,12-02-2010,abc,0,1,1,1,1\n")
    # The bad value stops the read.
    with pytest.raises(run.Stop) as caught:
        # Read the facts.
        run.read_csv_facts()
    # The message must point at line 5.
    assert "line 5" in caught.value.text


# Stores and flags are counted the way the project's loader reads them.
def test_read_csv_facts_counts_stores_and_flags_like_the_loader(tmp_path: Path, monkeypatch):
    # "1", "01" and "1.0" are the same store. An empty holiday flag means 0.
    use_csv(tmp_path, monkeypatch, "1,05-02-2010,1,0,1,1,1,1\n01,12-02-2010,1,,1,1,1,1\n1.0,19-02-2010,1,1,1,1,1,1\n")
    # Read the facts.
    facts = run.read_csv_facts()
    # One store, and two different flags (0 and 1).
    assert (facts["stores"], facts["flags"]) == (1, 2)


# The line picked from a database error must be the server's own answer.
def test_first_line_prefers_the_answer_of_the_server():
    # PostgreSQL reports one line per address it tried. Only the last one comes from the server.
    message = (
        'connection to server at "localhost" (::1), port 5432 failed: Connection refused\n'
        "\tIs the server running on that host and accepting TCP/IP connections?\n"
        'connection to server at "localhost" (127.0.0.1), port 5432 failed: FATAL:  database "walmart_sales" does not exist'
    )
    # No secrets to hide in this test.
    chosen = run.first_line(Exception(message), [])
    # The FATAL line is the useful one.
    assert chosen.endswith('FATAL:  database "walmart_sales" does not exist')
    # Without a FATAL line the first line is shown.
    assert run.first_line(Exception("first\nsecond"), []) == "first"


# A package that is installed but older than requirements.txt allows must be treated like a missing one.
# The case that matters: an old Streamlit starts fine and then fails on every chart.
def test_package_problem_notices_a_version_that_is_too_old(monkeypatch):
    # Version text becomes numbers, so that 1.9 counts as older than 1.51.
    assert run.version_numbers("1.9.2") < run.version_numbers("1.51")
    # Extra text after the numbers, as in a release candidate, does not get in the way.
    assert run.version_numbers("2.0.0rc1") == (2, 0, 0)
    # The limit is read from requirements.txt, where the line says streamlit>=1.51.
    assert run.oldest_allowed("streamlit") == "1.51"
    # Pretend an old Streamlit is installed.
    monkeypatch.setattr(run, "package_version", lambda module: "1.40.0")
    # It must be reported as too old.
    assert run.package_problem("streamlit") == "TOO OLD"
    # Pretend a new enough one is installed.
    monkeypatch.setattr(run, "package_version", lambda module: "1.51.0")
    # Nothing wrong.
    assert run.package_problem("streamlit") is None
    # Pretend it is not installed at all.
    monkeypatch.setattr(run, "package_version", lambda module: None)
    # That is the other kind of problem.
    assert run.package_problem("streamlit") == "MISSING"


# The two launcher files must be there, hand over to run.py, and keep the line endings their system needs.
def test_launchers_hand_over_to_run_py():
    # Read both as bytes, so line endings can be counted.
    command = (run.PROJECT / "run.command").read_bytes()
    # The Windows one.
    bat = (run.PROJECT / "run.bat").read_bytes()
    # The Mac launcher passes every word typed after it on to run.py.
    assert b'run.py "$@"' in command
    # The Windows launcher does the same with %*.
    assert b"run.py %*" in bat
    # A shell script must not have Windows line endings. bash would choke on the extra character.
    assert b"\r\n" not in command
    # A batch file must have them on every line. cmd can lose its place in a file without them.
    assert bat.count(b"\r\n") == bat.count(b"\n")

