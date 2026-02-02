#!/usr/bin/env python3
"""
Pruebas para el módulo core del proyecto ECG
===========================================

Prueba las funciones principales de procesamiento VTK y Poisson.
"""

import sys
import os
import traceback
import numpy as np

# Agregar el directorio padre al path para importar src
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.core import load_mesh_skfem, extract_surface_tris, solve_poisson_point, plot_surface


def test_vtk_loading():
    """Prueba la carga de archivos VTK"""
    print("Probando carga de archivos VTK...")
    
    vtk_file = os.path.join('..', 'data', 'Sphere.vtk')
    if not os.path.exists(vtk_file):
        vtk_file = 'Sphere.vtk'  # Fallback a ubicación actual
    
    if not os.path.exists(vtk_file):
        print("   Archivo Sphere.vtk no encontrado - saltando prueba")
        return True
    
    try:
        mesh, mio = load_mesh_skfem(vtk_file)
        print(f"   Malla cargada: {mesh.p.shape[1]} nodos, {mesh.t.shape[1]} elementos")
        
        # Verificar dimensiones
        assert mesh.p.shape[0] == 3, "La malla debe ser 3D"
        assert mesh.t.shape[0] == 4, "Los elementos deben ser tetraedros"
        
        return True
        
    except Exception as e:
        print(f"   Error: {e}")
        traceback.print_exc()
        return False


def test_surface_extraction():
    """Prueba la extracción de superficie"""
    print("\n🔍 Probando extracción de superficie...")
    
    vtk_file = os.path.join('..', 'data', 'Sphere.vtk')
    if not os.path.exists(vtk_file):
        vtk_file = 'Sphere.vtk'
    
    if not os.path.exists(vtk_file):
        print("   ⚠️ Archivo Sphere.vtk no encontrado - saltando prueba")
        return True
    
    try:
        mesh, mio = load_mesh_skfem(vtk_file)
        tris = extract_surface_tris(mio, mesh)
        
        print(f"   ✅ Superficie extraída: {len(tris)} triángulos")
        
        # Verificar que los triángulos son válidos
        assert len(tris) > 0, "Debe haber al menos un triángulo"
        assert tris.shape[1] == 3, "Cada triángulo debe tener 3 vértices"
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        traceback.print_exc()
        return False


def test_poisson_solver():
    """Prueba el solucionador de Poisson"""
    print("\n🔍 Probando solucionador de Poisson...")
    
    vtk_file = os.path.join('..', 'data', 'Sphere.vtk')
    if not os.path.exists(vtk_file):
        vtk_file = 'Sphere.vtk'
    
    if not os.path.exists(vtk_file):
        print("   ⚠️ Archivo Sphere.vtk no encontrado - saltando prueba")
        return True
    
    try:
        # Cargar malla
        mesh, mio = load_mesh_skfem(vtk_file)
        
        # Configurar fuentes y cargas
        sources = np.array([[0.0, 0.0, 0.0]])
        charges = np.array([1.0])
        
        # Resolver
        basis, V, used_sources = solve_poisson_point(mesh, sources, charges)
        
        print(f"   ✅ Poisson resuelto: {V.shape if hasattr(V, 'shape') else len(V)} valores")
        print(f"   📊 Fuentes usadas: {len(used_sources)}")
        
        # Verificar resultados
        V_arr = V.toarray().ravel() if hasattr(V, 'toarray') else np.asarray(V).ravel()
        assert len(V_arr) == mesh.p.shape[1], "Solución debe tener un valor por nodo"
        assert np.all(np.isfinite(V_arr)), "Solución debe ser finita"
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        traceback.print_exc()
        return False


def test_multiple_sources():
    """Prueba con múltiples fuentes"""
    print("\n🔍 Probando múltiples fuentes...")
    
    vtk_file = os.path.join('..', 'data', 'Sphere.vtk')
    if not os.path.exists(vtk_file):
        vtk_file = 'Sphere.vtk'
    
    if not os.path.exists(vtk_file):
        print("   ⚠️ Archivo Sphere.vtk no encontrado - saltando prueba")
        return True
    
    try:
        mesh, mio = load_mesh_skfem(vtk_file)
        
        # Múltiples fuentes
        sources = np.array([[0.3, 0.0, 0.1], [-0.3, 0.0, -0.1]])
        charges = np.array([1.0, -0.5])
        
        basis, V, used_sources = solve_poisson_point(mesh, sources, charges)
        
        print(f"   ✅ Múltiples fuentes resueltas: {len(used_sources)} fuentes")
        
        # Verificar que se usaron todas las fuentes
        assert len(used_sources) == len(sources), "Deben usarse todas las fuentes"
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        traceback.print_exc()
        return False


def test_visualization():
    """Prueba la generación de visualizaciones"""
    print("\n🔍 Probando visualización...")
    
    vtk_file = os.path.join('..', 'data', 'Sphere.vtk')
    if not os.path.exists(vtk_file):
        vtk_file = 'Sphere.vtk'
    
    if not os.path.exists(vtk_file):
        print("   ⚠️ Archivo Sphere.vtk no encontrado - saltando prueba")
        return True
    
    try:
        mesh, mio = load_mesh_skfem(vtk_file)
        tris = extract_surface_tris(mio, mesh)
        
        sources = np.array([[0.0, 0.0, 0.0]])
        charges = np.array([1.0])
        
        basis, V, used_sources = solve_poisson_point(mesh, sources, charges)
        
        # Crear figura
        fig = plot_surface(mesh, tris, V, sources=used_sources, 
                          title="Prueba de Visualización")
        
        print("   ✅ Figura creada correctamente")
        
        # Verificar que la figura tiene contenido
        assert len(fig.axes) > 0, "La figura debe tener al menos un eje"
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        traceback.print_exc()
        return False


def run_core_tests():
    """Ejecuta todas las pruebas del módulo core"""
    print("🧪 PRUEBAS DEL MÓDULO CORE")
    print("="*50)
    
    tests = [
        ("Carga VTK", test_vtk_loading),
        ("Extracción superficie", test_surface_extraction),
        ("Solucionador Poisson", test_poisson_solver),
        ("Múltiples fuentes", test_multiple_sources),
        ("Visualización", test_visualization)
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
    print("📊 RESUMEN - PRUEBAS CORE")
    print("="*50)
    
    all_passed = True
    for name, passed in results:
        status = "✅ PASÓ" if passed else "❌ FALLÓ"
        print(f"{name:25} - {status}")
        if not passed:
            all_passed = False
    
    return all_passed


if __name__ == "__main__":
    success = run_core_tests()
    sys.exit(0 if success else 1)