# -*- coding: utf-8 -*-
"""
Controles de visualización 3D
"""
import tkinter as tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk


def create_view_controls(parent, ax, canvas):
    """
    Crea controles de vista para la visualización 3D.
    
    Args:
        parent: Widget padre
        ax: Axes 3D de matplotlib
        canvas: Canvas de matplotlib
        
    Returns:
        tk.Frame: Frame con controles
    """
    controls_frame = tk.Frame(parent, bg='#f0f0f0', relief=tk.RAISED, bd=1)
    
    tk.Label(controls_frame, text="🎮 Controles:", 
            font=("Arial", 9, "bold"), bg='#f0f0f0').pack(side=tk.LEFT, padx=5)
    
    def set_view(elev, azim):
        ax.view_init(elev=elev, azim=azim)
        canvas.draw()
    
    tk.Button(controls_frame, text="Vista Frontal", 
             command=lambda: set_view(0, 0),
             font=("Arial", 8), bg='#3498db', fg='white', 
             relief=tk.FLAT, padx=8, pady=3).pack(side=tk.LEFT, padx=2)
    
    tk.Button(controls_frame, text="Vista Superior", 
             command=lambda: set_view(90, 0),
             font=("Arial", 8), bg='#3498db', fg='white', 
             relief=tk.FLAT, padx=8, pady=3).pack(side=tk.LEFT, padx=2)
    
    tk.Button(controls_frame, text="Vista Lateral", 
             command=lambda: set_view(0, 90),
             font=("Arial", 8), bg='#3498db', fg='white', 
             relief=tk.FLAT, padx=8, pady=3).pack(side=tk.LEFT, padx=2)
    
    tk.Button(controls_frame, text="Vista 3D", 
             command=lambda: set_view(25, 45),
             font=("Arial", 8), bg='#2ecc71', fg='white', 
             relief=tk.FLAT, padx=8, pady=3).pack(side=tk.LEFT, padx=2)
    
    tk.Frame(controls_frame, width=2, bg='#bdc3c7').pack(side=tk.LEFT, fill=tk.Y, padx=5)
    
    tk.Label(controls_frame, text="Zoom:", 
            font=("Arial", 8), bg='#f0f0f0').pack(side=tk.LEFT, padx=5)
    
    return controls_frame


def create_zoom_controls(parent, ax, canvas, X):
    """
    Crea controles de zoom.
    
    Args:
        parent: Widget padre
        ax: Axes 3D
        canvas: Canvas de matplotlib
        X: Puntos de la malla
        
    Returns:
        tuple: (zoom_in, zoom_out, reset_view) funciones
    """
    def zoom_in():
        xlim, ylim, zlim = ax.get_xlim(), ax.get_ylim(), ax.get_zlim()
        x_center = (xlim[0] + xlim[1]) / 2
        y_center = (ylim[0] + ylim[1]) / 2
        z_center = (zlim[0] + zlim[1]) / 2
        x_range = (xlim[1] - xlim[0]) * 0.8
        y_range = (ylim[1] - ylim[0]) * 0.8
        z_range = (zlim[1] - zlim[0]) * 0.8
        ax.set_xlim(x_center - x_range/2, x_center + x_range/2)
        ax.set_ylim(y_center - y_range/2, y_center + y_range/2)
        ax.set_zlim(z_center - z_range/2, z_center + z_range/2)
        canvas.draw()
    
    def zoom_out():
        xlim, ylim, zlim = ax.get_xlim(), ax.get_ylim(), ax.get_zlim()
        x_center = (xlim[0] + xlim[1]) / 2
        y_center = (ylim[0] + ylim[1]) / 2
        z_center = (zlim[0] + zlim[1]) / 2
        x_range = (xlim[1] - xlim[0]) * 1.25
        y_range = (ylim[1] - ylim[0]) * 1.25
        z_range = (zlim[1] - zlim[0]) * 1.25
        ax.set_xlim(x_center - x_range/2, x_center + x_range/2)
        ax.set_ylim(y_center - y_range/2, y_center + y_range/2)
        ax.set_zlim(z_center - z_range/2, z_center + z_range/2)
        canvas.draw()
    
    def reset_view():
        x_min, x_max = X[:, 0].min(), X[:, 0].max()
        y_min, y_max = X[:, 1].min(), X[:, 1].max()
        z_min, z_max = X[:, 2].min(), X[:, 2].max()
        margin = 0.1
        x_margin = (x_max - x_min) * margin
        y_margin = (y_max - y_min) * margin
        z_margin = (z_max - z_min) * margin
        ax.set_xlim(x_min - x_margin, x_max + x_margin)
        ax.set_ylim(y_min - y_margin, y_max + y_margin)
        ax.set_zlim(z_min - z_margin, z_max + z_margin)
        ax.view_init(elev=25, azim=45)
        canvas.draw()
    
    tk.Button(parent, text="➕", command=zoom_in,
             font=("Arial", 10, "bold"), bg='#27ae60', fg='white', 
             relief=tk.FLAT, padx=8, pady=2).pack(side=tk.LEFT, padx=2)
    
    tk.Button(parent, text="➖", command=zoom_out,
             font=("Arial", 10, "bold"), bg='#e67e22', fg='white', 
             relief=tk.FLAT, padx=8, pady=2).pack(side=tk.LEFT, padx=2)
    
    tk.Button(parent, text="🔄 Reset", command=reset_view,
             font=("Arial", 8), bg='#95a5a6', fg='white', 
             relief=tk.FLAT, padx=8, pady=3).pack(side=tk.LEFT, padx=2)
    
    return zoom_in, zoom_out, reset_view


def setup_mouse_controls(canvas, ax, zoom_in, zoom_out):
    """
    Configura controles de mouse para la visualización.
    
    Args:
        canvas: Canvas de matplotlib
        ax: Axes 3D
        zoom_in: Función de zoom in
        zoom_out: Función de zoom out
    """
    def on_mouse_press(event):
        canvas._button_pressed = event.button
        canvas._mouse_x = event.x
        canvas._mouse_y = event.y
    
    def on_mouse_move(event):
        if hasattr(canvas, '_button_pressed') and canvas._button_pressed == 1:
            dx = event.x - canvas._mouse_x
            dy = event.y - canvas._mouse_y
            elev = ax.elev - dy * 0.5
            azim = ax.azim + dx * 0.5
            ax.view_init(elev=elev, azim=azim)
            canvas.draw()
            canvas._mouse_x = event.x
            canvas._mouse_y = event.y
    
    def on_mouse_release(event):
        if hasattr(canvas, '_button_pressed'):
            del canvas._button_pressed
    
    def on_scroll(event):
        if event.delta > 0:
            zoom_in()
        else:
            zoom_out()
    
    canvas.mpl_connect('button_press_event', on_mouse_press)
    canvas.mpl_connect('motion_notify_event', on_mouse_move)
    canvas.mpl_connect('button_release_event', on_mouse_release)
    canvas.mpl_connect('scroll_event', on_scroll)
