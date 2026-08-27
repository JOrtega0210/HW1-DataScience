@echo off
REM ============================================================
REM run.bat - Ejecuta el bot RPA de registro de ingresos PeopleSync
REM Pensado para lanzarse manualmente o desde Windows Task Scheduler.
REM ============================================================

REM Cambia al directorio donde vive este script (independiente de
REM desde dónde se invoque, importante para Task Scheduler).
cd /d "%~dp0"

REM Activa el entorno virtual si existe.
if exist "venv\Scripts\activate.bat" (
    call "venv\Scripts\activate.bat"
) else (
    echo [AVISO] No se encontro venv\Scripts\activate.bat, se usara el Python del PATH del sistema.
)

REM Ejecuta el bot. Los argumentos que se le pasen a run.bat se
REM reenvian tal cual al script (ej: run.bat --headless --limit 5).
python run_bot.py %*
set EXIT_CODE=%ERRORLEVEL%

if exist "venv\Scripts\deactivate.bat" (
    call deactivate
)

exit /b %EXIT_CODE%
