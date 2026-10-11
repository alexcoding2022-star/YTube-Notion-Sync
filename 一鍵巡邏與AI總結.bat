@echo off
chcp 65001 >nul
title YouTube 一鍵巡邏與 AI 智慧總結
cd /d "%~dp0"
if exist "venv\Scripts\activate.bat" (
    call "venv\Scripts\activate.bat"
) else if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
)
python main.py
echo.
echo 任務已全部執行完畢，視窗將於 3 秒後自動關閉...

timeout /t 3 /nobreak >nul