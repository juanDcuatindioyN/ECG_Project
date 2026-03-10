# -*- coding: utf-8 -*-
"""
Módulo de Visualización 3D
===========================

Este módulo contiene funciones para renderizado y visualización
de mallas 3D con materiales y colores.

Módulos:
--------
- visor_mallas_3d: Creación de figuras 3D con Poly3DCollection,
  extracción de superficies, configuración de colores por material
"""

from .visor_mallas_3d import crear_figura_3d, COLORES_MATERIALES

__all__ = [
    'crear_figura_3d',
    'COLORES_MATERIALES'
]
