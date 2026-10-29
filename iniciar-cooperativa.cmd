@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Execute primeiro os comandos de instalacao descritos no README.md.
  pause
  exit /b 1
)
echo Cooperativa: http://127.0.0.1:8000/
".venv\Scripts\python.exe" manage.py runserver
pause
