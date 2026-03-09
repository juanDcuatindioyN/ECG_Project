# Solución: Python no funciona correctamente

## Problema Detectado

Python está instalado desde Microsoft Store, lo cual puede causar problemas de ejecución.

**Ubicación detectada**: `C:\Users\FRI-01\AppData\Local\Microsoft\WindowsApps\python.exe`

## Soluciones

### Opción 1: Instalar Python desde python.org (RECOMENDADO)

1. Desinstala Python de Microsoft Store:
   - Abre "Configuración" → "Aplicaciones"
   - Busca "Python" y desinstálalo

2. Descarga Python oficial:
   - Ve a https://www.python.org/downloads/
   - Descarga Python 3.10 o superior
   - **IMPORTANTE**: Durante la instalación, marca "Add Python to PATH"

3. Verifica la instalación:
   ```bash
   python --version
   ```

4. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
   ```

### Opción 2: Deshabilitar alias de Microsoft Store

1. Abre "Configuración" → "Aplicaciones"
2. Ve a "Configuración avanzada de aplicaciones"
3. Haz clic en "Alias de ejecución de aplicaciones"
4. Desactiva los alias de Python

### Opción 3: Usar Python directamente (temporal)

Si tienes Python instalado en otro lugar, puedes usarlo directamente:

```bash
# Buscar todas las instalaciones de Python
where.exe python

# Usar una instalación específica
C:\Python310\python.exe main.py
```

## Verificar que todo funciona

Después de instalar Python correctamente:

```bash
# 1. Verificar Python
python --version

# 2. Verificar pip
pip --version

# 3. Instalar dependencias
pip install numpy matplotlib scikit-fem meshio

# 4. Verificar instalación
python verificar_instalacion.py

# 5. Ejecutar aplicación
python main.py
```

## Dependencias Requeridas

El proyecto necesita:
- `numpy` - Cálculos numéricos
- `matplotlib` - Visualización 3D
- `scikit-fem` - Elementos finitos
- `meshio` - Lectura de archivos VTK
- `tkinter` - Interfaz gráfica (incluido con Python)

## Instalación Rápida

```bash
pip install numpy matplotlib scikit-fem meshio
```

O usando el archivo requirements.txt:

```bash
pip install -r requirements.txt
```

## Problemas Comunes

### "No module named 'numpy'"
```bash
pip install numpy
```

### "No module named 'skfem'"
```bash
pip install scikit-fem
```

### "pip no se reconoce"
Python no está en el PATH. Reinstala Python marcando "Add to PATH".

### "python no se reconoce"
Python no está instalado o no está en el PATH.

## Contacto

Si sigues teniendo problemas, verifica:
1. Python está instalado correctamente
2. Python está en el PATH del sistema
3. pip funciona correctamente
4. Las dependencias están instaladas
