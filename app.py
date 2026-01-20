import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import tempfile
import os
import numpy as np
from readVTK import load_mesh_skfem, extract_surface_tris, solve_poisson_point, plot_surface
import matplotlib.pyplot as plt

class ECGApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Proyecto ECG - Solucionador de Malla VTK")
        self.root.geometry("600x500")

        # Variables
        self.file_path = None
        self.mesh = None
        self.mio = None
        self.tris = None

        # Widgets
        self.create_widgets()

    def create_widgets(self):
        # Título
        title_label = tk.Label(self.root, text="Proyecto ECG - Solucionador de Malla VTK", font=("Arial", 16, "bold"))
        title_label.pack(pady=10)

        desc_label = tk.Label(self.root, text="Esta aplicación permite cargar un archivo VTK, resolver una ecuación PDE en la malla y visualizar la solución.")
        desc_label.pack(pady=5)

        # Cargar archivo
        file_frame = tk.Frame(self.root)
        file_frame.pack(pady=10)
        self.file_button = tk.Button(file_frame, text="Seleccionar archivo VTK", command=self.load_file)
        self.file_button.pack(side=tk.LEFT)
        self.file_label = tk.Label(file_frame, text="Ningún archivo seleccionado")
        self.file_label.pack(side=tk.LEFT, padx=10)

        # Botón resolver
        self.solve_button = tk.Button(self.root, text="Resolver y Visualizar", command=self.solve_and_plot, state=tk.DISABLED)
        self.solve_button.pack(pady=20)

        # Información
        self.info_label = tk.Label(self.root, text="")
        self.info_label.pack(pady=5)



    def load_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Archivos VTK", "*.vtk")])
        if file_path:
            self.file_path = file_path
            self.file_label.config(text=os.path.basename(file_path))
            try:
                self.mesh, self.mio = load_mesh_skfem(file_path)
                self.tris = extract_surface_tris(self.mio, self.mesh)
                self.info_label.config(text=f"Malla cargada: {self.mesh.p.shape[1]} nodos, {self.mesh.t.shape[1]} elementos tetraédricos\n"
                                           f"Límites de la malla: x=[{self.mesh.p[0].min():.3f}, {self.mesh.p[0].max():.3f}], "
                                           f"y=[{self.mesh.p[1].min():.3f}, {self.mesh.p[1].max():.3f}], "
                                           f"z=[{self.mesh.p[2].min():.3f}, {self.mesh.p[2].max():.3f}]")
                self.solve_button.config(state=tk.NORMAL)
            except Exception as e:
                messagebox.showerror("Error", f"Error al procesar el archivo: {e}")
                self.solve_button.config(state=tk.DISABLED)

    def update_sliders(self):
        if self.mesh:
            zmin = float(self.mesh.p[2].min())
            zmax = float(self.mesh.p[2].max())
            self.z0_slider.config(from_=zmin, to=zmax)
            self.z1_slider.config(from_=zmin, to=zmax)
            self.z0_var.set(zmin + 0.1 * (zmax - zmin))
            self.z1_var.set(zmax - 0.1 * (zmax - zmin))

    def update_mode(self):
        if self.mode.get() == "sigma":
            self.sigma_frame.pack(fill=tk.X)
            self.poisson_frame.pack_forget()
        else:
            self.sigma_frame.pack_forget()
            self.poisson_frame.pack(fill=tk.X)

    # Método update_sources eliminado ya que no se usan entradas manuales

    def solve_and_plot(self):
        if not self.mesh:
            return
        try:
            # Usar valores por defecto de readVTK.py
            from readVTK import DEFAULT_SOURCES, DEFAULT_CHARGES
            sources = np.array(DEFAULT_SOURCES, dtype=float)
            charges = np.array(DEFAULT_CHARGES, dtype=float)
            basis, V, used = solve_poisson_point(self.mesh, sources, charges)
            title = "Poisson 3D (fuente(s) puntual(es))"
            fig = plot_surface(self.mesh, self.tris, V, sources=used, title=title)
            messagebox.showinfo("Fuentes", f"Fuentes usadas (proyectadas al interior):\n{used}")
            plt.show()  # Mostrar en ventana separada
            messagebox.showinfo("Éxito", "PDE resuelta exitosamente")
        except Exception as e:
            messagebox.showerror("Error", f"Error en la resolución: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = ECGApp(root)
    root.mainloop()
