@echo off
:: Heezo Auto-Push — runs silently via Task Scheduler
:: Commits and pushes any pending changes every 30 minutes

cd /d D:\heezo_repo

:: Check if there are any changes
git status --porcelain > nul 2>&1
for /f %%i in ('git status --porcelain') do (
    goto :has_changes
)
:: No changes — exit silently
exit /b 0

:has_changes
:: Stage all changes
git add -A

:: Commit with timestamp
for /f "tokens=1-3 delims=/ " %%a in ('date /t') do set mydate=%%c-%%a-%%b
for /f "tokens=1-2 delims=: " %%a in ('time /t') do set mytime=%%a:%%b
git commit -m "🤖 Auto-deploy: %mydate% %mytime%"

:: Push to origin
git push origin main

exit /b 0
