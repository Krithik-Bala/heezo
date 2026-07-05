@echo off
cd /d D:\heezo_repo
git add .
git commit -m "🚀 Auto-deploy by Heezo Bot"
git push
echo.
echo ✅ Deployed to heezo.vercel.app!
pause
