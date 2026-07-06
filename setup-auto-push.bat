@echo off
:: One-time setup: Creates a Task Scheduler job to run auto-push every 30 minutes
:: Run this AS ADMINISTRATOR once, then delete it

echo Setting up Heezo Auto-Push scheduled task...

schtasks /create ^
  /tn "Heezo Auto Push" ^
  /tr "D:\heezo_repo\auto-push.bat" ^
  /sc minute ^
  /mo 30 ^
  /f

if %errorlevel% equ 0 (
    echo.
    echo ✅ Done! "Heezo Auto Push" will run every 30 minutes.
    echo    - Silently commits and pushes any changes in D:\heezo_repo
    echo    - Uses your Windows Credential Manager for GitHub auth
    echo    - Does nothing if there are no changes
    echo.
    echo To remove later: schtasks /delete /tn "Heezo Auto Push" /f
) else (
    echo.
    echo ❌ Failed. Make sure you're running this as Administrator.
)

pause
