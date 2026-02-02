#!/usr/bin/env python3
"""
Pruebas para el módulo GUI del proyecto ECG
==========================================

Prueba los componentes de la interfaz gráfica.
"""

import sys
import os
import traceback
import tkinter as tk

# Agregar el directorio padre al path para importar src
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.gui import ECGApp


def test_gui_imports():
    """Prueba las importaciones de GUI"""
    print("🔍 Probando importaciones de GUI...")
    
    try:
        import tkinter as tk
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        from matplotlib.figure import Figure
        print("   ✅ Tkinter y Matplotlib")
        
        try:
            from tkinterdnd2 import DND_FILES, TkinterDnD
            print("   ✅ TkinterDnD (Drag & Drop disponible)")
            dnd_available = True
        except ImportError:
            print("   ⚠️ TkinterDnD no disponible (Drag & Drop deshabilitado)")
            dnd_available = False
        
        return True, dnd_available
        
    except Exception as e:
        print(f"   ❌ Error en importaciones: {e}")
        return False, False


def test_app_creation():
    """Prueba la creación de la aplicación"""
    print("\n🔍 Probando creación de aplicación...")
    
    try:
        root = tk.Tk()
        root.withdraw()  # Ocultar ventana
        
        app = ECGApp(root)
        print("   ✅ Aplicación creada correctamente")
        
        # Verificar que los componentes principales existen
        assert hasattr(app, 'mesh'), "App debe tener atributo mesh"
        assert hasattr(app, 'sources_var'), "App debe tener variables de fuentes"
        assert hasattr(app, 'charges_var'), "App debe tener variables de cargas"
        
        root.destroy()
        return True
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        traceback.print_exc()
        return False


def test_parameter_parsing():
    """Prueba el parseo de parámetros"""
    print("\n🔍 Probando parseo de parámetros...")
    
    try:
        root = tk.Tk()
        root.withdraw()
        
        app = ECGApp(root)
        
        # Probar fuente simple
        app.sources_var.set("0.5,-0.4,0.1")
        app.charges_var.set("1.0")
        
        sources, charges = app.parse_sources_and_charges()
        print(f"   ✅ Fuente simple: {sources.shape}, {charges.shape}")
        
        # Probar múltiples fuentes
        app.sources_var.set("0.5,-0.4,0.1;-0.2,0.3,0.0")
        app.charges_var.set("1.0,-0.5")
        
        sources, charges = app.parse_sources_and_charges()
        print(f"   ✅ Múltiples fuentes: {sources.shape}, {charges.shape}")
        
        assert sources.shape[0] == charges.shape[0], "Número de fuentes debe coincidir con cargas"
        
        root.destroy()
        return True
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        traceback.print_exc()
        return False


def test_ui_components():
    """Prueba los componentes de UI"""
    print("\n🔍 Probando componentes de UI...")
    
    try:
        root = tk.Tk()
        root.withdraw()
        
        app = ECGApp(root)
        
        # Verificar que los widgets principales existen
        widgets_to_check = [
            'file_button', 'preview_button', 'solve_button',
            'progress_bar', 'status_label', 'file_info'
        ]
        
        for widget_name in widgets_to_check:
            assert hasattr(app, widget_name), f"Falta widget: {widget_name}"
        
        print("   ✅ Todos los widgets principales presentes")
        
        # Verificar estados iniciales
        assert app.preview_button['state'] == 'disabled', "Preview debe estar deshabilitado inicialmente"
        assert app.solve_button['state'] == 'disabled', "Solve debe estar deshabilitado inicialmente"
        
        print("   ✅ Estados iniciales correctos")
        
        root.destroy()
        return True
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        traceback.print_exc()
        return False


def test_error_handling():
    """Prueba el manejo de errores"""
    print("\n🔍 Probando manejo de errores...")
    
    try:
        root = tk.Tk()
        root.withdraw()
        
        app = ECGApp(root)
        
        # Probar parseo de parámetros inválidos
        app.sources_var.set("invalid")
        app.charges_var.set("1.0")
        
        try:
            sources, charges = app.parse_sources_and_charges()
            print("   ❌ Debería haber fallado con parámetros inválidos")
            return False
        except ValueError:
            print("   ✅ Error capturado correctamente para parámetros inválidos")
        
        # Probar número inconsistente de fuentes/cargas
        app.sources_var.set("0.5,-0.4,0.1;-0.2,0.3,0.0")
        app.charges_var.set("1.0")  # Solo una carga para dos fuentes
        
        try:
            sources, charges = app.parse_sources_and_charges()
            print("   ❌ Debería haber fallado con número inconsistente")
            return False
        except ValueError:
            print("   ✅ Error capturado correctamente para número inconsistente")
        
        root.destroy()
        return True
        
    except Exception as e:
        print(f"   ❌ Error inesperado: {e}")
        traceback.print_exc()
        return False


def run_gui_tests():
    """Ejecuta todas las pruebas de GUI"""
    print("🖥️ PRUEBAS DEL MÓDULO GUI")
    print("="*50)
    
    tests = [
        ("Importaciones GUI", lambda: test_gui_imports()[0]),
        ("Creación de app", test_app_creation),
        ("Parseo de parámetros", test_parameter_parsing),
        ("Componentes UI", test_ui_components),
        ("Manejo de errores", test_error_handling)
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ Error en prueba {name}: {e}")
            results.append((name, False))
    
    # Resumen
    print("\n" + "="*50)
    print("📊 RESUMEN - PRUEBAS GUI")
    print("="*50)
    
    all_passed = True
    for name, passed in results:
        status = "✅ PASÓ" if passed else "❌ FALLÓ"
        print(f"{name:25} - {status}")
        if not passed:
            all_passed = False
    
    return all_passed


if __name__ == "__main__":
    success = run_gui_tests()
    sys.exit(0 if success else 1)