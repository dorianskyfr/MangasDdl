@echo off
chcp 65001 > nul
title Publier MangasDdl sur GitHub
cd /d "%~dp0"
set "PATH=%LOCALAPPDATA%\Programs\MinGit\cmd;%PATH%"

echo ========================================================
echo   📤 Publication du projet vers GitHub : MangasDdl
echo ========================================================
echo.
echo Dépôt cible : https://github.com/dorianskyfr/MangasDdl.git
echo.

git add .
git commit -m "Mise a jour de MangasDdl"
git push origin main

if %errorlevel% neq 0 (
    echo.
    echo ⚠️ Une erreur est survenue lors de l'envoi.
) else (
    echo.
    echo 🎉 Projet publié avec succès sur https://github.com/dorianskyfr/MangasDdl !
)
echo.
pause
