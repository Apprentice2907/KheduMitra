@echo off
echo ==========================================
echo Starting KheduMitra Services...
echo ==========================================
echo.
echo Please ensure Redis is running on localhost:6379
echo (Check .env file for configuration)
echo.

echo [1/3] Starting FastAPI server (uvicorn)...
start "KheduMitra - FastAPI" cmd /k "venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

echo [2/3] Starting Celery worker...
start "KheduMitra - Celery Worker" cmd /k "venv\Scripts\celery.exe -A app.core.celery_app worker --loglevel=info --pool=solo"

echo [3/3] Starting Celery beat (scheduler)...
start "KheduMitra - Celery Beat" cmd /k "venv\Scripts\celery.exe -A app.core.celery_app beat --loglevel=info"

echo.
echo All services have been launched in separate windows!
echo - The API will be available at: http://localhost:8000
echo - The API docs will be at: http://localhost:8000/docs
echo.
pause
