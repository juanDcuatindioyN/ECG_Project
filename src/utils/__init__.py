# -*- coding: utf-8 -*-
"""
Utilidades del Proyecto ECG
============================

Este módulo contiene funciones auxiliares para análisis de mallas,
formateo de datos y otras utilidades generales.

Módulos:
--------
- analisis_mallas: Análisis automático de mallas, detección de fuentes,
  cálculo de complejidad y generación de textos informativos
  
- formateadores_datos: Conversión entre arrays y strings para la UI,
  parsing de datos de entrada del usuario
"""

from .analisis_mallas import (
    auto_detect_sources as detectar_fuentes_automaticamente,
    analyze_mesh_complexity as analizar_complejidad_malla,
    get_mesh_info_text as obtener_texto_info_malla,
    get_analysis_info_text as obtener_texto_info_analisis
)
from .formateadores_datos import (
    format_sources_for_display as formatear_fuentes_para_mostrar,
    format_charges_for_display as formatear_cargas_para_mostrar,
    parse_sources_string as parsear_string_fuentes,
    parse_charges_string as parsear_string_cargas
)

__all__ = [
    # Análisis de mallas
    'detectar_fuentes_automaticamente',
    'analizar_complejidad_malla',
    'obtener_texto_info_malla',
    'obtener_texto_info_analisis',
    # Formateadores
    'formatear_fuentes_para_mostrar',
    'formatear_cargas_para_mostrar',
    'parsear_string_fuentes',
    'parsear_string_cargas',
]
