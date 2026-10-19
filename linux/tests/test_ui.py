# SPDX-License-Identifier: GPL-3.0-only
import json
import os
from pathlib import Path
import queue
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

class FakeController:
    def __init__(self):
        self.features={};self.events=queue.Queue();self.closed=False
    def diag(self,*args):pass
    def shutdown(self):self.closed=True

@unittest.skipUnless(os.environ.get('DISPLAY'), 'Run with xvfb-run to verify the native window')
class UiTests(unittest.TestCase):
    def setUp(self):
        from app import FEATURES, VERSION
        from ui import create_window
        root=Path(__file__).resolve().parents[1]/'work'
        root.mkdir(exist_ok=True)
        self.temp=Path(tempfile.mkdtemp(prefix='ui-test-',dir=root))
        self.controller=FakeController()
        self.pref=self.temp/'settings.json'
        self.win,self.controls=create_window(self.controller,self.pref,self.temp/'log',VERSION,FEATURES)
        self.win.update()
    def tearDown(self):
        self.controls['close']()
    def test_brand_images_and_window_identity(self):
        self.assertEqual(self.win.winfo_class(),'Superlara')
        for name in ['header','burn_256.png','discord','github','support','speedrun']:
            self.assertIn(name,self.win.branding_images)
        self.assertGreater(self.win.branding_images['header'].width(),0)
    def test_controls_persist_then_disable_all(self):
        for widget in self.controls['checkboxes'].values():widget.invoke()
        self.assertTrue(all(self.controller.features.values()))
        self.assertTrue(all(json.loads(self.pref.read_text())['preferred_features'].values()))
        self.controls['stop'].invoke()
        self.assertFalse(any(self.controller.features.values()))
        self.assertFalse(any(json.loads(self.pref.read_text())['preferred_features'].values()))
    def test_connection_error_clears_checked_controls(self):
        self.controls['checkboxes']['infinite-oxygen'].invoke()
        self.controller.events.put({'state':'Connection failure','detail':'Test failure'})
        self.win.after(180,self.win.quit)
        self.win.mainloop()
        self.assertFalse(any(v.get() for v in self.controls['variables'].values()))

if __name__=='__main__':unittest.main()
