#!/usr/bin/env python3
"""
Ejecutor principal de todas las pruebas del proyecto ECG
======================================================

Este script ejecuta todas las pruebas disponibles y proporciona
un resumen completo del estado del proyecto.
"""

import sys
import os
import traceback

# Agregar el directorio padre al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from tests.test_core import run_core_tests
from tests.test_gui import run_gui_tests


def test_project_structure():
    """Verifica la estructura del proyecto"""
    print(" VERIFICANDO ESTRUCTURA DEL PROYECTO")
    print("="*50)
    
    required_dirs = ['src', 'tests', 'examples', 'docs', 'data']
    required_files = [
        'src/__init__.py',
        'src/app.py',
        'src/core/mesh_loader.py',
        'src/core/ecg_solver.py',
        'src/generation/mesh_generator.py',
        'src/visualization/viewer3d.py',
        'main.py',
        'README.md',
        'requirements.txt'
    ]

    missing_items = []
    base = os.path.join(os.path.dirname(__file__), '..')

    # Verificar directorios
    print(" Verificando directorios...")
    for dir_name in required_dirs:
        dir_path = os.path.join(base, dir_name)
        if os.path.exists(dir_path):
            print(f"   {dir_name}/")
        else:
            print(f"   {dir_name}/ - FALTANTE")
            missing_items.append(f"directorio {dir_name}")

    # Verificar archivos
    print("\n Verificando archivos principales...")
    for file_name in required_files:
        file_path = os.path.join(base, file_name)
        if os.path.exists(file_path):
            print(f"    {file_name}")
        else:
            print(f"    {file_name} - FALTANTE")
            missing_items.append(f"archivo {file_name}")

    # Verificar archivo de datos
    data_found = False
    for data_file in ['data/Sphere.vtk', 'data/ecg_torso_v2_con_pulmones.msh']:
        if os.path.exists(os.path.join(base, data_file)):
            print(f"    {data_file} (archivo de datos)")
            data_found = True
            break

    if not data_found:
        print("    Sphere.vtk no encontrado en data/")
        missing_items.append("archivo de datos Sphere.vtk")
    
    return len(missing_items) == 0, missing_items


def test_dependencies():
    """Verifica las dependencias"""
    print("\n VERIFICANDO DEPENDENCIAS")
    print("="*50)
    
    required_packages = [
        ('numpy',      'Cálculos numéricos'),
        ('matplotlib', 'Visualización'),
        ('skfem',      'Elementos finitos'),
        ('meshio',     'Lectura VTK'),
        ('tkinter',    'Interfaz gráfica'),
        ('scipy',      'Solver lineal'),
    ]
    
    optional_packages = [
        ('tkinterdnd2', 'Drag & Drop')
    ]
    
    missing_required = []
    
    print(" Dependencias requeridas...")
    for package, description in required_packages:
        try:
            if package == 'tkinter':
                import tkinter
            else:
                __import__(package.replace('-', '_'))
            print(f"    {package:15} - {description}")
        except ImportError:
            print(f"    {package:15} - {description} (FALTANTE)")
            missing_required.append(package)
    
    print("\n Dependencias opcionales...")
    for package, description in optional_packages:
        try:
            __import__(package)
            print(f"    {package:15} - {description}")
        except ImportError:
            print(f"    {package:15} - {description} (no disponible)")
    
    return len(missing_required) == 0, missing_required


def main():
    """Ejecuta todas las pruebas"""
    print(" SUITE COMPLETA DE PRUEBAS - PROYECTO ECG")
    print("="*60)
    print()
    
    # Lista de todas las pruebas
    all_tests = []
    
    # 1. Estructura del proyecto
    try:
        structure_ok, missing_items = test_project_structure()
        all_tests.append(("Estructura del proyecto", structure_ok))
        if not structure_ok:
            print(f"\n Elementos faltantes: {', '.join(missing_items)}")
    except Exception as e:
        print(f"ERROR Error verificando estructura: {e}")
        all_tests.append(("Estructura del proyecto", False))
    
    print()
    
    # 2. Dependencias
    try:
        deps_ok, missing_deps = test_dependencies()
        all_tests.append(("Dependencias", deps_ok))
        if not deps_ok:
            print(f"\n Dependencias faltantes: {', '.join(missing_deps)}")
    except Exception as e:
        print(f"ERROR Error verificando dependencias: {e}")
        all_tests.append(("Dependencias", False))
    
    print()
    
    # 3. Pruebas del módulo core
    try:
        core_ok = run_core_tests()
        all_tests.append(("Módulo Core", core_ok))
    except Exception as e:
        print(f"ERROR Error en pruebas core: {e}")
        traceback.print_exc()
        all_tests.append(("Módulo Core", False))
    
    print()
    
    # 4. Pruebas del módulo GUI
    try:
        gui_ok = run_gui_tests()
        all_tests.append(("Módulo GUI", gui_ok))
    except Exception as e:
        print(f" Error en pruebas GUI: {e}")
        traceback.print_exc()
        all_tests.append(("Módulo GUI", False))
    
    # Resumen final
    print("\n" + "="*60)
    print(" RESUMEN FINAL DE TODAS LAS PRUEBAS")
    print("="*60)
    
    all_passed = True
    for name, passed in all_tests:
        status = " PASÓ" if passed else " FALLÓ"
        print(f"{name:25} - {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "="*60)
    
    if all_passed:
        print(" ¡TODAS LAS PRUEBAS PASARON!")
        print("\n El proyecto está completamente funcional:")
        print("   • Estructura correcta")
        print("   • Dependencias instaladas")
        print("   • Módulos funcionando")
        print("   • Interfaz operativa")
        print("\n Para usar la aplicación:")
        print("   python main.py")
    else:
        print(" ALGUNAS PRUEBAS FALLARON")
        print("\n Acciones recomendadas:")
        print("   1. Instalar dependencias faltantes")
        print("   2. Verificar estructura de archivos")
        print("   3. Revisar errores específicos arriba")
        print("   4. Ejecutar pruebas individuales para más detalles")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())