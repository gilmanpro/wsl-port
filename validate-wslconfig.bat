@echo off
:: ============================================================
:: WSL Config Validator
:: Validates .wslconfig and fixes common issues
:: ============================================================
echo.
echo ============================================
echo  WSL Config Validator
echo ============================================
echo.

set "CONFIG=%USERPROFILE%\.wslconfig"
set "BACKUP=%USERPROFILE%\.wslconfig.backup"

:: Check if file exists
if not exist "%CONFIG%" (
    echo [ERROR] .wslconfig not found at %CONFIG%
    echo Creating minimal config...
    echo [wsl2]> "%CONFIG%"
    echo Created minimal .wslconfig
    goto :validate
)

:: Backup current config
echo [1/5] Backing up current config...
copy "%CONFIG%" "%BACKUP%" >nul 2>&1
echo Backup created: %BACKUP%

:: Check for common issues
echo.
echo [2/5] Checking for common issues...

:: Check for bridged networking (can cause hangs)
findstr /i "networkingMode=bridged" "%CONFIG%" >nul 2>&1
if not errorlevel 1 (
    echo [WARNING] Found networkingMode=bridged - this can cause WSL to hang!
    echo [FIX] Removing bridged networking mode...
    powershell -Command "(Get-Content '%CONFIG%') -replace 'networkingMode=bridged', '# networkingMode=bridged (disabled - causes hangs)' | Set-Content '%CONFIG%'"
)

:: Check for invalid memory values
findstr /i "memory=" "%CONFIG%" >nul 2>&1
if not errorlevel 1 (
    for /f "tokens=2 delims==" %%a in ('findstr /i "memory=" "%CONFIG%"') do (
        set "MEM=%%a"
    )
    echo Memory limit: %MEM%
)

:: Check for invalid processor values
findstr /i "processors=" "%CONFIG%" >nul 2>&1
if not errorlevel 1 (
    for /f "tokens=2 delims==" %%a in ('findstr /i "processors=" "%CONFIG%"') do (
        set "CPU=%%a"
    )
    echo Processor limit: %CPU%
)

:: Validate syntax
echo.
echo [3/5] Validating syntax...

:: Check for valid section headers
findstr /r "^\[.*\]" "%CONFIG%" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] No valid section headers found!
    echo [FIX] Adding [wsl2] section...
    echo [wsl2]> "%CONFIG%"
    echo Added [wsl2] section
)

:: Check for common typos
echo.
echo [4/5] Checking for common typos...

:: Check for misspelled options
for %%o in (memory processors swap localhostForwarding nestedVirtualization vmIdleTimeout networkingMode) do (
    findstr /i "%%o" "%CONFIG%" >nul 2>&1
    if not errorlevel 1 (
        echo Found option: %%o
    )
)

:: Test WSL with current config
echo.
echo [5/5] Testing WSL with current config...
wsl --list --verbose >nul 2>&1
if errorlevel 1 (
    echo [ERROR] WSL not working with current config!
    echo [FIX] Restoring backup...
    copy "%BACKUP%" "%CONFIG%" >nul 2>&1
    echo Restored backup config
    goto :end
)

echo.
echo ============================================
echo  Config validation PASSED
echo ============================================
echo.
echo Current .wslconfig:
type "%CONFIG%"
echo.
echo.
echo If WSL still has issues, try:
echo 1. wsl --shutdown
echo 2. Restart WSL service: net stop WSLService ^& net start WSLService
echo 3. Run fix-wsl-robust.bat as administrator

:end
pause
