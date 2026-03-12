# -*- coding: utf-8 -*-
"""
Módulo principal para procesamiento VTK y resolución de Poisson

Este módulo contiene las funciones principales para:
- Carga y procesamiento de archivos VTK
- Extracción de superficies de mallas tetraédricas
- Resolución de ecuaciones de Poisson con fuentes puntuales
- Visualización 3D de resultados

Funciones principales:
    load_mesh_skfem: Carga mallas VTK usando scikit-fem
    extract_surface_tris: Extrae triángulos de superficie
    solve_poisson_point: Resuelve Poisson con fuentes puntuales
    plot_surface: Crea visualizaciones 3D
"""

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

# Configuración por defecto
DEFAULT_VTK = "Sphere.vtk"
DEFAULT_MODE = "poisson"            
DEFAULT_Z0, DEFAULT_Z1 = -0.4, 0.4  # tapas (modo sigma)

# Para modo Poisson:
DEFAULT_SOURCES = np.array([[0.5, -0.4, 0.1]], dtype=float)
DEFAULT_CHARGES = np.array([1.0], dtype=float)


def load_mesh_skfem(vtk_path: str):
    """
    Carga una malla VTK y la convierte a formato scikit-fem.
    
    Args:
        vtk_path (str): Ruta al archivo VTK
        
    Returns:
        tuple: (mesh, mio) donde mesh es la malla scikit-fem y mio es el objeto meshio
        
    Raises:
        RuntimeError: Si el VTK no contiene celdas tetraédricas
    """
    mio = meshio.read(vtk_path)
    P = np.asarray(mio.points, dtype=float).T
    
    if "tetra" in mio.cells_dict:
        T = np.asarray(mio.cells_dict["tetra"], dtype=int).T
    elif "tetra10" in mio.cells_dict:
        t10 = np.asarray(mio.cells_dict["tetra10"], dtype=int)
        T = t10[:, [0, 1, 2, 3]].T
    else:
        raise RuntimeError("El VTK no contiene celdas tetraédricas.")
    
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
        mesh: Malla scikit-fem
        sources: Array de coordenadas de fuentes (N x 3)
        charges: Array de cargas para cada fuente (N,)
        
    Returns:
        tuple: (basis, V, used_sources) donde:
            - basis: Base de elementos finitos
            - V: Solución del potencial
            - used_sources: Fuentes proyectadas al interior
    """
    basis = Basis(mesh, ElementTetP1())
    A = asm(laplace, basis)
    b = np.zeros(basis.N)
    used = []
    c = mesh.p.mean(axis=1)  # centroide
    
    print(f"\n=== PROYECTANDO {len(sources)} FUENTES AL INTERIOR ===")
    print(f"Centroide de la malla: ({c[0]:.6f}, {c[1]:.6f}, {c[2]:.6f})")
    
    for idx, (s, q) in enumerate(zip(np.asarray(sources, float), np.asarray(charges, float))):
        print(f"\nFuente {idx+1}:")
        print(f"  Original: ({s[0]:.6f}, {s[1]:.6f}, {s[2]:.6f})")
        print(f"  Dentro?: {_is_inside(mesh, s)}")
        
        s_in = _project_inside(mesh, s)
        
        if not _is_inside(mesh, s_in):
            print(f"  ⚠️ Proyección falló, usando centroide")
            s_in = c  # usar centroide si la proyección falla
        
        print(f"  Proyectada: ({s_in[0]:.6f}, {s_in[1]:.6f}, {s_in[2]:.6f})")
        
        b += q * basis.point_source(s_in)
        used.append(s_in)
    
    print("=" * 50 + "\n")
    
    D = basis.get_dofs()
    # Usar enforce para condiciones de frontera Dirichlet
    xdir = np.zeros(basis.N)
    V = enforce(A, b, D=D, x=xdir)[0]
    
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
            from .visualization.visor_mallas_3d import crear_figura_3d_con_electrodos
            # Detectar si tiene pulmones
            from .visualization.visor_mallas_3d import extraer_etiquetas_materiales
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