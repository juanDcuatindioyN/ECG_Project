# -*- coding: utf-8 -*-
"""
Proyecto ECG — Simulador del problema directo del ECG con FEM
=============================================================

Estructura:
    src/app.py                        — Interfaz gráfica (flujo de 5 pasos)
    src/core/mesh_loader.py           — Carga de mallas y resolución de Poisson
    src/core/ecg_solver.py            — Pipeline FEM completo
    src/generation/mesh_generator.py  — Generador de modelos anatómicos (Gmsh)
    src/visualization/viewer3d.py     — Visualización 3D
"""

import logging

__version__ = "3.0.0"
__description__ = "Simulador interactivo del problema directo del ECG con FEM"

logging.getLogger(__name__).addHandler(logging.NullHandler())

from .app import ECGAppAuto
from .core.mesh_loader import load_mesh_skfem, solve_poisson_point
from .core.ecg_solver import ECGSolver, DEFAULT_CONDUCTIVITIES, DEFAULT_DIPOLE_POS
from .generation.mesh_generator import generate_mesh, HAS_GMSH

# Alias público principal
ECGApp = ECGAppAuto

__all__ = [
    "ECGApp", "ECGAppAuto",
    "ECGSolver",
    "load_mesh_skfem", "solve_poisson_point",
    "generate_mesh", "HAS_GMSH",
    "DEFAULT_CONDUCTIVITIES", "DEFAULT_DIPOLE_POS",
]
