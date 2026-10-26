@echo off
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0deploy.ps1" %*
if errorlevel 1 (
  echo.
  echo IdentityAI deployment failed. Review the error above.
  pause
  exit /b 1
)
endlocal
