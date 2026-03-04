@echo off
echo Starting Chrome container...
docker compose up chrome -d

echo Waiting for Chrome to be ready...
timeout /t 5 /nobreak >nul

echo Running scraper...
uv run python src/main.py

echo.
echo Done. Results saved to downloads/results.txt
pause
