# Guía del Generador Automático de Modelos

## 🏥 Introducción

El Generador Automático de Modelos es una herramienta integrada en la GUI que permite crear modelos 3D realistas de torso con corazón y pulmones, listos para simulaciones de ECG.

## ✨ Características

- **Geometría anatómica realista** basada en proporciones humanas
- **Vista previa 3D** antes de generar la malla
- **Opciones configurables**: Con o sin pulmones
- **Malla adaptativa** con refinamiento automático
- **Conductividades eléctricas** realistas por tejido
- **Integración completa** con la GUI y el solver ECG

## 📐 Especificaciones del Modelo

### Geometría

| Componente | Forma | Dimensiones |
|------------|-------|-------------|
| Torso | Cilindro | Radio: 15 cm, Altura: 50 cm |
| Corazón | Esfera | Radio: 5 cm |
| Pulmón Izquierdo | Elipsoide | 4 × 6 × 9 cm |
| Pulmón Derecho | Elipsoide | 4 × 6 × 9 cm |

### Conductividades Eléctricas

| Tejido | Conductividad (S/m) | Physical Group ID |
|--------|---------------------|-------------------|
| Torso | 0.22 | 1 |
| Corazón | 0.40 | 2 |
| Pulmón Izquierdo | 0.05 | 3 |
| Pulmón Derecho | 0.05 | 4 |
| Superficie Torso | - | 10 |

### Malla

- **Tipo**: Tetraédrica 3D
- **Refinamiento**: Adaptativo
- **Tamaño característico**:
  - Torso: 3 cm
  - Órganos: 1 cm
- **Elementos**: ~5,000-15,000 tetraedros (según configuración)

## 🚀 Uso desde la GUI

### Paso 1: Abrir el Generador

```bash
python main.py
```

En la interfaz, haz clic en el botón:
```
🏥 Generar Modelo Automático
```

### Paso 2: Configurar Opciones

Se abrirá un diálogo con dos opciones:

1. **Con pulmones (modelo completo)**
   - Incluye torso, corazón y ambos pulmones
   - Más realista para simulaciones ECG
   - Malla más compleja (~15,000 elementos)

2. **Sin pulmones (solo torso y corazón)**
   - Modelo simplificado
   - Más rápido de generar y resolver
   - Malla más simple (~5,000 elementos)

### Paso 3: Vista Previa

Haz clic en **"👁 Vista Previa"** para ver una representación 3D del modelo antes de generarlo.

La vista previa muestra:
- Torso (cilindro azul transparente)
- Corazón (esfera roja)
- Pulmones (elipsoides rosados, si están incluidos)

### Paso 4: Generar Malla

Haz clic en **"⚙ Generar Malla"** para crear la malla.

**Tiempo estimado**: 1-2 minutos

Durante la generación:
- Se muestra una barra de progreso
- El proceso corre en segundo plano
- La interfaz permanece responsiva

### Paso 5: Uso Automático

Una vez generada:
- La malla se guarda en `data/ecg_torso_auto_con_pulmones.msh` (o `_sin_pulmones.msh`)
- Se carga automáticamente en la GUI
- Está lista para simulaciones

## 💻 Uso desde Código Python

### Ejemplo Básico

```python
from src.model_generator import generate_mesh

# Generar modelo con pulmones
mesh_file = generate_mesh(
    include_lungs=True,
    output_path='data/mi_modelo.msh'
)

print(f"Malla generada: {mesh_file}")
```

### Ejemplo con Vista Previa

```python
from src.model_generator import get_preview_data

# Obtener datos de vista previa
preview = get_preview_data(include_lungs=True)

print(f"Número de volúmenes: {preview['num_volumes']}")
print(f"Límites: {preview['bounds']}")
print(f"Componentes: {list(preview['components'].keys())}")
```

### Ejemplo con Parámetros Personalizados

```python
from src.model_generator import generate_mesh, DEFAULT_PARAMS

# Modificar parámetros
custom_params = DEFAULT_PARAMS.copy()
custom_params['torso_radio'] = 0.18  # Torso más ancho
custom_params['corazon_r'] = 0.06    # Corazón más grande

# Generar con parámetros personalizados
mesh_file = generate_mesh(
    include_lungs=True,
    output_path='data/modelo_custom.msh',
    params=custom_params
)
```

### Integración con ECGSolver

```python
from src.model_generator import generate_mesh
from src.ecg_solver import ECGSolver

# 1. Generar modelo
mesh_file = generate_mesh(include_lungs=True)

# 2. Cargar en solver
solver = ECGSolver(mesh_file)

# 3. Ejecutar simulación
results = solver.run_full_pipeline()

# 4. Analizar resultados
leads = results['ecg_data']['leads']
print(f"Lead I: {abs(leads['I']).max() * 1000:.2f} mV")
```

## 🔧 Requisitos

### Dependencias

```bash
pip install gmsh>=4.8.0
```

El generador requiere **Gmsh** para crear la geometría y generar la malla.

### Verificar Instalación

```python
from src.model_generator import HAS_GMSH

if HAS_GMSH:
    print("✅ Gmsh está instalado")
else:
    print("❌ Gmsh no está instalado")
    print("Instala con: pip install gmsh")
```

## 📊 Comparación de Modelos

| Característica | Con Pulmones | Sin Pulmones |
|----------------|--------------|--------------|
| Realismo | Alto | Medio |
| Elementos | ~15,000 | ~5,000 |
| Tiempo generación | 1-2 min | 30-60 seg |
| Tiempo simulación | Mayor | Menor |
| Conductividades | 4 tejidos | 2 tejidos |
| Uso recomendado | Investigación | Pruebas rápidas |

## 🎯 Casos de Uso

### 1. Investigación ECG
```python
# Modelo completo para resultados precisos
mesh = generate_mesh(include_lungs=True)
solver = ECGSolver(mesh)
results = solver.run_full_pipeline()
```

### 2. Pruebas Rápidas
```python
# Modelo simple para iteración rápida
mesh = generate_mesh(include_lungs=False)
solver = ECGSolver(mesh)
results = solver.run_full_pipeline()
```

### 3. Estudios Paramétricos
```python
# Variar geometría para estudios
for radio in [0.12, 0.15, 0.18]:
    params = DEFAULT_PARAMS.copy()
    params['torso_radio'] = radio
    mesh = generate_mesh(params=params, 
                        output_path=f'torso_r{radio}.msh')
```

## ⚠️ Notas Importantes

1. **Tiempo de generación**: La primera generación puede tardar más mientras Gmsh se inicializa

2. **Espacio en disco**: Cada malla ocupa ~1-5 MB dependiendo del refinamiento

3. **Memoria RAM**: La generación requiere ~500 MB de RAM

4. **Formato de salida**: Siempre genera archivos .msh (formato Gmsh)

5. **Physical Groups**: Los modelos incluyen etiquetas de material necesarias para ECGSolver

6. **Visualización**: Los materiales se muestran TODOS JUNTOS desde el inicio (torso transparente + corazón opaco visible simultáneamente)

## 🎨 Visualización del Modelo

### Renderizado Simultáneo

El generador automático muestra todos los materiales juntos desde el inicio:

- **Torso**: Azul claro transparente (α=0.3)
- **Corazón**: Rojo opaco (α=0.8)
- **Pulmones**: Verde/Naranja semi-transparente (α=0.7)

Esto permite ver la estructura interna (corazón, pulmones) dentro del torso transparente, similar a las visualizaciones de scikit-fem.

### Controles de Visualización

Una vez generado el modelo, puedes:

- **Rotar**: Arrastra con el mouse
- **Zoom**: Rueda del mouse o botones ➕➖
- **Vistas predefinidas**: Frontal, Superior, Lateral, 3D
- **Reset**: Volver a la vista inicial

### Implementación Técnica

La visualización usa `Poly3DCollection` de matplotlib para renderizado por lotes:
- Todas las superficies se preparan primero
- Se agregan al axes de una sola vez
- Se renderiza una sola vez con `canvas.draw()`

Esto evita el "renderizado progresivo" donde los materiales aparecían uno por uno.

Ver [SOLUCION_RENDERIZADO_PROGRESIVO.md](../SOLUCION_RENDERIZADO_PROGRESIVO.md) para detalles técnicos.

## 🐛 Solución de Problemas

### Error: "gmsh no está instalado"

```bash
pip install gmsh
```

### Error: "No se puede escribir en data/"

Verifica permisos de escritura en la carpeta del proyecto.

### La generación tarda mucho

- Normal para modelos con pulmones (1-2 minutos)
- Reduce el refinamiento modificando `lc_torso` y `lc_organo`

### La malla es muy grande

Aumenta los parámetros de tamaño:
```python
params = DEFAULT_PARAMS.copy()
params['lc_torso'] = 0.05   # Más grande
params['lc_organo'] = 0.02  # Más grande
```

## 📚 Referencias

- **Gmsh**: http://gmsh.info/
- **Anatomía cardíaca**: Dimensiones basadas en literatura médica
- **Conductividades**: Valores de Gabriel et al. (1996)

## 🔗 Ver También

- [QUICK_START.md](QUICK_START.md) - Guía de inicio rápido
- [ECG_SOLVER_GUIDE.md](ECG_SOLVER_GUIDE.md) - Guía técnica del solver
- [README.md](../README.md) - Documentación principal
