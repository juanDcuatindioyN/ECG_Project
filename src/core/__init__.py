"""
core — Lógica científica del simulador ECG

Módulos:
    mesh_loader  — Carga de mallas (VTK, MSH, STL...) y resolución de Poisson
    ecg_solver   — Pipeline FEM completo de 5 pasos para el problema directo del ECG
"""
from .mesh_loader import load_mesh_skfem, extract_surface_tris, solve_poisson_point, plot_surface, nodo_mas_cercano_en_superficie
from .ecg_solver import (
    ECGSolver,
    load_mesh_with_conductivities, assemble_stiffness_matrix,
    build_source_matrix, solve_ecg_system, postprocess_ecg,
    plot_electrodes_on_torso,
    DEFAULT_CONDUCTIVITIES, DEFAULT_DIPOLE_POS, DEFAULT_DIPOLE_TABLE, DEFAULT_ELECTRODES,
)
