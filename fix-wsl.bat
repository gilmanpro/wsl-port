@echo off
echo === Reparando WSL ===
echo.
echo 1. Cerrando procesos WSL...
taskkill /F /IM wslservice.exe 2>nul
taskkill /F /IM wslhost.exe 2>nul
taskkill /F /IM wslrelay.exe 2>nul
timeout /t 3 /nobreak >nul
echo.
echo 2. Restaurando .wslconfig...
echo [wsl2] > "%USERPROFILE%\.wslconfig"
echo.
echo 3. Reiniciando servicio WSL...
net stop LxssManager 2>nul
net start LxssManager 2>nul
echo.
echo 4. Probando WSL...
wsl --version
echo.
echo === Reparacion completada ===
echo.
echo Si WSL sigue colgado, reinicia el PC.
pause
