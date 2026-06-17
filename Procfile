web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
worker: celery -A app.worker.celery_app worker -l info
beat: celery -A app.worker.celery_app beat -l info
