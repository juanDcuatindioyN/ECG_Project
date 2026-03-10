# Guía de Inicio Rápido - ECG_Project v2.0.0

## Instalación

### 1. Instalar Dependencias

```bash
cd ECG_Project
pip install -r requirements.txt
```

**Dependencias instaladas:**
- numpy (cálculos numéricos)
- scipy (solvers y álgebra lineal)
- matplotlib (visualización)
- scikit-fem (elementos finitos)
- meshio (lectura de mallas)

### 2. Verificar Instalación

```bash
python main.py --test
```

## Modo Básico - Interfaz Gráfica

### Ejecutar la Aplicación

```bash
python main.py
```

### Uso
1. Arrastra un archivo `.vtk` a la ventana (o usa el botón)
2. La aplicación detecta automáticamente parámetros óptimos
3. Resuelve la ecuación de Poisson
4. Muestra visualización 3D

### Archivo de Ejemplo
```bash
# Usa el archivo incluido
data/Sphere.vtk
```

## Modo Avanzado - Simulador de ECG

### Preparar Datos

**Opción 1: Copiar archivo de ejemplo**
```bash
# Desde la raíz del proyecto
cp ../scikit-fem/ProyectoECG/ecg_torso_v2_con_pulmones.msh data/
```

**Opción 2: Usar tu propia malla**
- Debe tener etiquetas de material (1=torso, 2=corazón, 3-4=pulmones)
- Formato .msh o .vtk
- Ver `docs/ECG_SOLVER_GUIDE.md` para requisitos completos

### Ejecutar Demostración

```bash
python examples/demo_ecg_solver.py
```

**Salida esperada:**
- `ecg_12_leads_demo.png` - Gráfica de 12 derivaciones
- `potential_map_demo.png` - Mapa de potenciales en superficie

### Uso Programático

**Ejemplo mínimo:**
```python
from src.ecg_solver import ECGSolver

# Crear solver
solver = ECGSolver('data/ecg_torso_v2_con_pulmones.msh')

# Ejecutar pipeline completo
results = solver.run_full_pipeline()

# Ver resumen
summary = solver.get_summary()
print(summary)
```

**Ejemplo con configuración personalizada:**
```python
import numpy as np
from src.ecg_solver import ECGSolver

# Conductividades personalizadas (S/m)
conductivities = {
    1: 0.22,   # Torso
    2: 0.40,   # Corazón
    3: 0.05,   # Pulmón izquierdo
    4: 0.05,   # Pulmón derecho
}

# Posición del dipolo (metros)
dipole_pos = np.array([-0.02, 0.00, 0.30])

# Tabla temporal del dipolo [t(s), px, py, pz] en A·m
dipole_table = np.array([
    [0.00,   0.000,   0.000,   0.000],   # reposo
    [0.20,   0.006,   0.003,   0.008],   # pico QRS
    [0.80,   0.000,   0.000,   0.000],   # reposo
])

# Crear solver
solver = ECGSolver(
    vtk_path='data/ecg_torso_v2_con_pulmones.msh',
    conductivities=conductivities,
    dipole_pos=dipole_pos,
    dipole_table=dipole_table
)

# Ejecutar
results = solver.run_full_pipeline(tol=1e-8, max_iter=5000)

# Acceder a resultados
leads = results['ecg_data']['leads']
PHI = results['solution_data']['PHI']

# Derivación I en mV
ecg_I = leads['I'] * 1000
print(f"Amplitud máxima Lead I: {abs(ecg_I).max():.4f} mV")
```

## Visualización de Resultados

### Gráfica de 12 Derivaciones

```python
import matplotlib.pyplot as plt

def plot_ecg(leads, times):
    layout = [
        ["I", "aVR", "V1", "V4"],
        ["II", "aVL", "V2", "V5"],
        ["III", "aVF", "V3", "V6"],
    ]
    
    fig, axes = plt.subplots(3, 4, figsize=(16, 8))
    t_ms = times * 1000
    
    for row, row_names in enumerate(layout):
        for col, name in enumerate(row_names):
            ax = axes[row][col]
            signal = leads[name] * 1000  # mV
            ax.plot(t_ms, signal, linewidth=1.8)
            ax.set_title(name, fontweight="bold")
            ax.set_xlabel("t (ms)")
            ax.set_ylabel("mV")
            ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.show()

# Usar
results = solver.run_full_pipeline()
plot_ecg(results['ecg_data']['leads'], results['source_data']['times'])
```

### Mapa de Potenciales

```python
def plot_potentials(mesh, surface_nodes, PHI, instant_idx=4):
    coords = mesh.p.T[surface_nodes]
    phi_surf = PHI[surface_nodes, instant_idx] * 1000  # mV
    
    plt.figure(figsize=(10, 8))
    plt.scatter(coords[:, 0], coords[:, 2], c=phi_surf, 
                cmap='RdBu_r', s=10)
    plt.colorbar(label='Potencial (mV)')
    plt.xlabel('x (m)')
    plt.ylabel('z (m)')
    plt.title(f'Potenciales en superficie (instante {instant_idx})')
    plt.axis('equal')
    plt.show()

# Usar
results = solver.run_full_pipeline()
plot_potentials(
    results['mesh_data']['mesh'],
    results['mesh_data']['surface_nodes'],
    results['solution_data']['PHI'],
    instant_idx=4
)
```

## Comandos Útiles

```bash
# Ejecutar interfaz gráfica
python main.py

# Ejecutar tests
python main.py --test

# Ver información del proyecto
python main.py --info

# Demostración modo básico
python main.py --demo

# Demostración ECG completo
python examples/demo_ecg_solver.py

# Ayuda
python main.py --help
```

## Estructura de Resultados

Cuando ejecutas `solver.run_full_pipeline()`, obtienes:

```python
results = {
    'mesh_data': {
        'mesh': MeshTet,              # Malla scikit-fem
        'basis': Basis,               # Base funcional
        'sigma_el': ndarray,          # Conductividades
        'mat_labels': ndarray,        # Etiquetas de material
        'surface_nodes': ndarray,     # Nodos de superficie
        'mio': meshio object          # Objeto meshio original
    },
    'K': sparse matrix,               # Matriz de rigidez
    'source_data': {
        'F_matrix': ndarray (N, T),   # Matriz de fuentes
        'times': ndarray (T,),        # Instantes de tiempo
        'dipoles': ndarray (T, 3)     # Momentos dipolares
    },
    'solution_data': {
        'PHI': ndarray (N, T),        # Potenciales
        'ref_node': int,              # Nodo de referencia
        'ref_origin': str,            # Origen del nodo ref
        'residuals': ndarray (T,)     # Residuos por instante
    },
    'ecg_data': {
        'electrode_nodes': dict,      # Nodos de electrodos
        'phi_electrodes': dict,       # Potenciales en electrodos
        'leads': dict                 # 12 derivaciones
    }
}
```

## Resumen del Solver

```python
summary = solver.get_summary()

# Contiene:
# - num_nodes: Número de nodos
# - num_elements: Número de elementos
# - num_surface_nodes: Nodos en superficie
# - num_instants: Instantes temporales
# - phi_max: Potencial máximo (V)
# - max_residual: Residuo máximo
# - ref_node: Nodo de referencia
# - lead_amplitudes: Dict con amplitudes de cada derivación (mV)
```

## Troubleshooting

### Error: "No module named 'numpy'"
```bash
pip install -r requirements.txt
```

### Error: "No se encontró el archivo de malla"
```bash
# Verificar que el archivo existe
ls data/

# Copiar archivo de ejemplo
cp ../scikit-fem/ProyectoECG/ecg_torso_v2_con_pulmones.msh data/
```

### Error: "El dipolo no está dentro de ningún elemento"
```python
# Verificar límites de la malla
mesh = results['mesh_data']['mesh']
print(f"X: [{mesh.p[0].min():.3f}, {mesh.p[0].max():.3f}]")
print(f"Y: [{mesh.p[1].min():.3f}, {mesh.p[1].max():.3f}]")
print(f"Z: [{mesh.p[2].min():.3f}, {mesh.p[2].max():.3f}]")

# Ajustar posición del dipolo dentro de los límites
```

### Convergencia lenta
```python
# Aumentar iteraciones o relajar tolerancia
results = solver.run_full_pipeline(tol=1e-6, max_iter=10000)
```

## Documentación Adicional

- **README.md** - Descripción general del proyecto
- **docs/ECG_SOLVER_GUIDE.md** - Guía completa del solver de ECG
- **docs/AUTOMATIC_FEATURES.md** - Características del modo automático
- **INTEGRATION_SUMMARY.md** - Resumen de la integración v2.0.0

## Ejemplos Completos

Ver carpeta `examples/`:
- `demo_automatic.py` - Demostración modo básico
- `demo_ecg_solver.py` - Demostración ECG completo

## Soporte

Para más información:
1. Leer la documentación en `docs/`
2. Revisar ejemplos en `examples/`
3. Ejecutar tests: `python main.py --test`
4. Ver código fuente en `src/`

---

**Versión**: 2.0.0  
**Última actualización**: 2026-03-04
