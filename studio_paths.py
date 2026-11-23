"""Lógica de carga de mapas, sin dependencias de Qt (testeable y reutilizable).

Es la lógica que estaba dentro de ``map_launcher.py`` (autoproponer RSW/GND/GAT del
mismo nombre, raíz de texturas, carpeta de agua y validación), separada de la interfaz.
"""
import os
import re
from dataclasses import dataclass, asdict
from typing import List, Optional, Tuple


@dataclass
class MapConfig:
    """Archivos que definen un mapa. Solo ``gnd`` es obligatorio para el visor 3D."""
    gnd: str
    gat: Optional[str] = None
    rsw: Optional[str] = None
    tex: Optional[str] = None     # raíz de texturas (puede ser la carpeta ``data``)
    water: Optional[str] = None   # carpeta con water000.jpg … water031.jpg

    @property
    def name(self) -> str:
        return os.path.splitext(os.path.basename(self.gnd))[0]

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> Optional["MapConfig"]:
        try:
            return MapConfig(
                gnd=str(d["gnd"]),
                gat=d.get("gat") or None,
                rsw=d.get("rsw") or None,
                tex=d.get("tex") or None,
                water=d.get("water") or None,
            )
        except Exception:
            return None


# ----------------------------------------------------------------------
# Sugerencias automáticas
# ----------------------------------------------------------------------

def suggest_sibling(path: str, ext: str) -> Optional[str]:
    """Si existe ``path`` con otra extensión en la misma carpeta, la devuelve."""
    base, _ = os.path.splitext(path)
    for e in (ext.lower(), ext.upper()):
        candidate = base + e
        if os.path.isfile(candidate):
            return candidate
    return None


def suggest_texture_root(map_dir: str) -> str:
    """Raíz de texturas probable para un mapa: prefiere una carpeta ``data`` cercana."""
    suggested = map_dir
    for candidate in (
        os.path.join(map_dir, "data"),
        os.path.join(map_dir, "..", "data"),
        os.path.abspath(os.path.join(map_dir, "..")),
        map_dir,
    ):
        tex_probe = os.path.join(candidate, "texture")
        data_tex = os.path.join(candidate, "data", "texture")
        if os.path.isdir(tex_probe) or os.path.isdir(data_tex) or (
            os.path.basename(os.path.abspath(candidate)).lower() == "data"
            and os.path.isdir(candidate)
        ):
            suggested = os.path.abspath(candidate)
            break
    return suggested


_WATER_RE = re.compile(r"^water\d\d\d\.(jpg|jpeg|bmp|png|tga)$", re.I)


def find_water_dir(root: Optional[str], max_depth: int = 3) -> Optional[str]:
    """Busca bajo ``root`` una carpeta que contenga water0NN.jpg (o bmp/png/tga)."""
    if not root or not os.path.isdir(root):
        return None
    base_depth = os.path.abspath(root).rstrip(os.sep).count(os.sep)
    for dp, dn, fn in os.walk(root):
        if dp.count(os.sep) - base_depth >= max_depth:
            dn[:] = []
        if any(_WATER_RE.match(f) for f in fn):
            return dp
    return None


def autodetect_water(tex_root: Optional[str]) -> Optional[str]:
    """Carpeta de agua probable bajo la raíz de texturas."""
    if not tex_root:
        return None
    for cand in (tex_root, os.path.join(tex_root, "texture"),
                 os.path.join(tex_root, "data", "texture")):
        found = find_water_dir(cand)
        if found:
            return found
    return None


def propose_from_file(path: str, current: dict) -> dict:
    """Dado un .gat o .gnd elegido, completa SOLO los campos vacíos de ``current``
    (claves: gat, rsw, gnd, tex, water). Devuelve un dict nuevo con las propuestas."""
    out = dict(current)
    ext = os.path.splitext(path)[1].lower()
    if ext == ".gat" and not out.get("gat"):
        out["gat"] = path
    if ext == ".gnd" and not out.get("gnd"):
        out["gnd"] = path
    for key, e in (("rsw", ".rsw"), ("gnd", ".gnd"), ("gat", ".gat")):
        if not out.get(key):
            sib = suggest_sibling(path, e)
            if sib:
                out[key] = sib
    if not out.get("tex"):
        out["tex"] = suggest_texture_root(os.path.dirname(path))
    if not out.get("water"):
        w = autodetect_water(out.get("tex"))
        if w:
            out["water"] = w
    return out


# ----------------------------------------------------------------------
# Validación
# ----------------------------------------------------------------------

def validate_config(gat: str, rsw: str, gnd: str, tex: str, water: str
                    ) -> Tuple[Optional[MapConfig], List[str], List[str], List[str]]:
    """Valida los campos del formulario.
    Devuelve (config|None, errores, avisos, notas):
      - errores: impiden cargar.
      - avisos : se muestran al usuario pero no impiden cargar (carpeta de agua inválida).
      - notas  : informativas, sin interrumpir (faltan .rsw o .gat).

    Equivale a ``_validate_common(need_gnd=True, need_tex=True)`` del lanzador, salvo
    que el GAT es opcional (el visor 3D funciona sin él; sin GAT no hay overlay
    caminable ni piso GAT en el marcador de celda).
    """
    errors: List[str] = []
    warnings: List[str] = []
    notes: List[str] = []
    gat = (gat or "").strip() or None
    rsw = (rsw or "").strip() or None
    gnd = (gnd or "").strip() or None
    tex = (tex or "").strip() or None
    water = (water or "").strip() or None

    if not gnd:
        errors.append("Falta el archivo .gnd (el visor de terreno 3D lo necesita).")
    elif not os.path.isfile(gnd):
        errors.append(f"No existe el .gnd:\n{gnd}")
    if gat and not os.path.isfile(gat):
        errors.append(f"No existe el .gat:\n{gat}")
    if rsw and not os.path.isfile(rsw):
        errors.append(f"No existe el .rsw:\n{rsw}")

    if not tex and gnd:
        tex = os.path.dirname(gnd)
    if tex and not os.path.isdir(tex):
        errors.append(f"No existe la carpeta de texturas:\n{tex}")

    if water and not os.path.isdir(water):
        warnings.append(f"No existe la carpeta de agua:\n{water}\n\n"
                        "Se ignora (agua animada procedural).")
        water = None

    if errors:
        return None, errors, warnings, notes
    if not rsw:
        notes.append("sin .rsw: el mapa se carga sin modelos 3D")
    if not gat:
        notes.append("sin .gat: no hay overlay caminable ni piso GAT en el marcador")
    return MapConfig(gnd=gnd, gat=gat, rsw=rsw, tex=tex, water=water), errors, warnings, notes
