@echo off
chcp 65001 >nul
title 新增 YouTube 追蹤頻道
cd /d "%~dp0"
if exist "venv\Scripts\activate.bat" (
    call "venv\Scripts\activate.bat"
) else if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
)
python add_channel.py
echo.
echo 執行結束，視窗將於 3 秒後自動關閉...

timeout /t 3 /nobreak >nul