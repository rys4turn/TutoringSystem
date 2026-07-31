@echo off
chcp 65001 >nul
title 教务管理系统
cd /d "%~dp0"

echo 正在启动教务管理系统...
echo.
echo 管理页面将在浏览器中自动打开
echo =======================================

start "" /wait TutoringSystem.exe
