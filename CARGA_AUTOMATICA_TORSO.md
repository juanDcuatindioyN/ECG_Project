# Carga Automática de Modelo de Torso

## ✅ Cambio Implementado

La aplicación ahora busca y carga automáticamente los archivos `.msh` del proyecto scikit-fem en lugar de generar una esfera.

## 🔍 Ubicaciones de Búsqueda

La aplicación busca los archivos en este orden:

1. **Carpeta actual del proyecto**:
   - `ecg_torso_v2_con_pulmones.msh`
   - `ecg_torso_v2_sin_pulmones.msh`

2. **Subcarpeta data/**:
   - `data/ecg_torso_v2_con_pulmones.msh`
   - `data/ecg_torso_v2_sin_pulmones.msh`

3. **Carpeta de scikit-fem descargada**:
   - `c:\Users\FRI-01\Downloads\scikit-fem\ProyectoECG\ecg_torso_v2_con_pulmones.msh`
   - `c:\Users\FRI-01\Downloads\scikit-fem\ProyectoECG\ecg_torso_v2_sin_pulmones.msh`

4. **Rutas relativas desde Downloads**:
   - `../../../Downloads/scikit-fem/ProyectoECG/ecg_torso_v2_con_pulmones.msh`
   - `../../Downloads/scikit-fem/ProyectoECG/ecg_torso_v2_con_pulmones.msh`

## 🎯 Comportamiento

### Si encuentra un archivo MSH:
```
Inicio → Busca archivos MSH → Encuentra → Carga modelo de torso → Vista previa 3D
```

### Si NO encuentra archivos MSH:
```
Inicio → Busca archivos MSH → No encuentra → Genera esfera → Vista previa 3D
```

## 📋 Prioridad de Carga

1. **Primera opción**: `ecg_torso_v2_con_pulmones.msh` (modelo completo)
2. **Segunda opción**: `ecg_torso_v2_sin_pulmones.msh` (modelo simplificado)
3. **Fallback**: Genera esfera proceduralmente

## 🔧 Cómo Asegurar que Cargue el Modelo

### Opción 1: Copiar archivos al proyecto
```bash
# Copiar desde Downloads a tu proyecto
copy "c:\Users\FRI-01\Downloads\scikit-fem\ProyectoECG\ecg_torso_v2_con_pulmones.msh" "c:\Users\FRI-01\Desktop\ECG_Project\"
```

### Opción 2: Crear carpeta data/
```bash
# Crear carpeta data
mkdir data

# Copiar archivos
copy "c:\Users\FRI-01\Downloads\scikit-fem\ProyectoECG\*.msh" "data\"
```

### Opción 3: Dejar en Downloads
La aplicación ya busca en:
```
c:\Users\FRI-01\Downloads\scikit-fem\ProyectoECG\
```

## 📊 Diferencias entre Modelos

### Torso CON Pulmones:
- **Archivo**: `ecg_torso_v2_con_pulmones.msh`
- **Regiones**: 4 (Torso, Corazón, Pulmón izq, Pulmón der)
- **Elementos**: ~50,000-200,000
- **Uso**: Simulaciones realistas completas

### Torso SIN Pulmones:
- **Archivo**: `ecg_torso_v2_sin_pulmones.msh`
- **Regiones**: 2 (Torso, Corazón)
- **Elementos**: ~25,000-100,000
- **Uso**: Simulaciones simplificadas más rápidas

### Esfera (Fallback):
- **Generada**: Proceduralmente con scikit-fem
- **Regiones**: 1 (homogénea)
- **Elementos**: 512
- **Uso**: Pruebas y demostraciones

## 🎨 Mensajes de la Aplicación

### Al Iniciar:
```
"Buscando modelo de torso..."
"Cargando modelo de torso..."
```

### Si encuentra modelo:
```
"Cargando archivo..."
"Malla cargada - Lista para generar mallado"
```

### Si NO encuentra modelo:
```
"No se encontró modelo de torso - Generando esfera..."
"Generando malla con scikit-fem..."
```

## 🚀 Flujo Completo

```
1. Usuario ejecuta: python main.py
2. Aplicación busca archivos MSH
3. Si encuentra:
   - Carga ecg_torso_v2_con_pulmones.msh
   - Muestra modelo de torso en 3D
   - Analiza complejidad
   - Detecta parámetros óptimos
4. Usuario presiona "Generar Mallado"
5. Resuelve Poisson en el torso
6. Muestra solución con colores
```

## 💡 Recomendación

Para mejor experiencia, copia los archivos MSH a tu proyecto:

```bash
# Desde PowerShell en la carpeta del proyecto
Copy-Item "c:\Users\FRI-01\Downloads\scikit-fem\ProyectoECG\ecg_torso_v2_con_pulmones.msh" .
Copy-Item "c:\Users\FRI-01\Downloads\scikit-fem\ProyectoECG\ecg_torso_v2_sin_pulmones.msh" .
```

Así la aplicación los encontrará inmediatamente.

## 🔍 Verificar qué Archivo Cargó

Mira el panel izquierdo "Información de Malla":
- Si dice "Esfera Procedural" → Generó esfera (no encontró MSH)
- Si dice "ecg_torso_v2_con_pulmones.msh" → Cargó modelo completo ✅
- Si dice "ecg_torso_v2_sin_pulmones.msh" → Cargó modelo simplificado ✅

## 🎉 Resultado

Ahora la aplicación:
- ✅ Busca automáticamente modelos de torso
- ✅ Carga el modelo si lo encuentra
- ✅ Genera esfera como fallback
- ✅ Muestra qué archivo cargó
- ✅ Funciona sin intervención del usuario

¡Listo para simular ECG en modelos anatómicos reales! 🚀
