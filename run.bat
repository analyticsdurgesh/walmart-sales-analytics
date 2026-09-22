@echo off
rem Starts the Walmart sales project on Windows. Double-click this file, or type in a terminal:
rem   run.bat                  the dashboard
rem   run.bat test             the tests (same words as run.py: check, test, database, all)
rem On the first run it makes a project-local Python in the folder .venv. After that it hands over to
rem run.py, which checks the packages, offers to install what is missing, and starts the dashboard.
rem (The first line above, @echo off, stops cmd from printing every command before it runs it.)

rem Keep the variables set below inside this file, so they do not stay behind in an open terminal.
setlocal

rem Work inside the folder this file is in, whatever folder the window was opened in.
rem %~dp0 is the folder of this file. /d also switches the drive letter when needed.
cd /d "%~dp0"

rem run.py has to sit next to this file. It does not when a shortcut to this file was copied elsewhere.
if not exist "run.py" (
    rem Say what happened before anything is created in the wrong place.
    echo run.py was not found next to this file. Start the run.bat inside the project folder, not a copy of it.
    rem 1 means something failed.
    set "CODE=1"
    rem Skip to the pause at the end.
    goto :end
)

rem PYTHON stays empty until a usable Python is found.
set "PYTHON="

rem A project-local Python from an earlier run: jump to the checks for it.
if exist ".venv\Scripts\python.exe" goto :checkvenv

:find
rem Say what is happening, because the search below prints nothing of its own.
echo Looking for a Python 3.10 or newer on this computer. With the Python install manager this can download one first, which takes a minute.
rem The py launcher comes with Python from python.org. "py -3" picks the newest Python 3 on the computer.
rem The Python line ends with 0 for Python 3.10 or newer. The output is thrown away, only the result counts.
py -3 -c "import sys; sys.exit(sys.version_info < (3, 10))" >nul 2>&1
rem "not errorlevel 1" means the result was 0.
if not errorlevel 1 set "PYTHON=py -3"
rem Found one: go and make the .venv.
if defined PYTHON goto :make

rem Second try: a Python called python on the PATH.
python -c "import sys; sys.exit(sys.version_info < (3, 10))" >nul 2>&1
rem Same test as above.
if not errorlevel 1 set "PYTHON=python"
rem Found one: go and make the .venv.
if defined PYTHON goto :make

rem Nothing usable on this computer. Say so.
echo No Python 3.10 or newer was found on this computer.
rem And what to do.
echo Install Python from https://www.python.org/downloads/ (the Python install manager or the standalone installer).
rem Then come back.
echo Then run this file again.
rem 1 means something failed.
set "CODE=1"
rem Skip to the pause at the end.
goto :end

:make
rem Say which Python is used and why this takes a moment.
echo Making a project-local Python in the folder .venv with %PYTHON%. This happens once and takes a few seconds.
rem venv copies a small Python into .venv. Packages installed there stay inside this project folder.
rem --clear first empties a .venv that is there but broken, such as one without pip from an interrupted run.
%PYTHON% -m venv --clear .venv
rem A finished .venv has pip. Check for it, output thrown away.
".venv\Scripts\python.exe" -c "import pip" >nul 2>&1
rem A result of 0 means pip is there.
if not errorlevel 1 (
    rem Use the new one.
    set "PYTHON=.venv\Scripts\python.exe"
) else (
    rem Making it failed. Remove what was left, so the next run starts from nothing and shows this message again.
    if exist ".venv" rmdir /s /q ".venv"
    rem Say so and carry on with the Python that was found.
    echo Could not make the .venv folder. Running with %PYTHON% instead.
)
rem Hand over.
goto :run

:checkvenv
rem The .venv has to be new enough. One made with an old Python would fail on every run.
".venv\Scripts\python.exe" -c "import sys; sys.exit(sys.version_info < (3, 10))" >nul 2>&1
rem A result of 1 or more means too old.
if errorlevel 1 goto :oldvenv
rem It also has to have pip. A first run that was interrupted leaves a .venv without it.
".venv\Scripts\python.exe" -c "import pip" >nul 2>&1
rem Without pip, go back and let venv finish the folder.
if errorlevel 1 goto :find
rem Fine: use it.
set "PYTHON=.venv\Scripts\python.exe"
rem Hand over.
goto :run

:oldvenv
rem Say what to do. The folder is not deleted here, because it belongs to the user.
echo The folder .venv holds a Python older than 3.10, or the Python it was made from was removed. Delete the .venv folder and run this file again.
rem 1 means something failed.
set "CODE=1"
rem Skip to the pause at the end.
goto :end

:run
rem Hand over. %* passes on the words typed after the file name, such as test or database.
%PYTHON% run.py %*
rem Remember how run.py ended, so this file can end the same way.
set "CODE=%errorlevel%"

:end
rem An empty line first.
echo.
rem Wait for a key. A double-clicked window would otherwise close with its messages.
pause
rem 0 means fine, 1 means something failed, 2 means the user has to decide or fix something.
exit /b %CODE%
