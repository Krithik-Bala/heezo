@echo off
:: Sets up a Windows Scheduled Task that runs deploy.bat every 5 minutes
:: Run this ONCE as Administrator to enable auto-deploy

echo Setting up Heezo Auto-Deploy...
echo.

:: Create a silent deploy script (no pause, no window)
echo @echo off > "D:\heezo_repo\auto_deploy_silent.bat"
echo cd /d D:\heezo_repo >> "D:\heezo_repo\auto_deploy_silent.bat"
echo git add . >> "D:\heezo_repo\auto_deploy_silent.bat"
echo git diff --cached --quiet >> "D:\heezo_repo\auto_deploy_silent.bat"
echo if errorlevel 1 ( >> "D:\heezo_repo\auto_deploy_silent.bat"
echo     git commit -m "Auto-deploy by Heezo Bot" >> "D:\heezo_repo\auto_deploy_silent.bat"
echo     git push >> "D:\heezo_repo\auto_deploy_silent.bat"
echo ) >> "D:\heezo_repo\auto_deploy_silent.bat"

:: Create the scheduled task (runs every 5 minutes, silently)
schtasks /create /tn "HeezoAutoDeploy" /tr "D:\heezo_repo\auto_deploy_silent.bat" /sc minute /mo 5 /f /rl HIGHEST

echo.
echo ✅ Auto-deploy scheduled! Every 5 minutes, any new changes push automatically.
echo    Task name: HeezoAutoDeploy
echo.
echo To stop auto-deploy later, run:
echo    schtasks /delete /tn "HeezoAutoDeploy" /f
echo.
pause
