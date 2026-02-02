#!/usr/bin/env python3
"""
Proyecto ECG - Solucionador de Malla VTK con Poisson
===================================================

Aplicación principal para resolver ecuaciones de Poisson en mallas VTK
con interfaz gráfica interactiva y visualización 3D.

Uso:
    python main.py              # Ejecutar interfaz gráfica
    python main.py --help       # Mostrar ayuda
    python main.py --test       # Ejecutar pruebas
    python main.py --demo       # Ejecutar demostración

Autor: Proyecto ECG
Versión: 1.0.0
"""

import sys
import os
import argparse

# Agregar src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src import ECGAppAuto as ECGApp, __version__, __description__


def run_gui():
    """Ejecuta la interfaz gráfica principal"""
    try:
        import tkinter as tk
        
        # Intentar usar TkinterDnD si está disponible
        try:
            from tkinterdnd2 import TkinterDnD
            root = TkinterDnD.Tk()
        except ImportError:
            root = tk.Tk()
            print("Nota: Drag & Drop no disponible. Instala tkinterdnd2 para esta funcionalidad.")
        
        app = ECGApp(root)
        
        print(f"Iniciando {__description__} v{__version__}")
        print("Arrastra archivos .vtk o usa el botón para cargar")
        
        root.mainloop()
        
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
    """Ejecuta la demostración"""
    try:
        sys.path.insert(0, 'examples')
        from demo_automatic import main as demo_main
        return demo_main()
    except ImportError:
        print("Error: No se puede importar la demostración")
        print("Verifica que el archivo examples/demo_automatic.py existe")
        return 1
    except Exception as e:
        print(f"Error en demostración: {e}")
        return 1


def show_info():
    """Muestra información del proyecto"""
    print(f"""
{__description__}

Versión: {__version__}

Características:
  • Interfaz gráfica moderna con Tkinter
  • Carga interactiva de archivos VTK (con drag & drop)
  • Resolución automática de ecuaciones de Poisson
  • Visualización 3D integrada con matplotlib
  • Procesamiento asíncrono con barras de progreso
  • Detección automática de parámetros óptimos

Estructura del proyecto:
  src/           - Código fuente principal
  tests/         - Suite de pruebas
  examples/      - Ejemplos y demostraciones
  docs/          - Documentación
  data/          - Archivos de datos (mallas VTK)

Comandos disponibles:
  python main.py           - Ejecutar aplicación
  python main.py --test    - Ejecutar pruebas
  python main.py --demo    - Ver demostración
  python main.py --info    - Mostrar esta información

Para más información, consulta README.md
""")


def main():
    """Función principal"""
    parser = argparse.ArgumentParser(
        description=__description__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python main.py                    # Ejecutar interfaz gráfica
  python main.py --test             # Ejecutar todas las pruebas
  python main.py --demo             # Ver demostración de capacidades
  python main.py --info             # Mostrar información del proyecto
        """
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


if __name__ == "__main__":
    sys.exit(main())