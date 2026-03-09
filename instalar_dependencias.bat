@echo off
echo ============================================================
echo Instalador de Dependencias - Proyecto ECG
echo ============================================================
echo.

echo Verificando Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python no esta instalado o no esta en el PATH
    echo.
    echo Por favor, instala Python desde https://www.python.org/downloads/
    echo IMPORTANTE: Marca "Add Python to PATH" durante la instalacion
    echo.
    pause
    exit /b 1
)

echo Python encontrado!
python --version
echo.

echo Verificando pip...
pip --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: pip no esta disponible
    echo.
    pause
    exit /b 1
)

echo pip encontrado!
echo.

echo ============================================================
echo Instalando dependencias...
echo ============================================================
echo.

echo [1/4] Instalando numpy...
pip install numpy>=1.19.0

echo.
echo [2/4] Instalando matplotlib...
pip install matplotlib>=3.3.0

echo.
echo [3/4] Instalando scikit-fem...
pip install scikit-fem>=3.0.0

echo.
echo [4/4] Instalando meshio...
pip install meshio>=4.0.0

echo.
echo ============================================================
echo Verificando instalacion...
echo ============================================================
echo.

python verificar_instalacion.py

echo.
echo ============================================================
echo Instalacion completada!
echo ============================================================
echo.
echo Para ejecutar la aplicacion:
echo   python main.py
echo.
pause
