@echo off
chcp 65001 >nul
title [步驟2] 自由選擇是否執行 AI 總結
cd /d "%~dp0"
if exist "venv\Scripts\activate.bat" (
    call "venv\Scripts\activate.bat"
) else if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
)
python 02_ai_summarize.py
echo.
echo 執行結束，視窗將於 3 秒後自動關閉...
timeout /t 3 /nobreak >nul