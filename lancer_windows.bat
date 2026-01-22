@echo off

REM Se placer dans le dossier du script
cd /d "%~dp0"

REM Activer le venv
call venv310\Scripts\activate

REM Lancer le serveur en arrière-plan
start "" python ui_server.py

REM Attendre que le serveur démarre
timeout /t 2 /nobreak >nul

REM Ouvrir automatiquement la page d'accueil
start http://localhost:8000/index.html

pause
