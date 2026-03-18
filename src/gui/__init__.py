# -*- coding: utf-8 -*-
"""
Componentes de Interfaz Gráfica
================================

Este módulo contiene todos los componentes visuales y controles
de la interfaz gráfica de usuario.

Módulos:
--------
- controles_visualizacion_3d: Controles interactivos para visualización 3D
  (zoom, rotación, vistas predefinidas, interacción con mouse)
"""

from .controles_visualizacion_3d import (
    create_view_controls as crear_controles_vista,
    create_zoom_controls as crear_controles_zoom,
    setup_mouse_controls as configurar_controles_mouse
)

__all__ = [
    'crear_controles_vista',
    'crear_controles_zoom',
    'configurar_controles_mouse',
]
