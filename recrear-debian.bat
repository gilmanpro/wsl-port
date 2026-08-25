@echo off
:: ============================================================
:: Recrear Debian + arreglar causa raiz (nssm-wsl-debian)
:: EJECUTAR COMO ADMINISTRADOR
:: ============================================================
echo.
echo ============================================
echo  Recrear Debian y arreglar WSL
echo  EJECUTAR COMO ADMINISTRADOR
echo ============================================
echo.

echo [1/6] Deteniendo servicio nssm-wsl-debian (causa raiz)...
sc stop nssm-wsl-debian
timeout /t 3 /nobreak >nul
sc config nssm-wsl-debian start= disabled
echo   Servicio nssm-wsl-debian DETENIDO y deshabilitado.
echo.

echo [2/6] Matando procesos wsl.exe colgados...
taskkill /F /IM wsl.exe 2>nul
taskkill /F /IM wslhost.exe 2>nul
timeout /t 3 /nobreak >nul
echo.

echo [3/6] Reiniciando servicio WSL...
net stop WSLService 2>nul
timeout /t 3 /nobreak >nul
net start WSLService 2>nul
timeout /t 3 /nobreak >nul
echo.

echo [4/6] Verificando WSL...
wsl --list --verbose
echo.

echo [5/6] Unregister Debian (borra datos)...
wsl --unregister Debian
if errorlevel 1 (
    echo   ERROR al unregister. Reintenta o revisa WSL.
    pause
    exit /b 1
)
echo   Debian eliminada.
echo.

echo [6/6] Instalando Debian limpia (puede tardar varios minutos)...
wsl --install -d Debian
if errorlevel 1 (
    echo   ERROR al instalar. Revisa conexion a internet.
    pause
    exit /b 1
)
echo   Debian instalada.
echo.

echo Verificando Debian...
wsl -d Debian -- hostname
if errorlevel 1 (
    echo   Debian instalada pero no responde aun. Prueba: wsl -d Debian
    pause
    exit /b 1
)
echo.
echo ============================================
echo  Debian recreada correctamente!
echo  - Servicio nssm-wsl-debian deshabilitado (evita futuros colgados)
echo  - Puedes volver a configurar tus servicios (Jellyfin, etc.)
echo ============================================
pause