"""Pruebas del módulo de entrada y guarda contra dependencias no deseadas.
python -m unittest test_inputs -v"""
import glob
import os
import re
import unittest

import inputs as inp


class InputsTest(unittest.TestCase):
    def test_keys_are_unique(self):
        names = [n for n in dir(inp) if n.startswith("K_")]
        values = [getattr(inp, n) for n in names]
        self.assertEqual(len(values), len(set(values)), "hay teclas con el mismo código")

    def test_letters_and_digits_use_ascii(self):
        self.assertEqual(inp.K_g, ord("g"))
        self.assertEqual(inp.K_p, ord("p"))
        self.assertEqual(inp.K_1, ord("1"))
        self.assertEqual(inp.K_a + 1, inp.K_b)          # consecutivas (el mapeo Qt lo usa)
        self.assertEqual(inp.K_0 + 4, inp.K_4)

    def test_event_defaults(self):
        e = inp.InputEvent(inp.KEYDOWN, key=inp.K_p, mod=inp.KMOD_SHIFT)
        self.assertEqual((e.button, e.pos, e.unicode), (0, (0, 0), ""))
        self.assertTrue(e.mod & inp.KMOD_SHIFT)

    def test_handler_reads_only_existing_fields(self):
        src = open(os.path.join(os.path.dirname(__file__), "terrain_viewer_3d.py"),
                   encoding="utf-8").read()
        used = set(re.findall(r"event\.([a-z_]+)", src))
        self.assertLessEqual(used, set(inp.InputEvent.__dataclass_fields__))

    def test_project_does_not_import_pygame(self):
        here = os.path.dirname(__file__)
        for path in glob.glob(os.path.join(here, "*.py")):
            if os.path.basename(path).startswith("test_"):
                continue
            text = open(path, encoding="utf-8").read()
            self.assertIsNone(re.search(r"^\s*(import|from)\s+pygame", text, re.M),
                              f"{os.path.basename(path)} importa pygame")


if __name__ == "__main__":
    unittest.main()
