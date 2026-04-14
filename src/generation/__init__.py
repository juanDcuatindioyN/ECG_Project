"""
generation — Generación automática de modelos anatómicos

Módulos:
    mesh_generator — Crea modelos 3D de torso, corazón y pulmones usando Gmsh
"""
from .mesh_generator import generate_mesh, create_geometry, get_preview_data, HAS_GMSH
