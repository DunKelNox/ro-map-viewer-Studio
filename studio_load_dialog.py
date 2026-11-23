"""Diálogo "Cargar mapa": las mismas opciones del lanzador original (map_launcher.py),
ahora como ventana de PySide6."""
import os
from typing import Optional

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QFileDialog, QGridLayout, QHBoxLayout, QLabel,
    QLineEdit, QMessageBox, QPushButton, QVBoxLayout,
)

from studio_paths import MapConfig, propose_from_file, autodetect_water, validate_config


class LoadMapDialog(QDialog):
    """Pide los archivos del mapa. Al elegir un .gat o un .gnd propone los demás
    (mismo nombre base), la raíz de texturas y la carpeta de agua, igual que el lanzador."""

    FIELDS = ("gat", "rsw", "gnd", "tex", "water")

    def __init__(self, parent=None, initial: Optional[MapConfig] = None,
                 settings: Optional[QSettings] = None):
        super().__init__(parent)
        self.setWindowTitle("Cargar mapa")
        self.setModal(True)
        self.setMinimumWidth(720)
        self._settings = settings
        self._config: Optional[MapConfig] = None
        self._notes = []
        self.edits = {}

        root = QVBoxLayout(self)
        intro = QLabel(
            "Elegí los archivos del mapa. Al elegir el <b>.gat</b> o el <b>.gnd</b> se "
            "proponen automáticamente los demás (mismo nombre), la carpeta de texturas "
            "y la de agua. Solo el <b>.gnd</b> es obligatorio.")
        intro.setWordWrap(True)
        root.addWidget(intro)

        grid = QGridLayout()
        rows = (
            ("gat", "GAT (altura / caminable):", "file", "GAT (*.gat *.GAT);;Todos los archivos (*.*)"),
            ("rsw", "RSW (mundo / modelos):", "file", "RSW (*.rsw *.RSW);;Todos los archivos (*.*)"),
            ("gnd", "GND (terreno) — obligatorio:", "file", "GND (*.gnd *.GND);;Todos los archivos (*.*)"),
            ("tex", "Carpeta de texturas:", "dir", "Carpeta de texturas (.bmp)"),
            ("water", "Carpeta de agua (opcional):", "dir",
             "Carpeta con las texturas de agua (water000.jpg … water031.jpg)"),
        )
        for r, (key, label, kind, extra) in enumerate(rows):
            grid.addWidget(QLabel(label), r, 0)
            edit = QLineEdit()
            edit.setClearButtonEnabled(True)
            self.edits[key] = edit
            grid.addWidget(edit, r, 1)
            btn = QPushButton("Examinar…")
            btn.clicked.connect(lambda _=False, k=key, kd=kind, ex=extra: self._browse(k, kd, ex))
            grid.addWidget(btn, r, 2)
            if key in ("gat", "gnd"):
                # También al escribir/pegar una ruta a mano
                edit.editingFinished.connect(lambda k=key: self._on_edited(k))
        grid.setColumnStretch(1, 1)
        root.addLayout(grid)

        self.hint = QLabel("")
        self.hint.setWordWrap(True)
        self.hint.setStyleSheet("color: #888;")
        root.addWidget(self.hint)

        buttons = QDialogButtonBox()
        self.ok_button = buttons.addButton("Cargar mapa", QDialogButtonBox.AcceptRole)
        buttons.addButton("Cancelar", QDialogButtonBox.RejectRole)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(buttons)
        root.addLayout(row)

        if initial is not None:
            self.set_config(initial)

    # ------------------------------------------------------------------
    def set_config(self, cfg: MapConfig):
        for k in self.FIELDS:
            self.edits[k].setText(getattr(cfg, k) or "")

    def values(self) -> dict:
        return {k: self.edits[k].text().strip() for k in self.FIELDS}

    def config(self) -> Optional[MapConfig]:
        """Configuración validada (solo tiene sentido tras ``exec()`` == Accepted)."""
        return self._config

    def notes(self):
        return list(self._notes)

    # ------------------------------------------------------------------
    def _start_dir(self, key: str) -> str:
        cur = self.edits[key].text().strip()
        if cur:
            return cur if os.path.isdir(cur) else os.path.dirname(cur)
        for other in ("gnd", "gat", "rsw", "tex"):
            v = self.edits[other].text().strip()
            if v:
                return v if os.path.isdir(v) else os.path.dirname(v)
        if self._settings is not None:
            return str(self._settings.value("last_dir", "") or "")
        return ""

    def _browse(self, key: str, kind: str, extra: str):
        start = self._start_dir(key)
        if kind == "file":
            path, _ = QFileDialog.getOpenFileName(
                self, f"Elegir archivo {key.upper()}", start, extra)
        else:
            path = QFileDialog.getExistingDirectory(self, extra, start)
        if not path:
            return
        self.edits[key].setText(path)
        if self._settings is not None:
            self._settings.setValue(
                "last_dir", path if os.path.isdir(path) else os.path.dirname(path))
        self._after_pick(key, path)

    def _on_edited(self, key: str):
        path = self.edits[key].text().strip()
        if path and os.path.isfile(path):
            self._after_pick(key, path)

    def _after_pick(self, key: str, path: str):
        """Completa los campos vacíos a partir del archivo elegido."""
        if key in ("gat", "gnd"):
            new = propose_from_file(path, {k: self.edits[k].text().strip() for k in self.FIELDS})
            filled = []
            for k in self.FIELDS:
                if new.get(k) and not self.edits[k].text().strip():
                    self.edits[k].setText(new[k])
                    filled.append(k.upper())
            if filled:
                self.hint.setText("Propuesto automáticamente: " + ", ".join(filled))
        elif key == "tex" and not self.edits["water"].text().strip():
            w = autodetect_water(path)
            if w:
                self.edits["water"].setText(w)
                self.hint.setText("Propuesto automáticamente: WATER")

    # ------------------------------------------------------------------
    def accept(self):
        v = self.values()
        cfg, errors, warnings, notes = validate_config(v["gat"], v["rsw"], v["gnd"], v["tex"], v["water"])
        if errors:
            QMessageBox.critical(self, "No se puede cargar el mapa", "\n\n".join(errors))
            return
        for w in warnings:
            QMessageBox.warning(self, "Aviso", w)
        self._config = cfg
        self._notes = notes
        if self._settings is not None and cfg is not None:
            self._settings.setValue("last_dir", os.path.dirname(cfg.gnd))
        super().accept()
