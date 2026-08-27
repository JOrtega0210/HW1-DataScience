@echo off
REM Wrapper para ejecutar el scraper desde Windows Task Scheduler.
REM %~dp0 apunta siempre a la carpeta donde vive este .bat, sin importar
REM cual sea el "Start in" configurado en la tarea programada.
setlocal
cd /d "%~dp0"
".venv\Scripts\python.exe" "scraper_sunat.py" %*
endlocal
