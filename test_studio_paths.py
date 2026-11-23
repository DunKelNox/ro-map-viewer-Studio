"""Pruebas de studio_paths (sin Qt): python -m unittest test_studio_paths -v"""
import os
import tempfile
import unittest

from studio_paths import (
    MapConfig, autodetect_water, find_water_dir, propose_from_file,
    suggest_sibling, suggest_texture_root, validate_config,
)


def touch(path, data=b""):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)
    return path


class PathsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def test_sibling(self):
        gat = touch(os.path.join(self.root, "m", "aldebaran.gat"))
        rsw = touch(os.path.join(self.root, "m", "aldebaran.rsw"))
        self.assertEqual(suggest_sibling(gat, ".rsw"), rsw)
        self.assertIsNone(suggest_sibling(gat, ".gnd"))

    def test_texture_root_prefers_data(self):
        m = os.path.join(self.root, "proj", "maps")
        os.makedirs(os.path.join(self.root, "proj", "data", "texture"))
        os.makedirs(m)
        self.assertEqual(os.path.abspath(suggest_texture_root(m)),
                         os.path.abspath(os.path.join(self.root, "proj", "data")))
        # sin carpetas data/texture: se queda con la carpeta del mapa
        solo = os.path.join(self.root, "solo")
        os.makedirs(solo)
        self.assertEqual(suggest_texture_root(solo), solo)

    def test_water_detection(self):
        tex = os.path.join(self.root, "data", "texture")
        touch(os.path.join(tex, "워터", "water000.jpg"))
        self.assertEqual(find_water_dir(tex), os.path.join(tex, "워터"))
        self.assertEqual(autodetect_water(os.path.join(self.root, "data")), os.path.join(tex, "워터"))
        self.assertIsNone(find_water_dir(os.path.join(self.root, "no_existe")))

    def test_propose_fills_only_empty_fields(self):
        gat = touch(os.path.join(self.root, "m", "prt.gat"))
        gnd = touch(os.path.join(self.root, "m", "prt.gnd"))
        rsw = touch(os.path.join(self.root, "m", "prt.rsw"))
        mine = os.path.join(self.root, "mi_rsw.rsw")
        out = propose_from_file(gat, {"rsw": mine})
        self.assertEqual(out["rsw"], mine)          # no pisa lo que ya había
        self.assertEqual(out["gnd"], gnd)
        self.assertEqual(out["gat"], gat)
        out = propose_from_file(gnd, {})
        self.assertEqual((out["gat"], out["rsw"], out["gnd"]), (gat, rsw, gnd))

    def test_validate(self):
        gnd = touch(os.path.join(self.root, "m", "x.gnd"))
        cfg, errors, warnings, notes = validate_config("", "", gnd, "", "")
        self.assertEqual(errors, [])
        self.assertEqual(cfg.tex, os.path.dirname(gnd))        # texturas por defecto
        self.assertEqual(len(notes), 2)                         # sin rsw y sin gat
        cfg, errors, _, _ = validate_config("", "", "", "", "")
        self.assertIsNone(cfg)
        self.assertTrue(any("gnd" in e for e in errors))
        _, errors, _, _ = validate_config(os.path.join(self.root, "falta.gat"), "", gnd, "", "")
        self.assertTrue(any("gat" in e for e in errors))
        _, errors, _, _ = validate_config("", "", gnd, os.path.join(self.root, "nada"), "")
        self.assertTrue(any("texturas" in e for e in errors))
        cfg, errors, warnings, _ = validate_config("", "", gnd, "", os.path.join(self.root, "agua"))
        self.assertEqual(errors, [])
        self.assertIsNone(cfg.water)                            # agua inválida: se ignora
        self.assertEqual(len(warnings), 1)

    def test_config_roundtrip(self):
        c = MapConfig(gnd="/a/b/c.gnd", gat="/a/b/c.gat", tex="/a")
        self.assertEqual(MapConfig.from_dict(c.to_dict()), c)
        self.assertEqual(c.name, "c")
        self.assertIsNone(MapConfig.from_dict({"sin": "gnd"}))


if __name__ == "__main__":
    unittest.main()
