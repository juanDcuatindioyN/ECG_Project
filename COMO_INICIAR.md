# Cómo Iniciar el Proyecto ECG

## Problema Actual

El error que estás viendo es: **"ModuleNotFoundError: No module named 'numpy'"**

Esto significa que Python no tiene instaladas las dependencias necesarias.

## Solución Rápida

### Paso 1: Verificar Python

Abre una terminal (PowerShell o CMD) y ejecuta:

```bash
python --version
```

**Si ves un error** o dice "no se encontró Python":
- Lee el archivo `SOLUCION_PYTHON.md` para instalar Python correctamente

**Si ves la versión de Python** (ej: Python 3.10.0):
- Continúa al Paso 2

### Paso 2: Instalar Dependencias

Tienes 3 opciones:

#### Opción A: Script Automático (Windows)
```bash
instalar_dependencias.bat
```

#### Opción B: Comando Manual
```bash
pip install numpy matplotlib scikit-fem meshio
```

#### Opción C: Desde requirements.txt
```bash
pip install -r requirements.txt
```

### Paso 3: Verificar Instalación

```bash
python verificar_instalacion.py
```

Este script te dirá si falta alguna dependencia.

### Paso 4: Ejecutar la Aplicación

```bash
python main.py
```

## ¿Qué Hace la Aplicación?

Al iniciar, la aplicación:

1. ✨ **Genera automáticamente** una malla esférica 3D
2. 📊 **Muestra la geometría** en un gráfico 3D interactivo
3. 🔍 **Analiza la malla** y detecta parámetros óptimos
4. ⚡ **Espera tu acción**: Presiona "Generar Mallado" para resolver la ecuación de Poisson

## Flujo de Trabajo

```
Inicio → Malla Automática → Vista 3D → [Generar Mallado] → Solución de Poisson
```

## Características

- 🎯 **Sin archivos requeridos**: Genera malla automáticamente
- 🖼️ **Visualización inmediata**: Ver geometría al instante
- 🔧 **Botón principal**: "Generar Mallado" para resolver Poisson
- 📁 **Carga opcional**: Puedes cargar archivos VTK personalizados
- ⚙️ **Opciones avanzadas**: Ajustar parámetros manualmente

## Solución de Problemas

### Error: "python no se reconoce"
- Python no está instalado o no está en el PATH
- Lee `SOLUCION_PYTHON.md`

### Error: "No module named 'X'"
- Falta instalar dependencias
- Ejecuta: `pip install numpy matplotlib scikit-fem meshio`

### Error: "pip no se reconoce"
- Python no está correctamente instalado
- Reinstala Python desde python.org marcando "Add to PATH"

### La ventana no se abre
- Verifica que tkinter esté instalado (viene con Python)
- En Linux: `sudo apt-get install python3-tk`

## Archivos de Ayuda

- `SOLUCION_PYTHON.md` - Guía para instalar Python correctamente
- `CAMBIOS_REALIZADOS.md` - Documentación de los cambios en el proyecto
- `verificar_instalacion.py` - Script para verificar dependencias
- `instalar_dependencias.bat` - Instalador automático (Windows)

## Comandos Útiles

```bash
# Ver versión de Python
python --version

# Ver versión de pip
pip --version

# Listar paquetes instalados
pip list

# Instalar una dependencia específica
pip install numpy

# Actualizar una dependencia
pip install --upgrade numpy

# Desinstalar una dependencia
pip uninstall numpy
```

## Contacto y Soporte

Si después de seguir estos pasos sigues teniendo problemas:

1. Verifica que Python esté instalado correctamente
2. Verifica que pip funcione
3. Ejecuta `python verificar_instalacion.py` para ver qué falta
4. Lee `SOLUCION_PYTHON.md` para problemas comunes

## Próximos Pasos

Una vez que la aplicación funcione:

1. Explora la interfaz
2. Genera el mallado con el botón principal
3. Prueba cargar archivos VTK personalizados
4. Experimenta con opciones avanzadas
