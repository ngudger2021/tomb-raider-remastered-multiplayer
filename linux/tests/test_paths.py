# SPDX-License-Identifier: GPL-3.0-only
import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from paths import user_paths

class PathTests(unittest.TestCase):
    def test_default_paths_are_per_user(self):
        paths=user_paths({},Path('/example/home'))
        self.assertEqual(paths['config'],Path('/example/home/.config/super-lara'))
        self.assertEqual(paths['state'],Path('/example/home/.local/state/super-lara'))
        self.assertEqual(paths['runtime'],paths['state'])
    def test_xdg_overrides_and_runtime_lock(self):
        p=user_paths({'XDG_CONFIG_HOME':'/example/config','XDG_STATE_HOME':'/example/state','XDG_RUNTIME_DIR':'/example/runtime'})
        self.assertEqual(p['config'],Path('/example/config/super-lara'))
        self.assertEqual(p['state'],Path('/example/state/super-lara'))
        self.assertEqual(p['runtime'],Path('/example/runtime/super-lara'))

if __name__=='__main__':unittest.main()
