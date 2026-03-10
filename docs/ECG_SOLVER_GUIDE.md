# Guía del Solver de ECG

## Introducción

El módulo `ecg_solver.py` implementa el problema directo del electrocardiograma (ECG) usando el método de elementos finitos (FEM). Este documento describe la teoría, implementación y uso del solver.

## Fundamentos Teóricos

### Problema Directo del ECG

El problema directo del ECG consiste en calcular los potenciales eléctricos en la superficie del torso dado un modelo de la actividad eléctrica del corazón.

#### Ecuación Gobernante

La distribución de potenciales φ en el torso se rige por la ecuación de Poisson con conductividades heterogéneas:

```
∇ · (σ ∇φ) = Iv
```

Donde:
- φ: Potencial eléctrico (V)
- σ: Conductividad del tejido (S/m)
- Iv: Densidad de corriente volumétrica (A/m³)

#### Condiciones de Contorno

- **Neumann homogéneo** en la superficie del torso: σ ∂φ/∂n = 0
- **Condición de gauge**: φ = 0 en un nodo de referencia (para unicidad)

### Modelo de Fuentes Cardíacas

La actividad eléctrica del corazón se modela como un **dipolo equivalente** ubicado en el centro del corazón:

```
Iv = -p · ∇δ(r - r0)
```

Donde:
- p(t): Momento dipolar [px, py, pz] en A·m
- r0: Posición del dipolo (centro del corazón)
- δ: Delta de Dirac

#### Formulación Débil (FEM)

En la formulación de elementos finitos con funciones de forma P1:

```
fi = p · ∇φi(r0)
```

Solo los 4 nodos del tetraedro que contiene r0 tienen contribución no nula.

### Conductividades por Tejido

| Tejido | Conductividad (S/m) | Descripción |
|--------|---------------------|-------------|
| Torso | 0.22 | Músculo, grasa, piel |
| Corazón | 0.40 | Músculo cardíaco |
| Pulmones | 0.05 | Tejido pulmonar (baja conductividad) |

## Pipeline de 5 Pasos

### Paso 1: Cargar Malla con Conductividades

```python
mesh_data = load_mesh_with_conductivities(vtk_path, conductivities)
```

**Entrada:**
- Archivo VTK/MSH con etiquetas de material por elemento
- Diccionario de conductividades {material_id: sigma}

**Salida:**
- `mesh`: Malla scikit-fem (MeshTet)
- `basis`: Base funcional (ElementTetP1)
- `sigma_el`: Conductividad por elemento
- `sigma_field`: Campo discreto para ensamblaje
- `mat_labels`: Etiquetas de material
- `surface_nodes`: Nodos de la superficie del torso

**Detalles:**
- Usa ElementTetP1 (tetraedros lineales de 4 nodos)
- Extrae automáticamente etiquetas de material de .msh o .vtk
- Identifica nodos de superficie (tag=10)

### Paso 2: Ensamblar Matriz de Rigidez

```python
K = assemble_stiffness_matrix(basis, sigma_field)
```

**Forma bilineal:**
```
a(u, v) = ∫_Ω σ ∇u · ∇v dV
```

**Propiedades de K:**
- Simétrica: K = K^T
- Diagonal positiva: Kii > 0
- Singular: rango(K) = N-1 (Neumann puro)
- Dispersa: ~0.01% de densidad para mallas típicas

**Salida:**
- Matriz K en formato CSR (scipy.sparse)

### Paso 3: Fuentes Cardíacas - Dipolo Equivalente

```python
source_data = build_source_matrix(mesh, dipole_pos, dipole_table)
```

**Entrada:**
- `dipole_pos`: Posición del dipolo [x, y, z] en metros
- `dipole_table`: Array (T, 4) con [t, px, py, pz] por fila

**Tabla Temporal del Dipolo:**

El dipolo p(t) varía a lo largo del ciclo cardíaco para representar:
- **Onda P** (t~0.05s): Despolarización auricular
- **Complejo QRS** (t~0.15-0.25s): Despolarización ventricular
- **Onda T** (t~0.40s): Repolarización ventricular

**Salida:**
- `F_matrix`: Matriz de fuentes (N, T)
- `times`: Instantes de tiempo (T,)
- `dipoles`: Momentos dipolares (T, 3)

**Algoritmo:**
1. Localizar elemento que contiene el dipolo (coordenadas baricéntricas)
2. Calcular gradientes de funciones de forma P1 en ese elemento
3. Para cada instante: fi = p(t) · ∇φi(r0)

### Paso 4: Resolver Sistema K·φ = f

```python
solution_data = solve_ecg_system(K, F_matrix, mesh, surface_nodes, dipole_pos)
```

**Estrategia:**
1. Seleccionar nodo de referencia (más alejado del dipolo en superficie)
2. Aplicar condición de gauge: φ[ref_node] = 0
3. Eliminar fila y columna → K_red (N-1, N-1)
4. Resolver K_red·φ_red = f_red para cada instante

**Solver:**
- **MINRES** (Minimal Residual): Adecuado para sistemas simétricos
- **Precondicionador Jacobi**: M = diag(K)^(-1)
- **Tolerancia**: 1e-8 (relativa)
- **Max iteraciones**: 5000

**Salida:**
- `PHI`: Potenciales (N, T) en todos los nodos
- `ref_node`: Índice del nodo de referencia
- `residuals`: Residuos por instante (T,)

**Complejidad:**
- O(T × iter × nnz(K)) donde iter~100-500 para mallas típicas

### Paso 5: Postprocesar Potenciales en Electrodos

```python
ecg_data = postprocess_ecg(mesh, surface_nodes, PHI, electrode_positions)
```

**Electrodos Estándar:**

| Electrodo | Posición Anatómica | Uso |
|-----------|-------------------|-----|
| RA | Brazo derecho | Extremidades |
| LA | Brazo izquierdo | Extremidades |
| LL | Pierna izquierda | Extremidades |
| V1-V6 | Precordiales | Tórax anterior |

**12 Derivaciones:**

**Extremidades (bipolares):**
- I = LA - RA
- II = LL - RA
- III = LL - LA

**Extremidades (unipolares aumentadas):**
- aVR = RA - WCT
- aVL = LA - WCT
- aVF = LL - WCT

Donde WCT = (RA + LA + LL) / 3 (Wilson Central Terminal)

**Precordiales (unipolares):**
- V1..V6 = Vn - WCT

**Salida:**
- `electrode_nodes`: Nodos más cercanos a posiciones anatómicas
- `phi_electrodes`: Potenciales en electrodos (9 × T)
- `leads`: 12 derivaciones (cada una de shape T)

## Uso de la Clase ECGSolver

### Ejemplo Básico

```python
from src.ecg_solver import ECGSolver

# Crear solver
solver = ECGSolver('data/ecg_torso_v2_con_pulmones.msh')

# Ejecutar pipeline completo
results = solver.run_full_pipeline()

# Obtener resultados
leads = results['ecg_data']['leads']
PHI = results['solution_data']['PHI']

# Resumen
summary = solver.get_summary()
print(f"Nodos: {summary['num_nodes']}")
print(f"Amplitud máxima Lead I: {summary['lead_amplitudes']['I']:.4f} mV")
```

### Configuración Personalizada

```python
import numpy as np
from src.ecg_solver import ECGSolver

# Conductividades personalizadas
conductivities = {
    1: 0.20,   # Torso (ajustado)
    2: 0.45,   # Corazón (ajustado)
    3: 0.04,   # Pulmón izquierdo
    4: 0.04,   # Pulmón derecho
}

# Dipolo personalizado (solo pico QRS)
dipole_table = np.array([
    [0.00,   0.000,   0.000,   0.000],
    [0.10,   0.003,   0.002,   0.004],
    [0.20,   0.008,   0.004,   0.010],  # Pico
    [0.30,   0.003,   0.001,   0.004],
    [0.40,   0.000,   0.000,   0.000],
])

# Posición del dipolo ajustada
dipole_pos = np.array([-0.01, 0.00, 0.28])

# Crear solver
solver = ECGSolver(
    vtk_path='mi_malla.msh',
    conductivities=conductivities,
    dipole_pos=dipole_pos,
    dipole_table=dipole_table
)

# Ejecutar con parámetros de solver ajustados
results = solver.run_full_pipeline(tol=1e-10, max_iter=10000)
```

### Acceso a Resultados Intermedios

```python
# Ejecutar pipeline
results = solver.run_full_pipeline()

# Acceder a cada paso
mesh = results['mesh_data']['mesh']
basis = results['mesh_data']['basis']
K = results['K']
F_matrix = results['source_data']['F_matrix']
PHI = results['solution_data']['PHI']
leads = results['ecg_data']['leads']

# Información de convergencia
residuals = results['solution_data']['residuals']
print(f"Residuo máximo: {residuals.max():.2e}")
print(f"Residuo promedio: {residuals.mean():.2e}")

# Potenciales en instante específico
t_idx = 4  # Pico QRS
phi_at_peak = PHI[:, t_idx]
print(f"Potencial máximo en pico: {phi_at_peak.max()*1000:.4f} mV")
```

## Visualización de Resultados

### Gráfica de 12 Derivaciones

```python
import matplotlib.pyplot as plt

def plot_12_leads(leads, times):
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
plot_12_leads(results['ecg_data']['leads'], results['source_data']['times'])
```

### Mapa de Potenciales en Superficie

```python
def plot_surface_potentials(mesh, surface_nodes, PHI, instant_idx=4):
    coords = mesh.p.T[surface_nodes]
    phi_surf = PHI[surface_nodes, instant_idx] * 1000  # mV
    
    plt.figure(figsize=(10, 8))
    plt.scatter(coords[:, 0], coords[:, 2], c=phi_surf, 
                cmap='RdBu_r', s=10,
                vmin=-abs(phi_surf).max(), 
                vmax=abs(phi_surf).max())
    plt.colorbar(label='Potencial (mV)')
    plt.xlabel('x (m)')
    plt.ylabel('z (m)')
    plt.title(f'Mapa de potenciales (instante {instant_idx})')
    plt.axis('equal')
    plt.show()

# Usar
results = solver.run_full_pipeline()
plot_surface_potentials(
    results['mesh_data']['mesh'],
    results['mesh_data']['surface_nodes'],
    results['solution_data']['PHI'],
    instant_idx=4
)
```

## Requisitos de la Malla

Para usar el solver de ECG, tu archivo de malla debe cumplir:

### Geometría
- Torso cilíndrico o realista
- Corazón ubicado en el interior
- Pulmones (opcional pero recomendado)

### Etiquetas de Material
- **ID 1**: Torso
- **ID 2**: Corazón
- **ID 3**: Pulmón izquierdo (opcional)
- **ID 4**: Pulmón derecho (opcional)

### Etiquetas de Superficie
- **Tag 10**: Superficie del torso (para condiciones de contorno)

### Formato
- Soportado: `.msh` (Gmsh) o `.vtk`
- Elementos: Tetraedros (tetra o tetra10)
- Superficies: Triángulos (para identificar superficie)

### Ejemplo con Gmsh

```python
# En tu script de generación de malla con Gmsh
import gmsh

gmsh.initialize()

# Definir Physical Groups
gmsh.model.addPhysicalGroup(3, [torso_vol], 1)      # Torso
gmsh.model.addPhysicalGroup(3, [heart_vol], 2)      # Corazón
gmsh.model.addPhysicalGroup(3, [lung_l_vol], 3)     # Pulmón izq
gmsh.model.addPhysicalGroup(3, [lung_r_vol], 4)     # Pulmón der
gmsh.model.addPhysicalGroup(2, [torso_surf], 10)    # Superficie

gmsh.model.mesh.generate(3)
gmsh.write("mi_malla.msh")
gmsh.finalize()
```

## Troubleshooting

### Error: "El dipolo no está dentro de ningún elemento"

**Causa**: La posición del dipolo está fuera del dominio de la malla.

**Solución**:
```python
# Verificar límites de la malla
mesh = results['mesh_data']['mesh']
print(f"X: [{mesh.p[0].min():.3f}, {mesh.p[0].max():.3f}]")
print(f"Y: [{mesh.p[1].min():.3f}, {mesh.p[1].max():.3f}]")
print(f"Z: [{mesh.p[2].min():.3f}, {mesh.p[2].max():.3f}]")

# Ajustar posición del dipolo
dipole_pos = np.array([x, y, z])  # Dentro de los límites
```

### Error: "Material ID X no tiene conductividad definida"

**Causa**: La malla tiene materiales no definidos en el diccionario.

**Solución**:
```python
# Agregar conductividad para el material faltante
conductivities = {
    1: 0.22,
    2: 0.40,
    3: 0.05,
    4: 0.05,
    5: 0.10,  # Agregar nuevo material
}
```

### Convergencia lenta del solver

**Síntomas**: Residuos altos o muchas iteraciones.

**Soluciones**:
1. Aumentar max_iter:
```python
results = solver.run_full_pipeline(max_iter=10000)
```

2. Relajar tolerancia:
```python
results = solver.run_full_pipeline(tol=1e-6)
```

3. Verificar calidad de la malla (elementos muy distorsionados)

### Amplitudes de ECG muy pequeñas

**Causa**: Momento dipolar muy débil.

**Solución**: Aumentar amplitud del dipolo:
```python
dipole_table[:, 1:] *= 10  # Multiplicar por 10
```

## Referencias

1. Gulrajani, R. M. (1998). *Bioelectricity and Biomagnetism*. Wiley.
2. Malmivuo, J., & Plonsey, R. (1995). *Bioelectromagnetism*. Oxford University Press.
3. Logg, A., Mardal, K. A., & Wells, G. (2012). *Automated Solution of Differential Equations by the Finite Element Method*. Springer.
4. scikit-fem documentation: https://scikit-fem.readthedocs.io/

## Contacto y Soporte

Para preguntas, reportar bugs o contribuir:
- Ver `README.md` para información general
- Ver `examples/demo_ecg_solver.py` para ejemplos completos
- Revisar tests en `tests/` para casos de uso
