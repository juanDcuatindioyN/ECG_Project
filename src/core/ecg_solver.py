# -*- coding: utf-8 -*-
"""
Módulo de resolución completa del problema directo de ECG
=========================================================

Implementa el pipeline completo de 5 pasos para simular el problema
directo del ECG usando el método de elementos finitos:

  Paso 1: Cargar malla con conductividades heterogéneas
  Paso 2: Ensamblar matriz de rigidez K
  Paso 3: Definir fuentes cardíacas (dipolo equivalente temporal)
  Paso 4: Resolver sistema K·φ = f para cada instante
  Paso 5: Postprocesar potenciales en electrodos (12 derivaciones)

Autor: Proyecto ECG
"""

import logging
import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla
from skfem import Basis, ElementTetP1, BilinearForm
from skfem.element import DiscreteField
from skfem.helpers import grad, dot

from .mesh_loader import load_mesh_skfem, extract_surface_tris

logger = logging.getLogger(__name__)


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

# Posiciones precordiales por defecto (en metros)
DEFAULT_ELECTRODES = {
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

def extract_material_labels(mio, cell_type: str = "tetra") -> np.ndarray:
    """
    Extrae etiquetas de material del objeto meshio.
    Compatible con formatos .msh y .vtk.

    Args:
        mio: Objeto meshio con la malla.
        cell_type: Tipo de celda a buscar (por defecto "tetra").

    Returns:
        Array de enteros con la etiqueta de material por elemento.

    Raises:
        RuntimeError: Si no se encuentran elementos del tipo indicado o
                      no se localiza un campo de materiales válido.
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


def extract_surface_nodes(mio, surface_tag: int = 10) -> np.ndarray:
    """
    Extrae nodos de la superficie exterior del torso.

    Intenta primero con triángulos etiquetados (tag=10). Si no los encuentra,
    usa las caras que aparecen exactamente 1 vez en TODOS los tetraedros del
    modelo — esas son la superficie exterior real.

    Returns:
        Array 1D de índices de nodos en la superficie exterior.
    """
    # Intento 1: triángulos con tag explícito
    if "triangle" in mio.cells_dict:
        try:
            tri_labels = extract_material_labels(mio, "triangle")
            mask = tri_labels == surface_tag
            if mask.sum() > 0:
                triangles_surf = mio.cells_dict["triangle"][mask]
                return np.unique(triangles_surf.ravel()).astype(int)
        except Exception:
            pass

    # Intento 2: caras que aparecen 1 vez en el modelo completo = superficie exterior
    if "tetra" in mio.cells_dict:
        try:
            tetras = mio.cells_dict["tetra"]
            cara_count: dict = {}
            for tet in tetras:
                for cara in [
                    tuple(sorted([tet[0], tet[1], tet[2]])),
                    tuple(sorted([tet[0], tet[1], tet[3]])),
                    tuple(sorted([tet[0], tet[2], tet[3]])),
                    tuple(sorted([tet[1], tet[2], tet[3]])),
                ]:
                    cara_count[cara] = cara_count.get(cara, 0) + 1

            caras_ext = [c for c, n in cara_count.items() if n == 1]
            if caras_ext:
                return np.unique(np.array(caras_ext).ravel()).astype(int)
        except Exception:
            pass

    return np.array([], dtype=int)


# =============================================================
# PASO 1: CARGAR MALLA CON CONDUCTIVIDADES
# =============================================================

def load_mesh_with_conductivities(vtk_path: str, conductivities: dict | None = None) -> dict:
    """
    Carga malla VTK/MSH y asigna conductividades por material.

    Args:
        vtk_path: Ruta al archivo VTK o MSH.
        conductivities: Diccionario ``{material_id: sigma_S/m}``.
                        Si es None se usan :data:`DEFAULT_CONDUCTIVITIES`.

    Returns:
        Diccionario con claves:
        ``mesh``, ``basis``, ``sigma_el``, ``sigma_field``,
        ``mat_labels``, ``surface_nodes``, ``mio``.

    Raises:
        ValueError: Si algún material de la malla no tiene conductividad definida.
        RuntimeError: Si la malla no contiene tetraedros o etiquetas de material.
    """
    if conductivities is None:
        conductivities = DEFAULT_CONDUCTIVITIES

    # Cargar malla
    mesh, mio = load_mesh_skfem(vtk_path)

    # Extraer etiquetas de material
    mat_labels = extract_material_labels(mio, "tetra")

    # Verificar que todos los materiales tienen conductividad
    missing = [mid for mid in np.unique(mat_labels) if mid not in conductivities]
    if missing:
        raise ValueError(
            f"Los materiales {missing} no tienen conductividad definida. "
            "Agrégalos al diccionario de conductividades."
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

    logger.info(
        "Malla cargada: %d nodos, %d elementos, %d nodos de superficie",
        mesh.p.shape[1], mesh.t.shape[1], len(surface_nodes),
    )

    return {
        'mesh': mesh,
        'basis': basis,
        'sigma_el': sigma_el,
        'sigma_field': sigma_field,
        'mat_labels': mat_labels,
        'surface_nodes': surface_nodes,
        'mio': mio,
    }


# =============================================================
# PASO 2: ENSAMBLAR MATRIZ DE RIGIDEZ
# =============================================================

def assemble_stiffness_matrix(basis, sigma_field) -> sp.csr_matrix:
    """
    Ensambla la matriz de rigidez K para el problema de Poisson
    con conductividades heterogéneas.

    Forma bilineal: a(u,v) = ∫_Ω σ ∇u · ∇v dV

    Args:
        basis: Base funcional de scikit-fem.
        sigma_field: Campo de conductividades (DiscreteField).

    Returns:
        Matriz K dispersa en formato CSR.
    """
    @BilinearForm
    def bilinear_form(u, v, w):
        return w.sigma * dot(grad(u), grad(v))

    K = bilinear_form.assemble(basis, sigma=sigma_field)
    logger.debug("Matriz K ensamblada: %dx%d, nnz=%d", K.shape[0], K.shape[1], K.nnz)
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


def build_source_vector(mesh, dipole_pos: np.ndarray, dipole_moment: np.ndarray) -> np.ndarray:
    """
    Construye el vector de fuentes f para un dipolo puntual.

    f_i = p · grad(φ_i)(r0)

    Args:
        mesh: Malla scikit-fem.
        dipole_pos: Posición del dipolo, shape (3,).
        dipole_moment: Momento dipolar p = (px, py, pz) en A·m.

    Returns:
        Vector f de shape (N,).

    Raises:
        ValueError: Si el dipolo no está dentro de ningún elemento.
    """
    N = mesh.p.shape[1]
    f = np.zeros(N)

    elem_idx, _ = find_element_containing_point(mesh, dipole_pos)

    if elem_idx == -1:
        raise ValueError(
            f"El dipolo en {dipole_pos} no está dentro de ningún elemento. "
            "Verifica que la posición esté dentro del dominio."
        )

    grads = compute_p1_gradients(mesh, elem_idx)
    nodes = mesh.t.T[elem_idx]

    for local_i, global_i in enumerate(nodes):
        f[global_i] = np.dot(dipole_moment, grads[local_i])

    return f


def build_source_matrix(mesh, dipole_pos: np.ndarray, dipole_table: np.ndarray) -> dict:
    """
    Construye la matriz de fuentes F para todos los instantes del ciclo cardíaco.

    Args:
        mesh: Malla scikit-fem.
        dipole_pos: Posición del dipolo, shape (3,).
        dipole_table: Array (T, 4) con columnas [t, px, py, pz].

    Returns:
        Diccionario con:
        ``F_matrix`` (N, T), ``times`` (T,), ``dipoles`` (T, 3).
    """
    times = dipole_table[:, 0]
    dipoles = dipole_table[:, 1:]

    N = mesh.p.shape[1]
    T = len(times)
    F_matrix = np.zeros((N, T))

    for i, dipole_moment in enumerate(dipoles):
        F_matrix[:, i] = build_source_vector(mesh, dipole_pos, dipole_moment)

    logger.debug("Matriz de fuentes F construida: %dx%d", N, T)
    return {
        'F_matrix': F_matrix,
        'times': times,
        'dipoles': dipoles,
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


def solve_single_instant(
    K_red: sp.csr_matrix,
    f_col: np.ndarray,
    mask: np.ndarray,
    ref_node: int,
    N: int,
    tol: float = 1e-8,
    max_iter: int = 5000,
) -> tuple[np.ndarray, float, int]:
    """
    Resuelve K_red·phi_red = f_col usando MINRES con precondicionador Jacobi.

    La tolerancia se ajusta automáticamente si el sistema es grande para
    evitar tiempos de cómputo excesivos.

    Args:
        K_red: Matriz de rigidez reducida (sin fila/columna del nodo de referencia).
        f_col: Vector de fuentes reducido.
        mask: Máscara booleana que indica los DOF activos.
        ref_node: Índice del nodo de referencia (phi=0).
        N: Número total de nodos.
        tol: Tolerancia relativa del solver.
        max_iter: Número máximo de iteraciones.

    Returns:
        Tupla ``(phi_full, residual, info)`` donde:
        - ``phi_full``: Potencial en todos los nodos, shape (N,).
        - ``residual``: Residuo relativo ||K·x - f|| / ||f||.
        - ``info``: Código de retorno de MINRES (0 = convergió).
    """
    # Ajuste adaptativo de tolerancia para mallas grandes
    n_dof = K_red.shape[0]
    effective_tol = max(tol, 1e-6 * (n_dof / 10_000) ** 0.5) if n_dof > 10_000 else tol

    # Precondicionador diagonal (Jacobi)
    diag = K_red.diagonal()
    diag = np.where(np.abs(diag) > 1e-15, diag, 1.0)
    M_prec = sp.diags(1.0 / diag)

    phi_red, info = spla.minres(K_red, f_col, M=M_prec, rtol=effective_tol, maxiter=max_iter)

    if info != 0:
        logger.warning("MINRES no convergió (info=%d, tol=%.2e, iter=%d)", info, effective_tol, max_iter)

    # Reconstruir phi completo
    phi_full = np.zeros(N)
    phi_full[mask] = phi_red

    # Residuo relativo
    f_norm = np.linalg.norm(f_col)
    residual = np.linalg.norm(K_red @ phi_red - f_col) / (f_norm + 1e-30)

    return phi_full, residual, info


def solve_ecg_system(
    K: sp.csr_matrix,
    F_matrix: np.ndarray,
    mesh,
    surface_nodes: np.ndarray,
    dipole_pos: np.ndarray,
    tol: float = 1e-8,
    max_iter: int = 5000,
) -> dict:
    """
    Resuelve el sistema K·φ = f para todos los instantes temporales.

    Args:
        K: Matriz de rigidez CSR.
        F_matrix: Matriz de fuentes, shape (N, T).
        mesh: Malla scikit-fem.
        surface_nodes: Índices de nodos en la superficie del torso.
        dipole_pos: Posición del dipolo cardíaco.
        tol: Tolerancia del solver iterativo.
        max_iter: Máximo de iteraciones por instante.

    Returns:
        Diccionario con:
        ``PHI`` (N, T), ``ref_node``, ``ref_origin``, ``residuals`` (T,),
        ``n_converged`` (número de instantes que convergieron).
    """
    N = mesh.p.shape[1]
    T = F_matrix.shape[1]

    ref_node, origin = select_reference_node(mesh, surface_nodes, dipole_pos)
    K_red, F_red, mask = apply_gauge_condition(K, F_matrix, ref_node)

    PHI = np.zeros((N, T))
    residuals = np.zeros(T)
    n_converged = 0

    for i in range(T):
        f_col = F_red[:, i]

        if np.linalg.norm(f_col) < 1e-20:
            PHI[:, i] = 0.0
            n_converged += 1
            continue

        phi_i, res_i, info_i = solve_single_instant(
            K_red, f_col, mask, ref_node, N, tol, max_iter
        )
        PHI[:, i] = phi_i
        residuals[i] = res_i
        if info_i == 0:
            n_converged += 1

    logger.info(
        "Sistema resuelto: %d/%d instantes convergieron, residuo máx=%.2e",
        n_converged, T, residuals.max(),
    )

    return {
        'PHI': PHI,
        'ref_node': ref_node,
        'ref_origin': origin,
        'residuals': residuals,
        'n_converged': n_converged,
    }


# =============================================================
# PASO 5: POSTPROCESAR POTENCIALES EN ELECTRODOS
# =============================================================

def find_closest_node_on_surface(mesh, surface_nodes: np.ndarray, position: np.ndarray) -> int:
    """
    Encuentra el nodo de superficie más cercano a la posición dada.

    Siempre busca dentro de surface_nodes. Si está vacío lanza un error
    en lugar de buscar en nodos internos.
    """
    if len(surface_nodes) == 0:
        raise ValueError(
            "surface_nodes está vacío — no se puede localizar el electrodo en la superficie. "
            "Verifica que la malla tenga etiquetas de superficie (tag=10) o tetraedros del torso (material 1)."
        )
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


def compute_12_lead_ecg(phi_electrodes: dict) -> dict:
    """
    Calcula derivaciones ECG a partir de los electrodos disponibles.

    Solo usa los electrodos precordiales (V1–V6) que estén presentes.
    No requiere RA, LA ni LL.

    Args:
        phi_electrodes: dict {nombre_electrodo: array_potencial}

    Returns:
        dict con una derivación por cada electrodo presente.
    """
    leads = {}
    for name, signal in phi_electrodes.items():
        leads[name] = signal
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


def plot_electrodes_on_torso(mesh, mio, electrode_nodes, surface_nodes,
                              PHI=None, instant_idx=4,
                              output_file="output/electrodos_torso.png"):
    """Alias — implementacion en src/visualization/viewer3d.py."""
    from ..visualization.viewer3d import plot_electrodes_on_torso as _plot
    return _plot(mesh, mio, electrode_nodes, surface_nodes,
                 PHI=PHI, instant_idx=instant_idx, output_file=output_file)


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
    
    def run_full_pipeline(self, tol: float = 1e-8, max_iter: int = 5000) -> dict:
        """
        Ejecuta el pipeline completo de 5 pasos.

        Args:
            tol: Tolerancia del solver iterativo.
            max_iter: Máximo de iteraciones por instante temporal.

        Returns:
            Diccionario con todos los resultados del pipeline.

        Raises:
            ValueError: Si la malla no contiene los materiales requeridos o
                        el dipolo está fuera del dominio.
            RuntimeError: Si la malla no tiene el formato esperado.
        """
        logger.info("Iniciando pipeline ECG completo para: %s", self.vtk_path)

        # Paso 1: Cargar malla
        logger.info("Paso 1: Cargando malla con conductividades...")
        self.mesh_data = load_mesh_with_conductivities(
            self.vtk_path, self.conductivities
        )

        # Paso 2: Ensamblar K
        logger.info("Paso 2: Ensamblando matriz de rigidez K...")
        self.K = assemble_stiffness_matrix(
            self.mesh_data['basis'],
            self.mesh_data['sigma_field']
        )

        # Paso 3: Fuentes cardíacas
        logger.info("Paso 3: Construyendo fuentes cardíacas...")
        self.source_data = build_source_matrix(
            self.mesh_data['mesh'],
            self.dipole_pos,
            self.dipole_table
        )

        # Paso 4: Resolver sistema
        logger.info("Paso 4: Resolviendo sistema K·φ = f (%d instantes)...",
                    self.source_data['F_matrix'].shape[1])
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
        logger.info("Paso 5: Postprocesando potenciales en electrodos...")
        self.ecg_data = postprocess_ecg(
            self.mesh_data['mesh'],
            self.mesh_data['surface_nodes'],
            self.solution_data['PHI'],
            self.electrode_positions
        )

        logger.info("Pipeline completado exitosamente.")
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
        if not all([self.mesh_data is not None, self.K is not None,
                    self.solution_data is not None, self.ecg_data is not None]):
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
