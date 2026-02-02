"""
Utilidades y funciones auxiliares para el proyecto ECG
=====================================================

Este módulo contiene funciones de utilidad que apoyan
las funcionalidades principales del proyecto.

Funciones:
    validate_vtk_file: Valida archivos VTK
    format_mesh_info: Formatea información de malla
    parse_parameter_string: Parsea strings de parámetros
"""

import os
import numpy as np
from typing import Tuple, List, Optional


def validate_vtk_file(file_path: str) -> Tuple[bool, str]:
    """
    Valida si un archivo VTK es válido y accesible.
    
    Args:
        file_path (str): Ruta al archivo VTK
        
    Returns:
        tuple: (es_válido, mensaje_error)
    """
    if not os.path.exists(file_path):
        return False, f"El archivo no existe: {file_path}"
    
    if not file_path.lower().endswith('.vtk'):
        return False, "El archivo debe tener extensión .vtk"
    
    try:
        size = os.path.getsize(file_path)
        if size == 0:
            return False, "El archivo está vacío"
        
        # Verificar que se puede leer
        with open(file_path, 'r') as f:
            first_line = f.readline().strip()
            if not first_line.startswith('# vtk DataFile Version'):
                return False, "No es un archivo VTK válido (falta header)"
                
    except Exception as e:
        return False, f"Error al leer el archivo: {e}"
    
    return True, "Archivo VTK válido"


def format_mesh_info(mesh, file_path: str) -> str:
    """
    Formatea información de la malla para mostrar en la UI.
    
    Args:
        mesh: Malla scikit-fem
        file_path (str): Ruta del archivo original
        
    Returns:
        str: Información formateada
    """
    info_lines = [
        f"📄 {os.path.basename(file_path)}",
        f"📊 Nodos: {mesh.p.shape[1]:,}",
        f"🔺 Elementos: {mesh.t.shape[1]:,}",
        "📏 Límites:",
        f"   X: [{mesh.p[0].min():.3f}, {mesh.p[0].max():.3f}]",
        f"   Y: [{mesh.p[1].min():.3f}, {mesh.p[1].max():.3f}]",
        f"   Z: [{mesh.p[2].min():.3f}, {mesh.p[2].max():.3f}]"
    ]
    
    return "\n".join(info_lines)


def parse_parameter_string(param_str: str, param_type: str = "sources") -> np.ndarray:
    """
    Parsea strings de parámetros para fuentes o cargas.
    
    Args:
        param_str (str): String con parámetros
        param_type (str): Tipo de parámetro ("sources" o "charges")
        
    Returns:
        np.ndarray: Array con los parámetros parseados
        
    Raises:
        ValueError: Si el formato es incorrecto
    """
    param_str = param_str.strip()
    
    if not param_str:
        raise ValueError(f"String de {param_type} vacío")
    
    if param_type == "sources":
        # Parsear fuentes (formato: x1,y1,z1;x2,y2,z2 o x1,y1,z1)
        if ';' in param_str:
            source_groups = param_str.split(';')
            sources = []
            for group in source_groups:
                coords = [float(x.strip()) for x in group.split(',')]
                if len(coords) != 3:
                    raise ValueError(f"Cada fuente debe tener 3 coordenadas (x,y,z), encontradas {len(coords)}")
                sources.append(coords)
            return np.array(sources)
        else:
            coords = [float(x.strip()) for x in param_str.split(',')]
            if len(coords) != 3:
                raise ValueError(f"Fuente debe tener 3 coordenadas (x,y,z), encontradas {len(coords)}")
            return np.array([coords])
    
    elif param_type == "charges":
        # Parsear cargas
        if ';' in param_str or ',' in param_str:
            separator = ';' if ';' in param_str else ','
            charges = [float(x.strip()) for x in param_str.split(separator)]
            return np.array(charges)
        else:
            return np.array([float(param_str)])
    
    else:
        raise ValueError(f"Tipo de parámetro desconocido: {param_type}")


def validate_sources_charges(sources: np.ndarray, charges: np.ndarray) -> Tuple[bool, str]:
    """
    Valida que las fuentes y cargas sean compatibles.
    
    Args:
        sources (np.ndarray): Array de fuentes
        charges (np.ndarray): Array de cargas
        
    Returns:
        tuple: (es_válido, mensaje_error)
    """
    if sources.ndim != 2 or sources.shape[1] != 3:
        return False, f"Fuentes deben ser array 2D con 3 columnas, encontrado shape {sources.shape}"
    
    if charges.ndim != 1:
        return False, f"Cargas deben ser array 1D, encontrado shape {charges.shape}"
    
    if len(sources) != len(charges):
        return False, f"Número de fuentes ({len(sources)}) no coincide con número de cargas ({len(charges)})"
    
    if not np.all(np.isfinite(sources)):
        return False, "Fuentes contienen valores no finitos (NaN o Inf)"
    
    if not np.all(np.isfinite(charges)):
        return False, "Cargas contienen valores no finitos (NaN o Inf)"
    
    return True, "Fuentes y cargas válidas"


def get_mesh_statistics(mesh) -> dict:
    """
    Calcula estadísticas de la malla.
    
    Args:
        mesh: Malla scikit-fem
        
    Returns:
        dict: Diccionario con estadísticas
    """
    stats = {
        'num_nodes': mesh.p.shape[1],
        'num_elements': mesh.t.shape[1],
        'bounds': {
            'x': (float(mesh.p[0].min()), float(mesh.p[0].max())),
            'y': (float(mesh.p[1].min()), float(mesh.p[1].max())),
            'z': (float(mesh.p[2].min()), float(mesh.p[2].max()))
        },
        'center': (
            float(mesh.p[0].mean()),
            float(mesh.p[1].mean()),
            float(mesh.p[2].mean())
        ),
        'volume_estimate': 0.0  # Placeholder para cálculo futuro
    }
    
    # Calcular dimensiones
    stats['dimensions'] = {
        'x': stats['bounds']['x'][1] - stats['bounds']['x'][0],
        'y': stats['bounds']['y'][1] - stats['bounds']['y'][0],
        'z': stats['bounds']['z'][1] - stats['bounds']['z'][0]
    }
    
    return stats


def create_example_parameters() -> List[dict]:
    """
    Crea ejemplos de parámetros para la interfaz.
    
    Returns:
        list: Lista de diccionarios con ejemplos
    """
    examples = [
        {
            'name': 'Fuente Simple',
            'description': 'Una sola fuente en el centro',
            'sources': '0,0,0',
            'charges': '1.0'
        },
        {
            'name': 'Dipolo',
            'description': 'Dos fuentes con cargas opuestas',
            'sources': '0.3,0,0.1;-0.3,0,-0.1',
            'charges': '1.0,-1.0'
        },
        {
            'name': 'Configuración ECG',
            'description': 'Múltiples fuentes simulando ECG',
            'sources': '0.2,-0.3,0.1;-0.1,0.4,0.0;0.3,0.1,-0.2',
            'charges': '1.0,0.8,-0.6'
        },
        {
            'name': 'Fuente Intensa',
            'description': 'Fuente única con alta intensidad',
            'sources': '0.1,0.1,0.1',
            'charges': '5.0'
        }
    ]
    
    return examples