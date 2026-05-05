@echo off
title Solucionador ECG
color 0A
echo.
echo  ============================================
echo   Solucionador ECG - Iniciando...
echo  ============================================
echo.

:: Buscar Python disponible (cualquier version 3.x)
set PYTHON_CMD=

:: Intentar con 'python' primero
python --version >nul 2>&1
if %errorlevel% == 0 (
    for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PY_VER=%%v
    echo  Python encontrado: %PY_VER%
    set PYTHON_CMD=python
    goto :check_version
)

:: Intentar con 'python3'
python3 --version >nul 2>&1
if %errorlevel% == 0 (
    for /f "tokens=2" %%v in ('python3 --version 2^>^&1') do set PY_VER=%%v
    echo  Python encontrado: %PY_VER%
    set PYTHON_CMD=python3
    goto :check_version
)

:: Intentar con 'py' (launcher de Windows)
py --version >nul 2>&1
if %errorlevel% == 0 (
    for /f "tokens=2" %%v in ('py --version 2^>^&1') do set PY_VER=%%v
    echo  Python encontrado: %PY_VER%
    set PYTHON_CMD=py
    goto :check_version
)

echo  [ERROR] No se encontro Python instalado.
echo.
echo  Instala Python desde: https://www.python.org/downloads/
echo  Asegurate de marcar "Add Python to PATH" durante la instalacion.
echo.
pause
exit /b 1

:check_version
:: Verificar que sea Python 3
%PYTHON_CMD% -c "import sys; exit(0 if sys.version_info.major >= 3 else 1)" >nul 2>&1
if %errorlevel% neq 0 (
    echo  [ERROR] Se requiere Python 3 o superior.
    echo  Version encontrada: %PY_VER%
    pause
    exit /b 1
)

:: Verificar dependencias
echo.
echo  Verificando dependencias...
%PYTHON_CMD% -c "import numpy, scipy, matplotlib, skfem, meshio" >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo  Faltan dependencias. Instalando...
    echo  (Esto solo ocurre la primera vez)
    echo.
    %PYTHON_CMD% -m pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo.
        echo  [ERROR] No se pudieron instalar las dependencias.
        echo  Intenta manualmente: %PYTHON_CMD% -m pip install -r requirements.txt
        echo.
        pause
        exit /b 1
    )
    echo.
    echo  Dependencias instaladas correctamente.
)

:: Lanzar la aplicacion
echo.
echo  Lanzando aplicacion...
echo.
%PYTHON_CMD% main.py
if %errorlevel% neq 0 (
    echo.
    echo  [ERROR] La aplicacion cerro con un error.
    echo  Revisa los mensajes anteriores.
    echo.
    pause
)
