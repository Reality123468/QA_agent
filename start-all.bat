@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:: ============================================
:: QA Agent 一键启动脚本（除 Docker 外）
:: 双击运行或命令行: start-all.bat
:: 前提: Docker 已启动 (Qdrant + MinIO)
:: ============================================

set ROOT_DIR=%~dp0
set LOGS_DIR=%ROOT_DIR%logs
if not exist "%LOGS_DIR%" mkdir "%LOGS_DIR%"

echo.
echo ========================================
echo   QA Agent 一键启动
echo   项目目录: %ROOT_DIR%
echo ========================================
echo.

:: ---- 1. Python AI ----
echo [1/5] 启动 Python AI 服务 (端口 8000)...
cd /d "%ROOT_DIR%python"
start "QA-Python" /MIN cmd /c "poetry run uvicorn api.main:app --host 0.0.0.0 --port 8000 > %LOGS_DIR%\python.log 2>&1"
cd /d "%ROOT_DIR%"

:: ---- 2. Java Auth ----
echo [2/5] 启动 Java Auth (端口 8080)...
cd /d "%ROOT_DIR%java"
start "QA-Auth" /MIN cmd /c "mvn -pl auth spring-boot:run -q > %LOGS_DIR%\auth.log 2>&1"
cd /d "%ROOT_DIR%"
timeout /t 4 /nobreak >nul

:: ---- 3. Java Document ----
echo [3/5] 启动 Java Document (端口 8081)...
cd /d "%ROOT_DIR%java"
start "QA-Document" /MIN cmd /c "mvn -pl document spring-boot:run -q > %LOGS_DIR%\document.log 2>&1"
cd /d "%ROOT_DIR%"
timeout /t 4 /nobreak >nul

:: ---- 4. Java Chat ----
echo [4/5] 启动 Java Chat (端口 8082)...
cd /d "%ROOT_DIR%java"
start "QA-Chat" /MIN cmd /c "mvn -pl chat spring-boot:run -q > %LOGS_DIR%\chat.log 2>&1"
cd /d "%ROOT_DIR%"
timeout /t 4 /nobreak >nul

:: ---- 5. Java Audit + Frontend ----
echo [5/5] 启动 Java Audit (端口 8083) + 前端 (端口 5173)...
cd /d "%ROOT_DIR%java"
start "QA-Audit" /MIN cmd /c "mvn -pl audit spring-boot:run -q > %LOGS_DIR%\audit.log 2>&1"
cd /d "%ROOT_DIR%"
timeout /t 4 /nobreak >nul

cd /d "%ROOT_DIR%java\frontend"
start "QA-Frontend" /MIN cmd /c "npm run dev > %LOGS_DIR%\frontend.log 2>&1"
cd /d "%ROOT_DIR%"

echo.
echo 等待服务启动 (约 60 秒)...
echo 可用 curl 或浏览器验证各端口:
echo   Python:  http://localhost:8000/api/agent/health
echo   Auth:    http://localhost:8080
echo   Document: http://localhost:8081
echo   Chat:    http://localhost:8082
echo   Audit:   http://localhost:8083
echo   前端:    http://localhost:5173
echo.
echo 日志目录: %LOGS_DIR%
echo 关闭窗口不会停止服务，请在各子窗口按 Ctrl+C 停止
echo.

pause
