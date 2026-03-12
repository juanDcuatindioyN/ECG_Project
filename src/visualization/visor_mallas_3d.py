# -*- coding: utf-8 -*-
"""
Visor de Mallas 3D con Materiales
==================================

Este módulo proporciona funciones para visualizar mallas 3D con
diferentes materiales usando Poly3DCollection de matplotlib.

Funciones principales:
- crear_figura_3d: Crea una figura 3D completa con todos los materiales
- extraer_etiquetas_materiales: Extrae IDs de material de la malla
- extraer_triangulos_superficie: Extrae triángulos de superficie

Autor: Proyecto ECG
"""
import numpy as np
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from matplotlib.colors import to_rgba
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
from collections import Counter


# Configuración de colores por material (ID: (color_hex, nombre, transparencia))
COLORES_MATERIALES = {
    4: ('#2ECC71', 'Pulmon der', 0.4),
    3: ('#F39C12', 'Pulmon izq', 0.4),
    2: ('#E74C3C', 'Corazon', 0.5),
    1: ('#5DADE2', 'Torso', 0.2),
}

# Configuración con mayor transparencia para visualizar electrodos internos
COLORES_MATERIALES_TRANSPARENTE = {
    4: ('#2ECC71', 'Pulmon der', 0.15),
    3: ('#F39C12', 'Pulmon izq', 0.15),
    2: ('#E74C3C', 'Corazon', 0.25),
    1: ('#5DADE2', 'Torso', 0.08),
}


def extraer_etiquetas_materiales(mio):
    """
    Extrae etiquetas de material de la malla.
    
    Args:
        mio: Objeto meshio
        
    Returns:
        np.array: Etiquetas de material o None
    """
    mat_labels = None
    
    if hasattr(mio, 'cell_data_dict'):
        datos = mio.cell_data_dict
        
        if "gmsh:physical" in datos and "tetra" in datos["gmsh:physical"]:
            mat_labels = datos["gmsh:physical"]["tetra"].flatten().astype(int)
        elif mat_labels is None:
            for clave, bloques in datos.items():
                if "tetra" in bloques:
                    arr = bloques["tetra"].flatten()
                    vals = np.unique(arr)
                    if len(vals) <= 20 and arr.min() >= 0:
                        mat_labels = arr.astype(int)
                        break
    
    return mat_labels


def extraer_triangulos_superficie(tetraedros, mascara_material, max_triangulos=500):
    """
    Extrae triángulos de superficie de tetraedros con reducción para rendimiento.
    
    Identifica las caras que aparecen solo una vez (superficie externa)
    contando las apariciones de cada cara triangular, y luego reduce
    el número de triángulos para mejorar el rendimiento.
    
    Args:
        tetraedros: Array de tetraedros (elementos 3D)
        mascara_material: Máscara booleana para filtrar por material
        max_triangulos: Número máximo de triángulos a retornar (para rendimiento)
        
    Returns:
        np.array: Triángulos de superficie reducidos o None si no hay
    """
    tetraedros_material = tetraedros[mascara_material]
    
    lista_caras = []
    for tet in tetraedros_material:
        lista_caras.append(tuple(sorted([tet[0], tet[1], tet[2]])))
        lista_caras.append(tuple(sorted([tet[0], tet[1], tet[3]])))
        lista_caras.append(tuple(sorted([tet[0], tet[2], tet[3]])))
        lista_caras.append(tuple(sorted([tet[1], tet[2], tet[3]])))
    
    conteo_caras = Counter(lista_caras)
    caras_superficie = [cara for cara, conteo in conteo_caras.items() if conteo == 1]
    
    if not caras_superficie:
        return None
    
    caras_array = np.array(caras_superficie)
    
    # OPTIMIZACIÓN: Reducir número de triángulos para mejor rendimiento
    if len(caras_array) > max_triangulos:
        # Muestreo uniforme para mantener distribución
        indices = np.linspace(0, len(caras_array) - 1, max_triangulos, dtype=int)
        caras_array = caras_array[indices]
    
    return caras_array


def crear_figura_3d(malla, mio, incluir_pulmones=False):
    """
    Crea figura 3D con visualización por materiales usando Poly3DCollection.
    
    Esta función crea una visualización 3D completa mostrando todos los
    materiales simultáneamente con colores y transparencias configurables.
    Estilo sólido y opaco para mejor visualización.
    
    Args:
        malla: Malla scikit-fem (MeshTet)
        mio: Objeto meshio con datos de la malla
        incluir_pulmones: Si True, incluye pulmones en la visualización
        
    Returns:
        Figure: Figura de matplotlib lista para mostrar
        
    Raises:
        ValueError: Si no se encuentran tetraedros en la malla
    """
    fig = Figure(figsize=(8, 6), dpi=80)  # DPI reducido para mejor rendimiento
    ax = fig.add_subplot(111, projection='3d')
    
    X = malla.p.T
    etiquetas_mat = extraer_etiquetas_materiales(mio)
    
    if etiquetas_mat is not None and len(etiquetas_mat) > 0:
        tetraedros = mio.cells_dict.get('tetra')
        if tetraedros is None:
            raise ValueError("No se encontraron tetraedros en la malla")
        
        colecciones = []
        manejadores_leyenda = []
        
        # Procesar materiales en orden: órganos primero, torso último
        # Diferentes límites de triángulos según material para optimizar rendimiento
        limites_triangulos = {
            1: 300,  # Torso (más grande, menos triángulos)
            2: 400,  # Corazón
            3: 350,  # Pulmón izq
            4: 350,  # Pulmón der
        }
        
        for id_material in [4, 3, 2, 1]:
            if id_material not in COLORES_MATERIALES:
                continue
            if id_material not in np.unique(etiquetas_mat):
                continue
            
            color, nombre, alfa = COLORES_MATERIALES[id_material]
            mascara_material = etiquetas_mat == id_material
            
            if not mascara_material.any():
                continue
            
            # Usar límite específico por material
            max_tris = limites_triangulos.get(id_material, 400)
            triangulos_sup = extraer_triangulos_superficie(tetraedros, mascara_material, max_tris)
            if triangulos_sup is None:
                continue
            
            vertices = [[X[tri[0]], X[tri[1]], X[tri[2]]] for tri in triangulos_sup]
            color_rgba = to_rgba(color, alpha=alfa)
            
            # Renderizado optimizado con malla visible
            coleccion = Poly3DCollection(vertices, 
                                        facecolors=color_rgba,
                                        edgecolors='gray',
                                        linewidths=0.2,  # Líneas más finas
                                        shade=False,     # Sin sombreado para más velocidad
                                        antialiased=False)  # Sin antialiasing para más velocidad
            colecciones.append(coleccion)
            manejadores_leyenda.append(mpatches.Patch(color=color, alpha=alfa, label=nombre))
        
        # Agregar todas las colecciones al axes de una vez
        for coleccion in colecciones:
            ax.add_collection3d(coleccion)
        
        # Configurar límites del axes
        ax.set_xlim(X[:, 0].min(), X[:, 0].max())
        ax.set_ylim(X[:, 1].min(), X[:, 1].max())
        ax.set_zlim(X[:, 2].min(), X[:, 2].max())
        ax.legend(handles=manejadores_leyenda, loc='upper right', fontsize=9, 
                 framealpha=0.95, edgecolor='gray', fancybox=True)
    
    tipo = "con pulmones" if incluir_pulmones else "sin pulmones"
    ax.set_title(f"Modelo Generado ({tipo})", fontsize=12, fontweight='bold', pad=20)
    ax.set_xlabel("X (m)", fontsize=9)
    ax.set_ylabel("Y (m)", fontsize=9)
    ax.set_zlabel("Z (m)", fontsize=9)
    ax.view_init(elev=25, azim=45)
    ax.set_box_aspect([1,1,1])
    
    # Configuración de grid y fondo (desactivado para mejor rendimiento)
    ax.grid(False)  # Grid desactivado
    ax.xaxis.pane.fill = False
    ax.yaxis.pane.fill = False
    ax.zaxis.pane.fill = False
    ax.xaxis.pane.set_edgecolor('lightgray')
    ax.yaxis.pane.set_edgecolor('lightgray')
    ax.zaxis.pane.set_edgecolor('lightgray')
    
    # Reducir número de ticks para mejor rendimiento
    ax.xaxis.set_major_locator(plt.MaxNLocator(5))
    ax.yaxis.set_major_locator(plt.MaxNLocator(5))
    ax.zaxis.set_major_locator(plt.MaxNLocator(5))
    
    fig.tight_layout()
    return fig


def crear_figura_3d_con_electrodos(malla, mio, sources, incluir_pulmones=False):
    """
    Crea figura 3D con visualización por materiales y electrodos visibles.
    
    Esta función es similar a crear_figura_3d pero con transparencias aumentadas
    para permitir ver los electrodos internos. También dibuja líneas desde los
    electrodos internos hacia afuera para mejor visualización.
    
    Args:
        malla: Malla scikit-fem (MeshTet)
        mio: Objeto meshio con datos de la malla
        sources: Array de coordenadas de electrodos (N x 3)
        incluir_pulmones: Si True, incluye pulmones en la visualización
        
    Returns:
        Figure: Figura de matplotlib lista para mostrar
        
    Raises:
        ValueError: Si no se encuentran tetraedros en la malla
    """
    fig = Figure(figsize=(8, 6), dpi=80)
    ax = fig.add_subplot(111, projection='3d')
    
    X = malla.p.T
    etiquetas_mat = extraer_etiquetas_materiales(mio)
    
    if etiquetas_mat is not None and len(etiquetas_mat) > 0:
        tetraedros = mio.cells_dict.get('tetra')
        if tetraedros is None:
            raise ValueError("No se encontraron tetraedros en la malla")
        
        colecciones = []
        manejadores_leyenda = []
        
        # Usar configuración con mayor transparencia
        limites_triangulos = {
            1: 300,
            2: 400,
            3: 350,
            4: 350,
        }
        
        for id_material in [4, 3, 2, 1]:
            if id_material not in COLORES_MATERIALES_TRANSPARENTE:
                continue
            if id_material not in np.unique(etiquetas_mat):
                continue
            
            color, nombre, alfa = COLORES_MATERIALES_TRANSPARENTE[id_material]
            mascara_material = etiquetas_mat == id_material
            
            if not mascara_material.any():
                continue
            
            max_tris = limites_triangulos.get(id_material, 400)
            triangulos_sup = extraer_triangulos_superficie(tetraedros, mascara_material, max_tris)
            if triangulos_sup is None:
                continue
            
            vertices = [[X[tri[0]], X[tri[1]], X[tri[2]]] for tri in triangulos_sup]
            color_rgba = to_rgba(color, alpha=alfa)
            
            coleccion = Poly3DCollection(vertices, 
                                        facecolors=color_rgba,
                                        edgecolors='gray',
                                        linewidths=0.1,
                                        shade=False,
                                        antialiased=False)
            colecciones.append(coleccion)
            manejadores_leyenda.append(mpatches.Patch(color=color, alpha=alfa, label=nombre))
        
        # Agregar todas las colecciones al axes
        for coleccion in colecciones:
            ax.add_collection3d(coleccion)
        
        # Configurar límites del axes
        ax.set_xlim(X[:, 0].min(), X[:, 0].max())
        ax.set_ylim(X[:, 1].min(), X[:, 1].max())
        ax.set_zlim(X[:, 2].min(), X[:, 2].max())
    
    # Agregar electrodos si existen
    if sources is not None:
        S = np.asarray(sources, dtype=float)
        if S.size > 0:
            print(f"\n=== DIBUJANDO {len(S)} ELECTRODOS ===")
            for i, (x, y, z) in enumerate(S):
                print(f"Electrodo {i+1}: ({x:.6f}, {y:.6f}, {z:.6f})")
            
            # Verificar si hay electrodos duplicados
            if len(S) > 1:
                distancias = []
                for i in range(len(S)):
                    for j in range(i+1, len(S)):
                        dist = np.linalg.norm(S[i] - S[j])
                        distancias.append(dist)
                        if dist < 0.001:  # Menos de 1mm
                            print(f"⚠️ ADVERTENCIA: Electrodos {i+1} y {j+1} están muy cerca ({dist*1000:.2f}mm)")
                
                print(f"Distancia promedio entre electrodos: {np.mean(distancias)*1000:.2f}mm")
            
            # Calcular centro del modelo
            centro = X.mean(axis=0)
            
            # Dibujar líneas desde cada electrodo hacia el exterior
            for i, (x, y, z) in enumerate(S):
                # Vector desde el centro hacia el electrodo
                direccion = np.array([x, y, z]) - centro
                direccion_norm = direccion / (np.linalg.norm(direccion) + 1e-10)
                
                # Punto externo (proyectado hacia afuera)
                punto_externo = np.array([x, y, z]) + direccion_norm * 0.05
                
                # Dibujar línea punteada desde electrodo hacia afuera
                ax.plot([x, punto_externo[0]], 
                       [y, punto_externo[1]], 
                       [z, punto_externo[2]], 
                       'r--', linewidth=1.5, alpha=0.6, zorder=999)
            
            # Dibujar puntos rojos grandes para los electrodos
            # Si están muy cerca, agregar pequeño offset para visualización
            S_visual = S.copy()
            if len(S) > 1:
                for i in range(len(S)):
                    for j in range(i+1, len(S)):
                        if np.linalg.norm(S[i] - S[j]) < 0.001:
                            # Agregar pequeño offset en espiral para separar visualmente
                            angle = i * 2 * np.pi / len(S)
                            offset = np.array([
                                0.003 * np.cos(angle),
                                0.003 * np.sin(angle),
                                0.002 * (i - len(S)/2)
                            ])
                            S_visual[i] += offset
                            print(f"Aplicando offset visual a electrodo {i+1}")
            
            ax.scatter(S_visual[:, 0], S_visual[:, 1], S_visual[:, 2], 
                      s=250, c="red", marker='o', 
                      label=f"Electrodos ({len(S)})", 
                      edgecolors='darkred', linewidth=2.5,
                      zorder=1000, alpha=1.0)
            
            # Agregar etiquetas numéricas a cada electrodo
            for i, (x, y, z) in enumerate(S_visual):
                ax.text(x, y, z, f'  E{i+1}', 
                       fontsize=10, color='darkred', 
                       fontweight='bold', zorder=1001,
                       bbox=dict(boxstyle='round,pad=0.3', 
                                facecolor='white', 
                                edgecolor='darkred',
                                alpha=0.8))
            
            # Agregar electrodo a la leyenda
            manejadores_leyenda.append(mpatches.Patch(color='red', alpha=1.0, 
                                                     label=f'Electrodos ({len(S)})'))
            
            print("=" * 40 + "\n")
        
        # Actualizar leyenda
        ax.legend(handles=manejadores_leyenda, loc='upper right', fontsize=9, 
                 framealpha=0.95, edgecolor='gray', fancybox=True)
    
    tipo = "con pulmones" if incluir_pulmones else "sin pulmones"
    ax.set_title(f"Solución con Electrodos ({tipo})", fontsize=12, fontweight='bold', pad=20)
    ax.set_xlabel("X (m)", fontsize=9)
    ax.set_ylabel("Y (m)", fontsize=9)
    ax.set_zlabel("Z (m)", fontsize=9)
    ax.view_init(elev=25, azim=45)
    ax.set_box_aspect([1,1,1])
    
    # Configuración de grid y fondo
    ax.grid(False)
    ax.xaxis.pane.fill = False
    ax.yaxis.pane.fill = False
    ax.zaxis.pane.fill = False
    ax.xaxis.pane.set_edgecolor('lightgray')
    ax.yaxis.pane.set_edgecolor('lightgray')
    ax.zaxis.pane.set_edgecolor('lightgray')
    
    ax.xaxis.set_major_locator(plt.MaxNLocator(5))
    ax.yaxis.set_major_locator(plt.MaxNLocator(5))
    ax.zaxis.set_major_locator(plt.MaxNLocator(5))
    
    fig.tight_layout()
    return fig
