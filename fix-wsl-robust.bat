@echo off
:: ============================================================
:: WSL Emergency Recovery Script
:: Run as Administrator
:: ============================================================
echo.
echo ============================================
echo  WSL Emergency Recovery
echo  Run as Administrator
echo ============================================
echo.

:: Step 1: Kill all WSL processes
echo [1/6] Killing all WSL processes...
taskkill /F /IM wsl.exe 2>nul
taskkill /F /IM wslhost.exe 2>nul
taskkill /F /IM wslrelay.exe 2>nul
taskkill /F /IM wslservice.exe 2>nul
timeout /t 3 /nobreak >nul

:: Step 2: Stop WSL service
echo [2/6] Stopping WSL service...
net stop WSLService 2>nul
timeout /t 5 /nobreak >nul

:: Step 3: Kill vmmemWSL (Hyper-V VM)
echo [3/6] Killing vmmemWSL...
taskkill /F /IM vmmemWSL 2>nul
timeout /t 3 /nobreak >nul

:: Step 4: Reset .wslconfig to minimal
echo [4/6] Resetting .wslconfig...
echo [wsl2]> "%USERPROFILE%\.wslconfig"
echo .wslconfig reset to minimal

:: Step 5: Start WSL service
echo [5/6] Starting WSL service...
net start WSLService 2>nul
timeout /t 5 /nobreak >nul

:: Step 6: Test WSL
echo [6/6] Testing WSL...
wsl --list --verbose
if errorlevel 1 (
    echo.
    echo ============================================
    echo  WSL still not working!
    echo  Try: wsl --shutdown
    echo  Then: wsl --list --verbose
    echo ============================================
    pause
    exit /b 1
)

echo.
echo ============================================
echo  WSL recovered successfully!
echo ============================================
pause
