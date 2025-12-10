@echo off
REM Script di avvio per CSV/Excel Merger App (Windows)

echo ============================================================
echo                    CSV/Excel Merger App
echo ============================================================
echo.

cd /d "%~dp0"

REM Controlla se le dipendenze sono installate
python -c "import flask" 2>nul
if errorlevel 1 (
    echo Installazione dipendenze...
    pip install -r requirements.txt
)

echo Avvio server...
echo Apri il browser su: http://localhost:5000
echo Premi CTRL+C per terminare
echo.

python app.py
pause
