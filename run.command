#!/bin/bash
# Starts the Walmart sales project on a Mac. Double-click this file in Finder, or type in a terminal:
#   bash run.command             the dashboard
#   bash run.command test        the tests (same words as run.py: check, test, database, all)
# On the first run it makes a project-local Python in the folder .venv. After that it hands over to
# run.py, which checks the packages, offers to install what is missing, and starts the dashboard.
# Linux users can run it the same way.

# Work inside the folder this file is in, whatever folder the terminal was opened in.
# "$0" is the path of this file and dirname cuts off the file name. Stop if the folder cannot be entered.
cd "$(dirname "$0")" || exit 1

# One line of Python that ends with 0 for Python 3.10 or newer, and with 1 for anything older.
NEW_ENOUGH="import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)"

# Waits for Enter when a keyboard is attached, so a double-clicked window does not vanish with its messages.
pause() {
    # "-t 0" is true when the input is a terminal, and false for a pipe or an automated run.
    if [ -t 0 ]; then
        # An empty line first.
        echo
        # -p shows the text, -r keeps a typed backslash as it is.
        read -r -p "Press Enter to finish. "
    fi
}

# run.py has to sit next to this file. It does not when a link to this file was started from another folder.
if [ ! -f "run.py" ]; then
    # Say what happened before anything is created in the wrong place.
    echo "run.py was not found next to this file. Start the run.command inside the project folder, not a link to it."
    # Let the message be read.
    pause
    # 1 means something failed.
    exit 1
fi

# The Python that will run the project. Empty until one is found.
PYTHON=""

# A project-local Python from an earlier run.
if [ -x ".venv/bin/python" ]; then
    # It has to be new enough. A .venv made with an old Python would fail on every run.
    if ! ".venv/bin/python" -c "$NEW_ENOUGH" 2>/dev/null; then
        # Say what to do. The folder is not deleted here, because it belongs to the user.
        echo "The folder .venv holds a Python older than 3.10. Delete the .venv folder and run this file again."
        # Let the message be read.
        pause
        # 1 means something failed.
        exit 1
    # It also has to have pip. A first run that was interrupted leaves a .venv without it.
    elif ".venv/bin/python" -c "import pip" 2>/dev/null; then
        # Use it.
        PYTHON=".venv/bin/python"
    fi
    # Otherwise PYTHON stays empty, and the block below makes the .venv again.
fi

# No finished .venv yet: find a Python 3.10 or newer to make one with.
if [ -z "$PYTHON" ]; then
    # The name that passed the test. Empty until one does.
    FOUND=""
    # python3 is the usual name. The numbered names catch a newer Python that is not the default one.
    for candidate in python3 python3.15 python3.14 python3.13 python3.12 python3.11 python3.10 python; do
        # "command -v" tells whether the name exists. The Python line tells whether it is new enough.
        if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c "$NEW_ENOUGH" >/dev/null 2>&1; then
            # Keep the name.
            FOUND="$candidate"
            # Stop looking.
            break
        fi
    done
    # Nothing usable on this computer.
    if [ -z "$FOUND" ]; then
        # Say so.
        echo "No Python 3.10 or newer was found on this computer."
        # And what to do.
        echo "Install Python from https://www.python.org/downloads/ and run this file again."
        # A Mac without developer tools pops up an offer to install them while the search above runs.
        echo "If a window offers to install command line developer tools, cancel it: those bring Python 3.9, which is too old."
        # Let the message be read.
        pause
        # 1 means something failed.
        exit 1
    fi
    # Say which Python is used. The part in $( ) prints its version number.
    echo "Making a project-local Python in the folder .venv with $FOUND ($("$FOUND" -c 'import sys; print(sys.version.split()[0])'))."
    # And why this takes a moment.
    echo "This happens once and takes a few seconds."
    # venv copies a small Python into .venv. Packages installed there stay inside this project folder.
    # --clear first empties a .venv that is there but broken: one without pip, or one whose Python was removed.
    if "$FOUND" -m venv --clear .venv && ".venv/bin/python" -c "import pip" 2>/dev/null; then
        # Use the new one.
        PYTHON=".venv/bin/python"
    else
        # Making it failed. Remove what was left, so the next run starts from nothing and shows this message again.
        rm -rf .venv
        # Say so and carry on with the Python that was found.
        echo "Could not make the .venv folder. Running with $FOUND instead."
        # The one system where venv is not part of Python.
        echo "(On Debian or Ubuntu the venv module is a separate package: sudo apt install python3-venv)"
        # Fall back.
        PYTHON="$FOUND"
    fi
fi

# Hand over. "$@" passes on the words typed after the file name, such as test or database.
"$PYTHON" run.py "$@"
# Remember how run.py ended, so this file can end the same way.
CODE=$?

# Keep the window open until Enter is pressed.
pause
# 0 means fine, 1 means something failed, 2 means the user has to decide or fix something.
exit $CODE
