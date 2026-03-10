# -*- coding: utf-8 -*-
"""
Módulo de resolución completa del problema directo de ECG
=========================================================

Este módulo implementa el pipeline completo de 5 pasos para simular
el problema directo del ECG usando el método de elementos finitos:

Paso 1: Cargar malla con conductividades heterogéneas
Paso 2: Ensamblar matriz de rigidez K
Paso 3: Definir fuentes cardíacas (dipolo equivalente temporal)
Paso 4: Resolver sistema K·φ = f para cada instante
Paso 5: Postprocesar potenciales en electrodos (12 derivaciones)

Autor: Proyecto ECG
"""

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla
from skfem import Basis, ElementTetP1, BilinearForm
from skfem.element import DiscreteField
from skfem.helpers import grad, dot

from .nucleo_poisson import load_mesh_skfem, extract_surface_tris


# =============================================================
# CONFIGURACIÓN POR DEFECTO
# =============================================================

# Conductividades típicas (S/m)
DEFAULT_CONDUCTIVITIES = {
    1: 0.22,   # Torso
    2: 0.40,   # Corazón
    3: 0.05,   # Pulmón izquierdo
    4: 0.05,   # Pulmón derecho
}

# Posición del dipolo cardíaco (centro del corazón, en metros)
DEFAULT_DIPOLE_POS = np.array([-0.02, 0.00, 0.30])

# Tabla de momentos dipolares p(t) - Ciclo cardíaco simplificado
# Cada fila: [t(s), px(A·m), py(A·m), pz(A·m)]
DEFAULT_DIPOLE_TABLE = np.array([
    [0.00,   0.000,   0.000,   0.000],   # reposo
    [0.05,   0.001,   0.001,   0.001],   # onda P
    [0.10,   0.000,   0.000,   0.000],   # segmento PR
    [0.15,  -0.003,   0.002,   0.004],   # inicio QRS
    [0.20,   0.006,   0.003,   0.008],   # pico QRS (máximo)
    [0.25,   0.004,   0.001,   0.005],   # final QRS
    [0.30,   0.000,   0.000,   0.000],   # segmento ST
    [0.40,   0.002,   0.001,   0.003],   # onda T
    [0.50,   0.001,   0.000,   0.001],   # final onda T
    [0.80,   0.000,   0.000,   0.000],   # reposo (diástole)
])

# Dimensiones del torso (para posicionamiento de electrodos)
TORSO_RADIUS = 0.15   # m
TORSO_HEIGHT = 0.50   # m

# Posiciones anatómicas de electrodos (en metros)
DEFAULT_ELECTRODES = {
    # Extremidades
    "RA": np.array([-TORSO_RADIUS * 0.9,  0.0,              TORSO_HEIGHT * 0.85]),
    "LA": np.array([ TORSO_RADIUS * 0.9,  0.0,              TORSO_HEIGHT * 0.85]),
    "LL": np.array([ TORSO_RADIUS * 0.3,  0.0,              0.05]),
    # Precordiales
    "V1": np.array([-0.02,               TORSO_RADIUS * 0.95, 0.32]),
    "V2": np.array([ 0.02,               TORSO_RADIUS * 0.95, 0.32]),
    "V3": np.array([ 0.06,               TORSO_RADIUS * 0.90, 0.32]),
    "V4": np.array([ 0.09,               TORSO_RADIUS * 0.80, 0.32]),
    "V5": np.array([ 0.11,               TORSO_RADIUS * 0.65, 0.32]),
    "V6": np.array([ TORSO_RADIUS * 0.90, TORSO_RADIUS * 0.40, 0.32]),
}


# =============================================================
# FUNCIONES AUXILIARES
# =============================================================

def extract_material_labels(mio, cell_type="tetra"):
    """
    Extrae etiquetas de material del objeto meshio.
    Compatible con formatos .msh y .vtk.
    """
    if cell_type not in mio.cells_dict:
        raise RuntimeError(f"No se encontraron elementos '{cell_type}' en la malla")
    
    data = mio.cell_data_dict
    
    # Formato MSH: clave estándar de Gmsh
    if "gmsh:physical" in data and cell_type in data["gmsh:physical"]:
        return data["gmsh:physical"][cell_type].flatten().astype(int)
    
    # Formato VTK: buscar campo con IDs enteros pequeños
    for key, blocks in data.items():
        if cell_type in blocks:
            arr = blocks[cell_type].flatten()
            vals = np.unique(arr)
            if len(vals) <= 20 and arr.min() >= 0:
                return arr.astype(int)
    
    raise RuntimeError(f"No se encontró campo de materiales para '{cell_type}'")


def extract_surface_nodes(mio, surface_tag=10):
    """
    Extrae nodos de la superficie del torso (tag=10).
    """
    if "triangle" not in mio.cells_dict:
        return np.array([], dtype=int)
    
    try:
        tri_labels = extract_material_labels(mio, "triangle")
        mask = tri_labels == surface_tag
        if mask.sum() > 0:
            triangles_surf = mio.cells_dict["triangle"][mask]
            return np.unique(triangles_surf)
    except RuntimeError:
        pass
    
    return np.array([], dtype=int)


# =============================================================
# PASO 1: CARGAR MALLA CON CONDUCTIVIDADES
# =============================================================

def load_mesh_with_conductivities(vtk_path, conductivities=None):
    """
    Carga malla VTK y asigna conductividades por material.
    
    Args:
        vtk_path: Ruta al archivo VTK/MSH
        conductivities: Dict {material_id: sigma_S/m}
        
    Returns:
        dict con: mesh, basis, sigma_el, sigma_field, mat_labels, surface_nodes, mio
    """
    if conductivities is None:
        conductivities = DEFAULT_CONDUCTIVITIES
    
    # Cargar malla
    mesh, mio = load_mesh_skfem(vtk_path)
    
    # Extraer etiquetas de material
    mat_labels = extract_material_labels(mio, "tetra")
    
    # Verificar que todos los materiales tienen conductividad
    for mid in np.unique(mat_labels):
        if mid not in conductivities:
            raise ValueError(
                f"Material ID {mid} no tiene conductividad definida. "
                f"Agrégalo al diccionario de conductividades."
            )
    
    # Conductividad por elemento
    sigma_el = np.array([conductivities[m] for m in mat_labels], dtype=float)
    
    # Base funcional
    basis = Basis(mesh, ElementTetP1())
    
    # DiscreteField para ensamblaje
    n_quad = basis.X.shape[1]
    sigma_qp = np.repeat(sigma_el[:, np.newaxis], n_quad, axis=1)
    sigma_field = DiscreteField(value=sigma_qp)
    
    # Nodos de superficie
    surface_nodes = extract_surface_nodes(mio)
    
    return {
        'mesh': mesh,
        'basis': basis,
        'sigma_el': sigma_el,
        'sigma_field': sigma_field,
        'mat_labels': mat_labels,
        'surface_nodes': surface_nodes,
        'mio': mio
    }


# =============================================================
# PASO 2: ENSAMBLAR MATRIZ DE RIGIDEZ
# =============================================================

def assemble_stiffness_matrix(basis, sigma_field):
    """
    Ensambla la matriz de rigidez K para el problema de Poisson
    con conductividades heterogéneas.
    
    Args:
        basis: Base funcional de scikit-fem
        sigma_field: Campo de conductividades
        
    Returns:
        Matriz K en formato CSR
    """
    @BilinearForm
    def bilinear_form(u, v, w):
        return w.sigma * dot(grad(u), grad(v))
    
    K = bilinear_form.assemble(basis, sigma=sigma_field)
    return K.tocsr()


# =============================================================
# PASO 3: FUENTES CARDÍACAS - DIPOLO EQUIVALENTE
# =============================================================

def find_element_containing_point(mesh, point):
    """
    Encuentra el índice del tetraedro que contiene al punto dado
    usando coordenadas baricéntricas.
    
    Returns:
        (element_idx, barycentric_coords) o (-1, None) si no se encuentra
    """
    p = mesh.p.T  # (N, 3)
    t = mesh.t.T  # (E, 4)
    
    v0 = p[t[:, 0]]
    v1 = p[t[:, 1]]
    v2 = p[t[:, 2]]
    v3 = p[t[:, 3]]
    
    # Matriz de transformación afín: T = [v1-v0, v2-v0, v3-v0]
    T = np.stack([v1 - v0, v2 - v0, v3 - v0], axis=2)  # (E, 3, 3)
    rhs = (point - v0)  # (E, 3)
    
    try:
        lam123 = np.linalg.solve(T, rhs[:, :, np.newaxis])[:, :, 0]
    except np.linalg.LinAlgError:
        return -1, None
    
    lam0 = 1.0 - lam123.sum(axis=1)
    bary = np.column_stack([lam0, lam123])
    
    # Punto pertenece donde todas las coordenadas baricéntricas >= 0
    inside = np.all(bary >= -1e-10, axis=1)
    idxs = np.where(inside)[0]
    
    if len(idxs) == 0:
        return -1, None
    
    return idxs[0], bary[idxs[0]]


def compute_p1_gradients(mesh, element_idx):
    """
    Calcula los gradientes de las 4 funciones de forma P1
    dentro del elemento dado.
    
    Returns:
        Array (4, 3) con grad(phi_i) para i=0,1,2,3
    """
    p = mesh.p.T
    t = mesh.t.T
    
    nodes = t[element_idx]
    v = p[nodes]  # (4, 3)
    
    # Jacobiano: J = [v1-v0, v2-v0, v3-v0]^T
    J = (v[1:] - v[0]).T  # (3, 3)
    J_inv = np.linalg.inv(J)
    
    # Gradientes en elemento de referencia
    grad_ref = np.array([
        [-1., -1., -1.],
        [ 1.,  0.,  0.],
        [ 0.,  1.,  0.],
        [ 0.,  0.,  1.],
    ])
    
    # Transformar al espacio físico
    grads = (J_inv.T @ grad_ref.T).T
    return grads


def build_source_vector(mesh, dipole_pos, dipole_moment):
    """
    Construye el vector de fuentes f para un dipolo puntual.
    
    f_i = p · grad(phi_i)(r0)
    
    Args:
        mesh: Malla scikit-fem
        dipole_pos: Posición del dipolo (3,)
        dipole_moment: Momento dipolar p = (px, py, pz) en A·m
        
    Returns:
        Vector f de shape (N,)
    """
    N = mesh.p.shape[1]
    f = np.zeros(N)
    
    elem_idx, bary = find_element_containing_point(mesh, dipole_pos)
    
    if elem_idx == -1:
        raise ValueError(
            f"El dipolo en {dipole_pos} no está dentro de ningún elemento. "
            "Verifica que la posición esté dentro del dominio."
        )
    
    # Gradientes de funciones de forma
    grads = compute_p1_gradients(mesh, elem_idx)
    
    # Nodos del elemento
    nodes = mesh.t.T[elem_idx]
    
    # f_i = p · grad(phi_i) para los 4 nodos
    for local_i, global_i in enumerate(nodes):
        f[global_i] = np.dot(dipole_moment, grads[local_i])
    
    return f


def build_source_matrix(mesh, dipole_pos, dipole_table):
    """
    Construye matriz de fuentes F para todos los instantes del ciclo cardíaco.
    
    Args:
        mesh: Malla scikit-fem
        dipole_pos: Posición del dipolo
        dipole_table: Array (T, 4) con [t, px, py, pz] por fila
        
    Returns:
        dict con: F_matrix (N, T), times (T,), dipoles (T, 3)
    """
    times = dipole_table[:, 0]
    dipoles = dipole_table[:, 1:]
    
    N = mesh.p.shape[1]
    T = len(times)
    F_matrix = np.zeros((N, T))
    
    for i, dipole_moment in enumerate(dipoles):
        F_matrix[:, i] = build_source_vector(mesh, dipole_pos, dipole_moment)
    
    return {
        'F_matrix': F_matrix,
        'times': times,
        'dipoles': dipoles
    }


# =============================================================
# PASO 4: RESOLVER SISTEMA K·φ = f
# =============================================================

def select_reference_node(mesh, surface_nodes, dipole_pos):
    """
    Selecciona nodo de referencia (phi=0) como el más alejado del dipolo.
    """
    if len(surface_nodes) > 0:
        coords = mesh.p.T[surface_nodes]
        distances = np.linalg.norm(coords - dipole_pos, axis=1)
        ref_node = surface_nodes[np.argmax(distances)]
        origin = "superficie"
    else:
        distances = np.linalg.norm(mesh.p.T - dipole_pos, axis=1)
        ref_node = np.argmax(distances)
        origin = "malla completa"
    
    return int(ref_node), origin


def apply_gauge_condition(K, F, ref_node):
    """
    Fija phi[ref_node] = 0 eliminando su fila y columna.
    
    Returns:
        K_red, F_red, mask
    """
    N = K.shape[0]
    mask = np.ones(N, dtype=bool)
    mask[ref_node] = False
    
    K_red = K[mask][:, mask]
    
    if F.ndim == 1:
        F_red = F[mask]
    else:
        F_red = F[mask, :]
    
    return K_red, F_red, mask


def solve_single_instant(K_red, f_col, mask, ref_node, N, tol=1e-8, max_iter=5000):
    """
    Resuelve K_red·phi_red = f_col usando MINRES con precondicionador Jacobi.
    
    Returns:
        phi_full (N,), residual, solver_info
    """
    # Precondicionador diagonal
    diag = K_red.diagonal()
    diag = np.where(np.abs(diag) > 1e-15, diag, 1.0)
    M_prec = sp.diags(1.0 / diag)
    
    # Resolver
    phi_red, info = spla.minres(K_red, f_col, M=M_prec, rtol=tol, maxiter=max_iter)
    
    # Reconstruir phi completo
    phi_full = np.zeros(N)
    phi_full[mask] = phi_red
    
    # Calcular residuo
    residual = np.linalg.norm(K_red @ phi_red - f_col) / (np.linalg.norm(f_col) + 1e-30)
    
    return phi_full, residual, info


def solve_ecg_system(K, F_matrix, mesh, surface_nodes, dipole_pos, 
                     tol=1e-8, max_iter=5000):
    """
    Resuelve el sistema K·φ = f para todos los instantes.
    
    Args:
        K: Matriz de rigidez
        F_matrix: Matriz de fuentes (N, T)
        mesh: Malla
        surface_nodes: Nodos de superficie
        dipole_pos: Posición del dipolo
        tol: Tolerancia del solver
        max_iter: Máximo de iteraciones
        
    Returns:
        dict con: PHI (N, T), ref_node, residuals (T,)
    """
    N = mesh.p.shape[1]
    T = F_matrix.shape[1]
    
    # Nodo de referencia
    ref_node, origin = select_reference_node(mesh, surface_nodes, dipole_pos)
    
    # Aplicar condición de gauge
    K_red, F_red, mask = apply_gauge_condition(K, F_matrix, ref_node)
    
    # Resolver para cada instante
    PHI = np.zeros((N, T))
    residuals = np.zeros(T)
    
    for i in range(T):
        f_col = F_red[:, i]
        
        # Si dipolo es nulo, phi = 0
        if np.linalg.norm(f_col) < 1e-20:
            PHI[:, i] = 0.0
            residuals[i] = 0.0
            continue
        
        phi_i, res_i, info_i = solve_single_instant(
            K_red, f_col, mask, ref_node, N, tol, max_iter
        )
        PHI[:, i] = phi_i
        residuals[i] = res_i
    
    return {
        'PHI': PHI,
        'ref_node': ref_node,
        'ref_origin': origin,
        'residuals': residuals
    }


# =============================================================
# PASO 5: POSTPROCESAR POTENCIALES EN ELECTRODOS
# =============================================================

def find_closest_node_on_surface(mesh, surface_nodes, position):
    """
    Encuentra el nodo de superficie más cercano a la posición dada.
    """
    if len(surface_nodes) == 0:
        # Fallback: buscar en toda la malla
        distances = np.linalg.norm(mesh.p.T - position, axis=1)
        return int(np.argmin(distances))
    
    coords = mesh.p.T[surface_nodes]
    distances = np.linalg.norm(coords - position, axis=1)
    return int(surface_nodes[np.argmin(distances)])


def locate_electrodes(mesh, surface_nodes, electrode_positions=None):
    """
    Localiza los electrodos en la malla.
    
    Returns:
        dict {electrode_name: node_index}
    """
    if electrode_positions is None:
        electrode_positions = DEFAULT_ELECTRODES
    
    electrode_nodes = {}
    for name, pos in electrode_positions.items():
        node = find_closest_node_on_surface(mesh, surface_nodes, pos)
        electrode_nodes[name] = node
    
    return electrode_nodes


def compute_12_lead_ecg(phi_electrodes):
    """
    Calcula las 12 derivaciones estándar del ECG.
    
    Args:
        phi_electrodes: dict {electrode_name: potential_array}
        
    Returns:
        dict con las 12 derivaciones
    """
    RA = phi_electrodes["RA"]
    LA = phi_electrodes["LA"]
    LL = phi_electrodes["LL"]
    WCT = (RA + LA + LL) / 3.0  # Wilson Central Terminal
    
    leads = {
        "I":   LA - RA,
        "II":  LL - RA,
        "III": LL - LA,
        "aVR": RA - WCT,
        "aVL": LA - WCT,
        "aVF": LL - WCT,
        "V1":  phi_electrodes["V1"] - WCT,
        "V2":  phi_electrodes["V2"] - WCT,
        "V3":  phi_electrodes["V3"] - WCT,
        "V4":  phi_electrodes["V4"] - WCT,
        "V5":  phi_electrodes["V5"] - WCT,
        "V6":  phi_electrodes["V6"] - WCT,
    }
    
    return leads


def postprocess_ecg(mesh, surface_nodes, PHI, electrode_positions=None):
    """
    Postprocesa potenciales para obtener las 12 derivaciones del ECG.
    
    Args:
        mesh: Malla
        surface_nodes: Nodos de superficie
        PHI: Potenciales (N, T)
        electrode_positions: Posiciones de electrodos
        
    Returns:
        dict con: electrode_nodes, phi_electrodes, leads
    """
    # Localizar electrodos
    electrode_nodes = locate_electrodes(mesh, surface_nodes, electrode_positions)
    
    # Extraer potenciales en electrodos
    phi_electrodes = {
        name: PHI[node, :]
        for name, node in electrode_nodes.items()
    }
    
    # Calcular 12 derivaciones
    leads = compute_12_lead_ecg(phi_electrodes)
    
    return {
        'electrode_nodes': electrode_nodes,
        'phi_electrodes': phi_electrodes,
        'leads': leads
    }


# =============================================================
# PIPELINE COMPLETO
# =============================================================

class ECGSolver:
    """
    Clase principal para resolver el problema directo del ECG.
    """
    
    def __init__(self, vtk_path, conductivities=None, dipole_pos=None, 
                 dipole_table=None, electrode_positions=None):
        """
        Inicializa el solver de ECG.
        
        Args:
            vtk_path: Ruta al archivo VTK/MSH
            conductivities: Dict de conductividades por material
            dipole_pos: Posición del dipolo cardíaco
            dipole_table: Tabla temporal del dipolo
            electrode_positions: Posiciones de electrodos
        """
        self.vtk_path = vtk_path
        self.conductivities = conductivities or DEFAULT_CONDUCTIVITIES
        self.dipole_pos = dipole_pos if dipole_pos is not None else DEFAULT_DIPOLE_POS
        self.dipole_table = dipole_table if dipole_table is not None else DEFAULT_DIPOLE_TABLE
        self.electrode_positions = electrode_positions or DEFAULT_ELECTRODES
        
        # Estado interno
        self.mesh_data = None
        self.K = None
        self.source_data = None
        self.solution_data = None
        self.ecg_data = None
    
    def run_full_pipeline(self, tol=1e-8, max_iter=5000):
        """
        Ejecuta el pipeline completo de 5 pasos.
        
        Returns:
            dict con todos los resultados
        """
        # Paso 1: Cargar malla
        self.mesh_data = load_mesh_with_conductivities(
            self.vtk_path, self.conductivities
        )
        
        # Paso 2: Ensamblar K
        self.K = assemble_stiffness_matrix(
            self.mesh_data['basis'],
            self.mesh_data['sigma_field']
        )
        
        # Paso 3: Fuentes cardíacas
        self.source_data = build_source_matrix(
            self.mesh_data['mesh'],
            self.dipole_pos,
            self.dipole_table
        )
        
        # Paso 4: Resolver sistema
        self.solution_data = solve_ecg_system(
            self.K,
            self.source_data['F_matrix'],
            self.mesh_data['mesh'],
            self.mesh_data['surface_nodes'],
            self.dipole_pos,
            tol,
            max_iter
        )
        
        # Paso 5: Postprocesar ECG
        self.ecg_data = postprocess_ecg(
            self.mesh_data['mesh'],
            self.mesh_data['surface_nodes'],
            self.solution_data['PHI'],
            self.electrode_positions
        )
        
        return self.get_results()
    
    def get_results(self):
        """
        Retorna todos los resultados en un diccionario.
        """
        return {
            'mesh_data': self.mesh_data,
            'K': self.K,
            'source_data': self.source_data,
            'solution_data': self.solution_data,
            'ecg_data': self.ecg_data
        }
    
    def get_summary(self):
        """
        Retorna un resumen de los resultados.
        """
        if not all([self.mesh_data, self.K, self.solution_data, self.ecg_data]):
            return "Pipeline no ejecutado aún"
        
        mesh = self.mesh_data['mesh']
        PHI = self.solution_data['PHI']
        leads = self.ecg_data['leads']
        
        summary = {
            'num_nodes': mesh.p.shape[1],
            'num_elements': mesh.t.shape[1],
            'num_surface_nodes': len(self.mesh_data['surface_nodes']),
            'num_instants': PHI.shape[1],
            'phi_max': float(np.abs(PHI).max()),
            'max_residual': float(self.solution_data['residuals'].max()),
            'ref_node': int(self.solution_data['ref_node']),
            'lead_amplitudes': {
                name: float(np.abs(signal * 1000).max())  # mV
                for name, signal in leads.items()
            }
        }
        
        return summary
