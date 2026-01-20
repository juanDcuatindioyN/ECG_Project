"""
readVTK.py — AUTO-RUN con valores por defecto (sin argumentos)
Muestra el modelo y la solución ya aplicada con Matplotlib.

Por defecto:
  - Lee 'Sphere.vtk' (malla tetra).
  - Resuelve ∇·(−σ∇V)=0 con tapas Dirichlet:
        z > z1  => V = 1
        z < z0  => V = 0
    (resto de la superficie con Neumann natural).
  - σ se toma de cell_data["sigma"] por elemento si existe; si no, σ ≡ 1.

Si prefieres Poisson con fuente puntual, cambia DEFAULT_MODE = "poisson"
y ajusta DEFAULT_SOURCES / DEFAULT_CHARGES.
"""

import numpy as np
import meshio
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401

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

#CONFIGURACIÓN

DEFAULT_VTK = "Sphere.vtk"
DEFAULT_MODE = "poisson"            
DEFAULT_Z0, DEFAULT_Z1 = -0.4, 0.4  # tapas (modo sigma)

# Para modo Poisson:
DEFAULT_SOURCES = np.array([[0.5, -0.4, 0.1]], dtype=float)
DEFAULT_CHARGES = np.array([1.0], dtype=float)


# Carga de malla 
def load_mesh_skfem(vtk_path: str):
    mio = meshio.read(vtk_path)
    P = np.asarray(mio.points, dtype=float).T
    if "tetra" in mio.cells_dict:
        T = np.asarray(mio.cells_dict["tetra"], dtype=int).T
    elif "tetra10" in mio.cells_dict:
        t10 = np.asarray(mio.cells_dict["tetra10"], dtype=int)
        T = t10[:, [0, 1, 2, 3]].T
    else:
        raise RuntimeError("El VTK no contiene celdas.")
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
    tri_blocks = [b for b in mio.cells if b.type in ("triangle", "tri")]
    if tri_blocks:
        return tri_blocks[0].data
    from collections import Counter
    t = mesh.t.T
    faces = np.vstack([t[:, [0, 1, 2]], t[:, [0, 1, 3]], t[:, [0, 2, 3]], t[:, [1, 2, 3]]])
    faces_sorted = np.sort(faces, axis=1)
    counts = Counter(map(tuple, faces_sorted))
    mask = np.array([counts[tuple(f)] == 1 for f in map(tuple, faces_sorted)])
    return faces[mask]


# Modo Poisson (fuentes puntuales) 
def _is_inside(mesh, x):
    try:
        _ = mesh.element_finder()(x[0], x[1], x[2], _search_all=True)
        return True
    except Exception:
        return False


def _project_inside(mesh, s, max_iter=25):
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
    basis = Basis(mesh, ElementTetP1())
    A = asm(laplace, basis)
    b = np.zeros(basis.N)
    used = []
    c = mesh.p.mean(axis=1)  # centroid
    for s, q in zip(np.asarray(sources, float), np.asarray(charges, float)):
        s_in = _project_inside(mesh, s)
        if not _is_inside(mesh, s_in):
            s_in = c  # use centroid if projection fails
        b += q * basis.point_source(s_in)
        used.append(s_in)
    D = basis.get_dofs()
    # Use enforce for Dirichlet boundary conditions
    xdir = np.zeros(basis.N)
    V = enforce(A, b, D=D, x=xdir)[0]
    return basis, V, np.vstack(used)


# Modo σ-Laplace 
def _sigma_from_vtk(mio, n_elems):
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


def _dview_to_idx_array(Dview):
    """Convierte DofsView (o similar) a np.ndarray[int] robusto entre versiones."""
    cand = []
    for attr in ("nodal", "all", "dofs"):
        if hasattr(Dview, attr):
            val = getattr(Dview, attr)
            val = val() if callable(val) else val
            cand.append(val)
    for v in cand:
        try:
            arr = np.asarray(v).astype(int).ravel()
            return arr
        except Exception:
            pass
    return np.asarray(Dview, dtype=int).ravel()


def _collect_dirichlet_indices(basis, z0, z1, mesh, auto_adjust=True, debug=False):
    facets_top = mesh.facets_satisfying(lambda x: x[2] > z1)
    facets_bot = mesh.facets_satisfying(lambda x: x[2] < z0)
    idx_top = _dview_to_idx_array(basis.get_dofs(facets=facets_top))
    idx_bot = _dview_to_idx_array(basis.get_dofs(facets=facets_bot))

    if (idx_top.size + idx_bot.size == 0) and auto_adjust:
        zmin, zmax = float(mesh.p[2].min()), float(mesh.p[2].max())
        dz = zmax - zmin
        # mueve levemente umbrales hacia adentro (5%) y reintenta
        z0a = zmin + 0.05 * dz
        z1a = zmax - 0.05 * dz
        if debug:
            print(f"[Auto-ajuste] Reintentando tapas con z0={z0a:.6f}, z1={z1a:.6f}")
        facets_top = mesh.facets_satisfying(lambda x: x[2] > z1a)
        facets_bot = mesh.facets_satisfying(lambda x: x[2] < z0a)
        idx_top = _dview_to_idx_array(basis.get_dofs(facets=facets_top))
        idx_bot = _dview_to_idx_array(basis.get_dofs(facets=facets_bot))
    return idx_top, idx_bot


def solve_sigma_laplace(mesh, mio, z0=-0.4, z1=0.4, debug=False):
    """
    ∇·(−σ∇V)=0 con Dirichlet: z>z1 ⇒ V=1, z<z0 ⇒ V=0; resto Neumann natural.
    σ por elemento desde VTK si existe; si no, σ≡1.
    Retorna (basis, V).
    """
    basis = Basis(mesh, ElementTetP1())
    nelems = mesh.t.shape[1]

    # σ por elemento con broadcasting correcto (nelems,1)
    sigma = _sigma_from_vtk(mio, nelems)
    sigma_elem = np.asarray(sigma, float)[basis.tind].reshape(-1, 1)

    if debug:
        zmin, zmax = float(mesh.p[2].min()), float(mesh.p[2].max())
        print("=== DEBUG solve_sigma_laplace ===")
        print(f"nodos={mesh.p.shape[1]}  nelems={nelems}")
        print(f"z-range = [{zmin:.6f}, {zmax:.6f}]  (z0={z0}, z1={z1})")
        print(f"sigma.size={sigma.size}  sigma_elem.shape={sigma_elem.shape}")
        print(f"sigma_elem min/max = {float(sigma_elem.min())} / {float(sigma_elem.max())}")

    assert sigma.size == nelems, f"[σ] tamaño inconsistente: {sigma.size} != {nelems}"
    assert sigma_elem.shape == (nelems, 1), f"[σ] shape esperado ({nelems},1), got {sigma_elem.shape}"
    assert np.all(np.isfinite(sigma_elem)), "[σ] hay valores no finitos"

    @BilinearForm
    def a(u, v, w):
        return w.sigma * dot(grad(u), grad(v))  # (nelems,1) * (nelems,nqp)

    A = asm(a, basis, sigma=sigma_elem)
    rhs = np.zeros(basis.N)

    # Dirichlet (robusto y con auto-ajuste si no hay facetas)
    idx_top, idx_bot = _collect_dirichlet_indices(basis, z0, z1, mesh, auto_adjust=True, debug=debug)
    assert idx_top.size + idx_bot.size > 0, (
        "No se fijó ningún nodo de Dirichlet. Revisa z0/z1 o la geometría."
    )

    xdir = np.zeros(basis.N, dtype=float)
    if idx_top.size:
        xdir[idx_top] = 1.0
    if idx_bot.size:
        xdir[idx_bot] = 0.0
    idx_dir = np.unique(np.hstack([idx_top, idx_bot])).astype(int)

    V = enforce(A, rhs, D=idx_dir, x=xdir)[0]

    if debug:
        V_arr = V.toarray().ravel() if hasattr(V, 'toarray') else np.asarray(V).ravel()
        print("Sistema resuelto. V stats:",
              f"min={float(np.min(V_arr))}, max={float(np.max(V_arr))}, ||V||2={float(np.linalg.norm(V_arr))}")
    return basis, V


# ---------- Visualización ----------
def plot_surface(mesh, tris, V, sources=None, title=None):
    X = mesh.p.T
    fig = plt.figure(figsize=(9, 8))
    ax = fig.add_subplot(111, projection="3d")
    surf = ax.plot_trisurf(
        X[:, 0], X[:, 1], X[:, 2],
        triangles=tris,
        linewidth=0.2,
        antialiased=True,
        shade=False,
        cmap=None
    )
    V_arr = V.toarray().ravel() if hasattr(V, 'toarray') else np.asarray(V).ravel()
    surf.set_array(V_arr[tris].mean(axis=1))
    surf.autoscale()
    if sources is not None:
        S = np.asarray(sources, dtype=float)
        ax.scatter(S[:, 0], S[:, 1], S[:, 2], s=50, c="red", label="Fuente(s)")
        ax.legend()
    ax.set_title(title or "Solución de PDE en la superficie")
    ax.set_xlabel("x"); ax.set_ylabel("y"); ax.set_zlabel("z")
    ax.view_init(elev=25, azim=35)
    plt.colorbar(surf, ax=ax, shrink=0.6, label="V")
    plt.tight_layout()
    return fig


# AUTO-RUN 
if __name__ == "__main__":
    vtk_path = DEFAULT_VTK
    mesh, mio = load_mesh_skfem(vtk_path)
    tris = extract_surface_tris(mio, mesh)
    print(f"Malla: {mesh.p.shape[1]} nodos, {mesh.t.shape[1]} tetras")
    print(f"Mesh bounds: x=[{mesh.p[0].min():.3f}, {mesh.p[0].max():.3f}], y=[{mesh.p[1].min():.3f}, {mesh.p[1].max():.3f}], z=[{mesh.p[2].min():.3f}, {mesh.p[2].max():.3f}]")

    if DEFAULT_MODE.lower() == "poisson":
        try:
            basis, V, used = solve_poisson_point(mesh, DEFAULT_SOURCES, DEFAULT_CHARGES)
            plot_surface(mesh, tris, V, sources=used,
                         title="Poisson 3D (fuente(s) puntual(es))")
            print("Fuentes usadas (interior):", used)
        except ValueError as e:
            print(f"Error en Poisson: {e}")
            print("Cambiando a modo sigma...")
            basis, V = solve_sigma_laplace(mesh, mio, z0=DEFAULT_Z0, z1=DEFAULT_Z1, debug=True)
            plot_surface(
                mesh, tris, V, sources=None,
                title=f"∇·(−σ∇V)=0 (z<{DEFAULT_Z0} ⇒ V=0, z>{DEFAULT_Z1} ⇒ V=1)"
            )
    else:
        basis, V = solve_sigma_laplace(mesh, mio, z0=DEFAULT_Z0, z1=DEFAULT_Z1, debug=True)
        plot_surface(
            mesh, tris, V, sources=None,
            title=f"∇·(−σ∇V)=0 (z<{DEFAULT_Z0} ⇒ V=0, z>{DEFAULT_Z1} ⇒ V=1)"
        )
