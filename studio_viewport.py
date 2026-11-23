"""Widget de PySide6 que aloja el visor 3D de terreno (TerrainViewer3D).

El visor no abre ventana propia: usa el contexto OpenGL de este QOpenGLWidget. Los
eventos de Qt se traducen a ``inputs.InputEvent`` y se entregan a ``viewer.handle_event``.
"""
import time
import traceback

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtOpenGLWidgets import QOpenGLWidget

import inputs as inp
from studio_paths import MapConfig


# ----------------------------------------------------------------------
# Traducción de teclas Qt -> inputs
# ----------------------------------------------------------------------

_KEYPAD = {1: inp.K_KP1, 2: inp.K_KP2, 3: inp.K_KP3, 4: inp.K_KP4}


def qt_to_key(ev) -> int:
    """Código de tecla (inputs.K_*) equivalente al de un QKeyEvent (0 si no se usa)."""
    k = ev.key()
    if Qt.Key_A <= k <= Qt.Key_Z:
        return inp.K_a + (k - Qt.Key_A)
    if Qt.Key_0 <= k <= Qt.Key_9:
        n = k - Qt.Key_0
        if ev.modifiers() & Qt.KeypadModifier and n in _KEYPAD:
            return _KEYPAD[n]
        return inp.K_0 + n
    table = {
        Qt.Key_Escape: inp.K_ESCAPE,
        Qt.Key_Home: inp.K_HOME,
        Qt.Key_BracketLeft: inp.K_LEFTBRACKET,
        Qt.Key_BraceLeft: inp.K_LEFTBRACKET,
        Qt.Key_BracketRight: inp.K_RIGHTBRACKET,
        Qt.Key_BraceRight: inp.K_RIGHTBRACKET,
    }
    return table.get(k, 0)


def qt_to_mods(mods) -> int:
    m = 0
    if mods & Qt.ShiftModifier:
        m |= inp.KMOD_SHIFT
    if mods & Qt.ControlModifier:
        m |= inp.KMOD_CTRL
    if mods & Qt.AltModifier:
        m |= inp.KMOD_ALT
    return m


class GLViewport(QOpenGLWidget):
    """Vista 3D del mapa. Se crea con la configuración de un mapa y lo carga al
    inicializar su contexto OpenGL (el constructor del visor necesita un contexto actual).

    Señales:
      loadFinished(ok, mensaje): el visor se construyó (ok=True) o falló (ok=False).
    """

    loadFinished = Signal(bool, str)

    def __init__(self, cfg: MapConfig = None, parent=None):
        super().__init__(parent)
        self.cfg = cfg
        self.viewer = None
        self.load_error = None
        self._last_paint = time.perf_counter()
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMouseTracking(True)
        self.setMinimumSize(320, 240)
        # Repintado continuo (~60 FPS): el visor anima agua/modelos y carga de forma progresiva
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self.update)
        self._timer.start()

    # ------------------------------------------------------------------
    # Ciclo de vida OpenGL
    # ------------------------------------------------------------------
    def initializeGL(self):
        if self.cfg is None:
            return
        try:
            from terrain_viewer_3d import TerrainViewer3D
            dpr = self.devicePixelRatioF()
            self.viewer = TerrainViewer3D(
                self.cfg.gnd,
                rsw_path=self.cfg.rsw,
                texture_dir=self.cfg.tex,
                water_dir=self.cfg.water,
                gat_path=self.cfg.gat,
                width=max(1, int(self.width() * dpr)),
                height=max(1, int(self.height() * dpr)),
            )
            self.viewer.hud_scale = dpr
        except Exception as e:                     # noqa: BLE001
            self.viewer = None
            self.load_error = f"{type(e).__name__}: {e}"
            traceback.print_exc()
            QTimer.singleShot(0, lambda: self.loadFinished.emit(False, self.load_error))
            return
        QTimer.singleShot(0, lambda: self.loadFinished.emit(True, self.cfg.name))

    def resizeGL(self, w, h):
        if self.viewer is not None:
            dpr = self.devicePixelRatioF()
            self.viewer.set_view_size(w * dpr, h * dpr)

    def paintGL(self):
        from OpenGL.GL import glClearColor, glClear, GL_COLOR_BUFFER_BIT, GL_DEPTH_BUFFER_BIT
        v = self.viewer
        if v is None:
            glClearColor(0.16, 0.17, 0.19, 1.0)
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
            return
        dpr = self.devicePixelRatioF()
        v.set_view_size(self.width() * dpr, self.height() * dpr)
        v.hud_scale = dpr
        now = time.perf_counter()
        v._frame_dt_ms = min(100.0, (now - self._last_paint) * 1000.0)
        self._last_paint = now
        glClearColor(0.5, 0.65, 0.85, 1.0)
        try:
            v.render_frame()
            v._pump_loading()
        except Exception as e:                     # noqa: BLE001
            traceback.print_exc()
            self._timer.stop()
            msg = f"Error al dibujar: {e}"          # 'e' no existe fuera del except
            QTimer.singleShot(0, lambda: self.loadFinished.emit(False, msg))

    def closeEvent(self, ev):
        self._timer.stop()
        super().closeEvent(ev)

    # ------------------------------------------------------------------
    # API para el anfitrión
    # ------------------------------------------------------------------
    @property
    def loading_text(self) -> str:
        v = self.viewer
        if v is not None and v.loading_busy:
            return v.loading_phase or "Cargando…"
        return ""

    def send_key(self, key: int, shift: bool = False, unicode: str = ""):
        """Envía una tecla al visor como si se hubiera pulsado (usado por el menú Ver)."""
        if self.viewer is None:
            return
        mod = inp.KMOD_SHIFT if shift else 0
        self.viewer.handle_event(inp.InputEvent(
            type=inp.KEYDOWN, key=key, mod=mod, unicode=unicode))
        self.update()

    # ------------------------------------------------------------------
    # Eventos de Qt -> eventos del visor
    # ------------------------------------------------------------------
    def _pos(self, ev):
        p = ev.position()
        dpr = self.devicePixelRatioF()
        return int(p.x() * dpr), int(p.y() * dpr)

    def keyPressEvent(self, ev):
        if self.viewer is None or ev.isAutoRepeat():
            ev.ignore()
            return
        if ev.modifiers() & (Qt.ControlModifier | Qt.AltModifier):
            ev.ignore()                            # atajos de la ventana (Ctrl+O, etc.)
            return
        key = qt_to_key(ev)
        if not key and not ev.text():
            ev.ignore()
            return
        # ESC no cierra la aplicación (el visor lo interpreta como 'salir')
        if key == inp.K_ESCAPE:
            ev.accept()
            return
        self.viewer.handle_event(inp.InputEvent(
            type=inp.KEYDOWN, key=key, mod=qt_to_mods(ev.modifiers()),
            unicode=ev.text()))
        ev.accept()

    def mousePressEvent(self, ev):
        self.setFocus()
        if self.viewer is None:
            return
        btn = {Qt.LeftButton: 1, Qt.RightButton: 3}.get(ev.button())
        if btn:
            self.viewer._host_mouse = (True, self._pos(ev))
            self.viewer.handle_event(inp.InputEvent(
                type=inp.MOUSEBUTTONDOWN, button=btn, pos=self._pos(ev)))

    def mouseReleaseEvent(self, ev):
        if self.viewer is None:
            return
        btn = {Qt.LeftButton: 1, Qt.RightButton: 3}.get(ev.button())
        if btn:
            self.viewer.handle_event(inp.InputEvent(
                type=inp.MOUSEBUTTONUP, button=btn, pos=self._pos(ev)))

    def mouseMoveEvent(self, ev):
        if self.viewer is None:
            return
        pos = self._pos(ev)
        self.viewer._host_mouse = (True, pos)
        self.viewer.handle_event(inp.InputEvent(
            type=inp.MOUSEMOTION, pos=pos, rel=(0, 0)))

    def wheelEvent(self, ev):
        if self.viewer is None:
            return
        dy = ev.angleDelta().y()
        if dy == 0:
            return
        button = 4 if dy > 0 else 5               # 4 = zoom in, 5 = zoom out
        for _ in range(max(1, abs(dy) // 120)):
            self.viewer.handle_event(inp.InputEvent(
                type=inp.MOUSEBUTTONDOWN, button=button, pos=self._pos(ev)))
        ev.accept()

    def enterEvent(self, ev):
        if self.viewer is not None:
            self.viewer._host_mouse = (True, self.viewer._host_mouse[1])
        super().enterEvent(ev)

    def leaveEvent(self, ev):
        if self.viewer is not None:
            self.viewer._host_mouse = (False, self.viewer._host_mouse[1])
        super().leaveEvent(ev)
