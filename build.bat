@echo off
chcp 65001 >nul
title 构建系统
cd /d "%~dp0frontend"

echo 正在构建前端...
call npx vite build

echo.
echo 正在复制静态文件...
if exist "..\backend\static" rmdir /s /q "..\backend\static"
xcopy /e /i "dist" "..\backend\static"

echo.
echo 正在打包 exe...
cd /d "%~dp0backend"
del /q "..\TutoringSystem.exe" 2>nul
python -m PyInstaller --onefile --add-data "static;static" --collect-all app --name "TutoringSystem" --clean --exclude-module matplotlib --exclude-module numpy --exclude-module scipy --exclude-module IPython --exclude-module sphinx --exclude-module PIL --exclude-module nbformat --exclude-module jsonschema --exclude-module pygments --exclude-module docutils --exclude-module jinja2 --exclude-module babel --exclude-module pytest --exclude-module setuptools --exclude-module wheel --exclude-module pip --exclude-module tkinter launcher.py
copy /y "dist\TutoringSystem.exe" "..\" >nul
echo.
echo 构建完成！请使用 start.bat 启动系统
pause
