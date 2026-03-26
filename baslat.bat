@echo off
echo ==============================================
echo YouTube Uzun Video Botu Baslatiliyor...
echo ==============================================

cd /d "%~dp0"

if not exist venv (
    echo Python sanal ortami bulunamadi. Lutfen kurulumu kontrol edin.
    pause
    exit /b
)

call venv\Scripts\activate.bat
python gui.py
pause
