# -*- coding: utf-8 -*-
"""
Interfaz grafica ECG - flujo secuencial de 5 pasos.

Pasos:
  1. Cargar / Generar malla
  2. Configurar dipolo cardiaco
  3. Ubicar electrodos
  4. Ejecutar simulacion
  5. Postprocesamiento (ECG + potenciales)
"""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import queue
import os
import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    HAS_DND = True
except ImportError:
    HAS_DND = False

try:
    from .generation.mesh_generator import generate_mesh, HAS_GMSH
except ImportError:
    HAS_GMSH = False

from .core.mesh_loader import (
    load_mesh_skfem, extract_surface_tris,
    solve_poisson_point, plot_surface,
    nodo_mas_cercano_en_superficie,
)
from .ui import results as ui_results

# ─────────────────────────────────────────────
# Paleta de colores
# ─────────────────────────────────────────────
C = {
    "bg":      "white",
    "bg2":     "#f5f6fa",
    "border":  "#dee2e6",
    "text":    "#212529",
    "muted":   "#6c757d",
    "primary": "#0d6efd",
    "success": "#198754",
    "danger":  "#dc3545",
    "warning": "#fd7e14",
    "neutral": "#495057",
    "purple":  "#6f42c1",
    "cyan":    "#0dcaf0",
    "field":   "#f0f2f5",
}

BTN = dict(relief=tk.FLAT, font=("Arial", 9))


def _btn(parent, text, cmd, color=None, fg="white", **kw):
    """Crea un boton con estilo consistente."""
    return tk.Button(parent, text=text, command=cmd,
                     bg=color or C["primary"], fg=fg, **BTN, **kw)


def _output_path(name: str, subfolder: str = "") -> str:
    """Genera una ruta en output/<subfolder>/ con timestamp.
    Ejemplo: output/modelos/electrodos_torso_20260414_153022.png
    """
    from datetime import datetime
    folder = os.path.join("output", subfolder) if subfolder else "output"
    os.makedirs(folder, exist_ok=True)
    base, ext = os.path.splitext(name)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(folder, f"{base}_{ts}{ext}")


# ─────────────────────────────────────────────
# Helpers de deteccion automatica
# ─────────────────────────────────────────────

def _get_heart_nodes(mesh, mio):
    """Nodos del material 2 (corazon)."""
    mat_arr = None
    if hasattr(mio, "cell_data_dict"):
        d = mio.cell_data_dict
        if "gmsh:physical" in d and "tetra" in d["gmsh:physical"]:
            mat_arr = d["gmsh:physical"]["tetra"].flatten().astype(int)
        else:
            for _, blk in d.items():
                if "tetra" in blk:
                    a = blk["tetra"].flatten()
                    if len(np.unique(a)) <= 20 and a.min() >= 0:
                        mat_arr = a.astype(int); break
    if mat_arr is None or 2 not in np.unique(mat_arr):
        return None
    tets = mio.cells_dict.get("tetra")
    if tets is None:
        return None
    return mesh.p[:, np.unique(tets[mat_arr == 2].ravel())].T


def _kmeans_nodes(nodes, n):
    """Selecciona n nodos distribuidos espacialmente."""
    if len(nodes) <= n:
        return nodes
    np.random.seed(0)
    idx = [np.random.randint(len(nodes))]
    for _ in range(n - 1):
        d = np.array([min(np.linalg.norm(nodes[i] - nodes[j]) for j in idx)
                      for i in range(len(nodes))])
        p = d ** 2; p /= p.sum()
        idx.append(np.random.choice(len(nodes), p=p))
    c = nodes[idx].copy()
    for _ in range(5):
        lbl = np.argmin(np.linalg.norm(nodes[:, None] - c[None], axis=2), axis=1)
        for k in range(n):
            if (lbl == k).any():
                c[k] = nodes[lbl == k].mean(axis=0)
    return np.array([nodes[np.argmin(np.linalg.norm(nodes - ci, axis=1))] for ci in c])


def auto_detect_sources(mesh, num_sources=3, mio=None):
    """Detecta fuentes Poisson optimas."""
    if mio is not None:
        try:
            hn = _get_heart_nodes(mesh, mio)
            if hn is not None and len(hn) >= num_sources:
                src = _kmeans_nodes(hn, num_sources)
                chg = np.array([(1.0 if i % 2 == 0 else -0.8) * (0.9 ** (i // 2))
                                for i in range(num_sources)])
                return src, chg
        except Exception:
            pass
    c = mesh.p.mean(axis=1)
    dim = mesh.p.max(axis=1) - mesh.p.min(axis=1)
    if num_sources == 1:
        return np.array([c]), np.array([1.0])
    if num_sources == 2:
        off = np.zeros(3); off[np.argmax(dim)] = dim[np.argmax(dim)] * 0.15
        return np.array([c + off, c - off]), np.array([1.0, -1.0])
    r = float(min(dim[:2])) * 0.15
    ang = np.linspace(0, 4 * np.pi / 3, num_sources, endpoint=False)
    src = np.array([[c[0] + r * np.cos(a), c[1] + r * np.sin(a),
                     c[2] + (i - 1) * dim[2] * 0.05]
                    for i, a in enumerate(ang)])
    chg = np.array([(1.0 if i % 2 == 0 else -0.8) * (0.9 ** (i // 2))
                    for i in range(num_sources)])
    return src, chg


def analyze_mesh_complexity(mesh):
    n = mesh.p.shape[1]
    dim = mesh.p.max(axis=1) - mesh.p.min(axis=1)
    opt = 1 if n < 100 else 2 if n < 500 else 3 if n < 1000 else 4
    lvl = ["simple", "moderada", "compleja", "muy compleja"][opt - 1]
    return {"num_nodes": n, "num_elements": mesh.t.shape[1],
            "dimensions": dim, "volume": float(np.prod(dim)),
            "optimal_sources": opt, "complexity": lvl}


# ─────────────────────────────────────────────
# Clase principal
# ─────────────────────────────────────────────

class ECGAppAuto:
    """Aplicacion ECG con flujo secuencial de 5 pasos."""

    STEPS = ["1. Malla", "2. Dipolo", "3. Electrodos", "4. Simulacion", "5. Resultados"]

    def __init__(self, root=None):
        if root is None:
            self.root = TkinterDnD.Tk() if HAS_DND else tk.Tk()
        else:
            self.root = root

        self.root.title("Solucionador ECG")
        self.root.geometry("1280x820")
        self.root.configure(bg=C["bg2"])

        # Estado
        self.mesh = None
        self.mio = None
        self.tris = None
        self.file_path = None
        self.auto_sources = None
        self.auto_charges = None
        self.manual_electrodes = None
        self.dipole_pos = None
        self.dipole_table = None
        self.ecg_mesh_data = None
        self.ecg_solution = None
        self.ecg_source_data = None
        self.ecg_data = None

        self._queue = queue.Queue()
        self._build_ui()
        if HAS_DND:
            self._setup_dnd()
        self._poll()

    # ──────────────────────────────────────────
    # Construccion de la UI
    # ──────────────────────────────────────────

    def _build_ui(self):
        self._build_step_bar()

        body = tk.Frame(self.root, bg=C["bg2"])
        body.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 6))
        body.grid_columnconfigure(0, weight=0, minsize=440)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        # Panel izquierdo con scroll
        left_wrap = tk.Frame(body, bg=C["bg"])
        left_wrap.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        self._left_canvas = tk.Canvas(left_wrap, bg=C["bg"], highlightthickness=0, width=420)
        sb = tk.Scrollbar(left_wrap, orient="vertical", command=self._left_canvas.yview)
        self._scroll_frame = tk.Frame(self._left_canvas, bg=C["bg"])
        self._scroll_frame.bind("<Configure>",
            lambda e: self._left_canvas.configure(
                scrollregion=self._left_canvas.bbox("all")))
        self._left_canvas.create_window((0, 0), window=self._scroll_frame, anchor="nw", width=420)
        self._left_canvas.configure(yscrollcommand=sb.set)
        self._left_canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self._left_canvas.bind("<Configure>",
            lambda e: self._left_canvas.itemconfig(
                self._left_canvas.find_all()[0], width=e.width))
        self._left_canvas.bind_all("<MouseWheel>",
            lambda e: self._left_canvas.yview_scroll(int(-1 * e.delta / 120), "units"))

        # Panel derecho
        right = tk.Frame(body, bg=C["bg"], relief=tk.RAISED, bd=1)
        right.grid(row=0, column=1, sticky="nsew")
        tk.Label(right, text="Visualizacion 3D", font=("Arial", 13, "bold"),
                 bg=C["bg"], fg=C["text"]).pack(pady=8)
        self.plot_frame = tk.Frame(right, bg=C["bg"])
        self.plot_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)
        self._show_placeholder()

        self._build_section_mesh()
        self._build_section_dipole()
        self._build_section_electrodes()
        self._build_section_simulation()
        self._build_section_results()

        # Barra de estado
        self.status_var = tk.StringVar(value="Listo - carga o genera una malla para comenzar")
        self.progress_var = tk.DoubleVar()
        status_bar = tk.Frame(self.root, bg=C["bg2"])
        status_bar.pack(fill=tk.X, padx=6, pady=(0, 4))
        ttk.Progressbar(status_bar, variable=self.progress_var,
                        maximum=100, mode="determinate").pack(fill=tk.X, pady=(0, 2))
        tk.Label(status_bar, textvariable=self.status_var,
                 font=("Arial", 8), bg=C["bg2"], fg=C["muted"],
                 anchor="w").pack(fill=tk.X)

    def _build_step_bar(self):
        bar = tk.Frame(self.root, bg=C["bg"], pady=6)
        bar.pack(fill=tk.X, padx=6, pady=(6, 0))
        self._step_labels = []
        for i, name in enumerate(self.STEPS):
            lbl = tk.Label(bar, text=name, font=("Arial", 9, "bold"),
                           bg=C["neutral"], fg="white", padx=14, pady=5, relief=tk.FLAT)
            lbl.pack(side=tk.LEFT, padx=2)
            self._step_labels.append(lbl)
            if i < len(self.STEPS) - 1:
                tk.Label(bar, text=">", font=("Arial", 11, "bold"),
                         bg=C["bg"], fg=C["muted"]).pack(side=tk.LEFT)
        self._set_active_step(0)

    def _set_active_step(self, step: int):
        for i, lbl in enumerate(self._step_labels):
            if i < step:
                lbl.config(bg=C["success"])
            elif i == step:
                lbl.config(bg=C["primary"])
            else:
                lbl.config(bg=C["neutral"])

    def _section(self, title: str) -> tk.LabelFrame:
        f = tk.LabelFrame(self._scroll_frame, text=title,
                          font=("Arial", 10, "bold"),
                          bg=C["bg"], fg=C["muted"], padx=10, pady=8)
        f.pack(fill=tk.X, padx=6, pady=4)
        return f

    # ──────────────────────────────────────────
    # PASO 1 - Malla
    # ──────────────────────────────────────────

    def _build_section_mesh(self):
        sec = self._section("Paso 1 - Cargar / Generar Malla")
        self.drop_frame = tk.Frame(sec, bg=C["field"], relief="solid", bd=1, height=60)
        self.drop_frame.pack(fill=tk.X, pady=4)
        self.drop_frame.pack_propagate(False)
        tk.Label(self.drop_frame,
                 text="Arrastra un archivo aqui o haz clic para seleccionar\n"
                      "(.vtk  .msh  .vtu  .stl  .obj  .ply  .off)",
                 font=("Arial", 8), bg=C["field"], fg=C["muted"],
                 wraplength=400).pack(expand=True)
        self.drop_frame.bind("<Button-1>", lambda _: self._load_file_dialog())
        row = tk.Frame(sec, bg=C["bg"])
        row.pack(fill=tk.X, pady=4)
        _btn(row, "Seleccionar archivo", self._load_file_dialog, C["success"]).pack(side=tk.LEFT, padx=4)
        if HAS_GMSH:
            _btn(row, "Generar modelo", self._show_generate_dialog, C["success"]).pack(side=tk.LEFT, padx=4)
        self.mesh_info = tk.Text(sec, height=5, font=("Consolas", 8),
                                 bg=C["field"], fg=C["text"], state=tk.DISABLED)
        self.mesh_info.pack(fill=tk.X, pady=4)

    def _load_file_dialog(self):
        path = filedialog.askopenfilename(
            title="Seleccionar malla",
            filetypes=[("Mallas soportadas", "*.vtk *.vtu *.msh *.mesh *.stl *.obj *.ply *.off"),
                       ("Todos", "*.*")])
        if path:
            self._load_mesh(path)

    def _load_mesh(self, path):
        self._set_status("Cargando malla...", 20)
        def _work():
            try:
                mesh, mio = load_mesh_skfem(path)
                tris = extract_surface_tris(mio, mesh)
                nodos_sup = np.unique(tris.flatten())
                analysis = analyze_mesh_complexity(mesh)
                src, chg = auto_detect_sources(mesh, analysis["optimal_sources"], mio=mio)
                self._queue.put(("mesh_loaded", {
                    "mesh": mesh, "mio": mio, "tris": tris,
                    "nodos_sup": nodos_sup, "path": path,
                    "analysis": analysis, "sources": src, "charges": chg,
                }))
            except Exception as e:
                self._queue.put(("error", str(e)))
        threading.Thread(target=_work, daemon=True).start()

    def _on_mesh_loaded(self, d):
        self.mesh = d["mesh"]
        self.mio = d["mio"]
        self.tris = d["tris"]
        self.nodos_sup = d["nodos_sup"]
        self.file_path = d["path"]
        self.auto_sources = d["sources"]
        self.auto_charges = d["charges"]
        # Resetear estado de pasos anteriores
        self.dipole_pos = None
        self.dipole_table = None
        self.manual_electrodes = None
        self.ecg_mesh_data = None
        self.ecg_solution = None
        self.ecg_source_data = None
        self.ecg_data = None
        # Re-bloquear pasos 2-5
        self._lock_section(self.sec_dipole)
        self._lock_section(self.sec_electrodes)
        self._lock_section(self.sec_simulation)
        self._lock_section(self.sec_results)
        # Limpiar campos
        for row_vars in self._elec_vars:
            for v in row_vars:
                v.set("")
        self.elec_info.config(text="")
        self.sim_info.config(text="")
        m = self.mesh
        a = d["analysis"]
        info = (f"Archivo : {os.path.basename(d['path'])}\n"
                f"Nodos   : {m.p.shape[1]:,}   Elementos: {m.t.shape[1]:,}\n"
                f"X: [{m.p[0].min():.3f}, {m.p[0].max():.3f}]\n"
                f"Y: [{m.p[1].min():.3f}, {m.p[1].max():.3f}]\n"
                f"Z: [{m.p[2].min():.3f}, {m.p[2].max():.3f}]")
        self._set_text(self.mesh_info, info)
        self._set_status(f"Malla cargada - {a['complexity']}, {m.p.shape[1]:,} nodos", 0)
        self._set_active_step(1)
        self._unlock_section(self.sec_dipole)
        ui_results.preview_mesh(self.mesh, self.mio, self._queue)

    # ──────────────────────────────────────────
    # PASO 2 - Dipolo
    # ──────────────────────────────────────────

    def _build_section_dipole(self):
        self.sec_dipole = self._section("Paso 2 - Posicion del Dipolo Cardiaco")
        tk.Label(self.sec_dipole,
                 text="Posicion del dipolo (centro del corazon, en metros):",
                 font=("Arial", 8), bg=C["bg"], fg=C["muted"]).pack(anchor="w")
        row = tk.Frame(self.sec_dipole, bg=C["bg"])
        row.pack(fill=tk.X, pady=4)
        self._dip_vars = {}
        from .core.ecg_solver import DEFAULT_DIPOLE_POS
        for ax_name, val in zip(("X", "Y", "Z"), DEFAULT_DIPOLE_POS):
            tk.Label(row, text=ax_name, font=("Arial", 9, "bold"),
                     bg=C["bg"], fg=C["text"], width=2).pack(side=tk.LEFT)
            v = tk.StringVar(value=f"{val:.4f}")
            tk.Entry(row, textvariable=v, width=9, font=("Consolas", 9)).pack(side=tk.LEFT, padx=2)
            self._dip_vars[ax_name] = v
        tk.Label(self.sec_dipole,
                 text="Usa los valores por defecto o ajusta segun tu malla.",
                 font=("Arial", 8), bg=C["bg"], fg=C["muted"]).pack(anchor="w", pady=(2, 4))
        _btn(self.sec_dipole, "Confirmar dipolo", self._confirm_dipole, C["primary"]).pack(anchor="w")
        self._lock_section(self.sec_dipole)

    def _confirm_dipole(self):
        try:
            pos = np.array([float(self._dip_vars[k].get().replace(",", "."))
                            for k in ("X", "Y", "Z")])
        except ValueError:
            messagebox.showerror("Error", "Coordenadas del dipolo invalidas.")
            return
        from .core.ecg_solver import DEFAULT_DIPOLE_TABLE
        self.dipole_pos = pos
        self.dipole_table = DEFAULT_DIPOLE_TABLE
        self._set_status(f"Dipolo confirmado en ({pos[0]:.3f}, {pos[1]:.3f}, {pos[2]:.3f})", 0)
        self._set_active_step(2)
        self._unlock_section(self.sec_electrodes)
        ui_results.preview_dipole(self.mesh, self.mio, pos, self._queue)

    # ──────────────────────────────────────────
    # PASO 3 - Electrodos
    # ──────────────────────────────────────────

    def _build_section_electrodes(self):
        self.sec_electrodes = self._section("Paso 3 - Ubicar Electrodos")
        tk.Label(self.sec_electrodes,
                 text="Ingresa las coordenadas de cada electrodo (metros).\n"
                      "Deja vacio para omitir.",
                 font=("Arial", 8), bg=C["bg"], fg=C["muted"]).pack(anchor="w")
        grid = tk.Frame(self.sec_electrodes, bg=C["bg"])
        grid.pack(fill=tk.X, pady=4)
        COLORS = ["#e74c3c", "#e67e22", "#f39c12", "#27ae60", "#2980b9", "#8e44ad"]
        for c, h in enumerate(["", "X", "Y", "Z"]):
            tk.Label(grid, text=h, font=("Arial", 8, "bold"),
                     bg=C["bg"], fg=C["text"], width=10).grid(row=0, column=c, padx=2)
        self._elec_vars = []
        for i in range(6):
            tk.Label(grid, text=f"V{i+1}", font=("Arial", 9, "bold"),
                     bg=C["bg"], fg=COLORS[i], width=4).grid(row=i+1, column=0, padx=2, pady=3)
            row_vars = []
            for j in range(3):
                v = tk.StringVar()
                tk.Entry(grid, textvariable=v, width=10,
                         font=("Consolas", 8)).grid(row=i+1, column=j+1, padx=2, pady=3)
                row_vars.append(v)
            self._elec_vars.append(row_vars)
        row1 = tk.Frame(self.sec_electrodes, bg=C["bg"])
        row1.pack(fill=tk.X, pady=(4, 2))
        _btn(row1, "Posiciones por defecto", self._use_default_electrodes, C["neutral"]).pack(side=tk.LEFT, padx=4)
        _btn(row1, "Confirmar electrodos", self._confirm_electrodes, C["primary"]).pack(side=tk.LEFT, padx=4)
        row2 = tk.Frame(self.sec_electrodes, bg=C["bg"])
        row2.pack(fill=tk.X, pady=(0, 4))
        _btn(row2, "Ver en plano", self._show_electrode_viewer, C["neutral"]).pack(side=tk.LEFT, padx=4)
        self.elec_info = tk.Label(self.sec_electrodes, text="",
                                  font=("Arial", 8), bg=C["bg"], fg=C["muted"])
        self.elec_info.pack(anchor="w")
        self._lock_section(self.sec_electrodes)

    def _use_default_electrodes(self):
        from .core.ecg_solver import DEFAULT_ELECTRODES
        for i, (name, pos) in enumerate(DEFAULT_ELECTRODES.items()):
            if i >= 6:
                break
            self._elec_vars[i][0].set(f"{pos[0]:.4f}")
            self._elec_vars[i][1].set(f"{pos[1]:.4f}")
            self._elec_vars[i][2].set(f"{pos[2]:.4f}")

    def _confirm_electrodes(self):
        if self.mesh is None:
            return
        elec = {}
        nodos_vis = np.asarray(getattr(self, "nodos_sup",
                                       np.arange(self.mesh.p.shape[1])), dtype=int)
        if len(nodos_vis) == 0:
            nodos_vis = np.arange(self.mesh.p.shape[1], dtype=int)
        used = set()
        for i, row_vars in enumerate(self._elec_vars):
            sx, sy, sz = [v.get().strip().replace(",", ".") for v in row_vars]
            if sx == "" or sy == "" or sz == "":
                continue
            try:
                pt = np.array([float(sx), float(sy), float(sz)])
            except ValueError:
                messagebox.showerror("Error", f"Coordenadas invalidas en V{i+1}")
                return
            nodo = nodo_mas_cercano_en_superficie(self.mesh, nodos_vis, pt, used_nodes=used)
            elec[f"V{i+1}"] = self.mesh.p[:, nodo]
            used.add(nodo)
        if not elec:
            messagebox.showwarning("Sin electrodos", "Ingresa al menos un electrodo.")
            return
        self.manual_electrodes = elec
        self.elec_info.config(text=f"{len(elec)} electrodos confirmados: {', '.join(elec)}")
        self._set_status(f"{len(elec)} electrodos ubicados", 0)
        self._set_active_step(3)
        self._unlock_section(self.sec_simulation)
        ui_results.preview_electrodes(self.mesh, self.mio, self.dipole_pos, elec, self._queue)

    def _show_electrode_viewer(self):
        if self.mesh is None:
            return
        import matplotlib.patches as mpatches
        from scipy.spatial import ConvexHull
        win = tk.Toplevel(self.root)
        win.title("Vista del modelo - referencia para electrodos")
        win.geometry("700x520")
        win.configure(bg=C["bg"])
        X = self.mesh.p.T
        COLORS_V = ["#e74c3c", "#e67e22", "#f39c12", "#27ae60", "#2980b9", "#8e44ad"]
        MAT = {1: ("#aed6f1", "#2980b9", "Torso", 0.25),
               2: ("#f1948a", "#c0392b", "Corazon", 0.75),
               3: ("#f8c471", "#e67e22", "Pulmon izq", 0.6),
               4: ("#a9dfbf", "#27ae60", "Pulmon der", 0.6)}
        _mat_contours = {}
        if self.mio is not None:
            d = getattr(self.mio, "cell_data_dict", {})
            mat = None
            if "gmsh:physical" in d and "tetra" in d["gmsh:physical"]:
                mat = d["gmsh:physical"]["tetra"].flatten().astype(int)
            if mat is not None and "tetra" in self.mio.cells_dict:
                tets = self.mio.cells_dict["tetra"]
                for mid in [1, 3, 4, 2]:
                    if mid in MAT and mid in np.unique(mat):
                        nd = np.unique(tets[mat == mid].ravel())
                        _mat_contours[mid] = nd

        def _hull_path(xs, ys):
            try:
                pts = np.column_stack([xs, ys])
                h = ConvexHull(pts)
                v = pts[h.vertices]
                return np.vstack([v, v[0]])
            except Exception:
                return None

        fig = Figure(figsize=(6.5, 4.5), dpi=90)
        ax_xz = fig.add_subplot(121)
        ax_xy = fig.add_subplot(122)

        def _draw_model(ax, dim_a, dim_b):
            for mid in [1, 3, 4, 2]:
                if mid not in _mat_contours:
                    continue
                fc, ec, nm, alfa = MAT[mid]
                nd = _mat_contours[mid]
                path = _hull_path(X[nd, dim_a], X[nd, dim_b])
                if path is not None:
                    ax.fill(path[:, 0], path[:, 1], color=fc, alpha=alfa)
                    ax.plot(path[:, 0], path[:, 1], color=ec, lw=1.3, label=nm)

        def _redraw():
            ax_xz.clear(); ax_xy.clear()
            _draw_model(ax_xz, 0, 2)
            _draw_model(ax_xy, 0, 1)
            for i, row_vars in enumerate(self._elec_vars):
                try:
                    vx = float(row_vars[0].get().replace(',', '.'))
                    vy = float(row_vars[1].get().replace(',', '.'))
                    vz = float(row_vars[2].get().replace(',', '.'))
                    c = COLORS_V[i % len(COLORS_V)]
                    kw = dict(s=80, color=c, zorder=20, edgecolors='black', linewidths=0.7)
                    ann = dict(textcoords="offset points", xytext=(5, 3),
                               fontsize=7, color=c, fontweight='bold',
                               bbox=dict(boxstyle='round,pad=0.2', facecolor='white',
                                         edgecolor=c, alpha=0.9))
                    ax_xz.scatter(vx, vz, **kw)
                    ax_xz.annotate(f"V{i+1}", (vx, vz), **ann)
                    ax_xy.scatter(vx, vy, **kw)
                    ax_xy.annotate(f"V{i+1}", (vx, vy), **ann)
                except ValueError:
                    pass
            for ax, xl, yl, tit in [(ax_xz, "X (m)", "Z (m)", "Frontal X-Z"),
                                     (ax_xy, "X (m)", "Y (m)", "Superior X-Y")]:
                ax.set_xlabel(xl, fontsize=8); ax.set_ylabel(yl, fontsize=8)
                ax.set_title(tit, fontsize=8)
                ax.grid(True, ls="--", alpha=0.3)
                ax.set_aspect("equal")
                ax.axhline(0, color="#ccc", lw=0.7, ls=":")
                ax.axvline(0, color="#ccc", lw=0.7, ls=":")
                ax.legend(fontsize=6, loc="upper right")
            fig.tight_layout()
            canvas.draw()

        canvas = FigureCanvasTkAgg(fig, win)
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        _redraw()
        def _on_change(*_): _redraw()
        for row_vars in self._elec_vars:
            for v in row_vars:
                v.trace_add("write", _on_change)
        _btn(win, "Actualizar vista", _redraw, C["neutral"]).pack(pady=4)

    # ──────────────────────────────────────────
    # PASO 4 - Simulacion
    # ──────────────────────────────────────────

    def _build_section_simulation(self):
        self.sec_simulation = self._section("Paso 4 - Ejecutar Simulacion")
        tk.Label(self.sec_simulation,
                 text="Ejecuta el pipeline FEM completo (puede tardar varios minutos).",
                 font=("Arial", 8), bg=C["bg"], fg=C["muted"]).pack(anchor="w", pady=(0, 6))
        _btn(self.sec_simulation, "Iniciar simulacion", self._run_simulation, C["primary"]).pack(anchor="w")
        self.sim_info = tk.Label(self.sec_simulation, text="",
                                 font=("Arial", 8), bg=C["bg"], fg=C["muted"])
        self.sim_info.pack(anchor="w", pady=4)
        self._lock_section(self.sec_simulation)

    def _run_simulation(self):
        if self.mesh is None or self.dipole_pos is None:
            return
        self._set_status("Ejecutando simulacion FEM...", 30)
        self.sim_info.config(text="Procesando...")
        def _work():
            try:
                from .core.ecg_solver import (
                    load_mesh_with_conductivities, assemble_stiffness_matrix,
                    build_source_matrix, solve_ecg_system, postprocess_ecg,
                    plot_electrodes_on_torso, DEFAULT_CONDUCTIVITIES,
                )
                md = load_mesh_with_conductivities(self.file_path, DEFAULT_CONDUCTIVITIES)
                K = assemble_stiffness_matrix(md["basis"], md["sigma_field"])
                sd = build_source_matrix(md["mesh"], self.dipole_pos, self.dipole_table)
                sol = solve_ecg_system(K, sd["F_matrix"], md["mesh"],
                                       md["surface_nodes"], self.dipole_pos)
                ecg = postprocess_ecg(md["mesh"], md["surface_nodes"], sol["PHI"],
                                      electrode_positions=self.manual_electrodes)
                fig = plot_electrodes_on_torso(
                    md["mesh"], md["mio"], ecg["electrode_nodes"],
                    md["surface_nodes"], PHI=sol["PHI"], instant_idx=4,
                    output_file=_output_path("electrodos_torso.png", "modelos"))
                self._queue.put(("sim_done", {
                    "mesh_data": md, "solution": sol,
                    "source_data": sd, "ecg": ecg, "fig": fig,
                }))
            except Exception as e:
                import traceback; traceback.print_exc()
                self._queue.put(("error", f"Error en simulacion: {e}"))
        threading.Thread(target=_work, daemon=True).start()

    def _on_sim_done(self, d):
        self.ecg_mesh_data = d["mesh_data"]
        self.ecg_solution = d["solution"]
        self.ecg_source_data = d["source_data"]
        self.ecg_data = d["ecg"]
        n_conv = d["solution"].get("n_converged", "?")
        T = d["source_data"]["F_matrix"].shape[1]
        self.sim_info.config(
            text=f"Completado - {n_conv}/{T} instantes convergieron  "
                 f"| residuo max: {d['solution']['residuals'].max():.2e}")
        self._show_figure(d["fig"])
        self._set_status("Simulacion completada", 100)
        self._set_active_step(4)
        self._unlock_section(self.sec_results)

    # ──────────────────────────────────────────
    # PASO 5 - Resultados
    # ──────────────────────────────────────────

    def _build_section_results(self):
        self.sec_results = self._section("Paso 5 - Postprocesamiento")
        row = tk.Frame(self.sec_results, bg=C["bg"])
        row.pack(fill=tk.X, pady=4)
        _btn(row, "Ver senales ECG", self._show_ecg_window, C["purple"]).pack(side=tk.LEFT, padx=4)
        _btn(row, "Mapa de potenciales", self._show_potential_map,
             C["warning"], fg="black").pack(side=tk.LEFT, padx=4)
        self._lock_section(self.sec_results)

    def _show_ecg_window(self):
        if not self.ecg_data:
            return
        ui_results.show_ecg_window(self.root, self.ecg_data, self.ecg_source_data)

    def _show_potential_map(self):
        if not self.ecg_solution or not self.ecg_mesh_data:
            return
        ui_results.show_potential_map(
            self.root, self.ecg_solution, self.ecg_mesh_data, self.ecg_source_data)

    # ──────────────────────────────────────────
    # Generador de modelo automatico
    # ──────────────────────────────────────────

    def _show_generate_dialog(self):
        if not HAS_GMSH:
            messagebox.showerror("Error", "gmsh no esta instalado.\npip install gmsh")
            return
        dlg = tk.Toplevel(self.root)
        dlg.title("Generar Modelo de Torso")
        dlg.geometry("420x280")
        dlg.configure(bg=C["bg"])
        dlg.transient(self.root); dlg.grab_set()
        tk.Label(dlg, text="Generar Modelo de Torso",
                 font=("Arial", 13, "bold"), bg=C["bg"], fg=C["text"]).pack(pady=10)
        lungs_var = tk.BooleanVar(value=True)
        tk.Radiobutton(dlg, text="Con pulmones (completo)", variable=lungs_var, value=True,
                       bg=C["bg"], fg=C["text"], activebackground=C["bg"],
                       selectcolor=C["field"]).pack(anchor="w", padx=20)
        tk.Radiobutton(dlg, text="Sin pulmones (torso + corazon)", variable=lungs_var, value=False,
                       bg=C["bg"], fg=C["text"], activebackground=C["bg"],
                       selectcolor=C["field"]).pack(anchor="w", padx=20)
        row = tk.Frame(dlg, bg=C["bg"])
        row.pack(fill=tk.X, padx=20, pady=8)
        tk.Label(row, text="Nombre:", bg=C["bg"], fg=C["text"],
                 font=("Arial", 9)).pack(side=tk.LEFT)
        name_var = tk.StringVar(value="mi_modelo_torso")
        tk.Entry(row, textvariable=name_var, width=22,
                 font=("Consolas", 9)).pack(side=tk.LEFT, padx=6)
        tk.Label(row, text=".msh", bg=C["bg"], fg=C["muted"],
                 font=("Arial", 9)).pack(side=tk.LEFT)
        tk.Label(dlg, text="Tiempo estimado: 1-2 minutos",
                 font=("Arial", 8), bg=C["bg"], fg=C["muted"]).pack(pady=4)
        def _gen():
            import re
            fname = re.sub(r'[<>:"/\\|?*]', "_", name_var.get().strip()) or "modelo"
            out_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
            os.makedirs(out_dir, exist_ok=True)
            out_path = os.path.join(out_dir, f"{fname}.msh")
            dlg.destroy()
            self._set_status("Generando malla (puede tardar 1-2 min)...", 20)
            try:
                path = generate_mesh(include_lungs=lungs_var.get(),
                                     output_path=out_path, show_gui=False)
                self._load_mesh(path)
            except Exception as e:
                self._queue.put(("error", f"Error generando malla: {e}"))
        btn_row = tk.Frame(dlg, bg=C["bg"])
        btn_row.pack(pady=10)
        _btn(btn_row, "Generar", _gen, C["primary"], padx=20, pady=6).pack(side=tk.LEFT, padx=6)
        _btn(btn_row, "Cancelar", dlg.destroy, C["danger"], padx=20, pady=6).pack(side=tk.LEFT, padx=6)

    # ──────────────────────────────────────────
    # Visualizacion
    # ──────────────────────────────────────────

    def _show_placeholder(self):
        tk.Label(self.plot_frame, text="Carga una malla para comenzar",
                 font=("Arial", 13), bg=C["bg"], fg=C["muted"]).pack(expand=True)

    def _clear_plot(self):
        for w in self.plot_frame.winfo_children():
            w.destroy()

    def _show_figure(self, fig):
        self._clear_plot()
        ctrl = tk.Frame(self.plot_frame, bg=C["bg2"], relief=tk.RAISED, bd=1)
        ctrl.pack(fill=tk.X, pady=(0, 2))
        tk.Label(ctrl, text="Controles:", font=("Arial", 8, "bold"),
                 bg=C["bg2"], fg=C["text"]).pack(side=tk.LEFT, padx=6)
        ax = fig.axes[0] if fig.axes else None
        canvas = FigureCanvasTkAgg(fig, self.plot_frame)
        if ax is not None:
            for label, (el, az) in [("Frontal", (0, 0)), ("Superior", (90, 0)),
                                     ("Lateral", (0, 90)), ("3D", (25, 45))]:
                _btn(ctrl, label,
                     lambda e=el, a=az: (ax.view_init(e, a), canvas.draw()),
                     C["neutral"], padx=6, pady=2).pack(side=tk.LEFT, padx=2)
            tk.Frame(ctrl, width=1, bg=C["border"]).pack(side=tk.LEFT, fill=tk.Y, padx=4)
            for label, factor in [("Z+", 0.8), ("Z-", 1.25)]:
                def _zoom(f=factor):
                    for getter, setter in [(ax.get_xlim, ax.set_xlim),
                                           (ax.get_ylim, ax.set_ylim),
                                           (ax.get_zlim, ax.set_zlim)]:
                        lo, hi = getter()
                        mid = (lo + hi) / 2
                        half = (hi - lo) * f / 2
                        setter(mid - half, mid + half)
                    canvas.draw()
                _btn(ctrl, label, _zoom, C["neutral"], padx=6, pady=2).pack(side=tk.LEFT, padx=2)
            _btn(ctrl, "Reset",
                 lambda: (ax.autoscale(), ax.view_init(25, 45), canvas.draw()),
                 C["neutral"], padx=6, pady=2).pack(side=tk.LEFT, padx=2)
        tb_frame = tk.Frame(self.plot_frame, bg=C["bg"])
        tb_frame.pack(fill=tk.X)
        NavigationToolbar2Tk(canvas, tb_frame).update()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        canvas.draw()

    # ──────────────────────────────────────────
    # Drag & Drop
    # ──────────────────────────────────────────

    def _setup_dnd(self):
        EXTS = (".vtk", ".vtu", ".msh", ".mesh", ".stl", ".obj", ".ply", ".off")
        try:
            self.drop_frame.drop_target_register(DND_FILES)
            def _on_drop(e):
                files = self.root.tk.splitlist(e.data)
                if files and files[0].lower().endswith(EXTS):
                    self._load_mesh(files[0])
            self.drop_frame.dnd_bind("<<Drop>>", _on_drop)
        except Exception:
            pass

    # ──────────────────────────────────────────
    # Helpers de UI
    # ──────────────────────────────────────────

    def _lock_section(self, frame):
        frame.config(fg=C["muted"], bg="#ebebeb")
        self._set_children_state(frame, tk.DISABLED, "#ebebeb")

    def _unlock_section(self, frame):
        frame.config(fg=C["text"], bg=C["bg"])
        self._set_children_state(frame, tk.NORMAL, C["bg"])
        self._restore_widget_colors(frame)

    def _set_children_state(self, parent, state, bg):
        for w in parent.winfo_children():
            cls = w.winfo_class()
            try: w.config(state=state)
            except Exception: pass
            try:
                if cls not in ("Entry", "Text"):
                    w.config(bg=bg)
            except Exception: pass
            if cls in ("Frame", "LabelFrame"):
                self._set_children_state(w, state, bg)

    def _restore_widget_colors(self, frame):
        for w in frame.winfo_children():
            cls = w.winfo_class()
            if cls == "Button":
                txt = w.cget("text")
                if any(x in txt for x in ["Confirmar", "Iniciar", "Ver sen", "Mapa"]):
                    w.config(bg=C["primary"] if "Mapa" not in txt else C["warning"], fg="white")
                elif any(x in txt for x in ["Posiciones", "Ver en", "Seleccionar", "Generar", "Actualizar"]):
                    w.config(bg=C["success"] if "Seleccionar" in txt or "Generar" in txt else C["neutral"], fg="white")
                elif "ECG" in txt:
                    w.config(bg=C["purple"], fg="white")
            elif cls == "Entry":
                w.config(bg="white")
            elif cls == "Text":
                w.config(bg=C["field"])
            if cls in ("Frame", "LabelFrame"):
                self._restore_widget_colors(w)

    def _set_text(self, widget, text):
        widget.config(state=tk.NORMAL)
        widget.delete("1.0", tk.END)
        widget.insert("1.0", text)
        widget.config(state=tk.DISABLED)

    def _set_status(self, msg, progress=None):
        self.status_var.set(msg)
        if progress is not None:
            self.progress_var.set(progress)

    # ──────────────────────────────────────────
    # Cola de eventos
    # ──────────────────────────────────────────

    def _poll(self):
        try:
            while True:
                event, data = self._queue.get_nowait()
                if event == "mesh_loaded":
                    self._on_mesh_loaded(data)
                elif event == "sim_done":
                    self._on_sim_done(data)
                elif event == "show_fig":
                    self._show_figure(data)
                elif event == "error":
                    messagebox.showerror("Error", data)
                    self._set_status("Error - revisa los datos", 0)
        except queue.Empty:
            pass
        self.root.after(100, self._poll)
