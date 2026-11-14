@echo off
chcp 65001 >nul
cd /d "%~dp0.."
echo 打包中（目录版）...
py -3.14 -m PyInstaller v3\AppTimer-onedir.spec --noconfirm --distpath v3\dist --workpath v3\build
if errorlevel 1 (
  echo 打包失败
  pause
  exit /b 1
)
echo.
echo 产物：v3\dist\AppTimer\AppTimer.exe
echo 分发方式：整个 v3\dist\AppTimer 文件夹压缩后发给用户
pause
