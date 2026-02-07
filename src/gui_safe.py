"""
Versión automática de la interfaz gráfica con resolución de Poisson automática

Esta versión detecta automáticamente puntos óptimos para fuentes de Poisson
y resuelve la ecuación inmediatamente después de cargar el archivo VTK.
"""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import queue
import threading

# Importación opcional de tkinterdnd2
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    HAS_DND = True
except ImportError:
    HAS_DND = False
    print("Nota: tkinterdnd2 no está disponible. Drag & Drop deshabilitado.")

# Importar funciones del módulo core
from .core import load_mesh_skfem, extract_surface_tris, solve_poisson_point, plot_surface


def auto_detect_sources(mesh, num_sources=3):
    """
    Detecta automáticamente puntos óptimos para fuentes de Poisson.
    
    Args:
        mesh: Malla scikit-fem
        num_sources: Número de fuentes a generar
        
    Returns:
        tuple: (sources, charges) arrays con fuentes y cargas automáticas
    """
    # Obtener límites de la malla
    bounds = {
        'x': (float(mesh.p[0].min()), float(mesh.p[0].max())),
        'y': (float(mesh.p[1].min()), float(mesh.p[1].max())),
        'z': (float(mesh.p[2].min()), float(mesh.p[2].max()))
    }
    
    # Calcular centro y dimensiones
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
    
    # Estrategias de colocación de fuentes
    if num_sources == 1:
        # Una fuente en el centro
        sources = np.array([center])
        charges = np.array([1.0])
        
    elif num_sources == 2:
        # Dipolo a lo largo del eje más largo
        max_dim_idx = np.argmax(dimensions)
        offset = np.zeros(3)
        offset[max_dim_idx] = dimensions[max_dim_idx] * 0.3
        
        sources = np.array([
            center + offset,
            center - offset
        ])
        charges = np.array([1.0, -1.0])
        
    elif num_sources == 3:
        # Configuración triangular en el plano XY
        radius = min(dimensions[:2]) * 0.25
        angles = np.array([0, 2*np.pi/3, 4*np.pi/3])
        
        sources = np.array([
            [center[0] + radius * np.cos(angle), 
             center[1] + radius * np.sin(angle), 
             center[2] + (i-1) * dimensions[2] * 0.1]
            for i, angle in enumerate(angles)
        ])
        charges = np.array([1.0, 0.8, -0.6])
        
    elif num_sources == 4:
        # Configuración tetraédrica
        radius = min(dimensions) * 0.2
        
        # Vértices de un tetraedro regular
        tetra_vertices = np.array([
            [1, 1, 1],
            [1, -1, -1],
            [-1, 1, -1],
            [-1, -1, 1]
        ]) * radius
        
        sources = center + tetra_vertices
        charges = np.array([1.0, -0.8, 0.6, -0.4])
        
    else:
        # Para más fuentes, distribución aleatoria estratificada
        np.random.seed(42)  # Para reproducibilidad
        
        # Generar fuentes en diferentes regiones
        sources = []
        for i in range(num_sources):
            # Dividir el espacio en regiones
            region_offset = np.array([
                (i % 2 - 0.5) * dimensions[0] * 0.4,
                ((i // 2) % 2 - 0.5) * dimensions[1] * 0.4,
                ((i // 4) % 2 - 0.5) * dimensions[2] * 0.4
            ])
            
            # Agregar variación aleatoria pequeña
            random_offset = np.random.normal(0, 0.1, 3) * dimensions * 0.1
            
            source = center + region_offset + random_offset
            sources.append(source)
        
        sources = np.array(sources)
        
        # Cargas alternantes con decaimiento
        charges = np.array([
            (1.0 if i % 2 == 0 else -0.8) * (0.9 ** (i // 2))
            for i in range(num_sources)
        ])
    
    return sources, charges


def analyze_mesh_complexity(mesh):
    """
    Analiza la complejidad de la malla para determinar parámetros automáticos.
    
    Args:
        mesh: Malla scikit-fem
        
    Returns:
        dict: Información sobre la complejidad de la malla
    """
    num_nodes = mesh.p.shape[1]
    num_elements = mesh.t.shape[1]
    
    # Calcular dimensiones
    dimensions = np.array([
        mesh.p[0].max() - mesh.p[0].min(),
        mesh.p[1].max() - mesh.p[1].min(),
        mesh.p[2].max() - mesh.p[2].min()
    ])
    
    volume_estimate = np.prod(dimensions)
    
    # Determinar número óptimo de fuentes basado en complejidad
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


class ECGAppAuto:
    """
    Versión automática de la aplicación ECG que detecta y resuelve automáticamente.
    
    Características automáticas:
    - Detección automática de fuentes óptimas
    - Cálculo automático de cargas
    - Resolución inmediata después de cargar archivo
    - Análisis de complejidad de malla
    """
    
    def __init__(self, root=None):
        # Importar tkinter al inicio
        import tkinter as tk
        
        # Crear ventana principal si no se proporciona una
        if root is None:
            # Intentar usar TkinterDnD si está disponible
            if HAS_DND:
                try:
                    self.root = TkinterDnD.Tk()
                except Exception:
                    self.root = tk.Tk()
                    print("Nota: Error inicializando TkinterDnD, usando Tkinter estándar")
            else:
                self.root = tk.Tk()
                print("Nota: Drag & Drop no disponible. Instala tkinterdnd2 para esta funcionalidad.")
        else:
            # Usar la ventana proporcionada
            self.root = root
            
        self.root.title("Proyecto ECG - Solucionador Automático de Poisson")
        self.root.geometry("1200x800")
        self.root.configure(bg='#f0f0f0')

        # Variables de estado
        self.file_path = None
        self.mesh = None
        self.mio = None
        self.tris = None
        self.current_solution = None
        self.mesh_analysis = None
        
        # Variables para parámetros automáticos
        self.auto_sources = None
        self.auto_charges = None
        
        # Variables para progreso
        self.progress_var = tk.DoubleVar()
        self.status_var = tk.StringVar(value="Listo para cargar archivo VTK - Resolución automática")
        
        # Queue para comunicación segura entre hilos
        self.task_queue = queue.Queue()
        
        # Crear interfaz
        self.create_widgets()
        if HAS_DND:
            self.setup_drag_drop()
        
        # Iniciar procesamiento de tareas
        self.process_queue()

    def create_widgets(self):
        """Crea todos los widgets de la interfaz."""
        # Frame principal con dos paneles
        main_frame = tk.Frame(self.root, bg='#f0f0f0')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Panel izquierdo - Controles
        left_panel = tk.Frame(main_frame, bg='white', relief=tk.RAISED, bd=2)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))
        left_panel.configure(width=400)
        left_panel.pack_propagate(False)
        
        # Panel derecho - Visualización
        right_panel = tk.Frame(main_frame, bg='white', relief=tk.RAISED, bd=2)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        self.create_control_panel(left_panel)
        self.create_visualization_panel(right_panel)

    def create_control_panel(self, parent):
        """Crea el panel de controles para la versión automática."""
        # Título
        title_label = tk.Label(parent, text="Solucionador ECG\n(Automático)", 
                              font=("Arial", 18, "bold"), bg='white', fg='#2c3e50')
        title_label.pack(pady=15)

        # Sección de carga de archivo
        file_section = tk.LabelFrame(parent, text="Archivo VTK", font=("Arial", 12, "bold"),
                                   bg='white', fg='#34495e', padx=10, pady=10)
        file_section.pack(fill=tk.X, padx=15, pady=10)

        # Zona de drag & drop
        self.drop_frame = tk.Frame(file_section, bg='#ecf0f1', relief='solid', bd=2, height=80)
        self.drop_frame.pack(fill=tk.X, pady=5)
        self.drop_frame.pack_propagate(False)
        
        if HAS_DND:
            drop_text = "Arrastra aquí tu archivo .vtk\nResolución automática de Poisson"
        else:
            drop_text = "Haz clic para seleccionar archivo .vtk\nResolución automática de Poisson"
            
        drop_label = tk.Label(self.drop_frame, text=drop_text, 
                             font=("Arial", 10), bg='#ecf0f1', fg='#7f8c8d')
        drop_label.pack(expand=True)
        
        # Botón de selección manual
        self.file_button = tk.Button(file_section, text="Seleccionar archivo VTK", 
                                   command=self.load_file, font=("Arial", 10),
                                   bg='#3498db', fg='white', relief=tk.FLAT, padx=20)
        self.file_button.pack(pady=5)
        
        # Información del archivo
        self.file_info = tk.Text(file_section, height=6, font=("Consolas", 9), 
                               bg='#f8f9fa', state=tk.DISABLED)
        self.file_info.pack(fill=tk.X, pady=5)

        # Sección de análisis automático
        analysis_section = tk.LabelFrame(parent, text="Análisis Automático", 
                                       font=("Arial", 12, "bold"), bg='white', fg='#34495e',
                                       padx=10, pady=10)
        analysis_section.pack(fill=tk.X, padx=15, pady=10)

        # Información de análisis
        self.analysis_info = tk.Text(analysis_section, height=8, font=("Consolas", 9), 
                                   bg='#f8f9fa', state=tk.DISABLED)
        self.analysis_info.pack(fill=tk.X, pady=5)
        
        # Información inicial
        self.analysis_info.config(state=tk.NORMAL)
        self.analysis_info.insert(1.0, """MODO AUTOMÁTICO ACTIVADO

Características automáticas:
• Detección inteligente de fuentes óptimas
• Cálculo automático de cargas balanceadas
• Resolución inmediata tras cargar archivo
• Análisis de complejidad de malla

Simplemente carga un archivo VTK y la
aplicación resolverá automáticamente la
ecuación de Poisson con parámetros óptimos.""")
        self.analysis_info.config(state=tk.DISABLED)

        # Botones de acción
        action_frame = tk.Frame(parent, bg='white')
        action_frame.pack(fill=tk.X, padx=15, pady=20)
        
        self.preview_button = tk.Button(action_frame, text="Vista Previa", 
                                      command=self.preview_mesh, state=tk.DISABLED,
                                      font=("Arial", 11), bg='#f39c12', fg='white', 
                                      relief=tk.FLAT, padx=20, pady=8)
        self.preview_button.pack(fill=tk.X, pady=2)
        
        self.auto_solve_button = tk.Button(action_frame, text="Resolver Automáticamente", 
                                         command=self.auto_solve, state=tk.DISABLED,
                                         font=("Arial", 11, "bold"), bg='#27ae60', fg='white', 
                                         relief=tk.FLAT, padx=20, pady=8)
        self.auto_solve_button.pack(fill=tk.X, pady=2)
        
        self.manual_solve_button = tk.Button(action_frame, text="Resolver Manualmente", 
                                           command=self.show_manual_options, state=tk.DISABLED,
                                           font=("Arial", 10), bg='#95a5a6', fg='white', 
                                           relief=tk.FLAT, padx=20, pady=6)
        self.manual_solve_button.pack(fill=tk.X, pady=2)

        # Barra de progreso
        self.progress_bar = ttk.Progressbar(parent, variable=self.progress_var, 
                                          maximum=100, mode='determinate')
        self.progress_bar.pack(fill=tk.X, padx=15, pady=5)
        
        # Estado
        self.status_label = tk.Label(parent, textvariable=self.status_var, 
                                   font=("Arial", 9), bg='white', fg='#7f8c8d', wraplength=350)
        self.status_label.pack(pady=5)

    def create_visualization_panel(self, parent):
        """Crea el panel de visualización."""
        # Título del panel
        viz_title = tk.Label(parent, text="Visualización 3D", font=("Arial", 14, "bold"),
                           bg='white', fg='#2c3e50')
        viz_title.pack(pady=10)
        
        # Frame para matplotlib
        self.plot_frame = tk.Frame(parent, bg='white')
        self.plot_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Placeholder inicial
        self.create_placeholder()

    def create_placeholder(self):
        """Crea un placeholder inicial para el área de visualización."""
        placeholder = tk.Label(self.plot_frame, 
                             text="Carga un archivo VTK para comenzar\nla visualización y resolución",
                             font=("Arial", 14), bg='white', fg='#bdc3c7')
        placeholder.pack(expand=True)
        self.placeholder = placeholder

    def setup_drag_drop(self):
        """Configura drag & drop para archivos VTK (solo si está disponible)"""
        if not HAS_DND:
            # Si no hay DND, hacer el frame clickeable
            self.drop_frame.bind("<Button-1>", lambda e: self.load_file())
            return
            
        try:
            self.drop_frame.drop_target_register(DND_FILES)
            self.drop_frame.dnd_bind('<<Drop>>', self.on_drop)
            
            # Hacer el frame clickeable también
            self.drop_frame.bind("<Button-1>", lambda e: self.load_file())
            
        except Exception as e:
            print(f"Error configurando Drag & Drop: {e}")
            # Fallback: hacer clickeable
            self.drop_frame.bind("<Button-1>", lambda e: self.load_file())

    def on_drop(self, event):
        """Maneja archivos arrastrados (solo si DND está disponible)"""
        if not HAS_DND:
            return
            
        files = self.root.tk.splitlist(event.data)
        if files:
            file_path = files[0]
            if file_path.lower().endswith('.vtk'):
                self.process_file(file_path)
            else:
                messagebox.showerror("Error", "Por favor selecciona un archivo .vtk")

    def load_file(self):
        """Carga archivo mediante diálogo"""
        file_path = filedialog.askopenfilename(
            title="Seleccionar archivo VTK",
            filetypes=[("Archivos VTK", "*.vtk"), ("Todos los archivos", "*.*")]
        )
        if file_path:
            self.process_file(file_path)

    def process_file(self, file_path):
        """Procesa el archivo VTK seleccionado de forma segura"""
        self.file_path = file_path
        self.status_var.set("Cargando archivo...")
        self.progress_var.set(20)
        
        # Agregar tarea al queue
        self.task_queue.put(('load_mesh', file_path))

    def process_queue(self):
        """Procesa tareas del queue de forma segura"""
        try:
            while True:
                task_type, data = self.task_queue.get_nowait()
                
                if task_type == 'load_mesh':
                    self._handle_load_mesh(data)
                elif task_type == 'preview':
                    self._handle_preview()
                elif task_type == 'solve_auto':
                    self._handle_solve_auto()
                elif task_type == 'update_ui':
                    self._handle_ui_update(data)
                elif task_type == 'show_error':
                    self._handle_error(data)
                    
        except queue.Empty:
            pass
        
        # Programar siguiente verificación
        self.root.after(100, self.process_queue)

    def _handle_load_mesh(self, file_path):
        """Maneja la carga de malla de forma segura con análisis automático"""
        def load_in_background():
            try:
                mesh, mio = load_mesh_skfem(file_path)
                tris = extract_surface_tris(mio, mesh)
                
                # Análisis automático de la malla
                analysis = analyze_mesh_complexity(mesh)
                
                # Detectar fuentes y cargas automáticamente
                sources, charges = auto_detect_sources(mesh, analysis['optimal_sources'])
                
                # Guardar parámetros automáticos
                self.auto_sources = sources
                self.auto_charges = charges
                
                # Enviar resultado de vuelta al hilo principal
                self.task_queue.put(('update_ui', {
                    'type': 'mesh_loaded',
                    'mesh': mesh,
                    'mio': mio,
                    'tris': tris,
                    'file_path': file_path,
                    'analysis': analysis
                }))
                
            except Exception as e:
                self.task_queue.put(('show_error', f"Error al cargar archivo: {e}"))
        
        # Ejecutar en hilo separado
        thread = threading.Thread(target=load_in_background, daemon=True)
        thread.start()

    def auto_solve(self):
        """Resuelve automáticamente con parámetros detectados"""
        if not self.mesh or self.auto_sources is None:
            return
            
        self.status_var.set("Resolviendo automáticamente...")
        self.progress_var.set(20)
        
        self.task_queue.put(('solve_auto', None))

    def _handle_solve_auto(self):
        """Maneja la resolución automática"""
        def solve_in_background():
            try:
                # Resolver con parámetros automáticos
                basis, V, used_sources = solve_poisson_point(self.mesh, self.auto_sources, self.auto_charges)
                
                # Crear visualización
                fig = plot_surface(self.mesh, self.tris, V, sources=used_sources, 
                                 title="Solución Automática de Poisson 3D")
                
                # Enviar resultado
                self.task_queue.put(('update_ui', {
                    'type': 'solution_ready',
                    'figure': fig,
                    'sources': used_sources,
                    'solution': V
                }))
                
            except Exception as e:
                self.task_queue.put(('show_error', f"Error en resolución automática: {e}"))
        
        thread = threading.Thread(target=solve_in_background, daemon=True)
        thread.start()

    def show_manual_options(self):
        """Muestra opciones para resolución manual"""
        if not self.mesh:
            return
        
        # Crear ventana de opciones manuales
        manual_window = tk.Toplevel(self.root)
        manual_window.title("Opciones Manuales")
        manual_window.geometry("400x300")
        manual_window.configure(bg='white')
        
        # Título
        title = tk.Label(manual_window, text="Configuración Manual", 
                        font=("Arial", 14, "bold"), bg='white')
        title.pack(pady=10)
        
        # Fuentes
        tk.Label(manual_window, text="Fuentes (x,y,z):", bg='white').pack(anchor=tk.W, padx=20)
        sources_var = tk.StringVar(value=self._format_sources_for_display(self.auto_sources))
        sources_entry = tk.Entry(manual_window, textvariable=sources_var, width=50)
        sources_entry.pack(fill=tk.X, padx=20, pady=5)
        
        # Cargas
        tk.Label(manual_window, text="Cargas:", bg='white').pack(anchor=tk.W, padx=20, pady=(10,0))
        charges_var = tk.StringVar(value=self._format_charges_for_display(self.auto_charges))
        charges_entry = tk.Entry(manual_window, textvariable=charges_var, width=50)
        charges_entry.pack(fill=tk.X, padx=20, pady=5)
        
        # Botones
        button_frame = tk.Frame(manual_window, bg='white')
        button_frame.pack(pady=20)
        
        def solve_manual():
            try:
                # Parsear parámetros manuales
                sources = self._parse_sources_string(sources_var.get())
                charges = self._parse_charges_string(charges_var.get())
                
                # Guardar parámetros manuales
                self.auto_sources = sources
                self.auto_charges = charges
                
                manual_window.destroy()
                self.auto_solve()
                
            except Exception as e:
                messagebox.showerror("Error", f"Error en parámetros: {e}")
        
        tk.Button(button_frame, text="Resolver", command=solve_manual,
                 bg='#27ae60', fg='white', padx=20).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Cancelar", command=manual_window.destroy,
                 bg='#e74c3c', fg='white', padx=20).pack(side=tk.LEFT, padx=5)

    def _format_sources_for_display(self, sources):
        """Formatea fuentes para mostrar en la UI"""
        if sources is None:
            return ""
        return ";".join([f"{s[0]:.3f},{s[1]:.3f},{s[2]:.3f}" for s in sources])

    def _format_charges_for_display(self, charges):
        """Formatea cargas para mostrar en la UI"""
        if charges is None:
            return ""
        return ",".join([f"{c:.3f}" for c in charges])

    def _parse_sources_string(self, sources_str):
        """Parsea string de fuentes"""
        if ';' in sources_str:
            source_groups = sources_str.split(';')
            sources = []
            for group in source_groups:
                coords = [float(x.strip()) for x in group.split(',')]
                if len(coords) == 3:
                    sources.append(coords)
            return np.array(sources)
        else:
            coords = [float(x.strip()) for x in sources_str.split(',')]
            if len(coords) == 3:
                return np.array([coords])
            else:
                raise ValueError("Formato de fuentes incorrecto")

    def _parse_charges_string(self, charges_str):
        """Parsea string de cargas"""
        if ';' in charges_str or ',' in charges_str:
            separator = ';' if ';' in charges_str else ','
            return np.array([float(x.strip()) for x in charges_str.split(separator)])
        else:
            return np.array([float(charges_str)])

    def _handle_ui_update(self, data):
        """Maneja actualizaciones de UI"""
        if data['type'] == 'mesh_loaded':
            self.mesh = data['mesh']
            self.mio = data['mio']
            self.tris = data['tris']
            self.mesh_analysis = data.get('analysis')
            
            self.progress_var.set(100)
            
            # Actualizar información del archivo
            self.file_info.config(state=tk.NORMAL)
            self.file_info.delete(1.0, tk.END)
            
            info_text = f"""📄 {os.path.basename(data['file_path'])}
📊 Nodos: {self.mesh.p.shape[1]:,}
🔺 Elementos: {self.mesh.t.shape[1]:,}
📏 Límites:
   X: [{self.mesh.p[0].min():.3f}, {self.mesh.p[0].max():.3f}]
   Y: [{self.mesh.p[1].min():.3f}, {self.mesh.p[1].max():.3f}]
   Z: [{self.mesh.p[2].min():.3f}, {self.mesh.p[2].max():.3f}]"""
            
            self.file_info.insert(1.0, info_text)
            self.file_info.config(state=tk.DISABLED)
            
            # Actualizar análisis automático
            if self.mesh_analysis:
                self.analysis_info.config(state=tk.NORMAL)
                self.analysis_info.delete(1.0, tk.END)
                
                analysis_text = f"""ANÁLISIS DE MALLA COMPLETADO

Complejidad: {self.mesh_analysis['complexity'].upper()}
Fuentes óptimas: {self.mesh_analysis['optimal_sources']}
Dimensiones: {self.mesh_analysis['dimensions'][0]:.3f} × {self.mesh_analysis['dimensions'][1]:.3f} × {self.mesh_analysis['dimensions'][2]:.3f}
Volumen estimado: {self.mesh_analysis['volume_estimate']:.6f}

PARÁMETROS AUTOMÁTICOS:
• {len(self.auto_sources)} fuentes detectadas
• Cargas balanceadas automáticamente
• Distribución espacial optimizada

Listo para resolución automática"""
                
                self.analysis_info.insert(1.0, analysis_text)
                self.analysis_info.config(state=tk.DISABLED)
            
            # Habilitar botones
            self.preview_button.config(state=tk.NORMAL)
            self.auto_solve_button.config(state=tk.NORMAL)
            self.manual_solve_button.config(state=tk.NORMAL)
            
            self.status_var.set("Archivo cargado - Parámetros automáticos calculados")
            self.progress_var.set(0)
            
            # ¡RESOLUCIÓN AUTOMÁTICA INMEDIATA!
            self.root.after(1000, self.auto_solve)  # Resolver automáticamente después de 1 segundo
            
        elif data['type'] == 'preview_ready':
            self._show_visualization(data['figure'])
            
        elif data['type'] == 'solution_ready':
            self._show_visualization(data['figure'])
            
            # Mostrar información de la solución
            sources_info = "Fuentes utilizadas (proyectadas al interior):\n"
            for i, source in enumerate(data['sources']):
                sources_info += f"  {i+1}: ({source[0]:.3f}, {source[1]:.3f}, {source[2]:.3f})\n"
            
            messagebox.showinfo("Solución Automática Completada", 
                              f"Ecuación de Poisson resuelta automáticamente!\n\n{sources_info}")
            
            self.status_var.set("Solución automática completada exitosamente")

    def _handle_error(self, error_msg):
        """Maneja errores de forma segura"""
        messagebox.showerror("Error", error_msg)
        self.status_var.set("Error en operación")
        self.progress_var.set(0)
        self.preview_button.config(state=tk.DISABLED)
        self.solve_button.config(state=tk.DISABLED)

    def preview_mesh(self):
        """Muestra vista previa de la malla"""
        if not self.mesh:
            return
            
        self.status_var.set("Generando vista previa...")
        self.progress_var.set(30)
        
        self.task_queue.put(('preview', None))

    def _handle_preview(self):
        """Maneja la vista previa de forma segura"""
        def preview_in_background():
            try:
                # Crear figura para vista previa
                fig = Figure(figsize=(8, 6), dpi=80)
                ax = fig.add_subplot(111, projection='3d')
                
                X = self.mesh.p.T
                
                # Mostrar solo superficie con colores por altura
                colors = X[:, 2]  # Color por coordenada Z
                surf = ax.plot_trisurf(X[:, 0], X[:, 1], X[:, 2], 
                                     triangles=self.tris, alpha=0.8,
                                     cmap='viridis', linewidth=0.1)
                surf.set_array(colors[self.tris].mean(axis=1))
                
                ax.set_title("Vista Previa de la Malla", fontsize=12, fontweight='bold')
                ax.set_xlabel("X")
                ax.set_ylabel("Y") 
                ax.set_zlabel("Z")
                ax.view_init(elev=25, azim=45)
                
                fig.colorbar(surf, ax=ax, shrink=0.6, label="Altura (Z)")
                fig.tight_layout()
                
                # Enviar figura de vuelta
                self.task_queue.put(('update_ui', {
                    'type': 'preview_ready',
                    'figure': fig
                }))
                
            except Exception as e:
                self.task_queue.put(('show_error', f"Error en vista previa: {e}"))
        
        thread = threading.Thread(target=preview_in_background, daemon=True)
        thread.start()

    def solve_and_plot(self):
        """Método legacy - redirige a resolución automática"""
        self.auto_solve()

    def _handle_solve(self):
        """Método legacy - redirige a resolución automática"""
        self._handle_solve_auto()

    def parse_sources_and_charges(self):
        """Retorna parámetros automáticos calculados"""
        if self.auto_sources is not None and self.auto_charges is not None:
            return self.auto_sources, self.auto_charges
        else:
            # Fallback a valores por defecto
            return np.array([[0.0, 0.0, 0.0]]), np.array([1.0])

    def _show_visualization(self, fig):
        """Muestra visualización en la UI"""
        self._clear_plot_area()
        
        canvas = FigureCanvasTkAgg(fig, self.plot_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        self.status_var.set("Visualización completada")
        self.progress_var.set(0)

    def _clear_plot_area(self):
        """Limpia el área de visualización"""
        for widget in self.plot_frame.winfo_children():
            widget.destroy()
        
        if hasattr(self, 'placeholder'):
            try:
                self.placeholder.destroy()
            except:
                pass