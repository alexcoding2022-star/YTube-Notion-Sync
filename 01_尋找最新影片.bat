@echo off
chcp 65001 >nul
title [步驟1] 巡邏 YouTube 發現新片 (零 AI 消耗)
cd /d "%~dp0"
if exist "venv\Scripts\activate.bat" (
    call "venv\Scripts\activate.bat"
) else if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
)
python 01_find_videos.py
echo.
echo 巡邏任務完成！視窗將於 3 秒後自動關閉...
timeout /t 3 /nobreak >nul