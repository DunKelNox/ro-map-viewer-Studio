# RO Studio

Visor de mapas de Ragnarok Online (GND / GAT / RSW / RSM) en una ventana de **PySide6** con
OpenGL. Es la base de un editor: la ventana, el cargador de mapas y el visor 3D están
separados para poder crecer por partes.

## Instalación

```bash
pip install -r requirements.txt
python ro_studio.py                 # Archivo ▸ Cargar mapa… (Ctrl+O)
python ro_studio.py mapa.gnd        # carga directa (propone .rsw, .gat, texturas y agua)
```

Funciona con Python 3.10 a 3.14. **No usa pygame.**

## Qué necesitás del GRF

Para un mapa (ej. `aldebaran`):

- `aldebaran.gnd` (obligatorio), `aldebaran.gat` y `aldebaran.rsw` (mismo nombre base)
- Texturas del terreno (`data/texture/...`)
- Modelos (`data/model/...` → `.rsm` / `.rsm2`) y sus texturas

Al elegir el `.gat` o el `.gnd` en **Cargar mapa…** se proponen los demás archivos, la
carpeta de texturas y la de agua. Sin `.gat` no hay overlay caminable ni piso GAT; sin
`.rsw` el mapa se carga sin modelos 3D.

## Menús

- **Archivo**: Cargar mapa…, Mapas recientes, Cerrar mapa, Salir.
- **Ver**: interruptores del visor (G, R, M, A, S, W, C, T, N, P), piso del marcador GND/GAT
  y modos de agua. Las casillas reflejan el estado real del visor.
- **Ayuda**: controles (F1).

## Controles

| Tecla / ratón | Acción |
|---------------|--------|
| Click izq. + arrastrar | Pan |
| Click der. + arrastrar | Orbitar |
| Rueda | Zoom (máx. 1500) |
| G | Overlay caminable (GAT) |
| P | Marca la celda bajo el cursor y muestra coordenadas GAT (juego), GND, mundo, altura GND/GAT y RSW |
| Shift+P | Piso del marcador: GND (terreno) / GAT (caminable y bloqueado; útil en puentes) |
| R | Modelos RSM on/off |
| M | Marcadores de modelos |
| A | Animación RSM |
| S | Lightmaps (sombras de terreno) |
| T | Iluminación estilo BrowEdit3 / anterior |
| N | Normales suaves del terreno |
| W | Muros del terreno |
| C | Brújula |
| 1 – 4 | Agua: sin agua / simple / animada (texturas RO) / animada procedural |
| J L / I K | Ajuste fino de modelos X / Z (±1; Shift = ±5) |
| Inicio | Restablecer el ajuste fino |
| { } | Distancia de dibujo RSM |
| Ctrl+O | Cargar mapa |

## Estructura

| Archivo | Rol |
|---------|-----|
| `ro_studio.py` | Aplicación: ventana principal, menús, estado y arranque. |
| `studio_viewport.py` | `GLViewport` (`QOpenGLWidget`): aloja el visor y traduce teclas/ratón de Qt a `inputs`. |
| `studio_load_dialog.py` | Diálogo **Cargar mapa**. |
| `studio_paths.py` | Lógica de rutas y validación del cargador, sin Qt (`MapConfig`). |
| `inputs.py` | Eventos de entrada propios (`InputEvent`, `K_*`, `KMOD_*`), sin depender de ninguna biblioteca. |
| `terrain_viewer_3d.py` | Visor 3D: terreno, lightmaps, agua, overlay GAT, marcador de celda, modelos. No crea ventana ni contexto: los pone el anfitrión. |
| `rsm_render.py` | Utilidades de render de modelos RSM/RSM2 (shaders, transformaciones, buffers, texturas). |
| `rsm_placement.py` | Colocación de modelos idéntica a BrowEdit3. |
| `ro_formats.py` | Lectores de formato: GAT, RSW, GND, RSM, RSM2 y búsqueda de texturas. Sin gráficos. |
| `mat4.py`, `rolog.py` | Matemática 4×4 y registro en consola. |
| `test_studio_paths.py`, `test_inputs.py` | Pruebas (`python -m unittest`). |

### Cómo se conectan

```
ro_studio.MainWindow ── LoadMapDialog ── studio_paths (MapConfig)
        │
        └── studio_viewport.GLViewport  (QOpenGLWidget, contexto OpenGL de Qt)
                 │  eventos Qt → inputs.InputEvent → viewer.handle_event()
                 │  paintGL    →                      viewer.render_frame()
                 └── terrain_viewer_3d.TerrainViewer3D ── ro_formats / rsm_render / rsm_placement
```

Para meter el visor en otra ventana Qt basta con `GLViewport(MapConfig(...))`. Para otro
anfitrión (por ejemplo un panel de vista previa) alcanza con crear el visor con un contexto
OpenGL actual y llamar a `handle_event` / `render_frame`.

## Colocación de modelos (RSM)

La posición en el mapa **no** usa el origen del nodo raíz del `.rsm`. Sigue a BrowEdit3
(`rsm_placement.py`):

1. Matrices de malla (`calcMatrix1` / `calcMatrix2`) y jerarquía.
2. Bounding box **real** del modelo completo (t = 0).
3. Instancia RSW: traslación/rotación/escala del `.rsw` + centrado por bbox (XZ) y apoyo en el
   punto más bajo (Y).

Soporta **RSM1** y **RSM2** (incl. animación de mallas cuando el archivo la trae).

## Limitaciones conocidas

- Agua **multi-zona** del GND: el parser puede leer zonas; el render 3D aún usa un plano al
  nivel global de agua.
- Los colores por tile del GND (que BrowEdit3 aplica por defecto) todavía no se usan.
- Los modelos con `shadeType` especial y los de escala negativa pueden iluminarse distinto que
  en BrowEdit3.
- Efectos de partículas del cliente (`.lub` EffectTool) no se renderizan.
- La carga del mapa (GND/RSW y malla) bloquea la interfaz unos segundos.
