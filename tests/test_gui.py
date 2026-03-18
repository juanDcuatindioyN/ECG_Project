#!/usr/bin/env python3
"""
Pruebas para el módulo GUI del proyecto ECG
==========================================
"""

import sys
import os
import traceback
import tkinter as tk

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src import ECGAppAuto as ECGApp


def test_gui_imports():
    """Prueba las importaciones de GUI"""
    print(" Probando importaciones de GUI...")
    try:
        import tkinter as tk
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        from matplotlib.figure import Figure
        print("   OK Tkinter y Matplotlib")
        try:
            from tkinterdnd2 import DND_FILES, TkinterDnD
            print("   OK TkinterDnD (Drag & Drop disponible)")
        except ImportError:
            print("   ADVERTENCIA TkinterDnD no disponible")
        return True
    except Exception as e:
        print(f"   ERROR: {e}")
        return False


def test_app_creation():
    """Prueba la creación de la aplicación"""
    print("\n Probando creación de aplicación...")
    try:
        root = tk.Tk()
        root.withdraw()
        app = ECGApp(root)
        print("   OK Aplicación creada correctamente")

        # Atributos de estado que debe tener ECGAppAuto
        required_attrs = ['mesh', 'mio', 'tris', 'current_solution',
                          'auto_sources', 'auto_charges', 'file_path']
        for attr in required_attrs:
            assert hasattr(app, attr), f"App debe tener atributo: {attr}"
        print("   OK Atributos de estado presentes")

        root.destroy()
        return True
    except Exception as e:
        print(f"   ERROR: {e}")
        traceback.print_exc()
        return False


def test_ui_components():
    """Prueba los componentes de UI"""
    print("\n Probando componentes de UI...")
    try:
        root = tk.Tk()
        root.withdraw()
        app = ECGApp(root)

        widgets_to_check = [
            'file_button', 'preview_button', 'auto_solve_button',
            'progress_bar', 'status_label', 'file_info', 'analysis_info'
        ]
        for widget_name in widgets_to_check:
            assert hasattr(app, widget_name), f"Falta widget: {widget_name}"
        print("   OK Todos los widgets principales presentes")

        # Estados iniciales
        assert app.preview_button['state'] == 'disabled', "Preview debe estar deshabilitado"
        assert app.auto_solve_button['state'] == 'disabled', "Auto-solve debe estar deshabilitado"
        print("   OK Estados iniciales correctos")

        root.destroy()
        return True
    except Exception as e:
        print(f"   ERROR: {e}")
        traceback.print_exc()
        return False


def test_format_helpers():
    """Prueba los helpers de formateo internos de la app"""
    print("\n Probando helpers de formateo...")
    try:
        import numpy as np
        root = tk.Tk()
        root.withdraw()
        app = ECGApp(root)

        sources = np.array([[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]])
        charges = np.array([1.0, -1.0])

        s_str = app._format_sources_for_display(sources)
        c_str = app._format_charges_for_display(charges)
        print(f"   OK Fuentes formateadas: {s_str}")
        print(f"   OK Cargas formateadas: {c_str}")

        s_parsed = app._parse_sources_string(s_str)
        c_parsed = app._parse_charges_string(c_str)
        assert s_parsed.shape == (2, 3), "Fuentes parseadas incorrectamente"
        assert len(c_parsed) == 2, "Cargas parseadas incorrectamente"
        print("   OK Parseo de vuelta correcto")

        root.destroy()
        return True
    except Exception as e:
        print(f"   ERROR: {e}")
        traceback.print_exc()
        return False


def run_gui_tests():
    """Ejecuta todas las pruebas de GUI"""
    print("PRUEBAS DEL MÓDULO GUI")
    print("=" * 50)

    tests = [
        ("Importaciones GUI",   test_gui_imports),
        ("Creación de app",     test_app_creation),
        ("Componentes UI",      test_ui_components),
        ("Helpers formateo",    test_format_helpers),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"ERROR en prueba {name}: {e}")
            results.append((name, False))

    print("\n" + "=" * 50)
    print("RESUMEN - PRUEBAS GUI")
    print("=" * 50)
    all_passed = True
    for name, passed in results:
        status = "PASÓ" if passed else "FALLÓ"
        print(f"{name:25} - {status}")
        if not passed:
            all_passed = False

    return all_passed


if __name__ == "__main__":
    success = run_gui_tests()
    sys.exit(0 if success else 1)
