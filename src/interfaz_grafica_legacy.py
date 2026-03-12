# -*- coding: utf-8 -*-
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
    print("Nota: tkinterdnd2 no esta disponible. Drag & Drop deshabilitado.")

# Importar funciones del modulo core
from .nucleo_poisson import load_mesh_skfem, extract_surface_tris, solve_poisson_point, plot_surface

# Importar visualización de mallas
from .visualization.visor_mallas_3d import crear_figura_3d

# Importar generador de modelos
try:
    from .generador_modelos_anatomicos import generate_mesh, get_preview_data, HAS_GMSH
except ImportError:
    HAS_GMSH = False
    print("Advertencia: No se pudo importar generador_modelos_anatomicos")


def auto_detect_sources(mesh, num_sources=3):
    """
    Detecta automaticamente puntos optimos para fuentes de Poisson.
    
    Args:
        mesh: Malla scikit-fem
        num_sources: Numero de fuentes a generar
        
    Returns:
        tuple: (sources, charges) arrays con fuentes y cargas automaticas
    """
    # Obtener limites de la malla
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
    
    # Estrategias de colocacion de fuentes
    if num_sources == 1:
        # Una fuente en el centro
        sources = np.array([center])
        charges = np.array([1.0])
        
    elif num_sources == 2:
        # Dipolo a lo largo del eje mas largo
        max_dim_idx = np.argmax(dimensions)
        offset = np.zeros(3)
        offset[max_dim_idx] = dimensions[max_dim_idx] * 0.3
        
        sources = np.array([
            center + offset,
            center - offset
        ])
        charges = np.array([1.0, -1.0])
        
    elif num_sources == 3:
        # Configuracion triangular en el plano XY
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
        # Configuracion distribuida dentro de una region pequena del centro
        # Usar el centro de la malla como punto de partida
        # Las fuentes deben estar MUY cerca del centro para asegurar que esten dentro
        
        # Radio muy pequeno para mantener fuentes cerca del centro
        radio = min(dimensions) * 0.05  # 5% de la dimension minima
        
        # Distribucion tetraedrica compacta alrededor del centro
        offsets = np.array([
            [radio, 0, radio * 0.5],           # Fuente 1: adelante-arriba
            [-radio, 0, -radio * 0.5],         # Fuente 2: atras-abajo
            [0, radio, 0],                      # Fuente 3: derecha
            [0, -radio, radio * 0.3]           # Fuente 4: izquierda-arriba
        ])
        
        sources = center + offsets
        charges = np.array([1.0, -0.8, 0.6, -0.4])
        
        print(f"\n=== GENERANDO 4 FUENTES ===")
        print(f"Centro de la malla: ({center[0]:.4f}, {center[1]:.4f}, {center[2]:.4f})")
        print(f"Radio usado: {radio:.4f} m")
        for i, (s, c) in enumerate(zip(sources, charges)):
            print(f"Fuente {i+1}: ({s[0]:.4f}, {s[1]:.4f}, {s[2]:.4f}), carga {c:.2f}")
        print("=" * 40 + "\n")
        
    else:
        # Para mas fuentes, distribucion aleatoria estratificada
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
            
            # Agregar variacion aleatoria pequeña
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
    Analiza la complejidad de la malla para determinar parametros automaticos.
    
    Args:
        mesh: Malla scikit-fem
        
    Returns:
        dict: Informacion sobre la complejidad de la malla
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
    
    # Determinar numero optimo de fuentes basado en complejidad
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
    Version automatica de la aplicacion ECG que detecta y resuelve automaticamente.
    
    Caracteristicas automaticas:
    - Deteccion automatica de fuentes optimas
    - Calculo automatico de cargas
    - Resolucion inmediata despues de cargar archivo
    - Analisis de complejidad de malla
    """
    
    def __init__(self, root=None):
        # Importar tkinter al inicio
        import tkinter as tk
        
        # Crear ventana principal si no se proporciona una
        if root is None:
            # Intentar usar TkinterDnD si esta disponible
            if HAS_DND:
                try:
                    self.root = TkinterDnD.Tk()
                except Exception:
                    self.root = tk.Tk()
                    print("Nota: Error inicializando TkinterDnD, usando Tkinter estandar")
            else:
                self.root = tk.Tk()
                print("Nota: Drag & Drop no disponible. Instala tkinterdnd2 para esta funcionalidad.")
        else:
            # Usar la ventana proporcionada
            self.root = root
            
        self.root.title("Solucionador ECG (Automático)")
        self.root.geometry("1200x800")
        self.root.configure(bg='#f0f0f0')

        # Variables de estado
        self.file_path = None
        self.mesh = None
        self.mio = None
        self.tris = None
        self.current_solution = None
        self.mesh_analysis = None
        
        # Bandera para controlar resolucion automatica
        self.skip_auto_solve = False
        
        # Bandera para rastrear si el modelo fue generado automáticamente
        self.is_auto_generated = False
        self.auto_generated_with_lungs = False
        
        # Variables para parametros automaticos
        self.auto_sources = None
        self.auto_charges = None
        
        # Variables para progreso
        self.progress_var = tk.DoubleVar()
        self.status_var = tk.StringVar(value="Listo - Soporta VTK, Gmsh, STL, OBJ, PLY y mas formatos")
        
        # Queue para comunicacion segura entre hilos
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
        
        # Panel derecho - Visualizacion
        right_panel = tk.Frame(main_frame, bg='white', relief=tk.RAISED, bd=2)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        self.create_control_panel(left_panel)
        self.create_visualization_panel(right_panel)

    def create_control_panel(self, parent):
        """Crea el panel de controles para la version automatica."""
        # Titulo
        title_label = tk.Label(parent, text="Solucionador ECG\n(Automatico)", 
                              font=("Arial", 18, "bold"), bg='white', fg='#2c3e50')
        title_label.pack(pady=15)

        # Seccion de carga de archivo
        file_section = tk.LabelFrame(parent, text="Archivo de Malla", font=("Arial", 12, "bold"),
                                   bg='white', fg='#34495e', padx=10, pady=10)
        file_section.pack(fill=tk.X, padx=15, pady=10)

        # Zona de drag & drop
        self.drop_frame = tk.Frame(file_section, bg='#ecf0f1', relief='solid', bd=2, height=80)
        self.drop_frame.pack(fill=tk.X, pady=5)
        self.drop_frame.pack_propagate(False)
        
        if HAS_DND:
            drop_text = "Arrastra aqui tu archivo de malla\n(.vtk, .msh, .vtu, .stl, .obj, etc.)"
        else:
            drop_text = "Haz clic para seleccionar archivo de malla\n(.vtk, .msh, .vtu, .stl, .obj, etc.)"
            
        drop_label = tk.Label(self.drop_frame, text=drop_text, 
                             font=("Arial", 10), bg='#ecf0f1', fg='#7f8c8d')
        drop_label.pack(expand=True)
        
        # Boton de seleccion manual
        self.file_button = tk.Button(file_section, text="Seleccionar archivo de malla", 
                                   command=self.load_file, font=("Arial", 10),
                                   bg='#3498db', fg='white', relief=tk.FLAT, padx=20)
        self.file_button.pack(pady=5)
        
        # Separador
        separator = tk.Frame(file_section, height=2, bg='#ecf0f1')
        separator.pack(fill=tk.X, pady=10)
        
        # Boton de modelo automatico
        if HAS_GMSH:
            auto_model_button = tk.Button(file_section, text="Generar Modelo Automatico", 
                                        command=self.show_auto_model_dialog, 
                                        font=("Arial", 10, "bold"),
                                        bg='#27ae60', fg='white', relief=tk.FLAT, padx=20)
            auto_model_button.pack(pady=5)
            
            auto_label = tk.Label(file_section, 
                                text="Genera modelo de torso con corazon y pulmones",
                                font=("Arial", 8), bg='white', fg='#7f8c8d')
            auto_label.pack(pady=(0, 5))
        
        # Informacion del archivo
        self.file_info = tk.Text(file_section, height=6, font=("Consolas", 9), 
                               bg='#f8f9fa', state=tk.DISABLED)
        self.file_info.pack(fill=tk.X, pady=5)

        # Seccion de analisis automatico
        analysis_section = tk.LabelFrame(parent, text="Analisis Automatico", 
                                       font=("Arial", 12, "bold"), bg='white', fg='#34495e',
                                       padx=10, pady=10)
        analysis_section.pack(fill=tk.X, padx=15, pady=10)

        # Informacion de analisis
        self.analysis_info = tk.Text(analysis_section, height=8, font=("Consolas", 9), 
                                   bg='#f8f9fa', state=tk.DISABLED)
        self.analysis_info.pack(fill=tk.X, pady=5)
        
        # Informacion inicial
        self.analysis_info.config(state=tk.NORMAL)
        self.analysis_info.insert(1.0, """MODO AUTOMATICO ACTIVADO

Caracteristicas automaticas:
• Deteccion inteligente de fuentes optimas
• Calculo automatico de cargas balanceadas
• Resolucion inmediata tras cargar archivo
• Analisis de complejidad de malla

Simplemente carga un archivo VTK y la
aplicacion resolvera automaticamente la
ecuacion de Poisson con parametros optimos.""")
        self.analysis_info.config(state=tk.DISABLED)

        # Botones de accion
        action_frame = tk.Frame(parent, bg='white')
        action_frame.pack(fill=tk.X, padx=15, pady=20)
        
        self.preview_button = tk.Button(action_frame, text="Vista Previa", 
                                      command=self.preview_mesh, state=tk.DISABLED,
                                      font=("Arial", 11), bg='#f39c12', fg='white', 
                                      relief=tk.FLAT, padx=20, pady=8)
        self.preview_button.pack(fill=tk.X, pady=2)
        
        self.auto_solve_button = tk.Button(action_frame, text="Resolver Automaticamente", 
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
        """Crea el panel de visualizacion."""
        # Titulo del panel
        viz_title = tk.Label(parent, text="Visualizacion 3D", font=("Arial", 14, "bold"),
                           bg='white', fg='#2c3e50')
        viz_title.pack(pady=10)
        
        # Frame para matplotlib
        self.plot_frame = tk.Frame(parent, bg='white')
        self.plot_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Placeholder inicial
        self.create_placeholder()

    def create_placeholder(self):
        """Crea un placeholder inicial para el area de visualizacion."""
        placeholder = tk.Label(self.plot_frame, 
                             text="Carga un archivo VTK para comenzar\nla visualizacion y resolucion",
                             font=("Arial", 14), bg='white', fg='#bdc3c7')
        placeholder.pack(expand=True)
        self.placeholder = placeholder

    def setup_drag_drop(self):
        """Configura drag & drop para archivos VTK (solo si esta disponible)"""
        if not HAS_DND:
            # Si no hay DND, hacer el frame clickeable
            self.drop_frame.bind("<Button-1>", lambda e: self.load_file())
            return
            
        try:
            self.drop_frame.drop_target_register(DND_FILES)
            self.drop_frame.dnd_bind('<<Drop>>', self.on_drop)
            
            # Hacer el frame clickeable tambien
            self.drop_frame.bind("<Button-1>", lambda e: self.load_file())
            
        except Exception as e:
            print(f"Error configurando Drag & Drop: {e}")
            # Fallback: hacer clickeable
            self.drop_frame.bind("<Button-1>", lambda e: self.load_file())

    def on_drop(self, event):
        """Maneja archivos arrastrados (solo si DND esta disponible)"""
        if not HAS_DND:
            return
            
        files = self.root.tk.splitlist(event.data)
        if files:
            file_path = files[0]
            # Lista de extensiones soportadas
            supported_extensions = (
                '.vtk', '.vtu', '.msh', '.mesh', '.stl', '.obj', '.ply', '.off',
                '.inp', '.nas', '.bdf', '.fem', '.e', '.exo', '.med', '.xdmf'
            )
            if file_path.lower().endswith(supported_extensions):
                self.process_file(file_path)
            else:
                messagebox.showerror("Error", 
                    "Formato no soportado.\n\n"
                    "Formatos aceptados:\n"
                    "VTK (.vtk, .vtu), Gmsh (.msh), Medit (.mesh),\n"
                    "STL (.stl), OBJ (.obj), PLY (.ply), OFF (.off),\n"
                    "Abaqus (.inp), Nastran (.nas, .bdf), y mas.")

    def load_file(self):
        """Carga archivo mediante dialogo"""
        file_path = filedialog.askopenfilename(
            title="Seleccionar archivo de malla",
            filetypes=[
                ("Todos los formatos soportados", "*.vtk *.vtu *.msh *.mesh *.stl *.obj *.ply *.off"),
                ("VTK Legacy", "*.vtk"),
                ("VTK XML", "*.vtu"),
                ("Gmsh", "*.msh"),
                ("Medit", "*.mesh"),
                ("STL", "*.stl"),
                ("Wavefront OBJ", "*.obj"),
                ("PLY", "*.ply"),
                ("OFF", "*.off"),
                ("Todos los archivos", "*.*")
            ]
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
        
        # Programar siguiente verificacion
        self.root.after(100, self.process_queue)

    def _handle_load_mesh(self, file_path):
        """Maneja la carga de malla de forma segura con analisis automatico"""
        def load_in_background():
            try:
                mesh, mio = load_mesh_skfem(file_path)
                tris = extract_surface_tris(mio, mesh)
                
                # Analisis automatico de la malla
                analysis = analyze_mesh_complexity(mesh)
                
                # Detectar fuentes y cargas automaticamente
                sources, charges = auto_detect_sources(mesh, analysis['optimal_sources'])
                
                # Guardar parametros automaticos
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
        """Resuelve automaticamente con parametros detectados"""
        if not self.mesh or self.auto_sources is None:
            return
            
        self.status_var.set("Resolviendo automaticamente...")
        self.progress_var.set(20)
        
        self.task_queue.put(('solve_auto', None))

    def _handle_solve_auto(self):
        """Maneja la resolucion automatica"""
        def solve_in_background():
            try:
                # Mostrar coordenadas de fuentes antes de resolver
                print("\n=== ELECTRODOS CONFIGURADOS ===")
                for i, (source, charge) in enumerate(zip(self.auto_sources, self.auto_charges)):
                    print(f"Electrodo {i+1}: posición ({source[0]:.4f}, {source[1]:.4f}, {source[2]:.4f}), carga {charge:.2f}")
                
                # Resolver con parametros automaticos
                basis, V, used_sources = solve_poisson_point(self.mesh, self.auto_sources, self.auto_charges)
                
                # Mostrar coordenadas de fuentes proyectadas (usadas realmente)
                print("\n=== ELECTRODOS PROYECTADOS (USADOS) ===")
                for i, source in enumerate(used_sources):
                    print(f"Electrodo {i+1}: posición ({source[0]:.4f}, {source[1]:.4f}, {source[2]:.4f})")
                print("=" * 40 + "\n")
                
                # Crear visualización con modelo completo
                fig = plot_surface(self.mesh, self.tris, V, sources=used_sources, 
                                 title="Solucion Automatica de Poisson 3D",
                                 mio=self.mio)
                
                # Enviar resultado
                self.task_queue.put(('update_ui', {
                    'type': 'solution_ready',
                    'figure': fig,
                    'sources': used_sources,
                    'solution': V
                }))
                
            except Exception as e:
                self.task_queue.put(('show_error', f"Error en resolucion automatica: {e}"))
        
        thread = threading.Thread(target=solve_in_background, daemon=True)
        thread.start()

    def show_manual_options(self):
        """Muestra opciones para resolucion manual"""
        if not self.mesh:
            return
        
        # Crear ventana de opciones manuales
        manual_window = tk.Toplevel(self.root)
        manual_window.title("Opciones Manuales")
        manual_window.geometry("400x300")
        manual_window.configure(bg='white')
        
        # Titulo
        title = tk.Label(manual_window, text="Configuracion Manual", 
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
                # Parsear parametros manuales
                sources = self._parse_sources_string(sources_var.get())
                charges = self._parse_charges_string(charges_var.get())
                
                # Guardar parametros manuales
                self.auto_sources = sources
                self.auto_charges = charges
                
                manual_window.destroy()
                self.auto_solve()
                
            except Exception as e:
                messagebox.showerror("Error", f"Error en parametros: {e}")
        
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
            
            # Resetear banderas de modelo auto-generado si se carga un archivo normal
            if not self.skip_auto_solve:
                self.is_auto_generated = False
                self.auto_generated_with_lungs = False
            
            self.progress_var.set(100)
            
            # Actualizar informacion del archivo
            self.file_info.config(state=tk.NORMAL)
            self.file_info.delete(1.0, tk.END)
            
            info_text = f""" {os.path.basename(data['file_path'])}
    Nodos: {self.mesh.p.shape[1]:,}
    Elementos: {self.mesh.t.shape[1]:,}
    Limites:
   X: [{self.mesh.p[0].min():.3f}, {self.mesh.p[0].max():.3f}]
   Y: [{self.mesh.p[1].min():.3f}, {self.mesh.p[1].max():.3f}]
   Z: [{self.mesh.p[2].min():.3f}, {self.mesh.p[2].max():.3f}]"""
            
            self.file_info.insert(1.0, info_text)
            self.file_info.config(state=tk.DISABLED)
            
            # Actualizar analisis automatico
            if self.mesh_analysis:
                self.analysis_info.config(state=tk.NORMAL)
                self.analysis_info.delete(1.0, tk.END)
                
                analysis_text = f"""ANALISIS DE MALLA COMPLETADO

Complejidad: {self.mesh_analysis['complexity'].upper()}
Fuentes optimas: {self.mesh_analysis['optimal_sources']}
Dimensiones: {self.mesh_analysis['dimensions'][0]:.3f} o— {self.mesh_analysis['dimensions'][1]:.3f} o— {self.mesh_analysis['dimensions'][2]:.3f}
Volumen estimado: {self.mesh_analysis['volume_estimate']:.6f}

PARAMETROS AUTOMoTICOS:
    {len(self.auto_sources)} fuentes detectadas
    Cargas balanceadas automaticamente
    Distribucion espacial optimizada

Listo para resolucion automatica"""
                
                self.analysis_info.insert(1.0, analysis_text)
                self.analysis_info.config(state=tk.DISABLED)
            
            # Habilitar botones
            self.preview_button.config(state=tk.NORMAL)
            self.auto_solve_button.config(state=tk.NORMAL)
            self.manual_solve_button.config(state=tk.NORMAL)
            
            self.status_var.set("Archivo cargado - Parametros automaticos calculados")
            self.progress_var.set(0)
            
            # RESOLUCIo“N AUTOMoTICA INMEDIATA! (solo si no se debe saltar)
            if not self.skip_auto_solve:
                self.root.after(1000, self.auto_solve)  # Resolver automaticamente despues de 1 segundo
            else:
                # Resetear la bandera
                self.skip_auto_solve = False
            
        elif data['type'] == 'preview_ready':
            self._show_visualization(data['figure'])
            
        elif data['type'] == 'solution_ready':
            self._show_visualization(data['figure'])
            
            # Mostrar informacion de la solucion
            sources_info = "Fuentes utilizadas (proyectadas al interior):\n"
            for i, source in enumerate(data['sources']):
                sources_info += f"  {i+1}: ({source[0]:.3f}, {source[1]:.3f}, {source[2]:.3f})\n"
            
            messagebox.showinfo("Solucion Automatica Completada", 
                              f"Ecuacion de Poisson resuelta automaticamente!\n\n{sources_info}")
            
            self.status_var.set("Solucion automatica completada exitosamente")

    def _handle_error(self, error_msg):
        """Maneja errores de forma segura"""
        messagebox.showerror("Error", error_msg)
        self.status_var.set("Error en operacion")
        self.progress_var.set(0)
        self.preview_button.config(state=tk.DISABLED)
        self.solve_button.config(state=tk.DISABLED)

    def preview_mesh(self):
        """Muestra vista previa de la malla"""
        if not self.mesh:
            return
        
        # Si el modelo fue generado automáticamente, mostrar vista interactiva
        if self.is_auto_generated:
            self.show_model_in_main_panel(self.auto_generated_with_lungs)
            return
            
        self.status_var.set("Generando vista previa...")
        self.progress_var.set(30)
        
        self.task_queue.put(('preview', None))

    def _handle_preview(self):
        """Maneja la vista previa de forma segura"""
        def preview_in_background():
            try:
                # Usar visualización completa del modelo si tiene materiales
                if self.mio is not None:
                    try:
                        fig = crear_figura_3d(self.mesh, self.mio, incluir_pulmones=True)
                        # Cambiar título
                        ax = fig.axes[0]
                        ax.set_title("Vista Previa de la Malla", fontsize=12, fontweight='bold')
                    except Exception as e:
                        print(f"Error usando crear_figura_3d: {e}")
                        # Fallback a visualización simple
                        fig = Figure(figsize=(8, 6), dpi=80)
                        ax = fig.add_subplot(111, projection='3d')
                        
                        X = self.mesh.p.T
                        colors = X[:, 2]
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
                else:
                    # Visualización simple para archivos sin materiales
                    fig = Figure(figsize=(8, 6), dpi=80)
                    ax = fig.add_subplot(111, projection='3d')
                    
                    X = self.mesh.p.T
                    colors = X[:, 2]
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
        """Metodo legacy - redirige a resolucion automatica"""
        self.auto_solve()

    def _handle_solve(self):
        """Metodo legacy - redirige a resolucion automatica"""
        self._handle_solve_auto()

    def parse_sources_and_charges(self):
        """Retorna parametros automaticos calculados"""
        if self.auto_sources is not None and self.auto_charges is not None:
            return self.auto_sources, self.auto_charges
        else:
            # Fallback a valores por defecto
            return np.array([[0.0, 0.0, 0.0]]), np.array([1.0])

    def _show_visualization(self, fig):
        """Muestra visualizacion en la UI con controles interactivos"""
        self._clear_plot_area()
        
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
        
        # Crear canvas
        canvas = FigureCanvasTkAgg(fig, self.plot_frame)
        
        # Toolbar para zoom, pan, rotar
        toolbar_frame = tk.Frame(self.plot_frame, bg='white')
        toolbar_frame.pack(side=tk.TOP, fill=tk.X)
        
        toolbar = NavigationToolbar2Tk(canvas, toolbar_frame)
        toolbar.update()
        
        # Frame de controles adicionales
        controls_frame = tk.Frame(self.plot_frame, bg='#f0f0f0', relief=tk.RAISED, bd=1)
        controls_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        tk.Label(controls_frame, text="🎮 Controles:", 
                font=("Arial", 9, "bold"), bg='#f0f0f0').pack(side=tk.LEFT, padx=5)
        
        # Obtener el axes 3D
        ax = fig.axes[0] if fig.axes else None
        
        if ax is not None:
            # Botones de vista
            def set_view(elev, azim):
                ax.view_init(elev=elev, azim=azim)
                canvas.draw()
            
            tk.Button(controls_frame, text="Vista Frontal", 
                     command=lambda: set_view(0, 0),
                     font=("Arial", 8), bg='#3498db', fg='white', 
                     relief=tk.FLAT, padx=8, pady=3).pack(side=tk.LEFT, padx=2)
            
            tk.Button(controls_frame, text="Vista Superior", 
                     command=lambda: set_view(90, 0),
                     font=("Arial", 8), bg='#3498db', fg='white', 
                     relief=tk.FLAT, padx=8, pady=3).pack(side=tk.LEFT, padx=2)
            
            tk.Button(controls_frame, text="Vista Lateral", 
                     command=lambda: set_view(0, 90),
                     font=("Arial", 8), bg='#3498db', fg='white', 
                     relief=tk.FLAT, padx=8, pady=3).pack(side=tk.LEFT, padx=2)
            
            tk.Button(controls_frame, text="Vista 3D", 
                     command=lambda: set_view(25, 45),
                     font=("Arial", 8), bg='#2ecc71', fg='white', 
                     relief=tk.FLAT, padx=8, pady=3).pack(side=tk.LEFT, padx=2)
            
            # Separador
            tk.Frame(controls_frame, width=2, bg='#bdc3c7').pack(side=tk.LEFT, fill=tk.Y, padx=5)
            
            # Controles de zoom
            tk.Label(controls_frame, text="Zoom:", 
                    font=("Arial", 8), bg='#f0f0f0').pack(side=tk.LEFT, padx=5)
            
            def zoom_in():
                xlim = ax.get_xlim()
                ylim = ax.get_ylim()
                zlim = ax.get_zlim()
                
                x_center = (xlim[0] + xlim[1]) / 2
                y_center = (ylim[0] + ylim[1]) / 2
                z_center = (zlim[0] + zlim[1]) / 2
                
                x_range = (xlim[1] - xlim[0]) * 0.8
                y_range = (ylim[1] - ylim[0]) * 0.8
                z_range = (zlim[1] - zlim[0]) * 0.8
                
                ax.set_xlim(x_center - x_range/2, x_center + x_range/2)
                ax.set_ylim(y_center - y_range/2, y_center + y_range/2)
                ax.set_zlim(z_center - z_range/2, z_center + z_range/2)
                canvas.draw()
            
            def zoom_out():
                xlim = ax.get_xlim()
                ylim = ax.get_ylim()
                zlim = ax.get_zlim()
                
                x_center = (xlim[0] + xlim[1]) / 2
                y_center = (ylim[0] + ylim[1]) / 2
                z_center = (zlim[0] + zlim[1]) / 2
                
                x_range = (xlim[1] - xlim[0]) * 1.25
                y_range = (ylim[1] - ylim[0]) * 1.25
                z_range = (zlim[1] - zlim[0]) * 1.25
                
                ax.set_xlim(x_center - x_range/2, x_center + x_range/2)
                ax.set_ylim(y_center - y_range/2, y_center + y_range/2)
                ax.set_zlim(z_center - z_range/2, z_center + z_range/2)
                canvas.draw()
            
            def reset_view():
                ax.autoscale()
                ax.view_init(elev=25, azim=45)
                canvas.draw()
            
            tk.Button(controls_frame, text="Z+", 
                     command=zoom_in,
                     font=("Arial", 8, "bold"), bg='#27ae60', fg='white', 
                     relief=tk.FLAT, padx=8, pady=3).pack(side=tk.LEFT, padx=2)
            
            tk.Button(controls_frame, text="Z-", 
                     command=zoom_out,
                     font=("Arial", 8, "bold"), bg='#e67e22', fg='white', 
                     relief=tk.FLAT, padx=8, pady=3).pack(side=tk.LEFT, padx=2)
            
            tk.Button(controls_frame, text="↻ Reset", 
                     command=reset_view,
                     font=("Arial", 8), bg='#95a5a6', fg='white', 
                     relief=tk.FLAT, padx=8, pady=3).pack(side=tk.LEFT, padx=2)
        
        # Mostrar canvas
        canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        canvas.draw()
        
        self.status_var.set("Visualizacion completada")
        self.progress_var.set(0)

    def _clear_plot_area(self):
        """Limpia el area de visualizacion"""
        for widget in self.plot_frame.winfo_children():
            widget.destroy()
        
        if hasattr(self, 'placeholder'):
            try:
                self.placeholder.destroy()
            except:
                pass

    def show_auto_model_dialog(self):
        """Muestra dialogo para generar modelo automatico"""
        if not HAS_GMSH:
            messagebox.showerror("Error", 
                "Gmsh no esta instalado.\n\n"
                "Para usar esta funcionalidad, instala gmsh:\n"
                "pip install gmsh")
            return
        
        # Crear ventana de dialogo
        dialog = tk.Toplevel(self.root)
        dialog.title("Generar Modelo Automatico")
        dialog.geometry("550x500")
        dialog.configure(bg='white')
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)
        
        # Titulo
        title = tk.Label(dialog, text=" Generador de Modelo de Torso", 
                        font=("Arial", 16, "bold"), bg='white', fg='#2c3e50')
        title.pack(pady=15)
        
        # Descripcion
        desc = tk.Label(dialog, 
                       text="Genera un modelo 3D de torso con corazon opcionalmente pulmones",
                       font=("Arial", 10), bg='white', fg='#7f8c8d')
        desc.pack(pady=5)
        
        # Frame de opciones
        options_frame = tk.LabelFrame(dialog, text="Configuracion del Modelo", 
                                     font=("Arial", 11, "bold"), bg='white', 
                                     fg='#34495e', padx=20, pady=15)
        options_frame.pack(fill=tk.X, padx=20, pady=15)
        
        # Variable para opcion de pulmones
        lungs_var = tk.BooleanVar(value=True)
        
        # Radio buttons
        tk.Label(options_frame, text="Tipo de modelo:", 
                font=("Arial", 10, "bold"), bg='white').pack(anchor=tk.W, pady=(0, 5))
        
        with_lungs = tk.Radiobutton(options_frame, text="Con pulmones (modelo completo)", 
                                   variable=lungs_var, value=True,
                                   font=("Arial", 10), bg='white', 
                                   activebackground='white')
        with_lungs.pack(anchor=tk.W, pady=2)
        
        without_lungs = tk.Radiobutton(options_frame, text="Sin pulmones (solo torso y corazon)", 
                                      variable=lungs_var, value=False,
                                      font=("Arial", 10), bg='white',
                                      activebackground='white')
        without_lungs.pack(anchor=tk.W, pady=2)
        
        # Nombre del archivo
        tk.Label(options_frame, text="Nombre del archivo:", 
                font=("Arial", 10, "bold"), bg='white').pack(anchor=tk.W, pady=(15, 5))
        
        filename_frame = tk.Frame(options_frame, bg='white')
        filename_frame.pack(fill=tk.X, pady=5)
        
        filename_var = tk.StringVar(value="mi_modelo_torso")
        filename_entry = tk.Entry(filename_frame, textvariable=filename_var, 
                                 font=("Arial", 10), width=30)
        filename_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        tk.Label(filename_frame, text=".msh", font=("Arial", 10), 
                bg='white', fg='#7f8c8d').pack(side=tk.LEFT, padx=(5, 0))
        
        # Informacion del modelo
        info_text = tk.Text(options_frame, height=5, font=("Consolas", 8), 
                          bg='#f8f9fa', state=tk.DISABLED, wrap=tk.WORD, bd=0)
        info_text.pack(fill=tk.X, pady=(10, 0))
        
        info_text.config(state=tk.NORMAL)
        info_text.insert(1.0, """Caracteristicas:
    Torso: cilindro (15cm o— 50cm)
    Corazon: esfera (5cm)
    Pulmones: elipsoides (4o—6o—9 cm)
    Conductividades realistas
    Tiempo: 1-2 minutos""")
        info_text.config(state=tk.DISABLED)
        
        # Separador
        separator = tk.Frame(dialog, height=2, bg='#ecf0f1')
        separator.pack(fill=tk.X, padx=20, pady=10)
        
        # Frame de botones con mejor espaciado
        button_frame = tk.Frame(dialog, bg='white')
        button_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 15), padx=30)
        
        def generate_and_preview():
            """Genera la malla y muestra vista previa en el panel principal"""
            try:
                include_lungs = lungs_var.get()
                filename = filename_var.get().strip()
                
                # Validar nombre de archivo
                if not filename:
                    messagebox.showerror("Error", "Debes especificar un nombre para el archivo")
                    return
                
                # Limpiar nombre de archivo
                import re
                filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
                
                # Cerrar dialogo
                dialog.destroy()
                
                # Determinar ruta de salida
                output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
                os.makedirs(output_dir, exist_ok=True)
                
                output_path = os.path.join(output_dir, f"{filename}.msh")
                
                # Actualizar estado
                self.status_var.set("Generando modelo automatico...")
                self.progress_var.set(10)
                self.root.update()
                
                # Deshabilitar botones durante generacion
                self.file_button.config(state=tk.DISABLED)
                self.preview_button.config(state=tk.DISABLED)
                self.auto_solve_button.config(state=tk.DISABLED)
                self.manual_solve_button.config(state=tk.DISABLED)
                
                # Generar en el hilo principal (Gmsh requiere main thread en Windows)
                try:
                    self.status_var.set("Generando geometria y malla (puede tardar 1-2 minutos)...")
                    self.progress_var.set(30)
                    self.root.update()
                    
                    generated_file = generate_mesh(
                        include_lungs=include_lungs,
                        output_path=output_path,
                        show_gui=False
                    )
                    
                    self.progress_var.set(70)
                    self.root.update()
                    
                    # Cargar el modelo
                    self.status_var.set("Cargando modelo generado...")
                    self.root.update()
                    
                    # Activar bandera para NO resolver automáticamente JUSTO ANTES de cargar
                    self.skip_auto_solve = True
                    
                    # Marcar que el modelo fue generado automáticamente
                    self.is_auto_generated = True
                    self.auto_generated_with_lungs = include_lungs
                    
                    self.process_file(generated_file)
                    
                    # Esperar a que se cargue y mostrar en panel principal (vista estática)
                    self.root.after(500, lambda: self.show_model_static_view(include_lungs))
                    
                except Exception as e:
                    messagebox.showerror("Error", f"Error generando modelo:\n{str(e)}")
                    self.status_var.set("Error en generacion")
                    self.progress_var.set(0)
                    
                    # Rehabilitar botones
                    self.file_button.config(state=tk.NORMAL)
                
            except Exception as e:
                messagebox.showerror("Error", f"Error al iniciar generacion:\n{e}")
        
        # Botones de accion
        generate_btn = tk.Button(button_frame, text="š™ï¸ Generar Modelo", 
                                command=generate_and_preview,
                                font=("Arial", 12, "bold"), bg='#27ae60', fg='white', 
                                relief=tk.FLAT, padx=40, pady=12, cursor='hand2',
                                activebackground='#229954')
        generate_btn.pack(fill=tk.X, pady=(0, 8))
        
        cancel_btn = tk.Button(button_frame, text="Cancelar", 
                              command=dialog.destroy,
                              font=("Arial", 10), bg='#95a5a6', fg='white', 
                              relief=tk.FLAT, padx=30, pady=8, cursor='hand2',
                              activebackground='#7f8c8d')
        cancel_btn.pack(fill=tk.X)

    def _simplify_surface(self, triangles, vertices, target_ratio=0.3):
        """Simplifica una superficie reduciendo el número de triángulos"""
        try:
            # Si hay pocos triángulos, no simplificar
            if len(triangles) < 1000:
                return triangles
            
            # Submuestreo simple: tomar cada N triángulos
            step = max(1, int(1.0 / target_ratio))
            simplified = triangles[::step]
            
            print(f"  Simplificado: {len(triangles)} → {len(simplified)} triángulos")
            return simplified
            
        except Exception as e:
            print(f"  Error simplificando: {e}, usando original")
            return triangles

    def show_model_static_view(self, include_lungs):
        """Muestra el modelo generado en vista estática optimizada (sin interacción)"""
        try:
            # Limpiar el area de visualizacion
            self._clear_plot_area()
            
            # Crear figura 3D estática
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            import matplotlib.pyplot as plt
            from matplotlib.colors import ListedColormap
            from collections import Counter
            
            # Desactivar modo interactivo de matplotlib
            plt.ioff()
            
            # Reducir DPI para mejor rendimiento
            fig = Figure(figsize=(8, 6), dpi=75)
            ax = fig.add_subplot(111, projection='3d')
            
            # Deshabilitar interacción del mouse
            ax.mouse_init = lambda: None
            
            # Obtener datos de la malla
            X = self.mesh.p.T
            
            # Visualizar por materiales con optimización
            try:
                mat_labels = None
                
                if hasattr(self.mio, 'cell_data_dict'):
                    datos = self.mio.cell_data_dict
                    
                    if "gmsh:physical" in datos and "tetra" in datos["gmsh:physical"]:
                        mat_labels = datos["gmsh:physical"]["tetra"].flatten().astype(int)
                    elif mat_labels is None:
                        for clave, bloques in datos.items():
                            if "tetra" in bloques:
                                arr = bloques["tetra"].flatten()
                                vals = np.unique(arr)
                                if len(vals) <= 20 and arr.min() >= 0:
                                    mat_labels = arr.astype(int)
                                    break
                
                if mat_labels is not None and len(mat_labels) > 0:
                    if 'tetra' in self.mio.cells_dict:
                        tetrahedra = self.mio.cells_dict['tetra']
                    else:
                        raise ValueError("No se encontraron tetraedros")
                    
                    colors_map = {
                        4: ('#2ECC71', 'Pulmon der', 0.7),
                        3: ('#F39C12', 'Pulmon izq', 0.7),
                        2: ('#E74C3C', 'Corazon', 0.8),
                        1: ('#5DADE2', 'Torso', 0.3),
                    }
                    
                    surfaces_to_plot = []
                    
                    for material_id in [4, 3, 2, 1]:
                        if material_id not in colors_map:
                            continue
                        
                        if material_id not in np.unique(mat_labels):
                            continue
                        
                        color, name, alpha = colors_map[material_id]
                        material_mask = mat_labels == material_id
                        n_tets = material_mask.sum()
                        
                        if n_tets == 0:
                            continue
                        
                        material_tets = tetrahedra[material_mask]
                        
                        # Optimización: usar set para faces en lugar de lista
                        faces_set = []
                        for tet in material_tets:
                            faces_set.append(tuple(sorted([tet[0], tet[1], tet[2]])))
                            faces_set.append(tuple(sorted([tet[0], tet[1], tet[3]])))
                            faces_set.append(tuple(sorted([tet[0], tet[2], tet[3]])))
                            faces_set.append(tuple(sorted([tet[1], tet[2], tet[3]])))
                        
                        face_counts = Counter(faces_set)
                        surface_faces = [face for face, count in face_counts.items() if count == 1]
                        
                        if len(surface_faces) > 0:
                            surface_tris = np.array(surface_faces)
                            
                            # OPTIMIZACIÓN: Simplificar superficie para vista estática
                            # Torso: reducir más (30%), órganos: reducir menos (50%)
                            ratio = 0.25 if material_id == 1 else 0.4
                            surface_tris = self._simplify_surface(surface_tris, X, ratio)
                            
                            surfaces_to_plot.append({
                                'triangles': surface_tris,
                                'color': color,
                                'alpha': alpha,
                                'name': name
                            })
                    
                    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
                    from matplotlib.colors import to_rgba
                    
                    collections = []
                    legend_handles = []
                    
                    for surf_data in surfaces_to_plot:
                        triangles = surf_data['triangles']
                        verts = []
                        for tri in triangles:
                            verts.append([X[tri[0]], X[tri[1]], X[tri[2]]])
                        
                        rgba_color = to_rgba(surf_data['color'], alpha=surf_data['alpha'])
                        # Optimización: sin bordes en vista estática
                        collection = Poly3DCollection(verts, 
                                                     facecolors=rgba_color,
                                                     edgecolors='none',
                                                     linewidths=0)
                        collections.append(collection)
                        
                        import matplotlib.patches as mpatches
                        legend_handles.append(mpatches.Patch(color=surf_data['color'], 
                                                            alpha=surf_data['alpha'],
                                                            label=surf_data['name']))
                    
                    for collection in collections:
                        ax.add_collection3d(collection)
                    
                    ax.set_xlim(X[:, 0].min(), X[:, 0].max())
                    ax.set_ylim(X[:, 1].min(), X[:, 1].max())
                    ax.set_zlim(X[:, 2].min(), X[:, 2].max())
                    
                    ax.legend(handles=legend_handles, loc='upper right', fontsize=9, 
                             framealpha=0.95, edgecolor='gray', fancybox=True)
                    
                else:
                    raise ValueError("Sin etiquetas")
                    
            except Exception as e:
                colors = X[:, 2]
                surf = ax.plot_trisurf(X[:, 0], X[:, 1], X[:, 2], 
                                     triangles=self.tris, alpha=0.8,
                                     cmap='viridis', linewidth=0, 
                                     edgecolor='none')
                surf.set_array(colors[self.tris].mean(axis=1))
                cbar = fig.colorbar(surf, ax=ax, shrink=0.6, aspect=10)
                cbar.set_label("Altura (Z)", rotation=270, labelpad=15, fontsize=9)
            
            tipo = "sin pulmones" if not include_lungs else "con pulmones"
            ax.set_title(f"Modelo Generado ({tipo})", fontsize=12, fontweight='bold', pad=20)
            ax.set_xlabel("X (m)", fontsize=9)
            ax.set_ylabel("Y (m)", fontsize=9)
            ax.set_zlabel("Z (m)", fontsize=9)
            ax.view_init(elev=25, azim=45)
            ax.set_box_aspect([1,1,1])
            
            # Desactivar grid para mejor rendimiento
            ax.grid(False)
            
            fig.tight_layout()
            
            # Crear canvas SIN toolbar (vista estática)
            canvas = FigureCanvasTkAgg(fig, self.plot_frame)
            canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
            
            # Mensaje informativo
            info_frame = tk.Frame(self.plot_frame, bg='#fffacd', relief=tk.RAISED, bd=2)
            info_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)
            
            tk.Label(info_frame, text="Vista estática del modelo generado. Usa el botón 'Vista Previa' para interactuar con zoom y rotación.", 
                    font=("Arial", 9), bg='#fffacd', fg='#333', wraplength=600, justify=tk.LEFT).pack(padx=10, pady=8)
            
            canvas.draw()
            
            # Actualizar estado
            self.status_var.set("Modelo generado exitosamente")
            self.progress_var.set(100)
            
            # Rehabilitar botones
            self.file_button.config(state=tk.NORMAL)
            self.preview_button.config(state=tk.NORMAL)
            self.auto_solve_button.config(state=tk.NORMAL)
            self.manual_solve_button.config(state=tk.NORMAL)
            
        except Exception as e:
            messagebox.showerror("Error", f"Error mostrando modelo:\n{str(e)}")
            import traceback
            traceback.print_exc()

    def show_model_in_main_panel(self, include_lungs):
        """Muestra el modelo generado en el panel de visualizacion principal con interacción completa"""
        try:
            # Limpiar el area de visualizacion
            self._clear_plot_area()
            
            # Crear figura 3D interactiva PERO NO MOSTRARLA TODAVoA
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
            import matplotlib.pyplot as plt
            from matplotlib.colors import ListedColormap
            from collections import Counter
            
            # Desactivar modo interactivo de matplotlib
            plt.ioff()
            
            # Mostrar mensaje de carga
            self.status_var.set("Preparando vista interactiva...")
            self.root.update()
            
            # Reducir DPI para mejor rendimiento
            fig = Figure(figsize=(8, 6), dpi=85)
            ax = fig.add_subplot(111, projection='3d')
            
            # Obtener datos de la malla
            X = self.mesh.p.T
            
            # Intentar visualizar por materiales
            try:
                # Extraer etiquetas de material usando el mismo metodo que scikit-fem
                mat_labels = None
                
                # Buscar en cell_data_dict
                if hasattr(self.mio, 'cell_data_dict'):
                    datos = self.mio.cell_data_dict
                    
                    # Formato MSH: clave estandar de Gmsh
                    if "gmsh:physical" in datos and "tetra" in datos["gmsh:physical"]:
                        mat_labels = datos["gmsh:physical"]["tetra"].flatten().astype(int)
                        print(f"œ“ Etiquetas encontradas (gmsh:physical): {np.unique(mat_labels)}")
                    
                    # Formato VTK: buscar campo con IDs enteros pequenos
                    elif mat_labels is None:
                        for clave, bloques in datos.items():
                            if "tetra" in bloques:
                                arr = bloques["tetra"].flatten()
                                vals = np.unique(arr)
                                if len(vals) <= 20 and arr.min() >= 0:
                                    mat_labels = arr.astype(int)
                                    print(f"œ“ Etiquetas encontradas ({clave}): {vals}")
                                    break
                
                if mat_labels is not None and len(mat_labels) > 0:
                    print(f"Total de elementos: {len(mat_labels)}")
                    
                    # Obtener tetraedros
                    if 'tetra' in self.mio.cells_dict:
                        tetrahedra = self.mio.cells_dict['tetra']
                        print(f"Tetraedros en malla: {len(tetrahedra)}")
                    else:
                        raise ValueError("No se encontraron tetraedros")
                    
                    # Colores y nombres por material
                    # ORDEN INVERTIDO: primero organos (opacos), luego torso (transparente)
                    colors_map = {
                        4: ('#2ECC71', 'Pulmon der', 0.7),     # verde
                        3: ('#F39C12', 'Pulmon izq', 0.7),     # naranja
                        2: ('#E74C3C', 'Corazon', 0.8),        # rojo, mas opaco
                        1: ('#5DADE2', 'Torso', 0.3),          # azul claro, mas transparente
                    }
                    
                    # Recolectar todas las superficies primero
                    surfaces_to_plot = []
                    
                    # Procesar cada material EN ORDEN INVERSO (organos primero)
                    for material_id in [4, 3, 2, 1]:  # Orden especifico
                        if material_id not in colors_map:
                            continue
                        
                        # Verificar si este material existe en la malla
                        if material_id not in np.unique(mat_labels):
                            continue
                        
                        color, name, alpha = colors_map[material_id]
                        
                        # Obtener tetraedros de este material
                        material_mask = mat_labels == material_id
                        n_tets = material_mask.sum()
                        
                        if n_tets == 0:
                            continue
                        
                        print(f"Procesando {name} (ID={material_id}): {n_tets} tetraedros")
                        
                        material_tets = tetrahedra[material_mask]
                        
                        # Extraer superficie: caras que aparecen solo una vez
                        faces_list = []
                        for tet in material_tets:
                            # Las 4 caras del tetraedro (ordenadas para comparacion)
                            faces_list.append(tuple(sorted([tet[0], tet[1], tet[2]])))
                            faces_list.append(tuple(sorted([tet[0], tet[1], tet[3]])))
                            faces_list.append(tuple(sorted([tet[0], tet[2], tet[3]])))
                            faces_list.append(tuple(sorted([tet[1], tet[2], tet[3]])))
                        
                        # Contar apariciones
                        face_counts = Counter(faces_list)
                        
                        # Superficie = caras que aparecen solo una vez
                        surface_faces = [face for face, count in face_counts.items() if count == 1]
                        
                        if len(surface_faces) > 0:
                            surface_tris = np.array(surface_faces)
                            print(f"  Superficie: {len(surface_tris)} triangulos")
                            
                            # Guardar para dibujar despues
                            surfaces_to_plot.append({
                                'triangles': surface_tris,
                                'color': color,
                                'alpha': alpha,
                                'name': name
                            })
                        else:
                            print(f" No se encontro superficie para {name}")
                    
                    # NUEVA ESTRATEGIA: Crear todas las colecciones 3D primero, luego agregarlas juntas
                    print(f"Construyendo figura con {len(surfaces_to_plot)} superficies...")
                    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
                    from matplotlib.colors import to_rgba
                    
                    collections = []
                    legend_handles = []
                    
                    for i, surf_data in enumerate(surfaces_to_plot):
                        print(f"  Preparando {i+1}/{len(surfaces_to_plot)}: {surf_data['name']}")
                        
                        # Crear los vertices de cada triangulo
                        triangles = surf_data['triangles']
                        verts = []
                        for tri in triangles:
                            verts.append([X[tri[0]], X[tri[1]], X[tri[2]]])
                        
                        # Crear la coleccion 3D (optimizado)
                        rgba_color = to_rgba(surf_data['color'], alpha=surf_data['alpha'])
                        collection = Poly3DCollection(verts, 
                                                     facecolors=rgba_color,
                                                     edgecolors='none',
                                                     linewidths=0)
                        collections.append(collection)
                        
                        # Crear handle para la leyenda
                        import matplotlib.patches as mpatches
                        legend_handles.append(mpatches.Patch(color=surf_data['color'], 
                                                            alpha=surf_data['alpha'],
                                                            label=surf_data['name']))
                    
                    # Agregar TODAS las colecciones al axes de una sola vez
                    print("Agregando todas las superficies al axes...")
                    for collection in collections:
                        ax.add_collection3d(collection)
                    
                    # Configurar limites del axes
                    ax.set_xlim(X[:, 0].min(), X[:, 0].max())
                    ax.set_ylim(X[:, 1].min(), X[:, 1].max())
                    ax.set_zlim(X[:, 2].min(), X[:, 2].max())
                    
                    # Agregar leyenda
                    ax.legend(handles=legend_handles, loc='upper right', fontsize=9, 
                             framealpha=0.95, edgecolor='gray', fancybox=True)
                    print("œ“ Figura construida completamente")
                    
                else:
                    print("š  No se encontraron etiquetas de material")
                    raise ValueError("Sin etiquetas")
                    
            except Exception as e:
                print(f"š  Error procesando materiales: {e}")
                import traceback
                traceback.print_exc()
                
                # Fallback: visualizacion por altura
                print("†’ Usando visualizacion por altura (fallback)")
                colors = X[:, 2]
                surf = ax.plot_trisurf(X[:, 0], X[:, 1], X[:, 2], 
                                     triangles=self.tris, alpha=0.8,
                                     cmap='viridis', linewidth=0, 
                                     edgecolor='none')
                surf.set_array(colors[self.tris].mean(axis=1))
                cbar = fig.colorbar(surf, ax=ax, shrink=0.6, aspect=10)
                cbar.set_label("Altura (Z)", rotation=270, labelpad=15, fontsize=9)
            
            tipo = "con pulmones" if include_lungs else "sin pulmones"
            ax.set_title(f"Modelo Generado ({tipo})", fontsize=12, fontweight='bold', pad=20)
            ax.set_xlabel("X (m)", fontsize=9)
            ax.set_ylabel("Y (m)", fontsize=9)
            ax.set_zlabel("Z (m)", fontsize=9)
            ax.view_init(elev=25, azim=45)
            
            # Ajustar aspecto para que se vea bien
            ax.set_box_aspect([1,1,1])
            
            fig.tight_layout()
            
            print("Creando canvas...")
            # AHORA So crear el canvas con la figura YA COMPLETA
            canvas = FigureCanvasTkAgg(fig, self.plot_frame)
            
            # Toolbar para zoom, pan, rotar
            toolbar_frame = tk.Frame(self.plot_frame, bg='white')
            toolbar_frame.pack(side=tk.TOP, fill=tk.X)
            
            toolbar = NavigationToolbar2Tk(canvas, toolbar_frame)
            toolbar.update()
            
            # Frame de controles adicionales
            controls_frame = tk.Frame(self.plot_frame, bg='#f0f0f0', relief=tk.RAISED, bd=1)
            controls_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
            
            tk.Label(controls_frame, text="🎮 Controles:", 
                    font=("Arial", 9, "bold"), bg='#f0f0f0').pack(side=tk.LEFT, padx=5)
            
            # Botones de vista
            def set_view(elev, azim):
                ax.view_init(elev=elev, azim=azim)
                canvas.draw()
            
            tk.Button(controls_frame, text="Vista Frontal", 
                     command=lambda: set_view(0, 0),
                     font=("Arial", 8), bg='#3498db', fg='white', 
                     relief=tk.FLAT, padx=8, pady=3).pack(side=tk.LEFT, padx=2)
            
            tk.Button(controls_frame, text="Vista Superior", 
                     command=lambda: set_view(90, 0),
                     font=("Arial", 8), bg='#3498db', fg='white', 
                     relief=tk.FLAT, padx=8, pady=3).pack(side=tk.LEFT, padx=2)
            
            tk.Button(controls_frame, text="Vista Lateral", 
                     command=lambda: set_view(0, 90),
                     font=("Arial", 8), bg='#3498db', fg='white', 
                     relief=tk.FLAT, padx=8, pady=3).pack(side=tk.LEFT, padx=2)
            
            tk.Button(controls_frame, text="Vista 3D", 
                     command=lambda: set_view(25, 45),
                     font=("Arial", 8), bg='#2ecc71', fg='white', 
                     relief=tk.FLAT, padx=8, pady=3).pack(side=tk.LEFT, padx=2)
            
            # Separador
            tk.Frame(controls_frame, width=2, bg='#bdc3c7').pack(side=tk.LEFT, fill=tk.Y, padx=5)
            
            # Controles de zoom
            tk.Label(controls_frame, text="Zoom:", 
                    font=("Arial", 8), bg='#f0f0f0').pack(side=tk.LEFT, padx=5)
            
            def zoom_in():
                xlim = ax.get_xlim()
                ylim = ax.get_ylim()
                zlim = ax.get_zlim()
                
                x_center = (xlim[0] + xlim[1]) / 2
                y_center = (ylim[0] + ylim[1]) / 2
                z_center = (zlim[0] + zlim[1]) / 2
                
                x_range = (xlim[1] - xlim[0]) * 0.8
                y_range = (ylim[1] - ylim[0]) * 0.8
                z_range = (zlim[1] - zlim[0]) * 0.8
                
                ax.set_xlim(x_center - x_range/2, x_center + x_range/2)
                ax.set_ylim(y_center - y_range/2, y_center + y_range/2)
                ax.set_zlim(z_center - z_range/2, z_center + z_range/2)
                canvas.draw()
            
            def zoom_out():
                xlim = ax.get_xlim()
                ylim = ax.get_ylim()
                zlim = ax.get_zlim()
                
                x_center = (xlim[0] + xlim[1]) / 2
                y_center = (ylim[0] + ylim[1]) / 2
                z_center = (zlim[0] + zlim[1]) / 2
                
                x_range = (xlim[1] - xlim[0]) * 1.25
                y_range = (ylim[1] - ylim[0]) * 1.25
                z_range = (zlim[1] - zlim[0]) * 1.25
                
                ax.set_xlim(x_center - x_range/2, x_center + x_range/2)
                ax.set_ylim(y_center - y_range/2, y_center + y_range/2)
                ax.set_zlim(z_center - z_range/2, z_center + z_range/2)
                canvas.draw()
            
            def reset_view():
                # Resetear limites a los originales
                x_min, x_max = X[:, 0].min(), X[:, 0].max()
                y_min, y_max = X[:, 1].min(), X[:, 1].max()
                z_min, z_max = X[:, 2].min(), X[:, 2].max()
                
                margin = 0.1
                x_margin = (x_max - x_min) * margin
                y_margin = (y_max - y_min) * margin
                z_margin = (z_max - z_min) * margin
                
                ax.set_xlim(x_min - x_margin, x_max + x_margin)
                ax.set_ylim(y_min - y_margin, y_max + y_margin)
                ax.set_zlim(z_min - z_margin, z_max + z_margin)
                ax.view_init(elev=25, azim=45)
                canvas.draw()
            
            tk.Button(controls_frame, text="ž•", 
                     command=zoom_in,
                     font=("Arial", 10, "bold"), bg='#27ae60', fg='white', 
                     relief=tk.FLAT, padx=8, pady=2).pack(side=tk.LEFT, padx=2)
            
            tk.Button(controls_frame, text="ž–", 
                     command=zoom_out,
                     font=("Arial", 10, "bold"), bg='#e67e22', fg='white', 
                     relief=tk.FLAT, padx=8, pady=2).pack(side=tk.LEFT, padx=2)
            
            tk.Button(controls_frame, text="ðŸ”„ Reset", 
                     command=reset_view,
                     font=("Arial", 8), bg='#95a5a6', fg='white', 
                     relief=tk.FLAT, padx=8, pady=3).pack(side=tk.LEFT, padx=2)
            
            # Instrucciones
            instructions = tk.Label(self.plot_frame, 
                                  text="ðŸ’¡ Arrastra con el mouse para rotar | Usa la rueda para zoom | Botones para vistas predefinidas",
                                  font=("Arial", 8), bg='white', fg='#7f8c8d')
            instructions.pack(side=tk.TOP, pady=3)
            
            # AHORA So mostrar el canvas (con todo ya dibujado)
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            print("Dibujando canvas...")
            canvas.draw()
            print("œ“ Canvas mostrado")
            
            # Habilitar rotacion con mouse
            def on_mouse_press(event):
                canvas._button_pressed = event.button
                canvas._mouse_x = event.x
                canvas._mouse_y = event.y
            
            def on_mouse_move(event):
                if hasattr(canvas, '_button_pressed') and canvas._button_pressed == 1:
                    dx = event.x - canvas._mouse_x
                    dy = event.y - canvas._mouse_y
                    
                    elev = ax.elev - dy * 0.5
                    azim = ax.azim + dx * 0.5
                    
                    ax.view_init(elev=elev, azim=azim)
                    canvas.draw()
                    
                    canvas._mouse_x = event.x
                    canvas._mouse_y = event.y
            
            def on_mouse_release(event):
                if hasattr(canvas, '_button_pressed'):
                    del canvas._button_pressed
            
            def on_scroll(event):
                if event.delta > 0:
                    zoom_in()
                else:
                    zoom_out()
            
            canvas.mpl_connect('button_press_event', on_mouse_press)
            canvas.mpl_connect('motion_notify_event', on_mouse_move)
            canvas.mpl_connect('button_release_event', on_mouse_release)
            canvas.mpl_connect('scroll_event', on_scroll)
            
            # Actualizar estado y habilitar botones
            self.status_var.set(f"Modelo generado ({tipo}) - Usa los controles para explorar")
            self.progress_var.set(0)
            
            self.file_button.config(state=tk.NORMAL)
            self.preview_button.config(state=tk.NORMAL)
            self.auto_solve_button.config(state=tk.NORMAL)
            self.manual_solve_button.config(state=tk.NORMAL)
            
            # Mostrar mensaje informativo
            messagebox.showinfo(
                "Modelo Generado", 
                f"   Modelo generado exitosamente ({tipo})\n\n"
                f"   Nodos: {self.mesh.p.shape[1]:,}\n"
                f"   Elementos: {self.mesh.t.shape[1]:,}\n\n"
                f"   Controles:\n"
                f"   Arrastra con el mouse para rotar\n"
                f"   Rueda del mouse para zoom\n"
                f"   Botones ž•ž– para zoom fino\n"
                f"   Botones de vista para angulos predefinidos\n\n"
                f"Cuando estes listo, haz clic en 'Resolver Automaticamente'"
            )
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            messagebox.showerror("Error", f"Error mostrando modelo:\n{e}")
            self.status_var.set("Error mostrando modelo")
            self.progress_var.set(0)
            
            # Rehabilitar botones
            self.file_button.config(state=tk.NORMAL)
            if self.mesh:
                self.preview_button.config(state=tk.NORMAL)
                self.auto_solve_button.config(state=tk.NORMAL)
                self.manual_solve_button.config(state=tk.NORMAL)
