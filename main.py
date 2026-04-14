#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Proyecto ECG - Solucionador de Malla VTK con Poisson
===================================================

Autor: Proyecto ECG
Versión: 1.0.0
"""

import sys
import os
import logging
import argparse

# Configurar logging básico para la aplicación
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)

# Agregar src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src import ECGAppAuto as ECGApp, __version__, __description__


def run_gui():
    """Ejecuta la interfaz gráfica principal"""
    try:
        import tkinter as tk
        
        print(f"Iniciando {__description__} v{__version__}")
        print("Formatos soportados: VTK, Gmsh (.msh), STL, OBJ, PLY, y más")
        print("Arrastra archivos o usa el botón para cargar")
        
        # Crear la aplicación directamente sin crear root por separado
        app = ECGApp(None)  # Pasamos None para que la clase cree su propia ventana
        
        app.root.mainloop()
        
    except ImportError as e:
        print(f"Error: Falta dependencia requerida: {e}")
        print("Instala las dependencias con: pip install -r requirements.txt")
        return 1
    except Exception as e:
        print(f"Error inesperado: {e}")
        return 1
    
    return 0


def run_tests():
    """Ejecuta la suite de pruebas"""
    try:
        from tests.run_all_tests import main as run_all_tests
        return run_all_tests()
    except ImportError:
        print("Error: No se pueden importar las pruebas")
        print("Verifica que el directorio tests/ existe y contiene los archivos necesarios")
        return 1


def run_demo():
    """Ejecuta la demostración del solver ECG"""
    try:
        import sys
        sys.path.insert(0, 'examples')
        from examples.demo_ecg_solver import main as demo_main
        return demo_main()
    except ImportError:
        print("Error: No se puede importar la demostración")
        print("Ejecuta directamente: py -3.13 -m examples.demo_ecg_solver")
        return 1
    except Exception as e:
        print(f"Error en demostración: {e}")
        return 1


def main():
    """Función principal"""
    parser = argparse.ArgumentParser(
        description=__description__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    parser.add_argument('--version', action='version', version=f'%(prog)s {__version__}')
    parser.add_argument('--test', action='store_true', help='Ejecutar suite de pruebas')
    parser.add_argument('--demo', action='store_true', help='Ejecutar demostración')
    parser.add_argument('--info', action='store_true', help='Mostrar información del proyecto')
    
    args = parser.parse_args()
    
    if args.test:
        return run_tests()
    elif args.demo:
        return run_demo()
    elif args.info:
        show_info()
        return 0
    else:
        return run_gui()


def show_info():
    """Muestra información del proyecto"""
    print("=" * 60)
    print(f"{__description__}")
    print(f"Versión: {__version__}")
    print("=" * 60)
    print("\nModos de Operación:")
    print("  1. Modo Básico (GUI)    - Resolución de Poisson con interfaz gráfica")
    print("  2. Modo Avanzado (API)  - Simulador completo de ECG con FEM")
    print("\nComandos:")
    print("  python main.py           - Ejecutar interfaz gráfica")
    print("  python main.py --test    - Ejecutar pruebas")
    print("  python main.py --demo    - Ver demostración")
    print("  python main.py --info    - Mostrar esta información")
    print("\nEjemplos de Uso:")
    print("  Modo Básico:")
    print("    python main.py")
    print("    # Arrastra archivos .vtk, .msh, .stl, .obj, etc.")
    print("    # Soporta múltiples formatos de malla")
    print("\n  Modo Avanzado:")
    print("    python examples/demo_ecg_solver.py")
    print("\n  API Programática:")
    print("    from src.ecg_solver import ECGSolver")
    print("    solver = ECGSolver('data/ecg_torso_v2_con_pulmones.msh')")
    print("    results = solver.run_full_pipeline()")
    print("\nDocumentación:")
    print("  docs/QUICK_START.md       - Guía de inicio rápido")
    print("  docs/ECG_SOLVER_GUIDE.md  - Guía técnica completa")
    print("  README.md                 - Descripción general")
    print("\nArchivos de Datos:")
    print("  data/Sphere.vtk                        - Malla simple (modo básico)")
    print("  data/ecg_torso_v2_con_pulmones.msh     - Malla ECG completa")
    print("=" * 60)


if __name__ == "__main__":
    sys.exit(main())