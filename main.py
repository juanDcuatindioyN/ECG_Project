#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Proyecto ECG - Solucionador de Malla VTK con Poisson
Compatible con Python 3.8+
"""

import sys
import os
import logging
import argparse

# Verificar version minima de Python
if sys.version_info < (3, 8):
    print("ERROR: Se requiere Python 3.8 o superior.")
    print("Version actual: {}".format(sys.version))
    sys.exit(1)

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)

# Agregar src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src import ECGAppAuto as ECGApp, __version__, __description__


def run_gui():
    """Ejecuta la interfaz grafica principal."""
    try:
        import tkinter  # noqa: F401
        print("Iniciando {} v{}".format(__description__, __version__))
        print("Python {}".format(sys.version.split()[0]))
        print("Formatos soportados: VTK, Gmsh (.msh), STL, OBJ, PLY, y mas")
        app = ECGApp(None)
        app.root.mainloop()
    except ImportError as e:
        print("Error: Falta dependencia requerida: {}".format(e))
        print("Instala las dependencias con: python -m pip install -r requirements.txt")
        return 1
    except Exception as e:
        print("Error inesperado: {}".format(e))
        return 1
    return 0


def run_tests():
    """Ejecuta la suite de pruebas."""
    try:
        from tests.run_all_tests import main as run_all_tests
        return run_all_tests()
    except ImportError:
        print("Error: No se pueden importar las pruebas")
        return 1


def run_demo():
    """Ejecuta la demostracion del solver ECG."""
    try:
        sys.path.insert(0, 'examples')
        from examples.demo_ecg_solver import main as demo_main
        return demo_main()
    except ImportError:
        print("Error: No se puede importar la demostracion")
        return 1
    except Exception as e:
        print("Error en demostracion: {}".format(e))
        return 1


def show_info():
    """Muestra informacion del proyecto."""
    print("=" * 60)
    print(__description__)
    print("Version: {}  |  Python: {}".format(__version__, sys.version.split()[0]))
    print("=" * 60)
    print("\nComandos:")
    print("  python main.py           - Ejecutar interfaz grafica")
    print("  python main.py --test    - Ejecutar pruebas")
    print("  python main.py --demo    - Ver demostracion")
    print("  python main.py --info    - Mostrar esta informacion")
    print("\nO simplemente haz doble clic en: iniciar.bat")
    print("=" * 60)


def main():
    """Funcion principal."""
    parser = argparse.ArgumentParser(
        description=__description__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('--version', action='version',
                        version='%(prog)s {}'.format(__version__))
    parser.add_argument('--test',  action='store_true',
                        help='Ejecutar suite de pruebas')
    parser.add_argument('--demo',  action='store_true',
                        help='Ejecutar demostracion')
    parser.add_argument('--info',  action='store_true',
                        help='Mostrar informacion del proyecto')

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


if __name__ == "__main__":
    sys.exit(main())
