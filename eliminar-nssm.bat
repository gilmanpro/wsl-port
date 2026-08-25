@echo off
rem Eliminar servicio nssm-wsl-debian (causa raiz de colgados WSL)
rem IMPORTANTE: click derecho sobre este archivo -> Ejecutar como administrador

echo ============================================
echo  Eliminar servicio nssm-wsl-debian
echo ============================================
echo.

echo [1/3] Renombrando wsl-debian.bat (backup)...
set "BAT=C:\Users\Gilman\Desktop\APPplicaciones\wsl-debian.bat"
if exist "%BAT%" ren "%BAT%" "wsl-debian.bat.disabled"
echo   ok.

echo [2/3] Deteniendo y eliminando servicio...
sc stop nssm-wsl-debian 2>nul
timeout /t 2 /nobreak >nul
sc delete nssm-wsl-debian

echo [3/3] Verificando...
sc query nssm-wsl-debian 2>nul
if errorlevel 1 echo   SERVICIO ELIMINADO.
echo.

echo Verificando WSL...
wsl --list --verbose
echo.
echo ============================================
echo  Listo. wsl-port gestiona las distros.
echo ============================================
pause