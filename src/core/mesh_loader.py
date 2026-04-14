# -*- coding: utf-8 -*-
"""
Módulo principal para procesamiento VTK y resolución de Poisson

Funciones principales:
    load_mesh_skfem: Carga mallas VTK usando scikit-fem
    extract_surface_tris: Extrae triángulos de superficie
    solve_poisson_point: Resuelve Poisson con fuentes puntuales
    plot_surface: Crea visualizaciones 3D
"""

import logging
import numpy as np
import meshio
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401
from matplotlib.figure import Figure

# --- scikit-fem imports con compatibilidad de versiones ---
from skfem import Basis, ElementTetP1
from skfem.models.poisson import laplace
try:
    from skfem import BilinearForm
except Exception:
    from skfem.assembly import BilinearForm
from skfem.assembly import asm
from skfem.utils import solve, enforce
from skfem.helpers import dot, grad

logger = logging.getLogger(__name__)

# Configuración por defecto
DEFAULT_VTK = "Sphere.vtk"
DEFAULT_MODE = "poisson"
DEFAULT_Z0, DEFAULT_Z1 = -0.4, 0.4

DEFAULT_SOURCES = np.array([[0.5, -0.4, 0.1]], dtype=float)
DEFAULT_CHARGES = np.array([1.0], dtype=float)


def load_mesh_skfem(vtk_path: str):
    """
    Carga una malla VTK/MSH y la convierte a formato scikit-fem.

    Args:
        vtk_path: Ruta al archivo de malla.

    Returns:
        Tupla ``(mesh, mio)`` donde ``mesh`` es la malla scikit-fem
        y ``mio`` es el objeto meshio original.

    Raises:
        FileNotFoundError: Si el archivo no existe.
        RuntimeError: Si la malla no contiene celdas tetraédricas.
    """
    import os
    if not os.path.exists(vtk_path):
        raise FileNotFoundError(f"Archivo de malla no encontrado: {vtk_path}")

    mio = meshio.read(vtk_path)
    P = np.asarray(mio.points, dtype=float).T

    if "tetra" in mio.cells_dict:
        T = np.asarray(mio.cells_dict["tetra"], dtype=int).T
    elif "tetra10" in mio.cells_dict:
        t10 = np.asarray(mio.cells_dict["tetra10"], dtype=int)
        T = t10[:, [0, 1, 2, 3]].T
    else:
        raise RuntimeError("El archivo no contiene celdas tetraédricas.")

    try:
        from skfem import MeshTet
        try:
            mesh = MeshTet.from_meshio(mio)
        except Exception:
            mesh = MeshTet(P, T)
    except Exception:
        from skfem import MeshTet1
        try:
            mesh = MeshTet1.from_meshio(mio)
        except Exception:
            mesh = MeshTet1(P, T)

    logger.info("Malla cargada: %d nodos, %d elementos — %s",
                mesh.p.shape[1], mesh.t.shape[1], vtk_path)
    return mesh, mio


def extract_surface_tris(mio, mesh):
    """
    Extrae los triángulos de la superficie de la malla.
    
    Args:
        mio: Objeto meshio con la malla original
        mesh: Malla scikit-fem
        
    Returns:
        np.ndarray: Array de triángulos de superficie
    """
    tri_blocks = [b for b in mio.cells if b.type in ("triangle", "tri")]
    if tri_blocks:
        return tri_blocks[0].data
    
    # Si no hay triángulos explícitos, extraer de tetraedros
    from collections import Counter
    t = mesh.t.T
    faces = np.vstack([t[:, [0, 1, 2]], t[:, [0, 1, 3]], t[:, [0, 2, 3]], t[:, [1, 2, 3]]])
    faces_sorted = np.sort(faces, axis=1)
    counts = Counter(map(tuple, faces_sorted))
    mask = np.array([counts[tuple(f)] == 1 for f in map(tuple, faces_sorted)])
    return faces[mask]


def _is_inside(mesh, x):
    """Verifica si un punto está dentro de la malla."""
    try:
        _ = mesh.element_finder()(x[0], x[1], x[2], _search_all=True)
        return True
    except Exception:
        return False


def _project_inside(mesh, s, max_iter=25):
    """
    Proyecta un punto al interior de la malla.
    
    Args:
        mesh: Malla scikit-fem
        s: Punto a proyectar
        max_iter: Máximo número de iteraciones
        
    Returns:
        np.ndarray: Punto proyectado al interior
    """
    s = np.asarray(s, dtype=float).copy()
    c = mesh.p.mean(axis=1)
    
    if not _is_inside(mesh, c):
        c = mesh.p[:, 0]
    
    if _is_inside(mesh, s):
        return s
    
    lo, hi = 0.0, 1.0
    for _ in range(max_iter):
        mid = 0.5 * (lo + hi)
        x = c + mid * (s - c)
        if _is_inside(mesh, x):
            lo = mid
        else:
            hi = mid
    
    return c + (lo - 1e-6) * (s - c)


def solve_poisson_point(mesh, sources, charges):
    """
    Resuelve la ecuación de Poisson con fuentes puntuales.

    Args:
        mesh: Malla scikit-fem.
        sources: Array de coordenadas de fuentes, shape (N, 3).
        charges: Array de cargas para cada fuente, shape (N,).

    Returns:
        Tupla ``(basis, V, used_sources)`` donde:
        - ``basis``: Base de elementos finitos.
        - ``V``: Solución del potencial, shape (N_nodos,).
        - ``used_sources``: Fuentes proyectadas al interior del dominio.

    Raises:
        ValueError: Si ``sources`` y ``charges`` tienen longitudes distintas.
    """
    sources = np.asarray(sources, dtype=float)
    charges = np.asarray(charges, dtype=float)

    if len(sources) != len(charges):
        raise ValueError(
            f"sources ({len(sources)}) y charges ({len(charges)}) deben tener la misma longitud."
        )

    basis = Basis(mesh, ElementTetP1())
    A = asm(laplace, basis)
    b = np.zeros(basis.N)
    used = []
    c = mesh.p.mean(axis=1)

    for s, q in zip(sources, charges):
        s_in = _project_inside(mesh, s)
        if not _is_inside(mesh, s_in):
            logger.warning("Fuente en %s no pudo proyectarse al interior; usando centroide.", s)
            s_in = c
        b += q * basis.point_source(s_in)
        used.append(s_in)

    D = basis.get_dofs()
    xdir = np.zeros(basis.N)
    A_bc, b_bc = enforce(A, b, D=D, x=xdir)
    V = solve(A_bc, b_bc)

    logger.debug("Poisson resuelto: %d fuentes, max|V|=%.4e", len(used), np.abs(V).max())
    return basis, V, np.vstack(used)


def plot_surface(mesh, tris, V, sources=None, title=None, figsize=(8, 6), mio=None):
    """
    Crea una figura de matplotlib mostrando el modelo completo con la solución V.
    
    Si mio está disponible (modelo generado), muestra el modelo completo con todos
    los materiales. Si no, usa visualización simple de superficie.
    
    Args:
        mesh: Malla scikit-fem
        tris: Triángulos de superficie
        V: Solución del potencial
        sources: Coordenadas de fuentes (opcional)
        title: Título del gráfico
        figsize: Tamaño de la figura
        mio: Objeto meshio con datos de materiales (opcional)
        
    Returns:
        Figure: Figura de matplotlib
    """
    # Si tenemos mio (modelo generado), usar visualización completa
    if mio is not None:
        try:
            from ..visualization.viewer3d import crear_figura_3d_con_electrodos
            # Detectar si tiene pulmones
            from ..visualization.viewer3d import extraer_etiquetas_materiales
            etiquetas = extraer_etiquetas_materiales(mio)
            incluir_pulmones = False
            if etiquetas is not None:
                materiales_unicos = np.unique(etiquetas)
                # Si tiene materiales 3 o 4 (pulmones), incluirlos
                incluir_pulmones = (3 in materiales_unicos or 4 in materiales_unicos)
            
            # Usar función especial que muestra electrodos con transparencia aumentada
            fig = crear_figura_3d_con_electrodos(mesh, mio, sources, incluir_pulmones=incluir_pulmones)
            
            # Actualizar título si se proporciona
            if title:
                ax = fig.axes[0]
                ax.set_title(title, fontsize=12, fontweight='bold', pad=20)
            
            return fig
        except Exception as e:
            print(f"Error usando visualización completa: {e}")
            import traceback
            traceback.print_exc()
            # Continuar con visualización simple
    
    # Visualización simple (fallback para archivos VTK sin materiales)
    X = mesh.p.T
    fig = Figure(figsize=figsize, dpi=100)
    ax = fig.add_subplot(111, projection="3d")
    
    # Crear superficie sólida con colores según potencial
    surf = ax.plot_trisurf(
        X[:, 0], X[:, 1], X[:, 2],
        triangles=tris,
        linewidth=0.1,
        antialiased=True,
        shade=True,
        cmap='plasma',
        alpha=0.9
    )
    
    # Asignar valores de la solución como colores
    V_arr = V.toarray().ravel() if hasattr(V, 'toarray') else np.asarray(V).ravel()
    surf.set_array(V_arr[tris].mean(axis=1))
    surf.autoscale()
    
    # Agregar fuentes/electrodos si existen
    if sources is not None:
        S = np.asarray(sources, dtype=float)
        if S.size > 0:
            # Dibujar puntos rojos grandes para los electrodos
            ax.scatter(S[:, 0], S[:, 1], S[:, 2], 
                      s=150, c="red", marker='o', 
                      label=f"Electrodos ({len(S)})", 
                      edgecolors='darkred', linewidth=2,
                      zorder=1000, alpha=0.9)
            
            # Agregar etiquetas numéricas a cada electrodo
            for i, (x, y, z) in enumerate(S):
                ax.text(x, y, z, f'  E{i+1}', 
                       fontsize=8, color='darkred', 
                       fontweight='bold', zorder=1001)
            
            ax.legend(loc='upper right')
    
    # Configurar ejes y título
    ax.set_title(title or "Solución Automática de Poisson 3D", 
                fontsize=12, fontweight='bold', pad=20)
    ax.set_xlabel("X", fontsize=10)
    ax.set_ylabel("Y", fontsize=10)
    ax.set_zlabel("Z", fontsize=10)
    
    # Vista inicial optimizada
    ax.view_init(elev=20, azim=45)
    
    # Colorbar
    try:
        cbar = fig.colorbar(surf, ax=ax, shrink=0.6, aspect=20, pad=0.1)
        cbar.set_label("Potencial (V)", fontsize=10)
    except:
        pass
    
    # Ajustar layout
    fig.tight_layout()
    
    return fig


# Funciones adicionales para compatibilidad con modo sigma (si se necesita en el futuro)
def _sigma_from_vtk(mio, n_elems):
    """Extrae valores de conductividad sigma del VTK."""
    sigma = np.ones(n_elems)
    try:
        for name, bytype in mio.cell_data_dict.items():
            if name.lower() != "sigma":
                continue
            s_all = []
            for ctype, arr in bytype.items():
                if ctype in ("tetra", "tetra10"):
                    s_all.append(np.ravel(arr))
            if s_all:
                s = np.concatenate(s_all)
                if s.size == n_elems:
                    return s
    except Exception:
        pass
    
    try:
        for name, arrays in mio.cell_data.items():
            if name.lower() != "sigma":
                continue
            s_all = []
            k = 0
            for blk in mio.cells:
                if blk.type in ("tetra", "tetra10"):
                    s_all.append(np.ravel(arrays[k]))
                k += 1
            if s_all:
                s = np.concatenate(s_all)
                if s.size == n_elems:
                    return s
    except Exception:
        pass
    
    return sigma





def nodo_mas_cercano(mesh, posicion):
    """
    Retorna el índice del nodo más cercano a la posición dada.
    """
    distancias = np.linalg.norm(mesh.p.T - posicion, axis=1)
    return int(np.argmin(distancias))

def nodo_mas_cercano_en_superficie(mesh, nodos_sup, posicion, used_nodes=None):
    """
    Devuelve el índice del nodo en nodos_sup más cercano a posicion.
    Si used_nodes es un set, evita devolver nodos ya usados (elige siguiente más cercano).
    """
    nodos_sup = np.asarray(nodos_sup, dtype=int)
    if nodos_sup.size == 0:
        return nodo_mas_cercano(mesh, posicion)
    coords = mesh.p[:, nodos_sup].T  # shape (M,3)
    distancias = np.linalg.norm(coords - posicion, axis=1)
    order = np.argsort(distancias)
    for idx in order:
        candidate = int(nodos_sup[idx])
        if used_nodes is None or candidate not in used_nodes:
            return candidate
    # fallback: devolver el más cercano aunque esté usado
    return int(nodos_sup[order[0]])
