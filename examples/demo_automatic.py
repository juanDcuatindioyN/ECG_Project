#!/usr/bin/env python3
"""
Demostración de las capacidades automáticas del solucionador ECG
==============================================================

Este script muestra cómo la aplicación detecta automáticamente
parámetros óptimos para la resolución de Poisson.
"""

import sys
import os
import numpy as np

# Agregar src al path
sys.path.insert(0, 'src')

from src.core import load_mesh_skfem, extract_surface_tris, solve_poisson_point, plot_surface
from src.gui_safe import auto_detect_sources, analyze_mesh_complexity

def demo_automatic_detection():
    """Demuestra la detección automática de parámetros"""
    print("🤖 DEMOSTRACIÓN: DETECCIÓN AUTOMÁTICA DE PARÁMETROS")
    print("="*60)
    
    # Buscar archivo VTK
    vtk_file = None
    for location in ['data/Sphere.vtk', 'Sphere.vtk']:
        if os.path.exists(location):
            vtk_file = location
            break
    
    if not vtk_file:
        print("❌ No se encontró archivo VTK")
        return False
    
    try:
        # Cargar malla
        print(f"📄 Cargando: {vtk_file}")
        mesh, mio = load_mesh_skfem(vtk_file)
        tris = extract_surface_tris(mio, mesh)
        print(f"✅ Malla cargada: {mesh.p.shape[1]} nodos, {mesh.t.shape[1]} elementos")
        
        # Análisis automático
        print("\n🔍 Analizando complejidad de malla...")
        analysis = analyze_mesh_complexity(mesh)
        
        print(f"📊 Complejidad: {analysis['complexity'].upper()}")
        print(f"📐 Dimensiones: {analysis['dimensions'][0]:.3f} × {analysis['dimensions'][1]:.3f} × {analysis['dimensions'][2]:.3f}")
        print(f"📦 Volumen estimado: {analysis['volume_estimate']:.6f}")
        print(f"🎯 Fuentes óptimas recomendadas: {analysis['optimal_sources']}")
        
        # Probar diferentes configuraciones automáticas
        configurations = [1, 2, 3, 4]
        
        for num_sources in configurations:
            print(f"\n🔄 Configuración automática con {num_sources} fuente(s):")
            
            # Detectar fuentes automáticamente
            sources, charges = auto_detect_sources(mesh, num_sources)
            
            print(f"   📍 Fuentes detectadas:")
            for i, (source, charge) in enumerate(zip(sources, charges)):
                print(f"      {i+1}: ({source[0]:.3f}, {source[1]:.3f}, {source[2]:.3f}) → carga: {charge:.3f}")
            
            # Resolver
            try:
                basis, V, used_sources = solve_poisson_point(mesh, sources, charges)
                V_arr = V.toarray().ravel() if hasattr(V, 'toarray') else np.asarray(V).ravel()
                
                print(f"   ✅ Solución: min={V_arr.min():.4f}, max={V_arr.max():.4f}")
                
                # Crear visualización
                fig = plot_surface(mesh, tris, V, sources=used_sources, 
                                 title=f"Configuración Automática - {num_sources} Fuente(s)")
                
                # Guardar imagen
                output_file = f"auto_config_{num_sources}_sources.png"
                fig.savefig(output_file, dpi=150, bbox_inches='tight')
                print(f"   💾 Guardado: {output_file}")
                
            except Exception as e:
                print(f"   ❌ Error en resolución: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def demo_comparison_manual_vs_auto():
    """Compara resolución manual vs automática"""
    print(f"\n🆚 COMPARACIÓN: MANUAL vs AUTOMÁTICO")
    print("="*60)
    
    vtk_file = None
    for location in ['data/Sphere.vtk', 'Sphere.vtk']:
        if os.path.exists(location):
            vtk_file = location
            break
    
    if not vtk_file:
        print("❌ No se encontró archivo VTK")
        return False
    
    try:
        mesh, mio = load_mesh_skfem(vtk_file)
        tris = extract_surface_tris(mio, mesh)
        
        # Configuración manual típica
        print("\n🔧 Configuración MANUAL típica:")
        manual_sources = np.array([[0.5, -0.4, 0.1]])
        manual_charges = np.array([1.0])
        
        print(f"   📍 Fuentes: {manual_sources[0]}")
        print(f"   ⚡ Cargas: {manual_charges[0]}")
        
        basis1, V1, used1 = solve_poisson_point(mesh, manual_sources, manual_charges)
        V1_arr = V1.toarray().ravel() if hasattr(V1, 'toarray') else np.asarray(V1).ravel()
        
        print(f"   📊 Resultado: min={V1_arr.min():.4f}, max={V1_arr.max():.4f}, rango={V1_arr.max()-V1_arr.min():.4f}")
        
        # Configuración automática
        print("\n🤖 Configuración AUTOMÁTICA:")
        analysis = analyze_mesh_complexity(mesh)
        auto_sources, auto_charges = auto_detect_sources(mesh, analysis['optimal_sources'])
        
        print(f"   🎯 {len(auto_sources)} fuentes detectadas automáticamente:")
        for i, (source, charge) in enumerate(zip(auto_sources, auto_charges)):
            print(f"      {i+1}: ({source[0]:.3f}, {source[1]:.3f}, {source[2]:.3f}) → {charge:.3f}")
        
        basis2, V2, used2 = solve_poisson_point(mesh, auto_sources, auto_charges)
        V2_arr = V2.toarray().ravel() if hasattr(V2, 'toarray') else np.asarray(V2).ravel()
        
        print(f"   📊 Resultado: min={V2_arr.min():.4f}, max={V2_arr.max():.4f}, rango={V2_arr.max()-V2_arr.min():.4f}")
        
        # Comparación
        print(f"\n📈 COMPARACIÓN:")
        print(f"   Rango manual:     {V1_arr.max()-V1_arr.min():.4f}")
        print(f"   Rango automático: {V2_arr.max()-V2_arr.min():.4f}")
        
        improvement = ((V2_arr.max()-V2_arr.min()) - (V1_arr.max()-V1_arr.min())) / (V1_arr.max()-V1_arr.min()) * 100
        if improvement > 0:
            print(f"   🎉 Mejora automática: +{improvement:.1f}% más rango dinámico")
        else:
            print(f"   📊 Diferencia: {improvement:.1f}%")
        
        # Crear visualizaciones comparativas
        import matplotlib.pyplot as plt
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6), subplot_kw={'projection': '3d'})
        
        # Manual
        X = mesh.p.T
        surf1 = ax1.plot_trisurf(X[:, 0], X[:, 1], X[:, 2], triangles=tris,
                                cmap='plasma', alpha=0.8, linewidth=0.1)
        surf1.set_array(V1_arr[tris].mean(axis=1))
        ax1.scatter(used1[:, 0], used1[:, 1], used1[:, 2], 
                   s=100, c='red', marker='*', label='Fuente Manual')
        ax1.set_title('Configuración Manual', fontweight='bold')
        ax1.legend()
        
        # Automático
        surf2 = ax2.plot_trisurf(X[:, 0], X[:, 1], X[:, 2], triangles=tris,
                                cmap='plasma', alpha=0.8, linewidth=0.1)
        surf2.set_array(V2_arr[tris].mean(axis=1))
        colors = ['red', 'blue', 'green', 'orange'][:len(used2)]
        ax2.scatter(used2[:, 0], used2[:, 1], used2[:, 2], 
                   s=100, c=colors, marker='*', label='Fuentes Automáticas')
        ax2.set_title('Configuración Automática', fontweight='bold')
        ax2.legend()
        
        plt.tight_layout()
        plt.savefig('comparison_manual_vs_auto.png', dpi=150, bbox_inches='tight')
        print(f"   💾 Comparación guardada: comparison_manual_vs_auto.png")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Ejecuta todas las demostraciones"""
    print("🎯 DEMOSTRACIÓN COMPLETA - SOLUCIONADOR AUTOMÁTICO")
    print("="*70)
    
    # Ejecutar demostraciones
    demo1_ok = demo_automatic_detection()
    demo2_ok = demo_comparison_manual_vs_auto()
    
    # Resumen
    print(f"\n{'='*70}")
    print("📊 RESUMEN DE DEMOSTRACIÓN")
    print("="*70)
    
    print(f"Detección automática:     {'✅ OK' if demo1_ok else '❌ FALLO'}")
    print(f"Comparación manual/auto:  {'✅ OK' if demo2_ok else '❌ FALLO'}")
    
    if demo1_ok and demo2_ok:
        print(f"\n🎉 ¡DEMOSTRACIÓN EXITOSA!")
        print(f"\n✨ Características automáticas demostradas:")
        print(f"   • Análisis inteligente de complejidad de malla")
        print(f"   • Detección automática de número óptimo de fuentes")
        print(f"   • Distribución espacial optimizada")
        print(f"   • Cálculo automático de cargas balanceadas")
        print(f"   • Comparación con configuraciones manuales")
        
        print(f"\n🚀 Para usar la aplicación automática:")
        print(f"   python main.py")
        print(f"   (¡Simplemente carga un archivo VTK y se resuelve automáticamente!)")
    else:
        print(f"\n⚠️ ALGUNAS DEMOSTRACIONES FALLARON")
        print(f"Revisa los errores arriba.")
    
    return demo1_ok and demo2_ok

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)