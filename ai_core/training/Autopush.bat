@echo off

cd /d "E:\Amis"

git add .

git diff --cached --quiet && (
    echo No changes to commit.
) || (
    git commit -m "Auto backup %date% %time%"
    git push origin main
)

pause