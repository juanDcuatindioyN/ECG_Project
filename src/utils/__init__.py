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
    detectar_fuentes_automaticamente,
    analizar_complejidad_malla,
    obtener_texto_info_malla,
    obtener_texto_info_analisis
)
from .formateadores_datos import (
    formatear_fuentes_para_mostrar,
    formatear_cargas_para_mostrar,
    parsear_string_fuentes,
    parsear_string_cargas
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
