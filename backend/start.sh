#!/bin/bash
cd /home/clawd/clawd/projects/spacex-orbital/backend
source venv/bin/activate
exec uvicorn app.main:app --host 0.0.0.0 --port 8001
