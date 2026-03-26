@echo off
set "PYTHONIOENCODING=utf-8"
echo ==============================================
echo YouTube Video Botu - RTX 4060 Modu (Python 3.12)
echo ==============================================

cd /d "%~dp0"

if not exist venv312 (
    echo Python 3.12 sanal ortami bulunamadi. Kurulum hatali.
    pause
    exit /b
)

echo [SISTEM] Sanal ortam aktif ediliyor...
call venv312\Scripts\activate.bat

echo [SISTEM] RTX 4060 Hızlandırması ile Uygulama Başlatılıyor...
python gui.py

pause
