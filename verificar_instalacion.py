#!/usr/bin/env python3
"""
Script de verificación de instalación
"""

print("=" * 60)
print("VERIFICACIÓN DE INSTALACIÓN - Proyecto ECG")
print("=" * 60)

# Verificar Python
import sys
print(f"\n✓ Python {sys.version}")
print(f"  Ejecutable: {sys.executable}")

# Verificar dependencias
dependencias = {
    'numpy': 'Cálculos numéricos',
    'matplotlib': 'Visualización 3D',
    'scikit-fem': 'Elementos finitos (skfem)',
    'meshio': 'Lectura de archivos VTK',
    'tkinter': 'Interfaz gráfica'
}

print("\nVerificando dependencias:")
print("-" * 60)

faltantes = []
for modulo, descripcion in dependencias.items():
    try:
        if modulo == 'scikit-fem':
            __import__('skfem')
        else:
            __import__(modulo)
        print(f"✓ {modulo:20s} - {descripcion}")
    except ImportError:
        print(f"✗ {modulo:20s} - {descripcion} (FALTA)")
        faltantes.append(modulo)

print("\n" + "=" * 60)

if faltantes:
    print("\n❌ FALTAN DEPENDENCIAS")
    print("\nPara instalar las dependencias faltantes, ejecuta:")
    print("\n  pip install " + " ".join(faltantes))
    print("\nO instala todas las dependencias con:")
    print("\n  pip install -r requirements.txt")
else:
    print("\n✅ TODAS LAS DEPENDENCIAS ESTÁN INSTALADAS")
    print("\nPuedes ejecutar la aplicación con:")
    print("\n  python main.py")

print("\n" + "=" * 60)
