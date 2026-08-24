@echo off
echo ============================================
echo  WSL Emergency Fix - Run as Administrator
echo ============================================
echo.

echo [1] Killing WSL processes...
taskkill /F /IM wsl.exe 2>nul
taskkill /F /IM wslhost.exe 2>nul
taskkill /F /IM wslrelay.exe 2>nul
timeout /t 3 /nobreak >nul

echo [2] Stopping WSL service...
net stop WSLService 2>nul
timeout /t 3 /nobreak >nul

echo [3] Starting WSL service...
net start WSLService 2>nul
timeout /t 3 /nobreak >nul

echo [4] Testing WSL...
wsl --list --verbose
echo.

echo [5] Restoring .wslconfig to minimal...
echo [wsl2]> "%USERPROFILE%\.wslconfig"
echo Done.

echo.
echo ============================================
echo  WSL should be working now. Test with:
echo  wsl --list --verbose
echo ============================================
pause
