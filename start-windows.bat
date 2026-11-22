@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  py -3.12 app.py --desktop
) else (
  python app.py --desktop
)
if errorlevel 1 (
  echo.
  echo The app could not start. Install Python 3.12 and run again.
  pause
)
endlocal
