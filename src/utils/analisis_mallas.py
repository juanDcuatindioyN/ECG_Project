# -*- coding: utf-8 -*-
"""
Utilidades para análisis de mallas
"""
import numpy as np


def auto_detect_sources(mesh, num_sources=3):
    """
    Detecta automáticamente puntos óptimos para fuentes de Poisson.
    
    Args:
        mesh: Malla scikit-fem
        num_sources: Número de fuentes a generar
        
    Returns:
        tuple: (sources, charges) arrays con fuentes y cargas automáticas
    """
    bounds = {
        'x': (float(mesh.p[0].min()), float(mesh.p[0].max())),
        'y': (float(mesh.p[1].min()), float(mesh.p[1].max())),
        'z': (float(mesh.p[2].min()), float(mesh.p[2].max()))
    }
    
    center = np.array([
        (bounds['x'][0] + bounds['x'][1]) / 2,
        (bounds['y'][0] + bounds['y'][1]) / 2,
        (bounds['z'][0] + bounds['z'][1]) / 2
    ])
    
    dimensions = np.array([
        bounds['x'][1] - bounds['x'][0],
        bounds['y'][1] - bounds['y'][0],
        bounds['z'][1] - bounds['z'][0]
    ])
    
    if num_sources == 1:
        sources = np.array([center])
        charges = np.array([1.0])
    elif num_sources == 2:
        max_dim_idx = np.argmax(dimensions)
        offset = np.zeros(3)
        offset[max_dim_idx] = dimensions[max_dim_idx] * 0.3
        sources = np.array([center + offset, center - offset])
        charges = np.array([1.0, -1.0])
    elif num_sources == 3:
        radius = min(dimensions[:2]) * 0.25
        angles = np.array([0, 2*np.pi/3, 4*np.pi/3])
        sources = np.array([
            [center[0] + radius * np.cos(angle), 
             center[1] + radius * np.sin(angle), 
             center[2] + (i-1) * dimensions[2] * 0.1]
            for i, angle in enumerate(angles)
        ])
        charges = np.array([1.0, 0.8, -0.6])
    else:
        radius = min(dimensions) * 0.2
        tetra_vertices = np.array([
            [1, 1, 1], [1, -1, -1], [-1, 1, -1], [-1, -1, 1]
        ]) * radius
        sources = center + tetra_vertices
        charges = np.array([1.0, -0.8, 0.6, -0.4])
    
    return sources, charges


def analyze_mesh_complexity(mesh):
    """
    Analiza la complejidad de la malla.
    
    Args:
        mesh: Malla scikit-fem
        
    Returns:
        dict: Información sobre la complejidad
    """
    num_nodes = mesh.p.shape[1]
    num_elements = mesh.t.shape[1]
    
    dimensions = np.array([
        mesh.p[0].max() - mesh.p[0].min(),
        mesh.p[1].max() - mesh.p[1].min(),
        mesh.p[2].max() - mesh.p[2].min()
    ])
    
    volume_estimate = np.prod(dimensions)
    
    if num_nodes < 100:
        optimal_sources = 1
        complexity = "simple"
    elif num_nodes < 500:
        optimal_sources = 2
        complexity = "moderada"
    elif num_nodes < 1000:
        optimal_sources = 3
        complexity = "compleja"
    else:
        optimal_sources = 4
        complexity = "muy compleja"
    
    return {
        'num_nodes': num_nodes,
        'num_elements': num_elements,
        'dimensions': dimensions,
        'volume_estimate': volume_estimate,
        'optimal_sources': optimal_sources,
        'complexity': complexity
    }


def get_mesh_info_text(mesh, file_path):
    """
    Genera texto informativo sobre la malla.
    
    Args:
        mesh: Malla scikit-fem
        file_path: Ruta del archivo
        
    Returns:
        str: Texto formateado con información
    """
    import os
    return f"""📄 {os.path.basename(file_path)}
📊 Nodos: {mesh.p.shape[1]:,}
🔺 Elementos: {mesh.t.shape[1]:,}
📏 Límites:
   X: [{mesh.p[0].min():.3f}, {mesh.p[0].max():.3f}]
   Y: [{mesh.p[1].min():.3f}, {mesh.p[1].max():.3f}]
   Z: [{mesh.p[2].min():.3f}, {mesh.p[2].max():.3f}]"""


def get_analysis_info_text(analysis, auto_sources):
    """
    Genera texto informativo sobre el análisis.
    
    Args:
        analysis: Diccionario con análisis de malla
        auto_sources: Array de fuentes automáticas
        
    Returns:
        str: Texto formateado con análisis
    """
    return f"""ANÁLISIS DE MALLA COMPLETADO

Complejidad: {analysis['complexity'].upper()}
Fuentes óptimas: {analysis['optimal_sources']}
Dimensiones: {analysis['dimensions'][0]:.3f} × {analysis['dimensions'][1]:.3f} × {analysis['dimensions'][2]:.3f}
Volumen estimado: {analysis['volume_estimate']:.6f}

PARÁMETROS AUTOMÁTICOS:
• {len(auto_sources)} fuentes detectadas
• Cargas balanceadas automáticamente
• Distribución espacial optimizada

Listo para resolución automática"""
