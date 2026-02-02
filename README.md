# Proyecto ECG - Solucionador de Malla VTK con Poisson

Una aplicación interactiva profesional para resolver ecuaciones de Poisson en mallas VTK con interfaz gráfica moderna y visualización 3D integrada.

## Inicio Rápido

```bash
# Clonar e instalar
git clone <repository-url>
cd ECG_Project
pip install -r requirements.txt

# Ejecutar aplicación
python main.py

# Ejecutar pruebas
python main.py --test

# Ver demostración
python main.py --demo
```

## Características

### Interfaz Moderna
- **Drag & Drop**: Arrastra archivos .vtk directamente
- **Visualización integrada**: Gráficos 3D embebidos
- **Procesamiento asíncrono**: Sin bloqueo de interfaz
- **Barras de progreso**: Feedback visual en tiempo real

### Resolución Automática
- **Ecuaciones de Poisson** con fuentes puntuales
- **Detección automática** de parámetros óptimos
- **Múltiples fuentes** configurables
- **Proyección automática** al interior de mallas
- **Visualización 3D** con colores por potencial

### Arquitectura Profesional
- **Código modular** bien organizado
- **Suite de pruebas** completa
- **Documentación** detallada
- **Manejo robusto** de errores

## Estructura del Proyecto

```
ECG_Project/
├── src/                    # Código fuente principal
│   ├── __init__.py        # Módulo principal
│   ├── core.py            # Funciones de procesamiento VTK/Poisson
│   ├── gui_safe.py        # Interfaz gráfica automática
│   └── utils.py           # Utilidades
├── tests/                  # Suite de pruebas
│   ├── test_core.py       # Pruebas del módulo core
│   ├── test_gui.py        # Pruebas de interfaz
│   └── run_all_tests.py   # Ejecutor de todas las pruebas
├── examples/               # Ejemplos y demostraciones
│   └── demo_automatic.py  # Demostración automática
├── docs/                   # Documentación
│   ├── AUTOMATIC_FEATURES.md
│   └── PROJECT_STRUCTURE.md
├── data/                   # Archivos de datos
│   └── Sphere.vtk         # Malla de ejemplo
├── main.py                 # Punto de entrada principal
└── requirements.txt        # Dependencias
```

## Uso de la Aplicación

### 1. Cargar Archivo VTK
- **Drag & Drop**: Arrastra `data/Sphere.vtk` a la zona de drop
- **Botón**: Haz clic en "Seleccionar archivo VTK"

### 2. Resolución Automática
- La aplicación detecta automáticamente parámetros óptimos
- Resuelve la ecuación de Poisson inmediatamente
- Muestra visualización 3D integrada

### 3. Opciones Avanzadas
- **Vista Previa**: Ver geometría de la malla
- **Resolver Automáticamente**: Usar parámetros detectados
- **Resolver Manualmente**: Ajustar parámetros si es necesario

## Ejemplos de Configuración

| Configuración | Descripción | Fuentes Detectadas |
|---------------|-------------|-------------------|
| **Simple** | Malla básica | 1 fuente central |
| **Moderada** | Malla estándar | 2 fuentes (dipolo) |
| **Compleja** | Malla avanzada | 3 fuentes (triangular) |
| **Muy Compleja** | Malla detallada | 4+ fuentes (tetraédrica) |

## Pruebas y Verificación

```bash
# Ejecutar todas las pruebas
python main.py --test

# Pruebas específicas
python tests/test_core.py      # Pruebas del módulo core
python tests/test_gui.py       # Pruebas de interfaz

# Verificación completa
python tests/run_all_tests.py
```

## Dependencias

### Requeridas
- `numpy` - Cálculos numéricos
- `matplotlib` - Visualización 3D
- `scikit-fem` - Elementos finitos
- `meshio` - Lectura de archivos VTK

### Opcionales
- `tkinterdnd2` - Drag & Drop (se deshabilita automáticamente si no está disponible)

## Instalación Detallada

### Opción 1: Instalación Básica
```bash
pip install numpy matplotlib scikit-fem meshio
python main.py
```

### Opción 2: Instalación Completa (con Drag & Drop)
```bash
pip install numpy matplotlib scikit-fem meshio tkinterdnd2
python main.py
```

### Verificar Instalación
```bash
python main.py --test
```

## Comandos Disponibles

| Comando | Descripción |
|---------|-------------|
| `python main.py` | Ejecutar interfaz gráfica |
| `python main.py --test` | Ejecutar todas las pruebas |
| `python main.py --demo` | Ver demostración de capacidades |
| `python main.py --info` | Mostrar información del proyecto |
| `python main.py --help` | Mostrar ayuda |

## Arquitectura Técnica

### Módulos Principales

- **`src/core.py`**: Funciones de procesamiento VTK y resolución de Poisson
- **`src/gui_safe.py`**: Interfaz gráfica automática con Tkinter y matplotlib
- **`src/utils.py`**: Utilidades y funciones auxiliares

### Flujo de Trabajo

1. **Carga**: Archivo VTK → scikit-fem mesh
2. **Análisis**: Detección automática de parámetros óptimos
3. **Resolución**: Ecuación de Poisson con elementos finitos
4. **Visualización**: Superficie 3D con colores por potencial

## Contribución

El proyecto está organizado de manera modular para facilitar contribuciones:

- **Nuevas características**: Agregar en `src/`
- **Pruebas**: Agregar en `tests/`
- **Ejemplos**: Agregar en `examples/`
- **Documentación**: Actualizar en `docs/`

## Estado del Proyecto

**Completamente funcional** - Todas las pruebas pasan  
**Interfaz moderna** - Resolución automática de Poisson  
**Código organizado** - Estructura modular profesional  
**Bien documentado** - Documentación completa y ejemplos  

---

Para más información detallada, consulta la documentación en `docs/`