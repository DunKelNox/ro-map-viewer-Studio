# RO Studio

Visor y base de editor de mapas de Ragnarok Online (`.gat`, `.gnd`, `.rsw`, `.rsm`, `.rsm2`) en Python + PySide6 + OpenGL. 

Esta es la evolución directa y profesional de [`ro-map-viewer`](https://github.com/DunKelNox/ro-map-viewer). Se ha reescrito la arquitectura para eliminar dependencias de Pygame, desacoplar totalmente el renderizado de la interfaz, implementar carga progresiva no bloqueante y añadir pruebas unitarias, sentando las bases sólidas para un editor de mapas completo.

## ✨ Características Principales

- **Alineación perfecta con BrowEdit3**: La colocación de modelos (RSM/RSM2) replica exactamente las matrices, el bounding box real y el anclaje del editor oficial.
- **Arquitectura Desacoplada**: El núcleo de renderizado (`TerrainViewer3D`) es ciego a la interfaz gráfica. Recibe eventos genéricos (`inputs.py`) y dibuja bajo demanda, permitiendo incrustarlo en cualquier framework (Qt, wxPython, etc.).
- **Carga Progresiva (Non-blocking)**: El terreno se muestra al instante con color plano, mientras las texturas, modelos RSM y mipmaps se cargan en segundo plano sin congelar la ventana.
- **Cero Pygame**: Migración completa a **PySide6 (Qt)** para una gestión de ventanas, menús y eventos nativa, robusta y escalable.
- **Testeable**: La lógica de rutas, validación y eventos está separada en módulos puros con pruebas unitarias incluidas (`unittest`).

Dependencias: PySide6-Essentials, Pillow, numpy, PyOpenGL, PyOpenGL_accelerate.
Uso
Interfaz gráfica (recomendado)
python ro_studio.py

Ve a Archivo → Cargar mapa… (o presiona Ctrl+O).
Selecciona el archivo .gnd (obligatorio) o .gat. El sistema propone automáticamente el .rsw, la carpeta de texturas (data/texture) y la carpeta de agua.
Haz clic en Cargar mapa.
Línea de comandos

python ro_studio.py mapa.gnd

Carga directa proponiendo archivos hermanos y carpetas de datos.
Pruebas unitarias

python -m unittest test_inputs test_studio_paths -v

Controles

Ratón
Acción                                Efecto
Click izq. + arrastrar                Desplazar vista (Pan)
Click der. + arrastrar                Orbitar cámara
Rueda                                 Zoom (máx. 1500)

Teclado
Tecla     Efecto
G         Activar/Desactivar overlay caminable (GAT)
P         Marcar celda bajo el cursor y mostrar panel de coordenadas
Shift +P  Alternar piso del marcador: GND (terreno) / GAT (caminable)
R         Mostrar/Ocultar modelos 3D (RSM)
M         Mostrar/Ocultar marcadores de posición de modelos
A         Activar/Desactivar animación de modelos
S         Activar/Desactivar lightmaps (sombras del terreno)
T         Alternar iluminación: Estilo BrowEdit3 (real) / Neutra
N         Alternar normales suaves del terreno
W         Mostrar/Ocultar muros laterales del terreno
C         Mostrar/Ocultar brújula 3D
1 - 4     Modos de agua: Sin agua / Simple / Animada (texturas RO) / Procedural
J / L     Ajuste fino de posición global de modelos en X (±1, Shift=±5)
I / K     Ajuste fino de posición global de modelos en Z (±1, Shift=±5)
Inicio    Restablecer ajuste fino de modelos a (0, 0)
{ / }     Disminuir / Aumentar distancia de dibujo (culling) de RSM
Ctrl + O  Abrir diálogo de carga de mapa
ESC       Cerrar la aplicación

Estructura del proyecto
Archivo                 Rol
ro_studio.py            Punto de entrada. Ventana principal, menús y estado de la aplicación.
studio_viewport.py      QOpenGLWidget que aloja el visor y traduce eventos de Qt a inputs.InputEvent.
studio_load_dialog.py   Diálogo de carga de mapas con autocompletado inteligente de rutas.
studio_paths.py         Lógica pura de validación y sugerencia de rutas (sin dependencias de UI, 100% testeable).
terrain_viewer_3d.py    Núcleo del visor 3D: terreno, lightmaps, agua, overlay GAT y modelos. No crea ventanas propias.
rsm_placement.py        Cálculo de matrices de colocación de modelos idéntico a BrowEdit3.
rsm_render.py           Shaders, buffers de vértices y carga de texturas OpenGL para RSM/RSM2.
ro_formats.py           Parsers binarios de formatos RO (GAT, RSW, GND, RSM, RSM2). Sin dependencias gráficas.
inputs.py               Definición agnóstica de eventos de entrada (teclas, ratón), independiente de bibliotecas.
mat4.py                 Utilidades de matrices 4x4 (sin PyGLM).
rolog.py                Sistema de logging de consola (info con RO_VERBOSE=1, warn siempre).
test_*.py               Pruebas unitarias para garantizar la estabilidad de la lógica de negocio.

Para visualizar un mapa completo (ej. aldebaran), necesitas extraer del GRF:
aldebaran.gnd (obligatorio para el terreno 3D).
aldebaran.gat y aldebaran.rsw (mismo nombre base, para overlay caminable y modelos).
Carpeta de texturas del terreno (data/texture/...).
Carpeta de modelos (data/model/... → .rsm / .rsm2) y sus texturas asociadas.
El diálogo de carga propone automáticamente estos archivos y carpetas si detecta una estructura de extracción de GRF estándar.
Limitaciones conocidas
Agua multi-zona: el parser GND lee las zonas correctamente, pero el render 3D actual aplica un plano de agua unificado a nivel global.
Colores por tile: el canal de color por celda del GND (usado por BrowEdit3 por defecto) aún no se aplica en el render.
Efectos: los efectos de partículas del cliente (.lub / EffectTool) no se renderizan.
Modelos especiales: algunos modelos con shadeType no estándar o escalas negativas pueden presentar diferencias menores de iluminación respecto a BrowEdit3.
Licencia
Distribuido bajo la licencia MIT. Libre para usar, modificar y compartir.
Manteniendo el legado de precisión y código abierto de la comunidad de desarrollo de Ragnarok Online.
Desarrollado con ❤️ por DunKelNox
