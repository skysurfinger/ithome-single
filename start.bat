@echo off
chcp 65001 >nul
title IT之家单列版
cd /d "%~dp0"
echo 正在启动 IT之家单列版本地服务...
echo 浏览器将自动打开 http://127.0.0.1:18734
echo 页面上的"刷新"按钮会实时重新抓取最新内容
echo 关闭本窗口即停止服务
python server.py
pause