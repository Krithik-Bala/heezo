@echo off 
cd /d D:\heezo_repo 
git add . 
git diff --cached --quiet 
if errorlevel 1 ( 
    git commit -m "Auto-deploy by Heezo Bot" 
    git push 
) 
