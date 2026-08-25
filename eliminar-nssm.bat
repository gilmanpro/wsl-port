@echo off
:: ============================================================
:: Eliminar servicio nssm-wsl-debian (causa raiz de colgados WSL)
:: EJECUTAR COMO ADMINISTRADOR
:: ============================================================
echo.
echo ============================================
echo  Eliminar servicio nssm-wsl-debian
echo  EJECUTAR COMO ADMINISTRADOR
echo ============================================
echo.
echo El servicio nssm-wsl-debian abre una sesion persistente de
echo Debian en cada arranque (wsl -d debian). Cuando Debian se
echo atasca, ese servicio deja wsl.exe colgados que degradan
echo todo WSL. La app wsl-port ya gestiona las distros mejor.
echo.
echo Se eliminara el servicio. Se conserva el .bat original.
echo.

set "BAT=C:\Users\Gilman\Desktop\APPlicaciones\wsl-debian.bat"
if exist "%BAT%" (
    echo [1/3] Renombrando el .bat original (backup)...
    ren "%BAT%" "wsl-debian.bat.disabled"
    echo   Backup: wsl-debian.bat.disabled
) else (
    echo [1/3] El .bat original no existe, continuando...
)

echo [2/3] Eliminando servicio nssm-wsl-debian...
sc stop nssm-wsl-debian 2>nul
timeout /t 2 /nobreak >nul
sc delete nssm-wsl-debian
if errorlevel 1 (
    echo   ERROR: no se pudo eliminar. Verifica permisos.
    pause
    exit /b 1
)
echo   Servicio ELIMINADO.
echo.

echo [3/3] Verificando que WSL sigue funcionando...
wsl --list --verbose
echo.
echo ============================================
echo  Servicio eliminado. WSL ya no se colgara por esto.
echo  La app wsl-port gestiona las distros (iniciar,
echo  detener, tunnels, forwards) sin necesidad del servicio.
echo ============================================
pause