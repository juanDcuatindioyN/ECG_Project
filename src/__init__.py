# -*- coding: utf-8 -*-
"""
Proyecto ECG - Solucionador de Malla VTK con Poisson
====================================================

Módulos principales:
    interfaz_grafica_legacy: Interfaz gráfica de usuario (legacy)
    aplicacion_principal: Aplicación GUI modular (nueva)
    nucleo_poisson: Funciones principales de procesamiento VTK y Poisson
    solucionador_ecg: Pipeline completo del problema directo de ECG
    generador_modelos_anatomicos: Generador automático de modelos
    
Submódulos:
    gui: Componentes de interfaz gráfica
    utils: Utilidades (análisis, formateo)
    visualization: Visualización 3D
"""

__version__ = "3.0.0"
__author__ = "Proyecto ECG"
__description__ = "Solucionador interactivo de Poisson y simulador de ECG para mallas VTK"

# Importaciones principales - Modo básico (Poisson simple)
from .nucleo_poisson import (
    load_mesh_skfem as cargar_malla_skfem,
    extract_surface_tris as extraer_triangulos_superficie,
    solve_poisson_point as resolver_poisson_punto,
    plot_surface as graficar_superficie
)

# Importaciones - Modo avanzado (ECG completo)
from .solucionador_ecg import (
    ECGSolver as SolucionadorECG,
    load_mesh_with_conductivities,
    assemble_stiffness_matrix,
    build_source_matrix,
    solve_ecg_system,
    postprocess_ecg,
    plot_electrodes_on_torso,
    DEFAULT_CONDUCTIVITIES,
    DEFAULT_DIPOLE_POS,
    DEFAULT_DIPOLE_TABLE,
    DEFAULT_ELECTRODES
)

# Generador de modelos
from .generador_modelos_anatomicos import (
    generate_mesh as generar_malla,
    create_geometry as crear_geometria,
    get_preview_data as obtener_datos_vista_previa,
    HAS_GMSH
)

# Interfaz gráfica (legacy - mantener compatibilidad)
from .interfaz_grafica_legacy import ECGAppAuto

# Aplicación principal (nueva)
try:
    from .aplicacion_principal import ECGApp as AplicacionECG
except ImportError:
    AplicacionECG = None

__all__ = [
    # GUI
    'ECGApp',
    'ECGAppAuto',
    'AplicacionECG',
    # Core básico (nombres originales para compatibilidad)
    'load_mesh_skfem',
    'extract_surface_tris',
    'solve_poisson_point',
    'plot_surface',
    # Core básico (nombres en español)
    'cargar_malla_skfem',
    'extraer_triangulos_superficie',
    'resolver_poisson_punto',
    'graficar_superficie',
    # ECG avanzado
    'ECGSolver',
    'SolucionadorECG',
    'load_mesh_with_conductivities',
    'assemble_stiffness_matrix',
    'build_source_matrix',
    'solve_ecg_system',
    'postprocess_ecg',
    'plot_electrodes_on_torso',
    # Generador
    'generate_mesh',
    'generar_malla',
    'crear_geometria',
    'obtener_datos_vista_previa',
    'HAS_GMSH',
    # Constantes
    'DEFAULT_CONDUCTIVITIES',
    'DEFAULT_DIPOLE_POS',
    'DEFAULT_DIPOLE_TABLE',
    'DEFAULT_ELECTRODES'
]

# Alias para compatibilidad con código existente
ECGApp = ECGAppAuto
load_mesh_skfem = cargar_malla_skfem
extract_surface_tris = extraer_triangulos_superficie
solve_poisson_point = resolver_poisson_punto
plot_surface = graficar_superficie
ECGSolver = SolucionadorECG
generate_mesh = generar_malla
create_geometry = crear_geometria
get_preview_data = obtener_datos_vista_previa