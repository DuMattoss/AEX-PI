@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 goto procurar_python
py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul
if not errorlevel 1 goto usar_py
:procurar_python
where python >nul 2>nul
if errorlevel 1 goto sem_python
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul
if errorlevel 1 goto sem_python
python "scripts\iniciar.py" %*
goto fim
:usar_py
py -3 "scripts\iniciar.py" %*
goto fim
:sem_python
echo Instale Python 3.10 ou superior antes de iniciar.
echo Download oficial: https://www.python.org/downloads/
echo Na instalacao, marque Add Python to PATH.
pause
exit /b 1
:fim
set "COOP_EXIT=%errorlevel%"
if "%COOP_EXIT%"=="0" exit /b 0
echo.
echo A inicializacao foi interrompida. Confira a mensagem acima.
pause
exit /b %COOP_EXIT%
