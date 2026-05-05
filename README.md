# Proyecto ECG — Simulador del Problema Directo del ECG con FEM

Simulador del problema directo del electrocardiograma usando el método de elementos finitos (FEM). Incluye interfaz gráfica con flujo guiado de 5 pasos y generador automático de modelos anatómicos.

## Inicio rápido

### Opción 1 — Doble clic (recomendado)
Haz doble clic en **`iniciar.bat`**. Detecta Python automáticamente, instala dependencias si faltan y lanza la aplicación.

### Opción 2 — Consola
```bash
# Instalar dependencias (solo la primera vez)
python -m pip install -r requirements.txt

# Ejecutar
python main.py
```

## Requisitos

- Python **3.8 o superior** (3.9, 3.10, 3.11, 3.12, 3.13 — todos compatibles)
- Las dependencias se instalan automáticamente con `iniciar.bat`

## Estructura

```
ECG_Project/
├── iniciar.bat                      # Lanzador con doble clic
├── main.py                          # Punto de entrada
├── requirements.txt
├── data/                            # Mallas de entrada (.vtk, .msh)
├── examples/
│   └── demo_ecg_solver.py
├── tests/
└── src/
    ├── app.py                       # Interfaz gráfica (flujo de 5 pasos)
    ├── core/
    │   ├── mesh_loader.py
    │   └── ecg_solver.py
    ├── generation/
    │   └── mesh_generator.py
    └── visualization/
        └── viewer3d.py
```

## Flujo de uso (GUI)

1. **Cargar / Generar malla** — soporta VTK, MSH, STL, OBJ, PLY, OFF
2. **Configurar dipolo** — posición del dipolo cardíaco
3. **Ubicar electrodos** — coordenadas V1–V6
4. **Ejecutar simulación** — pipeline FEM completo
5. **Ver resultados** — señales ECG, mapa de potenciales animado, exportar VTK ASCII

## Exportar resultados

El botón **Exportar resultado (.vtk)** genera un archivo VTK ASCII legacy que puede abrirse en el Bloc de notas o en ParaView/VisIt.

## API programática

```python
from src.core.ecg_solver import ECGSolver

solver = ECGSolver('data/ecg_torso_v2_con_pulmones.msh')
results = solver.run_full_pipeline()
leads = results['ecg_data']['leads']
```

---
**Versión**: 3.0.0 | **Python**: 3.8+
