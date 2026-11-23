"""Eventos de entrada independientes de cualquier biblioteca (Qt, SDL, etc.).

El visor (terrain_viewer_3d.TerrainViewer3D) recibe estos eventos en handle_event().
El anfitrión (hoy studio_viewport.GLViewport, con Qt) traduce sus propios eventos a estos.

Los nombres y valores son propios: no dependen de ninguna biblioteca.
"""
from dataclasses import dataclass
from typing import Tuple

# --- tipos de evento ---
KEYDOWN = 1
MOUSEBUTTONDOWN = 2
MOUSEBUTTONUP = 3
MOUSEMOTION = 4
VIDEORESIZE = 5
QUIT = 6

# --- modificadores (se combinan con |) ---
KMOD_SHIFT = 1
KMOD_CTRL = 2
KMOD_ALT = 4

# --- teclas: letras y dígitos usan su código ASCII en minúscula ---
K_a = 97
K_b = 98
K_c = 99
K_d = 100
K_e = 101
K_f = 102
K_g = 103
K_h = 104
K_i = 105
K_j = 106
K_k = 107
K_l = 108
K_m = 109
K_n = 110
K_o = 111
K_p = 112
K_q = 113
K_r = 114
K_s = 115
K_t = 116
K_u = 117
K_v = 118
K_w = 119
K_x = 120
K_y = 121
K_z = 122

K_0 = 48
K_1 = 49
K_2 = 50
K_3 = 51
K_4 = 52
K_5 = 53
K_6 = 54
K_7 = 55
K_8 = 56
K_9 = 57

# --- teclas especiales ---
K_ESCAPE = 27
K_LEFTBRACKET = 91     # [  ({ con Shift)
K_RIGHTBRACKET = 93    # ]  (} con Shift)
K_HOME = 1001
K_KP1 = 2001           # teclado numérico
K_KP2 = 2002
K_KP3 = 2003
K_KP4 = 2004

# Botones del ratón: 1 = izquierdo, 3 = derecho, 4 = rueda hacia adelante (zoom in),
# 5 = rueda hacia atrás (zoom out).


@dataclass
class InputEvent:
    """Evento de entrada. Solo se rellenan los campos que aplican al tipo."""
    type: int
    key: int = 0                      # KEYDOWN: código K_*
    mod: int = 0                      # KEYDOWN: combinación de KMOD_*
    unicode: str = ""                 # KEYDOWN: texto producido por la tecla ("{", "p", ...)
    button: int = 0                   # MOUSEBUTTON*: 1, 3, 4, 5
    pos: Tuple[int, int] = (0, 0)     # MOUSE*: posición en píxeles de la vista
    rel: Tuple[int, int] = (0, 0)     # MOUSEMOTION: desplazamiento
    w: int = 0                        # VIDEORESIZE: nuevo ancho
    h: int = 0                        # VIDEORESIZE: nuevo alto
