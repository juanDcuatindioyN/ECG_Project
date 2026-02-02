# Proyecto ECG - Solucionador de Malla VTK con Poisson

Una aplicación interactiva para cargar archivos VTK, configurar parámetros de la ecuación de Poisson y visualizar la solución en 3D.

## Características

### 🎯 Interfaz Interactiva
- **Drag & Drop**: Arrastra archivos .vtk directamente a la aplicación
- **Vista Previa**: Visualiza la malla antes de resolver
- **Configuración en Tiempo Real**: Ajusta fuentes y cargas de Poisson
- **Visualización Integrada**: Gráficos 3D embebidos en la interfaz
- **Progreso Visual**: Barras de progreso para operaciones largas

### ⚡ Funcionalidades
- Carga y procesamiento de archivos VTK con mallas tetraédricas
- Resolución de la ecuación de Poisson con fuentes puntuales
- Proyección automática de fuentes al interior de la malla
- Visualización 3D interactiva con colores por potencial
- Información detallada de la malla (nodos, elementos, límites)

## Instalación

1. **Instalar dependencias básicas**:
```bash
pip install numpy matplotlib scikit-fem meshio
```

2. **[Opcional] Para Drag & Drop**:
```bash
pip install tkinterdnd2
```

3. **Verificar instalación**:
```bash
python test_app.py
```

4. **Ejecutar la aplicación**:
```bash
python app.py
```

## Uso

### 1. Cargar Archivo VTK
- **Opción 1**: Arrastra un archivo .vtk a la zona de drop
- **Opción 2**: Haz clic en "Seleccionar archivo VTK"

### 2. Configurar Parámetros de Poisson
- **Fuentes**: Coordenadas (x,y,z) de las fuentes puntuales
  - Formato: `x1,y1,z1` para una fuente
  - Formato: `x1,y1,z1;x2,y2,z2` para múltiples fuentes
- **Cargas**: Valores de carga para cada fuente
  - Formato: `q1` para una carga
  - Formato: `q1,q2` o `q1;q2` para múltiples cargas

### 3. Visualizar y Resolver
- **Vista Previa**: Muestra la geometría de la malla
- **Resolver Poisson**: Calcula y visualiza la solución

## Ejemplos de Parámetros

### Ejemplo 1: Fuente Simple
- **Fuentes**: `0.5,-0.4,0.1`
- **Cargas**: `1.0`

### Ejemplo 2: Múltiples Fuentes
- **Fuentes**: `0.5,-0.4,0.1;-0.2,0.3,0.0`
- **Cargas**: `1.0,-0.5`

## Estructura del Proyecto

```
├── app.py              # Interfaz gráfica principal
├── readVTK.py          # Funciones de procesamiento VTK y Poisson
├── Sphere.vtk          # Archivo de ejemplo
├── requirements.txt    # Dependencias
└── README.md          # Este archivo
```

## Dependencias

### Requeridas
- `numpy`: Cálculos numéricos
- `matplotlib`: Visualización 3D
- `scikit-fem`: Elementos finitos
- `meshio`: Lectura de archivos VTK

### Opcionales
- `tkinterdnd2`: Drag & Drop (si no está instalado, la funcionalidad se deshabilita automáticamente)

## Notas Técnicas

- Las fuentes se proyectan automáticamente al interior de la malla
- La ecuación resuelta es: ∇²V = ρ (Poisson) con fuentes puntuales
- La visualización muestra el potencial V en la superficie de la malla
- Los colores representan la intensidad del potencial

## Solución de Problemas

### ✅ La aplicación funciona sin tkinterdnd2
La aplicación detecta automáticamente si tkinterdnd2 está disponible. Si no está instalado:
- El drag & drop se deshabilita automáticamente
- La zona de drop se convierte en un botón clickeable
- Todas las demás funcionalidades siguen disponibles

### Error: "No module named 'tkinterdnd2'"
Este error ya no debería ocurrir. Si aparece, ejecuta:
```bash
python test_app.py
```
Para verificar que la aplicación funciona correctamente.

### Error: "No se fijó ningún nodo de Dirichlet"
Verifica que el archivo VTK contenga una malla válida con superficie.

### Error al parsear parámetros
Verifica el formato de fuentes y cargas según los ejemplos:
- Fuentes: `0.5,-0.4,0.1` o `0.5,-0.4,0.1;-0.2,0.3,0.0`
- Cargas: `1.0` o `1.0,-0.5`