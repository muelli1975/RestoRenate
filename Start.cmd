@echo off
setlocal
cd /d "%~dp0"
if not exist "runtime\python\python.exe" (
  echo Bitte die ZIP vollstaendig entpacken. / Extract the entire ZIP.
  pause
  exit /b 1
)
"runtime\python\python.exe" -I -X utf8 "bootstrap.py"
if errorlevel 1 pause
