@echo off
echo ============================================
echo  Test Export/Import WSL
echo ============================================
echo.

echo [1] Verifying WSL...
wsl --list --verbose
if errorlevel 1 (
    echo ERROR: WSL not working
    pause
    exit /b 1
)

echo.
echo [2] Testing export Ubuntu-26.04...
wsl --export Ubuntu-26.04 "%USERPROFILE%\Downloads\test_export.tar"
if errorlevel 1 (
    echo ERROR: Export failed
    pause
    exit /b 1
)
echo Export OK: %USERPROFILE%\Downloads\test_export.tar

echo.
echo [3] Testing import as test-distro...
wsl --import test-distro "%USERPROFILE%\WSL\test-distro" "%USERPROFILE%\Downloads\test_export.tar"
if errorlevel 1 (
    echo ERROR: Import failed
    pause
    exit /b 1
)
echo Import OK: test-distro

echo.
echo [4] Verifying import...
wsl -d test-distro -- echo "test-distro works!"

echo.
echo [5] Cleaning up test-distro...
wsl --unregister test-distro

echo.
echo [6] Cleaning up test file...
del "%USERPROFILE%\Downloads\test_export.tar"

echo.
echo ============================================
echo  Test PASSED - Export/Import works!
echo ============================================
pause
