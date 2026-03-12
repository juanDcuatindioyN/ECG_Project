#  Proyecto ECG - Simulador de ECG con FEM

Simulador completo del problema directo del electrocardiograma (ECG) usando el método de elementos finitos (FEM). Interfaz gráfica con generador automático de modelos anatómicos.

## Inicio Rapido

```bash
# Instalar dependencias
pip install -r requirements.txt

# Iniciar aplicación
python main.py
```

##  Estructura del Proyecto

```
ECG_Project/
├── src/                                      # Código fuente
│   ├── gui/                                  # Componentes de interfaz
│   ├── utils/                                # Utilidades
│   ├── visualization/                        # Visualización 3D
│   ├── interfaz_grafica_legacy.py           # GUI principal
│   ├── nucleo_poisson.py                    # Núcleo de Poisson
│   ├── solucionador_ecg.py                  # Solver ECG completo
│   └── generador_modelos_anatomicos.py      # Generador de modelos
├── docs/                                     # Documentación
├── examples/                                 # Ejemplos
├── tests/                                    # Tests
├── data/                                     # Archivos de malla
├── main.py                                   # Punto de entrada
└── requirements.txt                          # Dependencias
```

##  Formatos Soportados

VTK, Gmsh (.msh), STL, OBJ, PLY, OFF y más formatos gracias a **meshio**. Ver [docs/FORMATOS_SOPORTADOS.txt](docs/FORMATOS_SOPORTADOS.txt).

##  Estructura del Proyecto

```
ECG_Project/
├── src/                                      # Código fuente
│   ├── gui/                                  # Componentes de interfaz
│   ├── utils/                                # Utilidades
│   ├── visualization/                        # Visualización 3D
│   ├── interfaz_grafica_legacy.py           # GUI principal
│   ├── nucleo_poisson.py                    # Núcleo de Poisson
│   ├── solucionador_ecg.py                  # Solver ECG completo
│   └── generador_modelos_anatomicos.py      # Generador de modelos
├── docs/                                     # Documentación
├── examples/                                 # Ejemplos
├── tests/                                    # Tests
├── data/                                     # Archivos de malla
├── main.py                                   # Punto de entrada
└── requirements.txt                          # Dependencias
```

## Caracteristicas

- Interfaz gráfica con Tkinter
- Soporte multi-formato de mallas
- Generador automático de modelos anatómicos (torso, corazón, pulmones)
- Resolución de Poisson con fuentes puntuales
- Visualización 3D integrada
- Solver ECG completo con FEM (5 pasos)
- 12 derivaciones ECG estándar

##  Uso

### Interfaz Gráfica
```bash
python main.py
```

### Generar Modelo Automático
1. Clic en " Generar Modelo Automático"
2. Seleccionar "Con pulmones" o "Sin pulmones"
3. Clic en " Generar Malla"

### API Programática
```python
from src import SolucionadorECG

solver = SolucionadorECG('data/ecg_torso_v2_con_pulmones.msh')
resultados = solver.ejecutar_pipeline_completo()
derivaciones = resultados['ecg_data']['leads']
```

## Documentacion

- [QUICK_START.md](docs/QUICK_START.md) - Guía de inicio rápido
- [ECG_SOLVER_GUIDE.md](docs/ECG_SOLVER_GUIDE.md) - Guía técnica del solver
- [GENERADOR_AUTOMATICO.md](docs/GENERADOR_AUTOMATICO.md) - Guía del generador

## Dependencias

- numpy >= 1.19.0
- scipy >= 1.5.0
- matplotlib >= 3.3.0
- scikit-fem >= 3.0.0
- meshio >= 4.0.0

---

**Versión**: 3.0.0  
**Estado**:  Funcional
