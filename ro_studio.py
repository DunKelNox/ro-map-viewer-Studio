"""RO Studio — visor de mapas de Ragnarok Online en una ventana de PySide6.

Uso:
    python ro_studio.py                 # abre la ventana; Archivo ▸ Cargar mapa… (Ctrl+O)
    python ro_studio.py mapa.gnd        # carga el mapa directamente (propone .rsw/.gat/texturas)

Requisitos: ver requirements.txt (PySide6, PyOpenGL, numpy, Pillow).
"""
import json
import os
import sys

from PySide6.QtCore import QSettings, Qt, QTimer
from PySide6.QtGui import QAction, QActionGroup, QGuiApplication, QSurfaceFormat
from PySide6.QtWidgets import (
    QApplication, QLabel, QMainWindow, QMessageBox, QPushButton, QVBoxLayout, QWidget,
)

import inputs as inp
from studio_load_dialog import LoadMapDialog
from studio_paths import MapConfig, propose_from_file, validate_config
from studio_viewport import GLViewport

APP_NAME = "RO Studio"
MAX_RECENT = 8

CONTROLS_HTML = """
<h3>Ratón</h3>
<table cellpadding="3">
<tr><td><b>Click izquierdo + arrastrar</b></td><td>Pan</td></tr>
<tr><td><b>Click derecho + arrastrar</b></td><td>Orbitar</td></tr>
<tr><td><b>Rueda</b></td><td>Zoom</td></tr>
</table>
<h3>Teclado</h3>
<table cellpadding="3">
<tr><td><b>G</b></td><td>Overlay caminable (GAT)</td></tr>
<tr><td><b>P</b></td><td>Marcar la celda bajo el cursor y mostrar coordenadas</td></tr>
<tr><td><b>Shift+P</b></td><td>Piso del marcador: GND (terreno) / GAT (caminable)</td></tr>
<tr><td><b>R</b></td><td>Modelos 3D (RSM)</td></tr>
<tr><td><b>M</b></td><td>Marcadores de modelos</td></tr>
<tr><td><b>A</b></td><td>Animación de modelos</td></tr>
<tr><td><b>S</b></td><td>Sombras (lightmaps)</td></tr>
<tr><td><b>T</b></td><td>Iluminación estilo BrowEdit3 / anterior</td></tr>
<tr><td><b>N</b></td><td>Normales suaves del terreno</td></tr>
<tr><td><b>W</b></td><td>Paredes del terreno</td></tr>
<tr><td><b>C</b></td><td>Brújula</td></tr>
<tr><td><b>1 – 4</b></td><td>Agua: sin agua / simple / animada (texturas RO) / animada procedural</td></tr>
<tr><td><b>J L / I K</b></td><td>Ajuste fino de modelos X / Z (Shift = ±5)</td></tr>
<tr><td><b>Inicio</b></td><td>Restablecer el ajuste fino</td></tr>
<tr><td><b>{ }</b></td><td>Distancia de dibujo de modelos</td></tr>
<tr><td><b>Ctrl+O</b></td><td>Cargar mapa</td></tr>
</table>
"""


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = QSettings("RO-Studio", "MapViewer")
        self.viewport = None
        self.current_cfg = None
        self.setWindowTitle(APP_NAME)
        self.resize(1280, 800)

        self._build_placeholder()
        self._build_menus()
        self.load_label = QLabel("")
        self.statusBar().addPermanentWidget(self.load_label)
        self.statusBar().showMessage("Archivo ▸ Cargar mapa… para empezar")

        self._status_timer = QTimer(self)
        self._status_timer.setInterval(200)
        self._status_timer.timeout.connect(self._update_status)
        self._status_timer.start()

    # ------------------------------------------------------------------
    # Interfaz
    # ------------------------------------------------------------------
    def _build_placeholder(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.addStretch(1)
        title = QLabel(f"<h2>{APP_NAME}</h2>No hay ningún mapa cargado.")
        title.setAlignment(Qt.AlignCenter)
        lay.addWidget(title)
        btn = QPushButton("Cargar mapa…")
        btn.setFixedWidth(200)
        btn.clicked.connect(self.open_load_dialog)
        lay.addWidget(btn, alignment=Qt.AlignCenter)
        lay.addStretch(1)
        self.setCentralWidget(page)       # reemplaza (y destruye) lo anterior
        self.viewport = None

    def _build_menus(self):
        bar = self.menuBar()

        # --- Archivo -------------------------------------------------
        m_file = bar.addMenu("&Archivo")
        self.act_open = QAction("&Cargar mapa…", self)
        self.act_open.setShortcut("Ctrl+O")
        self.act_open.triggered.connect(self.open_load_dialog)
        m_file.addAction(self.act_open)

        self.menu_recent = m_file.addMenu("Mapas &recientes")
        self.menu_recent.aboutToShow.connect(self._rebuild_recent_menu)

        self.act_close = QAction("Ce&rrar mapa", self)
        self.act_close.setShortcut("Ctrl+W")
        self.act_close.triggered.connect(self.close_map)
        m_file.addAction(self.act_close)

        m_file.addSeparator()
        act_quit = QAction("&Salir", self)
        act_quit.setShortcut("Ctrl+Q")
        act_quit.triggered.connect(self.close)
        m_file.addAction(act_quit)
        m_file.aboutToShow.connect(self._refresh_file_menu)

        # --- Ver -----------------------------------------------------
        # (texto, atajo mostrado, getter del estado, código de tecla (inputs.K_*), con Shift)
        self.m_view = bar.addMenu("&Ver")
        self._view_items = []
        spec = (
            ("Overlay caminable (GAT)", "G", lambda v: v.show_walkable, inp.K_g, False),
            ("Modelos 3D (RSM)", "R", lambda v: v.show_rsm, inp.K_r, False),
            ("Marcadores de modelos", "M", lambda v: v.show_models, inp.K_m, False),
            ("Animación de modelos", "A", lambda v: getattr(v, 'rsm_animate', False), inp.K_a, False),
            ("Sombras (lightmaps)", "S", lambda v: v.show_shadows, inp.K_s, False),
            ("Paredes del terreno", "W", lambda v: v.show_walls, inp.K_w, False),
            ("Brújula", "C", lambda v: v.show_compass, inp.K_c, False),
            None,
            ("Iluminación estilo BrowEdit3", "T", lambda v: v.use_rsw_light, inp.K_t, False),
            ("Normales suaves", "N", lambda v: v.smooth_normals, inp.K_n, False),
            None,
            ("Marcar celda y coordenadas", "P", lambda v: v.show_cell_info, inp.K_p, False),
        )
        for item in spec:
            if item is None:
                self.m_view.addSeparator()
                continue
            text, hint, getter, key, shift = item
            act = QAction(f"{text}\t{hint}", self)
            act.setCheckable(True)
            act.triggered.connect(lambda _=False, k=key, s=shift: self._send(k, s))
            self.m_view.addAction(act)
            self._view_items.append((act, getter))

        # Piso del marcador (GND / GAT)
        self.m_floor = self.m_view.addMenu("Piso del marcador\tShift+P")
        self.floor_group = QActionGroup(self)
        self.floor_actions = {}
        for fl, text in (("gnd", "Piso GND (terreno)"), ("gat", "Piso GAT (caminable / bloqueado)")):
            act = QAction(text, self, checkable=True)
            self.floor_group.addAction(act)
            self.m_floor.addAction(act)
            act.triggered.connect(lambda _=False, f=fl: self._set_floor(f))
            self.floor_actions[fl] = act

        # Agua
        self.m_water = self.m_view.addMenu("Agua")
        self.water_group = QActionGroup(self)
        self.water_actions = {}
        for mode, text, key in (
            (1, "Sin agua\t1", inp.K_1),
            (2, "Agua simple\t2", inp.K_2),
            (3, "Animada (texturas RO)\t3", inp.K_3),
            (4, "Animada procedural\t4", inp.K_4),
        ):
            act = QAction(text, self, checkable=True)
            self.water_group.addAction(act)
            self.m_water.addAction(act)
            act.triggered.connect(lambda _=False, k=key: self._send(k, False))
            self.water_actions[mode] = act
        self.m_view.aboutToShow.connect(self._refresh_view_menu)

        # --- Ayuda ---------------------------------------------------
        m_help = bar.addMenu("A&yuda")
        act_controls = QAction("&Controles…", self)
        act_controls.setShortcut("F1")
        act_controls.triggered.connect(self._show_controls)
        m_help.addAction(act_controls)
        act_about = QAction("&Acerca de…", self)
        act_about.triggered.connect(self._show_about)
        m_help.addAction(act_about)

        self._refresh_file_menu()
        self._refresh_view_menu()

    # ------------------------------------------------------------------
    # Estado de los menús
    # ------------------------------------------------------------------
    def _viewer(self):
        return self.viewport.viewer if self.viewport is not None else None

    def _refresh_file_menu(self):
        self.act_close.setEnabled(self.viewport is not None)
        self.menu_recent.setEnabled(bool(self._recent_list()))

    def _refresh_view_menu(self):
        v = self._viewer()
        self.m_view.setEnabled(v is not None)
        if v is None:
            return
        for act, getter in self._view_items:
            try:
                state = bool(getter(v))
            except Exception:                     # noqa: BLE001
                state = False
            act.setChecked(state)
        floor = getattr(v, 'cell_floor', 'gnd')
        self.floor_actions[floor].setChecked(True)
        self.floor_actions['gat'].setEnabled(getattr(v, 'gat', None) is not None)
        self.water_actions.get(getattr(v, 'water_mode', 2), self.water_actions[2]).setChecked(True)

    def _send(self, key, shift):
        if self.viewport is not None:
            self.viewport.send_key(key, shift)
            self.viewport.setFocus()

    def _set_floor(self, floor):
        v = self._viewer()
        if v is not None and getattr(v, 'cell_floor', 'gnd') != floor:
            self._send(inp.K_p, True)           # Shift+P alterna GND/GAT

    # ------------------------------------------------------------------
    # Cargar / cerrar mapa
    # ------------------------------------------------------------------
    def open_load_dialog(self):
        initial = None
        raw = self.settings.value("last_config", "")
        if raw:
            try:
                initial = MapConfig.from_dict(json.loads(raw))
            except Exception:                      # noqa: BLE001
                initial = None
        dlg = LoadMapDialog(self, initial=initial, settings=self.settings)
        if dlg.exec() == LoadMapDialog.Accepted and dlg.config() is not None:
            self.load_map(dlg.config(), notes=dlg.notes())

    def load_map(self, cfg: MapConfig, notes=None):
        """Carga un mapa en la vista 3D (reemplaza el anterior)."""
        self._pending_notes = list(notes or [])
        self.statusBar().showMessage(f"Cargando {cfg.name}…")
        QApplication.setOverrideCursor(Qt.WaitCursor)
        self._cursor_overridden = True
        QApplication.processEvents()
        vp = GLViewport(cfg)
        vp.loadFinished.connect(self._on_load_finished)
        self.current_cfg = cfg
        self.setCentralWidget(vp)           # destruye la vista anterior (y su contexto GL)
        self.viewport = vp
        vp.setFocus()

    def _on_load_finished(self, ok: bool, message: str):
        if getattr(self, '_cursor_overridden', False):
            QApplication.restoreOverrideCursor()
            self._cursor_overridden = False
        if not ok:
            QMessageBox.critical(self, "Error al cargar el mapa", message)
            self._build_placeholder()
            self.setWindowTitle(APP_NAME)
            self.statusBar().showMessage("No se pudo cargar el mapa")
            self.current_cfg = None
            return
        cfg = self.current_cfg
        self.setWindowTitle(f"{APP_NAME} — {cfg.name}")
        extra = ("  (" + "; ".join(self._pending_notes) + ")") if self._pending_notes else ""
        self.statusBar().showMessage(f"{cfg.gnd}{extra}")
        self.settings.setValue("last_config", json.dumps(cfg.to_dict()))
        self._add_recent(cfg)
        self._refresh_view_menu()

    def close_map(self):
        self._build_placeholder()
        self.current_cfg = None
        self.setWindowTitle(APP_NAME)
        self.statusBar().showMessage("Archivo ▸ Cargar mapa… para empezar")
        self._refresh_view_menu()

    def _update_status(self):
        vp = self.viewport
        self.load_label.setText(vp.loading_text if vp is not None else "")

    # ------------------------------------------------------------------
    # Mapas recientes
    # ------------------------------------------------------------------
    def _recent_list(self):
        raw = self.settings.value("recent", "")
        try:
            items = json.loads(raw) if raw else []
        except Exception:                          # noqa: BLE001
            items = []
        cfgs = [MapConfig.from_dict(d) for d in items if isinstance(d, dict)]
        return [c for c in cfgs if c is not None]

    def _save_recent(self, cfgs):
        self.settings.setValue("recent", json.dumps([c.to_dict() for c in cfgs[:MAX_RECENT]]))

    def _add_recent(self, cfg: MapConfig):
        cur = [c for c in self._recent_list() if c.gnd != cfg.gnd]
        self._save_recent([cfg] + cur)

    def _rebuild_recent_menu(self):
        self.menu_recent.clear()
        for cfg in self._recent_list():
            act = QAction(f"{cfg.name}    —    {os.path.dirname(cfg.gnd)}", self)
            act.triggered.connect(lambda _=False, c=cfg: self._load_recent(c))
            self.menu_recent.addAction(act)
        if self.menu_recent.isEmpty():
            self.menu_recent.addAction("(vacío)").setEnabled(False)
        else:
            self.menu_recent.addSeparator()
            clear = QAction("Borrar lista", self)
            clear.triggered.connect(lambda: self._save_recent([]))
            self.menu_recent.addAction(clear)

    def _load_recent(self, cfg: MapConfig):
        new_cfg, errors, _warnings, notes = validate_config(
            cfg.gat or "", cfg.rsw or "", cfg.gnd, cfg.tex or "", cfg.water or "")
        if errors:
            QMessageBox.critical(self, "No se puede cargar el mapa", "\n\n".join(errors))
            self._save_recent([c for c in self._recent_list() if c.gnd != cfg.gnd])
            return
        self.load_map(new_cfg, notes=notes)

    # ------------------------------------------------------------------
    # Ayuda
    # ------------------------------------------------------------------
    def _show_controls(self):
        QMessageBox.information(self, "Controles", CONTROLS_HTML)

    def _show_about(self):
        QMessageBox.about(
            self, f"Acerca de {APP_NAME}",
            f"<b>{APP_NAME}</b><br>Visor de mapas de Ragnarok Online (GND / GAT / RSW / RSM) "
            "sobre PySide6 y OpenGL.<br><br>Iluminación y lightmaps alineados con BrowEdit3.")


# ----------------------------------------------------------------------
def make_surface_format() -> QSurfaceFormat:
    """Formato OpenGL que necesita el visor: 3.3 core y buffer de profundidad de 24 bits."""
    fmt = QSurfaceFormat()
    fmt.setVersion(3, 3)
    fmt.setProfile(QSurfaceFormat.CoreProfile)
    fmt.setDepthBufferSize(24)
    fmt.setStencilBufferSize(8)
    fmt.setSwapInterval(1)
    return fmt


def config_from_path(path: str):
    """Arma una configuración a partir de un .gnd/.gat/.rsw suelto (con sugerencias)."""
    path = os.path.abspath(path)
    d = propose_from_file(path, {})
    ext = os.path.splitext(path)[1].lower()
    if ext == ".rsw" and not d.get("rsw"):
        d["rsw"] = path
    if not d.get("gnd"):
        return None
    return MapConfig(gnd=d["gnd"], gat=d.get("gat"), rsw=d.get("rsw"),
                     tex=d.get("tex"), water=d.get("water"))


def main(argv=None):
    argv = list(sys.argv if argv is None else argv)
    QSurfaceFormat.setDefaultFormat(make_surface_format())
    app = QApplication(argv)
    app.setApplicationName(APP_NAME)
    win = MainWindow()
    win.show()
    if len(argv) > 1:
        cfg = config_from_path(argv[1])
        if cfg is None:
            QMessageBox.warning(win, "Cargar mapa", f"No se encontró un .gnd para:\n{argv[1]}")
        else:
            QTimer.singleShot(0, lambda: win.load_map(cfg))
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
