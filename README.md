# Proyecto ECG — Simulador del Problema Directo del ECG con FEM

Simulador del problema directo del electrocardiograma usando el método de elementos finitos (FEM). Incluye interfaz gráfica con flujo guiado de 5 pasos y generador automático de modelos anatómicos.

## Requisitos

- Python 3.13
- Dependencias: `pip install -r requirements.txt`

```bash
py -3.13 -m pip install -r requirements.txt
py -3.13 main.py
```

## Estructura

```
ECG_Project/
├── main.py                          # Punto de entrada
├── requirements.txt
├── data/                            # Mallas de entrada (.vtk, .msh)
├── output/                          # Resultados generados (imágenes, CSV)
├── examples/
│   └── demo_ecg_solver.py           # Demo del pipeline completo
├── tests/
│   ├── test_core.py
│   ├── test_gui.py
│   └── run_all_tests.py
└── src/
    ├── app.py                       # Interfaz gráfica (flujo de 5 pasos)
    ├── core/
    │   ├── mesh_loader.py           # Carga de mallas + resolución de Poisson
    │   └── ecg_solver.py            # Pipeline FEM completo
    ├── generation/
    │   └── mesh_generator.py        # Generador de modelos anatómicos (Gmsh)
    └── visualization/
        └── viewer3d.py              # Visualización 3D con Poly3DCollection
```

## Flujo de uso (GUI)

1. **Cargar / Generar malla** — soporta VTK, MSH, STL, OBJ, PLY, OFF
2. **Configurar dipolo** — posición del dipolo cardíaco
3. **Ubicar electrodos** — coordenadas V1–V6
4. **Ejecutar simulación** — pipeline FEM de 5 pasos
5. **Ver resultados** — señales ECG y mapa de potenciales

## API programática

```python
from src.core.ecg_solver import ECGSolver

solver = ECGSolver('data/ecg_torso_v2_con_pulmones.msh')
results = solver.run_full_pipeline()
leads = results['ecg_data']['leads']
```

## Tests

```bash
py -3.13 -m tests.run_all_tests
```

## Demo

```bash
py -3.13 -m examples.demo_ecg_solver
```

---
**Versión**: 3.0.0 | **Python**: 3.13
