# -*- coding: utf-8 -*-
"""
Utilidades para formateo de datos
"""
import numpy as np


def format_sources_for_display(sources):
    """Formatea fuentes para mostrar en la UI"""
    if sources is None:
        return ""
    return ";".join([f"{s[0]:.3f},{s[1]:.3f},{s[2]:.3f}" for s in sources])


def format_charges_for_display(charges):
    """Formatea cargas para mostrar en la UI"""
    if charges is None:
        return ""
    return ",".join([f"{c:.3f}" for c in charges])


def parse_sources_string(sources_str):
    """Parsea string de fuentes"""
    if ';' in sources_str:
        source_groups = sources_str.split(';')
        sources = []
        for group in source_groups:
            coords = [float(x.strip()) for x in group.split(',')]
            if len(coords) == 3:
                sources.append(coords)
        return np.array(sources)
    else:
        coords = [float(x.strip()) for x in sources_str.split(',')]
        if len(coords) == 3:
            return np.array([coords])
        else:
            raise ValueError("Formato de fuentes incorrecto")


def parse_charges_string(charges_str):
    """Parsea string de cargas"""
    if ';' in charges_str or ',' in charges_str:
        separator = ';' if ';' in charges_str else ','
        return np.array([float(x.strip()) for x in charges_str.split(separator)])
    else:
        return np.array([float(charges_str)])
