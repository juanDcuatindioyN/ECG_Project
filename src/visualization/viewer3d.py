# -*- coding: utf-8 -*-
"""
Visor de Mallas 3D con Materiales
==================================

Proporciona funciones para visualizar mallas 3D con diferentes materiales
usando Poly3DCollection de matplotlib.

Funciones principales:
- crear_figura_3d: Crea una figura 3D completa con todos los materiales
- extraer_etiquetas_materiales: Extrae IDs de material de la malla
- extraer_triangulos_superficie: Extrae triángulos de superficie

Autor: Proyecto ECG
"""
import logging
import numpy as np
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from matplotlib.colors import to_rgba
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
from collections import Counter

logger = logging.getLogger(__name__)


# Colores por material (ID: (color_hex, nombre, alpha))
# Torso con alpha moderado para ver la forma pero también los órganos internos
COLORES_MATERIALES = {
    4: ('#2ECC71', 'Pulmon der', 0.65),
    3: ('#F39C12', 'Pulmon izq', 0.65),
    2: ('#E74C3C', 'Corazon',    0.80),
    1: ('#5DADE2', 'Torso',      0.55),
}

# Con mayor transparencia para cuando se muestran electrodos encima
COLORES_MATERIALES_TRANSPARENTE = {
    4: ('#2ECC71', 'Pulmon der', 0.35),
    3: ('#F39C12', 'Pulmon izq', 0.35),
    2: ('#E74C3C', 'Corazon',    0.45),
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

    # Submuestreo espacialmente uniforme (aleatorio con semilla fija)
    if len(caras_array) > max_triangulos:
        rng = np.random.default_rng(42)
        idx = rng.choice(len(caras_array), max_triangulos, replace=False)
        caras_array = caras_array[idx]

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
                                        linewidths=0.2,
                                        shade=False,
                                        antialiased=False)
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
            # Verificar si hay electrodos duplicados
            if len(S) > 1:
                for i in range(len(S)):
                    for j in range(i+1, len(S)):
                        dist = np.linalg.norm(S[i] - S[j])
                        if dist < 0.001:  # Menos de 1mm
                            print(f"ADVERTENCIA: Electrodos {i+1} y {j+1} están muy cerca ({dist*1000:.2f}mm)")
            
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


# ─────────────────────────────────────────────
# Figura de resultados: electrodos + mapa 2D
# ─────────────────────────────────────────────

def plot_electrodes_on_torso(mesh, mio, electrode_nodes, surface_nodes,
                              PHI=None, instant_idx=4):
    """
    Figura con vista 3D del torso con electrodos y mapa 2D de potenciales.

    Args:
        mesh: MeshTet de scikit-fem
        mio: Objeto meshio
        electrode_nodes: dict {nombre: indice_nodo}
        surface_nodes: array de indices de nodos en la superficie
        PHI: Potenciales (N, T), opcional
        instant_idx: Instante a mostrar en el mapa 2D

    Returns:
        matplotlib.figure.Figure
    """
    import os
    import matplotlib.patches as mpatches
    from matplotlib.colors import to_rgba
    from collections import Counter

    MAT_CONFIG = {
        1: ('#5DADE2', 'Torso',      0.55),
        2: ('#E74C3C', 'Corazon',    0.80),
        3: ('#F39C12', 'Pulmon izq', 0.65),
        4: ('#2ECC71', 'Pulmon der', 0.65),
    }
    PALETA = ['#E74C3C', '#E67E22', '#F1C40F', '#27AE60',
              '#2980B9', '#8E44AD', '#1ABC9C', '#D35400']

    X   = mesh.p.T
    fig = Figure(figsize=(14, 6))
    fig.suptitle("Electrodos ECG sobre la superficie del torso",
                 fontsize=13, fontweight="bold")

    # ── Vista 3D ──
    ax3d = fig.add_subplot(121, projection='3d')
    mat_labels = extraer_etiquetas_materiales(mio)
    legend_handles = []

    if mat_labels is not None and "tetra" in mio.cells_dict:
        tetras = mio.cells_dict["tetra"]
        for mat_id in [4, 3, 2, 1]:
            if mat_id not in MAT_CONFIG or mat_id not in np.unique(mat_labels):
                continue
            color, nombre, alfa = MAT_CONFIG[mat_id]
            tets_mat = tetras[mat_labels == mat_id]
            cara_count: dict = {}
            for tet in tets_mat:
                for cara in [tuple(sorted([tet[i], tet[j], tet[k]]))
                             for i, j, k in [(0,1,2),(0,1,3),(0,2,3),(1,2,3)]]:
                    cara_count[cara] = cara_count.get(cara, 0) + 1
            sup_arr = np.array([c for c, n in cara_count.items() if n == 1])
            if len(sup_arr) == 0:
                continue
            max_tris = {1: 800, 2: 600, 3: 500, 4: 500}.get(mat_id, 500)
            if len(sup_arr) > max_tris:
                sup_arr = sup_arr[np.random.default_rng(42).choice(
                    len(sup_arr), max_tris, replace=False)]
            sup_arr = sup_arr[np.all(sup_arr < X.shape[0], axis=1)]
            if len(sup_arr) == 0:
                continue
            verts = [[X[t[0]], X[t[1]], X[t[2]]] for t in sup_arr]
            ax3d.add_collection3d(Poly3DCollection(
                verts, facecolors=to_rgba(color, alfa),
                edgecolors='none', shade=False, antialiased=False))
            legend_handles.append(mpatches.Patch(color=color, alpha=max(alfa, 0.5), label=nombre))

    centro = X.mean(axis=0)
    for i, (nombre, nodo) in enumerate(electrode_nodes.items()):
        pos = X[nodo]
        c   = PALETA[i % len(PALETA)]
        d   = pos - centro; d /= (np.linalg.norm(d) + 1e-10)
        p_e = pos + d * 0.02
        ax3d.plot([pos[0], p_e[0]], [pos[1], p_e[1]], [pos[2], p_e[2]],
                  color=c, lw=1.0, alpha=0.7, ls='--')
        ax3d.scatter(*pos, s=80, c=c, marker='o', edgecolors='black', lw=0.6, zorder=1000)
        ax3d.text(*p_e, f" {nombre}", fontsize=7, color=c, fontweight='bold', zorder=1001)
        legend_handles.append(mpatches.Patch(color=c, label=nombre))

    ax3d.set_xlim(X[:,0].min(), X[:,0].max())
    ax3d.set_ylim(X[:,1].min(), X[:,1].max())
    ax3d.set_zlim(X[:,2].min(), X[:,2].max())
    ax3d.set_xlabel("X (m)", fontsize=8); ax3d.set_ylabel("Y (m)", fontsize=8)
    ax3d.set_zlabel("Z (m)", fontsize=8); ax3d.set_title("Vista 3D", fontsize=10)
    ax3d.view_init(elev=20, azim=45); ax3d.set_box_aspect([1,1,1])
    ax3d.grid(False)
    ax3d.xaxis.pane.fill = ax3d.yaxis.pane.fill = ax3d.zaxis.pane.fill = False
    ax3d.legend(handles=legend_handles, loc='upper right', fontsize=7, framealpha=0.9)

    # ── Vista 2D frontal XZ ──
    ax2d = fig.add_subplot(122)
    if len(surface_nodes) > 0:
        cs = X[surface_nodes]
        if PHI is not None:
            phi_s = PHI[surface_nodes, instant_idx] * 1000
            vmax  = np.abs(phi_s).max() or 1.0
            sc = ax2d.scatter(cs[:,0], cs[:,2], c=phi_s, cmap="RdBu_r",
                              s=6, vmin=-vmax, vmax=vmax, alpha=0.7)
            fig.colorbar(sc, ax=ax2d, label="Potencial (mV)", shrink=0.8)
            ax2d.set_title(f"Vista frontal XZ — t={instant_idx}", fontsize=10)
        else:
            ax2d.scatter(cs[:,0], cs[:,2], c='#5DADE2', s=6, alpha=0.4)
            ax2d.set_title("Vista frontal XZ", fontsize=10)

    for i, (nombre, nodo) in enumerate(electrode_nodes.items()):
        pos = X[nodo]; c = PALETA[i % len(PALETA)]
        ax2d.scatter(pos[0], pos[2], s=80, color=c, marker='o',
                     edgecolors='black', lw=0.6, zorder=10)
        ax2d.annotate(nombre, (pos[0], pos[2]),
                      textcoords="offset points", xytext=(5, 4),
                      fontsize=7, color=c, fontweight='bold')

    ax2d.set_xlabel("x (m)", fontsize=9); ax2d.set_ylabel("z (m)", fontsize=9)
    ax2d.set_aspect("equal"); ax2d.grid(True, ls="--", alpha=0.3)

    fig.tight_layout()
    return fig
