"""
Proyecto ECG - Solucionador de Malla VTK con Poisson
====================================================

Módulos:
    gui: Interfaz gráfica de usuario
    core: Funciones principales de procesamiento VTK y Poisson
    utils: Utilidades y funciones auxiliares
"""

__version__ = "1.0.0"
__author__ = "Proyecto ECG"
__description__ = "Solucionador interactivo de Poisson para mallas VTK"

# Importaciones principales
from .core import load_mesh_skfem, extract_surface_tris, solve_poisson_point, plot_surface
from .gui_safe import ECGAppAuto

__all__ = [
    'ECGApp',
    'ECGAppAuto', 
    'load_mesh_skfem', 
    'extract_surface_tris', 
    'solve_poisson_point', 
    'plot_surface'
]

# Alias para compatibilidad
ECGApp = ECGAppAuto