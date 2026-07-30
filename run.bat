@echo off
:: Start Python backend in a new window or background
start cmd /k "cd backend && venv\Scripts\activate && uvicorn app.main:app --reload"

:: Start React frontend
cd frontend && npm run dev