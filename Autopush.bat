@echo off

cd /d C:\Users\tham\amis

git add .

git commit -m "Auto backup %date% %time%"

git push origin main

pause