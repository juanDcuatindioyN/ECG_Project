# -*- coding: utf-8 -*-
"""
Ventanas de resultados y previsualizaciones 3D.

Funciones publicas:
    show_ecg_window       — Senales ECG por electrodo
    show_potential_map    — Mapa de potenciales con slider temporal
    preview_mesh          — Vista previa del modelo cargado
    preview_dipole        — Modelo con dipolo marcado
    preview_electrodes    — Modelo con electrodos confirmados
"""

import os
import tkinter as tk
from tkinter import messagebox
import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

# Fases del ciclo cardiaco (corresponden a DEFAULT_DIPOLE_TABLE)
CARDIAC_PHASES = [
    "Reposo", "Onda P", "Seg. PR", "Inicio QRS",
    "Pico QRS", "Final QRS", "Seg. ST", "Onda T",
    "Final T", "Diastole",
]

COLORS_V = ["#e74c3c", "#e67e22", "#f39c12", "#27ae60",
            "#2980b9", "#8e44ad", "#1abc9c", "#d35400"]

C_BG  = "white"
C_BG2 = "#f5f6fa"
C_TXT = "#212529"
C_PRI = "#0d6efd"
C_SUC = "#198754"


def _save_btn(toolbar, fig, default_filename):
    """Boton guardar integrado en el toolbar: abre dialogo para elegir destino."""
    import tkinter.filedialog as fd
    from datetime import datetime
    def _save():
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        base, ext = os.path.splitext(default_filename)
        suggested = f"{base}_{ts}{ext}"
        path = fd.asksaveasfilename(
            title="Guardar imagen",
            initialdir=os.path.expanduser("~"),
            initialfile=suggested,
            defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg"), ("PDF", "*.pdf"), ("Todos", "*.*")]
        )
        if not path:
            return
        fig.savefig(path, dpi=150, bbox_inches="tight")
        messagebox.showinfo("Guardado", f"Imagen guardada en:\n{path}")
    btn = tk.Button(toolbar, text="  Guardar imagen",
                    command=_save,
                    bg=C_SUC, fg="white",
                    relief=tk.FLAT,
                    font=("Arial", 9, "bold"),
                    padx=10, pady=3,
                    cursor="hand2")
    btn.pack(side=tk.RIGHT, padx=8)


def _embed_figure(parent, fig, extra_widget_fn=None):
    """Incrusta una figura matplotlib con toolbar en un frame tkinter."""
    frame = tk.Frame(parent, bg=C_BG)
    frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=4)
    tb = tk.Frame(frame, bg=C_BG)
    tb.pack(fill=tk.X)
    canvas = FigureCanvasTkAgg(fig, frame)
    toolbar = NavigationToolbar2Tk(canvas, tb)
    toolbar.update()
    # Boton guardar al lado derecho del toolbar, mismo estilo
    if extra_widget_fn:
        extra_widget_fn(toolbar)
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    canvas.draw()
    return canvas


# ─────────────────────────────────────────────
# Ventana de senales ECG
# ─────────────────────────────────────────────

def show_ecg_window(root, ecg_data, ecg_source_data):
    """Abre ventana con las senales ECG por electrodo."""
    leads = ecg_data.get("leads", {})
    times = ecg_source_data.get("times") if ecg_source_data else None
    if times is None:
        from ..core.ecg_solver import DEFAULT_DIPOLE_TABLE
        times = DEFAULT_DIPOLE_TABLE[:, 0]
    if not leads:
        messagebox.showwarning("Sin datos", "No hay senales ECG disponibles.")
        return

    names = list(leads.keys())
    cols  = min(len(names), 3)
    rows  = (len(names) + cols - 1) // cols
    t_ms  = times * 1000

    win = tk.Toplevel(root)
    win.title("Senales ECG por Electrodo")
    win.geometry("900x580")
    win.configure(bg=C_BG)
    tk.Label(win, text="Potenciales ECG", font=("Arial", 12, "bold"),
             bg=C_BG, fg=C_TXT).pack(pady=6)

    fig = Figure(figsize=(cols * 3.5, rows * 2.8), dpi=90)
    for idx, name in enumerate(names):
        ax  = fig.add_subplot(rows, cols, idx + 1)
        sig = leads[name] * 1000
        c   = COLORS_V[idx % len(COLORS_V)]

        ax.plot(t_ms, sig, color=c, lw=2)
        ax.fill_between(t_ms, sig, alpha=0.1, color=c)
        ax.axhline(0, color="#ccc", lw=0.8, ls="--")

        pk = int(np.argmax(np.abs(sig)))
        ax.scatter(t_ms[pk], sig[pk], s=40, color=c, zorder=10,
                   edgecolors="black", lw=0.7)
        dy = 12 if sig[pk] >= 0 else -18
        ax.annotate(f"{sig[pk]:.1f} mV", (t_ms[pk], sig[pk]),
                    textcoords="offset points", xytext=(4, dy),
                    fontsize=6.5, color=c, fontweight="bold",
                    bbox=dict(boxstyle="round,pad=0.2", facecolor="white",
                              edgecolor=c, alpha=0.85, linewidth=0.8),
                    arrowprops=dict(arrowstyle="-", color=c, lw=0.7, alpha=0.6))

        ax.set_title(name, fontsize=10, fontweight="bold", color=c, pad=4)
        ax.set_xlabel("t (ms)", fontsize=7)
        ax.set_ylabel("mV", fontsize=7)
        ax.tick_params(labelsize=7)
        ax.grid(True, ls="--", alpha=0.3)
        ax.set_facecolor("#fafafa")
        ymin, ymax = ax.get_ylim()
        margin = (ymax - ymin) * 0.18
        ax.set_ylim(ymin - margin * 0.3, ymax + margin)

    fig.tight_layout(pad=2.0)
    _embed_figure(win, fig,
                  extra_widget_fn=lambda tb: _save_btn(tb, fig, "ecg_senales.png"))


# ─────────────────────────────────────────────
# Ventana de mapa de potenciales
# ─────────────────────────────────────────────

def show_potential_map(root, ecg_solution, ecg_mesh_data, ecg_source_data):
    """Abre ventana con el mapa de potenciales en la superficie del torso."""
    PHI  = ecg_solution["PHI"]
    mesh = ecg_mesh_data["mesh"]
    sn   = ecg_mesh_data["surface_nodes"]
    X    = mesh.p.T
    times = ecg_source_data.get("times") if ecg_source_data else None

    if len(sn) == 0:
        sn = np.arange(X.shape[0])

    phi_surf_all = PHI[sn, :]
    variacion    = phi_surf_all.max(axis=0) - phi_surf_all.min(axis=0)
    best_t       = int(np.argmax(variacion))
    phi_sup      = phi_surf_all[:, 0] * 1000
    t_label      = f"t={times[0]*1000:.0f} ms" if times is not None else "inst. 0"

    win = tk.Toplevel(root)
    win.title("Mapa de Potenciales")
    win.geometry("900x600")
    win.configure(bg=C_BG)
    tk.Label(win, text="Mapa de Potenciales en la Superficie del Torso",
             font=("Arial", 11, "bold"), bg=C_BG, fg=C_TXT).pack(pady=6)

    fig  = Figure(figsize=(8, 4.5), dpi=90)
    ax1  = fig.add_subplot(121)
    ax2  = fig.add_subplot(122)
    vmax = np.abs(phi_sup).max() or 1.0

    sc1 = ax1.scatter(X[sn, 0], X[sn, 2], c=phi_sup,
                      cmap="RdBu_r", s=10, vmin=-vmax, vmax=vmax, alpha=0.85)
    fig.colorbar(sc1, ax=ax1, label="mV", shrink=0.85)
    ax1.set_xlabel("x (m)", fontsize=8); ax1.set_ylabel("z (m)", fontsize=8)
    ax1.set_title(f"Frontal X-Z  |  {t_label}", fontsize=9)
    ax1.set_aspect("equal"); ax1.grid(True, ls="--", alpha=0.25)

    sc2 = ax2.scatter(X[sn, 0], X[sn, 1], c=phi_sup,
                      cmap="RdBu_r", s=10, vmin=-vmax, vmax=vmax, alpha=0.85)
    fig.colorbar(sc2, ax=ax2, label="mV", shrink=0.85)
    ax2.set_xlabel("x (m)", fontsize=8); ax2.set_ylabel("y (m)", fontsize=8)
    ax2.set_title(f"Superior X-Y  |  {t_label}", fontsize=9)
    ax2.set_aspect("equal"); ax2.grid(True, ls="--", alpha=0.25)

    fig.tight_layout()
    canvas = _embed_figure(win, fig,
                           extra_widget_fn=lambda tb: _save_btn(
                               tb, fig, "mapa_potenciales.png"))

    # Slider temporal + animacion
    if times is not None and len(times) > 1:
        vmax_global = float(np.abs(phi_surf_all).max()) or 1.0
        ctrl = tk.Frame(win, bg=C_BG2)
        ctrl.pack(fill=tk.X, padx=6, pady=4)
        fase_var    = tk.StringVar()
        t_var       = tk.IntVar(value=0)
        playing     = [False]
        anim_id     = [None]
        speed_var   = tk.IntVar(value=120)   # ms entre frames

        def _update(val):
            t     = int(float(val))
            phi_t = phi_surf_all[:, t] * 1000
            vt    = max(float(np.abs(phi_t).max()), vmax_global * 0.01)
            sc1.set_array(phi_t); sc1.set_clim(-vt, vt)
            sc2.set_array(phi_t); sc2.set_clim(-vt, vt)
            fase  = CARDIAC_PHASES[t] if t < len(CARDIAC_PHASES) else f"t{t}"
            tl    = f"t={times[t]*1000:.0f} ms  —  {fase}"
            ax1.set_title(f"Frontal X-Z  |  {tl}", fontsize=9)
            ax2.set_title(f"Superior X-Y  |  {tl}", fontsize=9)
            fase_var.set(f"{fase}  (t = {times[t]*1000:.0f} ms)")
            canvas.draw()

        def _step():
            if not playing[0]:
                return
            nxt = (t_var.get() + 1) % len(times)
            t_var.set(nxt)
            _update(nxt)
            anim_id[0] = win.after(speed_var.get(), _step)

        def _toggle_play():
            playing[0] = not playing[0]
            if playing[0]:
                play_btn.config(text="⏸  Pausar")
                _step()
            else:
                play_btn.config(text="▶  Reproducir")
                if anim_id[0]:
                    win.after_cancel(anim_id[0])

        def _stop():
            playing[0] = False
            play_btn.config(text="▶  Reproducir")
            if anim_id[0]:
                win.after_cancel(anim_id[0])
            t_var.set(0)
            _update(0)

        win.protocol("WM_DELETE_WINDOW", lambda: (_stop(), win.destroy()))

        # Fila 1: fase actual
        row1 = tk.Frame(ctrl, bg=C_BG2)
        row1.pack(fill=tk.X, pady=(2, 0))
        tk.Label(row1, text="Fase:", font=("Arial", 8, "bold"),
                 bg=C_BG2, fg=C_TXT).pack(side=tk.LEFT, padx=4)
        tk.Label(row1, textvariable=fase_var, font=("Arial", 8),
                 bg=C_BG2, fg=C_PRI, width=34, anchor="w").pack(side=tk.LEFT, padx=2)

        # Fila 2: slider
        row2 = tk.Frame(ctrl, bg=C_BG2)
        row2.pack(fill=tk.X, pady=2)
        tk.Label(row2, text="Instante:", font=("Arial", 8),
                 bg=C_BG2, fg=C_TXT).pack(side=tk.LEFT, padx=4)
        tk.Scale(row2, from_=0, to=len(times)-1, orient=tk.HORIZONTAL,
                 variable=t_var, command=_update,
                 bg=C_BG2, fg=C_TXT, length=320).pack(side=tk.LEFT, padx=4)

        # Fila 3: controles de reproduccion
        row3 = tk.Frame(ctrl, bg=C_BG2)
        row3.pack(fill=tk.X, pady=(2, 4))
        play_btn = tk.Button(row3, text="▶  Reproducir", command=_toggle_play,
                             bg=C_PRI, fg="white", relief=tk.FLAT,
                             font=("Arial", 9, "bold"), padx=10, pady=3, cursor="hand2")
        play_btn.pack(side=tk.LEFT, padx=4)
        tk.Button(row3, text="⏹  Reiniciar", command=_stop,
                  bg="#6c757d", fg="white", relief=tk.FLAT,
                  font=("Arial", 9, "bold"), padx=10, pady=3, cursor="hand2").pack(side=tk.LEFT, padx=4)
        tk.Label(row3, text="Velocidad (ms/frame):", font=("Arial", 8),
                 bg=C_BG2, fg=C_TXT).pack(side=tk.LEFT, padx=(12, 2))
        tk.Scale(row3, from_=40, to=600, orient=tk.HORIZONTAL,
                 variable=speed_var, bg=C_BG2, fg=C_TXT, length=140,
                 showvalue=True).pack(side=tk.LEFT)

        fase_init = CARDIAC_PHASES[0] if len(CARDIAC_PHASES) > 0 else ""
        fase_var.set(f"{fase_init}  (t = {times[0]*1000:.0f} ms)")


# ─────────────────────────────────────────────
# Previsualizaciones 3D (en hilo separado)
# ─────────────────────────────────────────────

def preview_mesh(mesh, mio, queue):
    """Genera vista previa del modelo y la pone en la cola."""
    import threading
    def _work():
        try:
            from ..visualization.viewer3d import crear_figura_3d
            fig = crear_figura_3d(mesh, mio, incluir_pulmones=True)
            queue.put(("show_fig", fig))
        except Exception as e:
            queue.put(("error", f"Vista previa: {e}"))
    threading.Thread(target=_work, daemon=True).start()


def preview_dipole(mesh, mio, dipole_pos, queue):
    """Genera vista del modelo con el dipolo marcado."""
    import threading
    def _work():
        try:
            from ..visualization.viewer3d import crear_figura_3d
            import matplotlib.patches as mpatches
            fig = crear_figura_3d(mesh, mio, incluir_pulmones=True)
            ax  = fig.axes[0]
            x0, y0, z0 = mesh.p[0].min(), mesh.p[1].min(), mesh.p[2].min()
            ax.plot([dipole_pos[0]]*2, [dipole_pos[1]]*2, [z0, dipole_pos[2]],
                    color="#ff0000", lw=0.8, ls="--", alpha=0.5)
            ax.plot([dipole_pos[0]]*2, [y0, dipole_pos[1]], [dipole_pos[2]]*2,
                    color="#ff0000", lw=0.8, ls="--", alpha=0.5)
            ax.plot([x0, dipole_pos[0]], [dipole_pos[1]]*2, [dipole_pos[2]]*2,
                    color="#ff0000", lw=0.8, ls="--", alpha=0.5)
            ax.scatter(*dipole_pos, s=200, c="#ff0000", marker="*",
                       edgecolors="darkred", lw=1.2, zorder=1000)
            ax.text(*dipole_pos,
                    f"  Dipolo ({dipole_pos[0]:.3f}, {dipole_pos[1]:.3f}, {dipole_pos[2]:.3f})",
                    fontsize=7, color="#cc0000", fontweight="bold", zorder=1001)
            handles, _ = ax.get_legend_handles_labels()
            handles.append(mpatches.Patch(color="#ff0000", label="Dipolo cardiaco"))
            ax.legend(handles=handles, loc="upper right", fontsize=7, framealpha=0.9)
            fig.suptitle("Modelo - posicion del dipolo", fontsize=10, color="#333")
            queue.put(("show_fig", fig))
        except Exception as e:
            queue.put(("error", f"Vista dipolo: {e}"))
    threading.Thread(target=_work, daemon=True).start()


def preview_electrodes(mesh, mio, dipole_pos, elec, queue):
    """Genera vista del modelo con dipolo y electrodos confirmados."""
    import threading
    def _work():
        try:
            from ..visualization.viewer3d import crear_figura_3d
            import matplotlib.patches as mpatches
            fig    = crear_figura_3d(mesh, mio, incluir_pulmones=True)
            ax     = fig.axes[0]
            centro = mesh.p.T.mean(axis=0)

            if dipole_pos is not None:
                ax.scatter(*dipole_pos, s=180, c="#ff0000", marker="*",
                           edgecolors="darkred", lw=1.0, zorder=999)
                ax.text(*dipole_pos, "  Dipolo",
                        fontsize=6, color="#cc0000", fontweight="bold")

            legend_handles = []
            for i, (name, pos) in enumerate(elec.items()):
                c = COLORS_V[i % len(COLORS_V)]
                ax.scatter(*pos, s=100, c=c, marker="o",
                           edgecolors="black", lw=0.7, zorder=1000)
                dir_out = pos - centro
                norm = np.linalg.norm(dir_out)
                if norm > 1e-10:
                    dir_out /= norm
                p_ext = pos + dir_out * 0.015
                ax.plot([pos[0], p_ext[0]], [pos[1], p_ext[1]], [pos[2], p_ext[2]],
                        color=c, lw=1.0, ls="--", alpha=0.7)
                ax.text(*p_ext, f" {name}",
                        fontsize=7, color=c, fontweight="bold", zorder=1001)
                legend_handles.append(mpatches.Patch(color=c, label=name))

            if legend_handles:
                handles, _ = ax.get_legend_handles_labels()
                ax.legend(handles=handles + legend_handles,
                          loc="upper right", fontsize=6, framealpha=0.9)

            fig.suptitle(f"Modelo - {len(elec)} electrodos confirmados",
                         fontsize=10, color="#333")
            queue.put(("show_fig", fig))
        except Exception as e:
            queue.put(("error", f"Vista electrodos: {e}"))
    threading.Thread(target=_work, daemon=True).start()


# ─────────────────────────────────────────────
# Exportar resultados a VTK
# ─────────────────────────────────────────────

def export_vtk(root, ecg_mesh_data, ecg_solution, ecg_source_data):
    """
    Exporta la malla con los potenciales calculados a un archivo VTK ASCII legacy.
    El archivo puede abrirse directamente en un bloc de notas.
    """
    import tkinter.filedialog as fd

    if not ecg_mesh_data or not ecg_solution:
        messagebox.showwarning("Sin datos", "Primero ejecuta la simulacion.")
        return

    from datetime import datetime
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    default_name = f"resultado_ecg_{ts}.vtk"

    path = fd.asksaveasfilename(
        parent=root,
        title="Guardar resultado como VTK",
        initialdir=os.path.expanduser("~"),
        initialfile=default_name,
        defaultextension=".vtk",
        filetypes=[("VTK Legacy ASCII", "*.vtk"), ("Todos", "*.*")]
    )
    if not path:
        return

    try:
        mesh  = ecg_mesh_data["mesh"]
        mio   = ecg_mesh_data["mio"]
        PHI   = ecg_solution["PHI"]          # (N_nodos, T)
        times = ecg_source_data.get("times") if ecg_source_data else None

        points = mesh.p.T                    # (N, 3)
        cells  = mesh.t.T                    # (E, 4)
        N = points.shape[0]
        E = cells.shape[0]
        T = PHI.shape[1]

        # Etiquetas de material por elemento
        mat_labels = None
        if hasattr(mio, "cell_data_dict"):
            d = mio.cell_data_dict
            if "gmsh:physical" in d and "tetra" in d["gmsh:physical"]:
                mat_labels = d["gmsh:physical"]["tetra"].flatten().astype(int)

        with open(path, "w", encoding="utf-8") as f:
            # Cabecera
            f.write("# vtk DataFile Version 2.0\n")
            f.write(f"ECG Solver Result - {ts}\n")
            f.write("ASCII\n")
            f.write("DATASET UNSTRUCTURED_GRID\n\n")

            # Puntos
            f.write(f"POINTS {N} double\n")
            for x, y, z in points:
                f.write(f"{x:.10g} {y:.10g} {z:.10g}\n")
            f.write("\n")

            # Celdas (tetraedros: 4 nodos, prefijo 4)
            f.write(f"CELLS {E} {E * 5}\n")
            for tet in cells:
                f.write(f"4 {tet[0]} {tet[1]} {tet[2]} {tet[3]}\n")
            f.write("\n")

            # Tipos de celda (10 = VTK_TETRA)
            f.write(f"CELL_TYPES {E}\n")
            for _ in range(E):
                f.write("10\n")
            f.write("\n")

            # Datos de punto: potencial en cada instante
            f.write(f"POINT_DATA {N}\n")
            for t_idx in range(T):
                if times is not None:
                    label = f"phi_t{t_idx:02d}_{times[t_idx]*1000:.0f}ms"
                else:
                    label = f"phi_t{t_idx:02d}"
                f.write(f"SCALARS {label} double 1\n")
                f.write("LOOKUP_TABLE default\n")
                for val in PHI[:, t_idx]:
                    f.write(f"{val:.10g}\n")
                f.write("\n")

            # Datos de celda: material
            if mat_labels is not None and len(mat_labels) == E:
                f.write(f"CELL_DATA {E}\n")
                f.write("SCALARS material int 1\n")
                f.write("LOOKUP_TABLE default\n")
                for val in mat_labels:
                    f.write(f"{val}\n")
                f.write("\n")

        messagebox.showinfo("Exportado",
                            f"Archivo VTK ASCII guardado en:\n{path}\n\n"
                            f"Contiene {T} instantes temporales\n"
                            f"y {N:,} nodos.")
    except Exception as e:
        messagebox.showerror("Error al exportar", str(e))
