@echo off
REM 离火引网站快速更新脚本（Docker 版本）- Windows

echo ==========================================
echo 离火引网站 - Docker 快速更新
echo ==========================================
echo.

REM 配置
set SERVER=8.135.25.206
set USER=root
set REMOTE_DIR=/opt/innerseek

echo 目标服务器: %USER%@%SERVER%
echo 部署目录: %REMOTE_DIR%
echo.

REM 确认更新
set /p CONFIRM="确认更新? (y/n): "
if /i not "%CONFIRM%"=="y" (
    echo 更新已取消
    exit /b 0
)

echo.
echo [1/5] 检查本地文件...
if not exist "docker-compose.yml" (
    echo 错误: docker-compose.yml 不存在
    pause
    exit /b 1
)

echo [2/5] 打包项目文件...
set PACKAGE_NAME=innerseek-update-%date:~0,4%%date:~5,2%%date:~8,2%-%time:~0,2%%time:~3,2%%time:~6,2%.tar.gz
set PACKAGE_NAME=%PACKAGE_NAME: =0%

tar -czf %PACKAGE_NAME% ^
    --exclude=node_modules ^
    --exclude=dist ^
    --exclude=.git ^
    --exclude=__pycache__ ^
    --exclude=*.pyc ^
    --exclude=backend/logs ^
    --exclude=*.log ^
    --exclude=docs/archive ^
    .

if errorlevel 1 (
    echo 错误: 打包失败
    pause
    exit /b 1
)
echo 打包完成: %PACKAGE_NAME%
echo.

echo [3/5] 上传到服务器...
scp %PACKAGE_NAME% %USER%@%SERVER%:/tmp/

if errorlevel 1 (
    echo 错误: 上传失败
    del %PACKAGE_NAME%
    pause
    exit /b 1
)
echo 上传完成
echo.

echo [4/5] 在服务器上更新...
ssh %USER%@%SERVER% "cd %REMOTE_DIR%/current && [ -f .env ] && cp .env /tmp/.env.backup; tar -xzf /tmp/%PACKAGE_NAME%; rm /tmp/%PACKAGE_NAME%; [ -f /tmp/.env.backup ] && mv /tmp/.env.backup .env; echo '文件更新完成'"

if errorlevel 1 (
    echo 错误: 服务器更新失败
    del %PACKAGE_NAME%
    pause
    exit /b 1
)
echo.

echo [5/5] 重启 Docker 服务...
ssh %USER%@%SERVER% "cd %REMOTE_DIR%/current && docker-compose build --no-cache && docker-compose down && docker-compose up -d && sleep 10 && docker-compose ps"

if errorlevel 1 (
    echo 错误: 服务重启失败
    del %PACKAGE_NAME%
    pause
    exit /b 1
)

echo.
echo ==========================================
echo 更新成功！
echo ==========================================
echo.
echo 网站地址: http://%SERVER%
echo.
echo 查看日志:
echo   ssh %USER%@%SERVER% "cd %REMOTE_DIR%/current && docker-compose logs -f"
echo.

REM 清理本地打包文件
del %PACKAGE_NAME%

pause
