#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Render the native window on a test display; never attaches to the game."""
import argparse
from pathlib import Path
import queue
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from app import FEATURES, VERSION
from ui import create_window

class PreviewController:
    def __init__(self):
        self.features={};self.events=queue.Queue()
        self.events.put({'state':'Preview — mods off','detail':'Visual preview only. No game connection or memory writes.'})
    def diag(self,*args):pass
    def shutdown(self):pass

p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);args=p.parse_args()
root=Path(__file__).resolve().parents[1]
win, controls=create_window(PreviewController(),root/'work/preview-settings.json',root/'logs/super-lara.log',VERSION,FEATURES)
win.update()
subprocess.run(['import','-window',str(win.winfo_id()),str(args.output)],check=True)
controls['close']()
print(args.output)
