#!/usr/bin/env python3
"""
Demostración del solver completo de ECG
========================================

Este script demuestra el uso del pipeline completo de 5 pasos
para resolver el problema directo del ECG con el método de
elementos finitos.

Requisitos:
    - Archivo de malla con torso, corazón y pulmones
    - Conductividades heterogéneas por región
    - Dipolo cardíaco temporal

Uso:
    python demo_ecg_solver.py
"""

import sys
import os
import numpy as np
import matplotlib.pyplot as plt

# Agregar src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from solucionador_ecg import ECGSolver as SolucionadorECG

# Alias para compatibilidad con el código del demo
ECGSolver = SolucionadorECG


def plot_ecg_leads(leads, times, output_file="ecg_12_leads.png"):
    """
    Grafica las 12 derivaciones del ECG en formato clínico estándar.
    """
    layout = [
        ["I",   "aVR", "V1", "V4"],
        ["II",  "aVL", "V2", "V5"],
        ["III", "aVF", "V3", "V6"],
    ]
    
    fig, axes = plt.subplots(3, 4, figsize=(16, 8))
    fig.suptitle("ECG - 12 Derivaciones (Problema Directo FEM)",
                 fontsize=14, fontweight="bold")
    
    t_ms = times * 1000  # Convertir a ms
    
    for row, row_names in enumerate(layout):
        for col, name in enumerate(row_names):
            ax = axes[row][col]
            signal = leads[name] * 1000  # Convertir a mV
            
            ax.plot(t_ms, signal, color="#1a5276", linewidth=1.8)
            ax.axhline(0, color="gray", linewidth=0.5, linestyle="--")
            ax.set_title(name, fontsize=11, fontweight="bold")
            ax.set_xlabel("t (ms)", fontsize=8)
            ax.set_ylabel("mV", fontsize=8)
            ax.tick_params(labelsize=7)
            ax.grid(True, linestyle="--", alpha=0.35)
            
            # Marcar pico máximo
            idx_max = np.argmax(np.abs(signal))
            ax.plot(t_ms[idx_max], signal[idx_max], "ro", markersize=4)
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=150, bbox_inches="tight")
    print(f"  Figura guardada: {output_file}")
    plt.show()


def plot_potential_map(mesh, surface_nodes, PHI, times, instant_idx=4,
                       output_file="potential_map.png"):
    """
    Muestra el mapa de potenciales en la superficie del torso.
    """
    if len(surface_nodes) == 0:
        print("  Sin nodos de superficie disponibles")
        return
    
    coords = mesh.p.T[surface_nodes]
    phi_surf = PHI[surface_nodes, instant_idx] * 1000  # mV
    
    fig, axes = plt.subplots(1, 2, figsize=(12, 6))
    fig.suptitle(f"Mapa de potenciales en superficie del torso\n"
                 f"t = {times[instant_idx]:.2f} s (instante {instant_idx})",
                 fontsize=12, fontweight="bold")
    
    # Vista frontal XZ
    ax = axes[0]
    sc = ax.scatter(coords[:, 0], coords[:, 2],
                    c=phi_surf, cmap="RdBu_r", s=8,
                    vmin=-np.abs(phi_surf).max(),
                    vmax=np.abs(phi_surf).max())
    plt.colorbar(sc, ax=ax, label="Potencial (mV)")
    ax.set_xlabel("x (m)")
    ax.set_ylabel("z (m)")
    ax.set_title("Vista frontal (plano XZ)")
    ax.set_aspect("equal")
    ax.grid(True, linestyle="--", alpha=0.3)
    
    # Vista transversal XY
    ax2 = axes[1]
    z_heart = 0.30
    tol_z = 0.04
    mask_z = np.abs(coords[:, 2] - z_heart) < tol_z
    if mask_z.sum() > 10:
        sc2 = ax2.scatter(coords[mask_z, 0], coords[mask_z, 1],
                          c=phi_surf[mask_z], cmap="RdBu_r", s=12,
                          vmin=-np.abs(phi_surf).max(),
                          vmax=np.abs(phi_surf).max())
        plt.colorbar(sc2, ax=ax2, label="Potencial (mV)")
    ax2.set_xlabel("x (m)")
    ax2.set_ylabel("y (m)")
    ax2.set_title(f"Vista transversal XY (z ~ {z_heart:.2f} m)")
    ax2.set_aspect("equal")
    ax2.grid(True, linestyle="--", alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=150, bbox_inches="tight")
    print(f"  Figura guardada: {output_file}")
    plt.show()


def main():
    """
    Función principal de demostración.
    """
    print("=" * 60)
    print("DEMOSTRACIÓN: Solver Completo de ECG")
    print("=" * 60)
    
    # Configuración
    # Archivo de malla con torso, corazón y pulmones
    vtk_path = "../data/ecg_torso_v2_con_pulmones.msh"
    
    # Verificar si existe el archivo
    if not os.path.exists(vtk_path):
        print(f"\n[ERROR] No se encontró el archivo de malla: {vtk_path}")
        print("\nEl archivo debería estar en: ECG_Project/data/ecg_torso_v2_con_pulmones.msh")
        print("\nSi no lo tienes, cópialo desde:")
        print("  C:\\Users\\USUARIO\\Downloads\\scikit-fem\\ProyectoECG\\ecg_torso_v2_con_pulmones.msh")
        print("\nUsando archivo de ejemplo Sphere.vtk en su lugar...")
        vtk_path = "../data/Sphere.vtk"
        print(f"  (Nota: Sphere.vtk no tiene conductividades heterogéneas)")
        print(f"  (La demo puede fallar o dar resultados no realistas)")
        print()
    
    print(f"\n[1/6] Inicializando solver...")
    print(f"  Archivo: {vtk_path}")
    
    # Crear solver
    solver = ECGSolver(vtk_path)
    
    print(f"\n[2/6] Ejecutando pipeline completo (5 pasos)...")
    print("  Paso 1: Cargando malla con conductividades...")
    print("  Paso 2: Ensamblando matriz de rigidez K...")
    print("  Paso 3: Construyendo fuentes cardíacas (dipolo)...")
    print("  Paso 4: Resolviendo sistema K·φ = f...")
    print("  Paso 5: Postprocesando potenciales en electrodos...")
    
    try:
        results = solver.run_full_pipeline(tol=1e-8, max_iter=5000)
    except Exception as e:
        print(f"\n[ERROR] Fallo en el pipeline: {e}")
        print("\nEsto puede ocurrir si:")
        print("  - El archivo no tiene etiquetas de material")
        print("  - La posición del dipolo está fuera del dominio")
        print("  - El formato del archivo no es compatible")
        return 1
    
    print("\n[3/6] Pipeline completado exitosamente!")
    
    # Obtener resumen
    print("\n[4/6] Resumen de resultados:")
    summary = solver.get_summary()
    print(f"  Nodos totales        : {summary['num_nodes']:,}")
    print(f"  Elementos            : {summary['num_elements']:,}")
    print(f"  Nodos en superficie  : {summary['num_surface_nodes']:,}")
    print(f"  Instantes simulados  : {summary['num_instants']}")
    print(f"  |φ| máximo           : {summary['phi_max']:.4e} V")
    print(f"  Residuo máximo       : {summary['max_residual']:.2e}")
    print(f"  Nodo de referencia   : {summary['ref_node']}")
    
    print("\n  Amplitudes de derivaciones (mV):")
    for lead_name, amplitude in summary['lead_amplitudes'].items():
        print(f"    {lead_name:4s} : {amplitude:.4f} mV")
    
    # Graficar resultados
    print("\n[5/6] Generando gráficas...")
    
    leads = results['ecg_data']['leads']
    times = results['source_data']['times']
    
    plot_ecg_leads(leads, times, "ecg_12_leads_demo.png")
    
    mesh = results['mesh_data']['mesh']
    surface_nodes = results['mesh_data']['surface_nodes']
    PHI = results['solution_data']['PHI']
    
    plot_potential_map(mesh, surface_nodes, PHI, times, 
                      instant_idx=4, output_file="potential_map_demo.png")
    
    print("\n[6/6] Demostración completada!")
    print("\nArchivos generados:")
    print("  - ecg_12_leads_demo.png")
    print("  - potential_map_demo.png")
    
    print("\n" + "=" * 60)
    print("Para usar el solver en tu propio código:")
    print("=" * 60)
    print("""
from src.ecg_solver import ECGSolver

# Crear solver
solver = ECGSolver('tu_malla.vtk')

# Ejecutar pipeline completo
results = solver.run_full_pipeline()

# Obtener resultados
leads = results['ecg_data']['leads']
PHI = results['solution_data']['PHI']
summary = solver.get_summary()
""")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
