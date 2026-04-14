# -*- coding: utf-8 -*-
"""
Generador automático de modelo de torso para ECG
================================================

Genera modelos 3D de torso con corazón y opcionalmente pulmones
usando Gmsh.

Autor: Proyecto ECG
"""

import logging
import numpy as np
import os

logger = logging.getLogger(__name__)

try:
    import gmsh
    HAS_GMSH = True
except ImportError:
    HAS_GMSH = False
    logger.warning("gmsh no está instalado. Instala con: pip install gmsh")


# Parámetros geométricos por defecto (en metros)
DEFAULT_PARAMS = {
    'torso_radio': 0.15,
    'torso_alto': 0.50,
    'torso_z0': 0.00,
    'corazon_x': -0.02,
    'corazon_y': 0.00,
    'corazon_z': 0.30,
    'corazon_r': 0.05,
    'pulmon_rx': 0.04,
    'pulmon_ry': 0.06,
    'pulmon_rz': 0.09,
    'pulmon_izq_x': -0.08,
    'pulmon_der_x': 0.06,
    'pulmon_y': 0.01,
    'pulmon_z': 0.30,
    'lc_torso': 0.03,
    'lc_organo': 0.01
}


def add_ellipsoid(factory, cx, cy, cz, rx, ry, rz):
    """
    Crea un elipsoide con semiejes rx, ry, rz centrado en (cx, cy, cz).
    """
    tag = factory.addSphere(0, 0, 0, 1.0)
    factory.dilate([(3, tag)], 0, 0, 0, rx, ry, rz)
    factory.translate([(3, tag)], cx, cy, cz)
    return tag


def get_centroid(tag):
    """Centroide aproximado como centro de la bounding box."""
    bb = gmsh.model.getBoundingBox(3, tag)
    return (
        (bb[0] + bb[3]) / 2,
        (bb[1] + bb[4]) / 2,
        (bb[2] + bb[5]) / 2
    )


def get_bbox_volume(tag):
    """Volumen de la bounding box."""
    bb = gmsh.model.getBoundingBox(3, tag)
    return (bb[3]-bb[0]) * (bb[4]-bb[1]) * (bb[5]-bb[2])


def dist_to(tag, tx, ty, tz):
    """Distancia del centroide a un punto."""
    cx, cy, cz = get_centroid(tag)
    return ((cx-tx)**2 + (cy-ty)**2 + (cz-tz)**2) ** 0.5


def create_geometry(include_lungs=True, params=None):
    """
    Crea la geometría del modelo (sin generar malla).
    
    Args:
        include_lungs: Si True, incluye pulmones
        params: Diccionario con parámetros geométricos
        
    Returns:
        dict con información del modelo
    """
    if not HAS_GMSH:
        raise ImportError("gmsh no está instalado. Instala con: pip install gmsh")
    
    if params is None:
        params = DEFAULT_PARAMS
    
    # Inicializar Gmsh
    gmsh.initialize()
    gmsh.model.add("ecg_torso_preview")
    factory = gmsh.model.occ
    
    # Crear geometrías
    torso_tag = factory.addCylinder(
        0, 0, params['torso_z0'],
        0, 0, params['torso_alto'],
        params['torso_radio']
    )
    
    corazon_tag = factory.addSphere(
        params['corazon_x'], params['corazon_y'], 
        params['corazon_z'], params['corazon_r']
    )
    
    tool_list = [(3, corazon_tag)]
    
    if include_lungs:
        pulmon_izq_tag = add_ellipsoid(
            factory,
            params['pulmon_izq_x'], params['pulmon_y'], params['pulmon_z'],
            params['pulmon_rx'], params['pulmon_ry'], params['pulmon_rz']
        )
        pulmon_der_tag = add_ellipsoid(
            factory,
            params['pulmon_der_x'], params['pulmon_y'], params['pulmon_z'],
            params['pulmon_rx'], params['pulmon_ry'], params['pulmon_rz']
        )
        tool_list.extend([(3, pulmon_izq_tag), (3, pulmon_der_tag)])
    
    # Operación booleana fragment
    out, mapping = factory.fragment([(3, torso_tag)], tool_list)
    factory.synchronize()
    
    # Identificar volúmenes
    volumes = gmsh.model.getEntities(dim=3)
    tags = [v[1] for v in volumes]
    
    torso_vol = max(tags, key=get_bbox_volume)
    organo_tags = [t for t in tags if t != torso_vol]
    corazon_vol = min(organo_tags,
                      key=lambda t: dist_to(t, params['corazon_x'], 
                                           params['corazon_y'], 
                                           params['corazon_z']))
    
    result = {
        'torso_vol': torso_vol,
        'corazon_vol': corazon_vol,
        'include_lungs': include_lungs,
        'params': params
    }
    
    if include_lungs:
        pulmon_tags = [t for t in organo_tags if t != corazon_vol]
        pulmon_izq_vol = min(pulmon_tags, key=lambda t: get_centroid(t)[0])
        pulmon_der_vol = max(pulmon_tags, key=lambda t: get_centroid(t)[0])
        result['pulmon_izq_vol'] = pulmon_izq_vol
        result['pulmon_der_vol'] = pulmon_der_vol
    
    return result


def generate_mesh(include_lungs: bool = True, output_path: str | None = None,
                  params: dict | None = None, show_gui: bool = False) -> str:
    """
    Genera la malla completa del modelo de torso.

    Args:
        include_lungs: Si True, incluye pulmones en el modelo.
        output_path: Ruta donde guardar la malla. Si es None se usa un nombre
                     por defecto en el directorio actual.
        params: Parámetros geométricos. Si es None se usan :data:`DEFAULT_PARAMS`.
        show_gui: Si True, abre la GUI de Gmsh al finalizar.

    Returns:
        Ruta del archivo ``.msh`` generado.

    Raises:
        ImportError: Si gmsh no está instalado.
    """
    if not HAS_GMSH:
        raise ImportError("gmsh no está instalado. Instala con: pip install gmsh")

    if params is None:
        params = DEFAULT_PARAMS

    # Crear geometría
    model_info = create_geometry(include_lungs, params)

    # Asignar Physical Groups
    gmsh.model.addPhysicalGroup(3, [model_info['torso_vol']], tag=1)
    gmsh.model.addPhysicalGroup(3, [model_info['corazon_vol']], tag=2)
    gmsh.model.setPhysicalName(3, 1, "Torso")
    gmsh.model.setPhysicalName(3, 2, "Corazon")

    if include_lungs:
        gmsh.model.addPhysicalGroup(3, [model_info['pulmon_izq_vol']], tag=3)
        gmsh.model.addPhysicalGroup(3, [model_info['pulmon_der_vol']], tag=4)
        gmsh.model.setPhysicalName(3, 3, "PulmonIzquierdo")
        gmsh.model.setPhysicalName(3, 4, "PulmonDerecho")

    # Superficie exterior del torso
    surfs_torso = gmsh.model.getBoundary([(3, model_info['torso_vol'])], oriented=False)
    surf_tags = [abs(s[1]) for s in surfs_torso]
    gmsh.model.addPhysicalGroup(2, surf_tags, tag=10)
    gmsh.model.setPhysicalName(2, 10, "SuperficieTorso")

    # Refinamiento adaptativo
    gmsh.option.setNumber("Mesh.CharacteristicLengthMax", params['lc_torso'])
    gmsh.option.setNumber("Mesh.CharacteristicLengthMin", params['lc_organo'])

    def get_surfs(vol_tag):
        bnd = gmsh.model.getBoundary([(3, vol_tag)], oriented=False)
        return [abs(b[1]) for b in bnd]

    organo_surfs = get_surfs(model_info['corazon_vol'])
    if include_lungs:
        organo_surfs += get_surfs(model_info['pulmon_izq_vol'])
        organo_surfs += get_surfs(model_info['pulmon_der_vol'])

    field_dist = gmsh.model.mesh.field.add("Distance")
    gmsh.model.mesh.field.setNumbers(field_dist, "SurfacesList", organo_surfs)

    field_thresh = gmsh.model.mesh.field.add("Threshold")
    gmsh.model.mesh.field.setNumber(field_thresh, "InField", field_dist)
    gmsh.model.mesh.field.setNumber(field_thresh, "SizeMin", params['lc_organo'])
    gmsh.model.mesh.field.setNumber(field_thresh, "SizeMax", params['lc_torso'])
    gmsh.model.mesh.field.setNumber(field_thresh, "DistMin", 0.02)
    gmsh.model.mesh.field.setNumber(field_thresh, "DistMax", 0.08)

    gmsh.model.mesh.field.setAsBackgroundMesh(field_thresh)
    gmsh.option.setNumber("Mesh.Algorithm3D", 1)

    # Generar malla
    logger.info("Generando malla 3D...")
    gmsh.model.mesh.generate(3)

    # Determinar nombre de archivo
    if output_path is None:
        suffix = "_con_pulmones" if include_lungs else "_sin_pulmones"
        output_path = f"ecg_torso_auto{suffix}.msh"

    gmsh.write(output_path)
    logger.info("Malla guardada en: %s", output_path)

    if show_gui:
        gmsh.fltk.run()

    gmsh.finalize()
    return output_path


def get_preview_data(include_lungs=True, params=None):
    """
    Obtiene datos para vista previa del modelo (sin generar malla).
    
    Returns:
        dict con puntos y conectividad para visualización
    """
    if not HAS_GMSH:
        raise ImportError("gmsh no está instalado. Instala con: pip install gmsh")
    
    if params is None:
        params = DEFAULT_PARAMS
    
    # Crear geometría
    model_info = create_geometry(include_lungs, params)
    
    # Obtener información de volúmenes para visualización
    volumes = gmsh.model.getEntities(dim=3)
    
    preview_data = {
        'num_volumes': len(volumes),
        'include_lungs': include_lungs,
        'bounds': {
            'x': (-params['torso_radio'], params['torso_radio']),
            'y': (-params['torso_radio'], params['torso_radio']),
            'z': (params['torso_z0'], params['torso_z0'] + params['torso_alto'])
        },
        'components': {
            'torso': {
                'center': (0, 0, params['torso_z0'] + params['torso_alto']/2),
                'radius': params['torso_radio'],
                'height': params['torso_alto']
            },
            'corazon': {
                'center': (params['corazon_x'], params['corazon_y'], params['corazon_z']),
                'radius': params['corazon_r']
            }
        }
    }
    
    if include_lungs:
        preview_data['components']['pulmon_izq'] = {
            'center': (params['pulmon_izq_x'], params['pulmon_y'], params['pulmon_z']),
            'radii': (params['pulmon_rx'], params['pulmon_ry'], params['pulmon_rz'])
        }
        preview_data['components']['pulmon_der'] = {
            'center': (params['pulmon_der_x'], params['pulmon_y'], params['pulmon_z']),
            'radii': (params['pulmon_rx'], params['pulmon_ry'], params['pulmon_rz'])
        }
    
    gmsh.finalize()
    
    return preview_data
