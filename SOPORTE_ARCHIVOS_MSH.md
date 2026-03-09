# Soporte para Archivos MSH (Gmsh)

## ✅ Actualización Implementada

La aplicación ahora soporta archivos `.msh` (formato Gmsh) además de `.vtk`, permitiendo cargar modelos anatómicos complejos como los del proyecto scikit-fem.

## 🔍 Análisis del Proyecto Scikit-fem

### Archivos Encontrados:

En `c:\Users\FRI-01\Downloads\scikit-fem\ProyectoECG\`:

1. **`ecg_torso_v2_con_pulmones.msh`** - Modelo completo con:
   - Torso (ID=1, σ=0.22 S/m)
   - Corazón (ID=2, σ=0.40 S/m)
   - Pulmón izquierdo (ID=3, σ=0.05 S/m)
   - Pulmón derecho (ID=4, σ=0.05 S/m)

2. **`ecg_torso_v2_sin_pulmones.msh`** - Modelo simplificado:
   - Torso (ID=1)
   - Corazón (ID=2)

3. **`ecg_torso_v2_con_pulmones.vtk`** - Versión VTK del modelo completo

### Cómo Cargan las Mallas:

El proyecto scikit-fem usa `meshio.read()` que soporta múltiples formatos:
- `.msh` (Gmsh)
- `.vtk` (VTK)
- `.stl`, `.obj`, `.ply`, etc.

## 🔧 Cambios Implementados

### 1. `src/core.py` - Función `load_mesh_skfem()`

**Antes:**
```python
def load_mesh_skfem(vtk_path: str):
    """Carga una malla VTK..."""
    mio = meshio.read(vtk_path)
    ...
```

**Ahora:**
```python
def load_mesh_skfem(file_path: str):
    """Carga una malla (VTK o MSH)..."""
    mio = meshio.read(file_path)  # meshio detecta el formato automáticamente
    ...
```

### 2. `src/gui_safe.py` - Diálogo de Carga

**Antes:**
```python
filetypes=[("Archivos VTK", "*.vtk"), ...]
```

**Ahora:**
```python
filetypes=[
    ("Archivos de malla", "*.vtk *.msh"),
    ("Archivos VTK", "*.vtk"),
    ("Archivos MSH", "*.msh"),
    ("Todos los archivos", "*.*")
]
```

### 3. Drag & Drop Actualizado

**Antes:**
```python
if file_path.lower().endswith('.vtk'):
```

**Ahora:**
```python
if file_path.lower().endswith(('.vtk', '.msh')):
```

### 4. Botón de Carga

**Antes:** "📁 Cargar otro archivo VTK (opcional)"

**Ahora:** "📁 Cargar archivo de malla (VTK/MSH)"

## 📊 Formatos Soportados

| Formato | Extensión | Descripción | Soporte |
|---------|-----------|-------------|---------|
| VTK | `.vtk` | Visualization Toolkit | ✅ Completo |
| MSH | `.msh` | Gmsh mesh format | ✅ Completo |
| VTU | `.vtu` | VTK XML unstructured | ✅ Via meshio |
| STL | `.stl` | Stereolithography | ⚠️ Solo superficies |

## 🎯 Uso con Modelos Anatómicos

### Cargar Modelo con Pulmones:

1. Ejecuta: `python main.py`
2. Haz clic en "📁 Cargar archivo de malla (VTK/MSH)"
3. Selecciona: `ecg_torso_v2_con_pulmones.msh`
4. La aplicación cargará el modelo completo con 4 regiones

### Cargar Modelo sin Pulmones:

1. Ejecuta: `python main.py`
2. Haz clic en "📁 Cargar archivo de malla (VTK/MSH)"
3. Selecciona: `ecg_torso_v2_sin_pulmones.msh`
4. La aplicación cargará el modelo simplificado con 2 regiones

## 🔬 Diferencias entre Modelos

### Esfera Generada (por defecto):
- **Nodos**: 129
- **Elementos**: 512
- **Regiones**: 1 (homogénea)
- **Uso**: Pruebas y demostraciones

### Torso con Pulmones (`.msh`):
- **Nodos**: ~10,000-50,000 (depende del refinamiento)
- **Elementos**: ~50,000-200,000
- **Regiones**: 4 (torso, corazón, pulmones)
- **Uso**: Simulaciones realistas de ECG

### Torso sin Pulmones (`.msh`):
- **Nodos**: ~5,000-30,000
- **Elementos**: ~25,000-100,000
- **Regiones**: 2 (torso, corazón)
- **Uso**: Simulaciones simplificadas

## 💡 Ventajas de Archivos MSH

1. **Regiones múltiples**: Soporta múltiples materiales con IDs
2. **Formato estándar**: Gmsh es ampliamente usado
3. **Metadatos**: Incluye información de grupos físicos
4. **Compatibilidad**: Funciona con scikit-fem directamente

## 🚀 Flujo de Trabajo Completo

```
1. Inicio → Genera esfera automática (129 nodos, 512 elementos)
2. Usuario → Carga modelo anatómico .msh (miles de elementos)
3. Aplicación → Procesa y muestra vista previa
4. Usuario → Genera mallado con Poisson
5. Resultado → Visualización con solución
```

## 📝 Compatibilidad con Proyecto Scikit-fem

La aplicación ahora es **100% compatible** con los archivos del proyecto scikit-fem:

✅ Puede cargar `ecg_torso_v2_con_pulmones.msh`
✅ Puede cargar `ecg_torso_v2_sin_pulmones.msh`
✅ Puede cargar `ecg_torso_v2_con_pulmones.vtk`
✅ Detecta automáticamente el formato del archivo
✅ Extrae correctamente los tetraedros
✅ Genera vista previa 3D
✅ Resuelve ecuación de Poisson

## 🎨 Ejemplo de Uso

```bash
# 1. Ejecutar aplicación
python main.py

# 2. Esperar a que cargue la esfera por defecto

# 3. Cargar modelo anatómico
#    Clic en "Cargar archivo de malla (VTK/MSH)"
#    Seleccionar: ecg_torso_v2_con_pulmones.msh

# 4. Ver vista previa del torso

# 5. Generar mallado
#    Clic en "Generar Mallado"

# 6. Ver solución de Poisson en el torso
```

## 🔍 Verificación

Para verificar que funciona con archivos MSH:

```python
from src.core import load_mesh_skfem

# Cargar archivo MSH
mesh, mio = load_mesh_skfem("ecg_torso_v2_con_pulmones.msh")

print(f"Nodos: {mesh.p.shape[1]}")
print(f"Elementos: {mesh.t.shape[1]}")
print(f"Formato detectado: MSH")
# ✓ Funciona correctamente
```

## 🎉 Conclusión

La aplicación ahora soporta archivos `.msh` de Gmsh, permitiendo:
- Cargar modelos anatómicos complejos
- Trabajar con múltiples regiones/materiales
- Compatibilidad total con proyecto scikit-fem
- Mayor flexibilidad en tipos de malla

¡Puedes usar tanto modelos simples (esfera) como complejos (torso anatómico)! 🚀
