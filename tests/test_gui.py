#!/usr/bin/env python3
"""
Pruebas para el módulo GUI (src/app.py)
"""

import sys
import os
import traceback
import tkinter as tk

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src import ECGAppAuto as ECGApp


def test_gui_imports():
    print(" Probando importaciones de GUI...")
    try:
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        from matplotlib.figure import Figure
        print("   OK Tkinter y Matplotlib")
        try:
            from tkinterdnd2 import DND_FILES, TkinterDnD
            print("   OK TkinterDnD disponible")
        except ImportError:
            print("   ADVERTENCIA TkinterDnD no disponible")
        return True
    except Exception as e:
        print(f"   ERROR: {e}")
        return False


def test_app_creation():
    print("\n Probando creación de aplicación...")
    try:
        root = tk.Tk()
        root.withdraw()
        app = ECGApp(root)
        print("   OK Aplicación creada")

        # Atributos de estado de la nueva app
        required = ['mesh', 'mio', 'file_path', 'auto_sources',
                    'manual_electrodes', 'dipole_pos', 'ecg_data']
        for attr in required:
            assert hasattr(app, attr), f"Falta atributo: {attr}"
        print("   OK Atributos de estado presentes")

        root.destroy()
        return True
    except Exception as e:
        print(f"   ERROR: {e}")
        traceback.print_exc()
        return False


def test_ui_components():
    print("\n Probando componentes de UI...")
    try:
        root = tk.Tk()
        root.withdraw()
        app = ECGApp(root)

        # Widgets clave de la nueva interfaz
        required_widgets = ['plot_frame', 'status_var', 'progress_var',
                            'drop_frame', 'mesh_info']
        for w in required_widgets:
            assert hasattr(app, w), f"Falta widget: {w}"
        print("   OK Widgets principales presentes")

        # Secciones de pasos
        for sec in ['sec_dipole', 'sec_electrodes', 'sec_simulation', 'sec_results']:
            assert hasattr(app, sec), f"Falta sección: {sec}"
        print("   OK Secciones de pasos presentes")

        root.destroy()
        return True
    except Exception as e:
        print(f"   ERROR: {e}")
        traceback.print_exc()
        return False


def test_step_flow():
    """Verifica que los pasos están bloqueados inicialmente."""
    print("\n Probando flujo de pasos...")
    try:
        root = tk.Tk()
        root.withdraw()
        app = ECGApp(root)

        # Sin malla cargada, dipolo/electrodos/simulación deben estar bloqueados
        assert app.mesh is None, "mesh debe ser None al inicio"
        assert app.dipole_pos is None, "dipole_pos debe ser None al inicio"
        assert app.manual_electrodes is None, "manual_electrodes debe ser None al inicio"
        assert app.ecg_data is None, "ecg_data debe ser None al inicio"
        print("   OK Estado inicial correcto (todos los pasos bloqueados)")

        root.destroy()
        return True
    except Exception as e:
        print(f"   ERROR: {e}")
        traceback.print_exc()
        return False


def run_gui_tests():
    print("PRUEBAS DEL MÓDULO GUI")
    print("=" * 50)

    tests = [
        ("Importaciones GUI",  test_gui_imports),
        ("Creación de app",    test_app_creation),
        ("Componentes UI",     test_ui_components),
        ("Flujo de pasos",     test_step_flow),
    ]

    results = []
    for name, fn in tests:
        try:
            results.append((name, fn()))
        except Exception as e:
            print(f"ERROR en {name}: {e}")
            results.append((name, False))

    print("\n" + "=" * 50)
    print("RESUMEN - PRUEBAS GUI")
    print("=" * 50)
    all_ok = True
    for name, ok in results:
        print(f"{name:25} - {'PASÓ' if ok else 'FALLÓ'}")
        if not ok:
            all_ok = False
    return all_ok


if __name__ == "__main__":
    sys.exit(0 if run_gui_tests() else 1)
