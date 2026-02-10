@echo off
cd /d "C:\Users\FastAPIUser\Desktop\ToDoApp"
start chrome --kiosk "http://127.0.0.1:8000"
timeout /t 2 /nobreak >nul
uvicorn main:app --host 0.0.0.0 --port 8000
