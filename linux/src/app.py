#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
import argparse
import fcntl
import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import queue
import signal
import sys
import threading
import time
from backend import BUILD, ROOT, Connection, StageError, discover, steam_installations
from paths import user_paths

VERSION = '0.1.0~beta2'
PATHS = user_paths()
DATA = PATHS['config']
LOG = PATHS['state'] / 'super-lara.log'
FEATURES = {'infinite-oxygen': 'Infinite oxygen', 'infinite-health': 'Infinite health',
            'no-fall-damage': 'No fall damage', 'super-jump': 'Super jump'}
logger = logging.getLogger('super-lara')
logger.setLevel(logging.INFO)
def configure_runtime():
    for directory in set(PATHS.values()):
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    handler = RotatingFileHandler(LOG, maxBytes=2_000_000, backupCount=3)
    handler.setFormatter(logging.Formatter('%(asctime)s %(message)s'))
    logger.addHandler(handler)
    logger.addHandler(logging.StreamHandler())


class Diagnostics:
    def __init__(self):
        self.last = {}
    def __call__(self, stage, message):
        key = (stage, message)
        if len(self.last) > 256:
            self.last = {k: v for k, v in self.last.items() if time.monotonic() - v < 60}
        now = time.monotonic()
        if now - self.last.get(key, -100) >= 10:
            logger.info('[%s] %s', stage, message)
            self.last[key] = now

class Controller:
    def __init__(self):
        self.features = {key: False for key in FEATURES}
        self.stop = threading.Event()
        self.events = queue.Queue(maxsize=4)
        self.diag = Diagnostics()
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()
    def emit(self, value):
        try:
            self.events.put_nowait(value)
        except queue.Full:
            self.events.get_nowait()
            self.events.put_nowait(value)
    def run(self):
        connection = None
        next_event = next_sample = 0
        try:
            while not self.stop.is_set():
                try:
                    if connection is None:
                        pid = discover()
                        if pid is None:
                            self.emit({'state': 'Game not running', 'detail': 'Start app 2478970 through Steam.'})
                            self.stop.wait(1)
                            continue
                        self.emit({'state': 'Connecting', 'detail': f'Validating PID {pid} and all four modules…'})
                        connection = Connection(pid, self.diag)
                        self.diag('build validation', BUILD['name'])
                    requested = self.features.copy()
                    status = connection.tick(requested)
                    status['features'] = [key for key, value in requested.items() if value]
                    status['state'] = ('Mods active' if any(requested.values()) else 'Connected — mods off') if status['ready'] else 'Connected — waiting for a playable level'
                    status['detail'] = f"{status['module']} · level {status['level']} · oxygen {status['oxygen']} · health {status['health']} · writes {status['writes']}"
                    now = time.monotonic()
                    if now >= next_event:
                        self.emit(status)
                        next_event = now + 0.2
                    if now >= next_sample:
                        self.diag('telemetry', json.dumps(status, sort_keys=True))
                        next_sample = now + 2
                    self.stop.wait(0.005)
                except Exception as exc:
                    if connection:
                        connection.close()
                        connection = None
                    stage = getattr(exc, 'stage', 'attachment / memory access')
                    self.diag(stage, f'{type(exc).__name__}: {exc}')
                    self.emit({'state': 'Unsupported build' if stage == 'unsupported build' else 'Connection failure',
                               'detail': f'{stage}: {exc}. See {LOG}'})
                    # Require explicit re-enabling following any error; never silently retry writes.
                    self.features = {key: False for key in FEATURES}
                    self.stop.wait(3)
        finally:
            if connection:
                connection.close()
    def shutdown(self):
        self.features = {key: False for key in FEATURES}
        self.stop.set()
        self.thread.join(timeout=5)


def cli(args):
    diag = Diagnostics()
    if args.installations:
        print(json.dumps(steam_installations(), indent=2))
        return
    pid = discover()
    if pid is None:
        raise StageError('process discovery', 'Game not running')
    with_connection = Connection(pid, diag)
    enabled = args.oxygen
    # SIGUSR1 toggles the timed test without touching the game UI.
    def toggle(*_):
        nonlocal enabled
        enabled = not enabled
        diag('control', f'oxygen enabled={enabled}')
    signal.signal(signal.SIGUSR1, toggle)
    try:
        until = time.monotonic() + args.seconds
        next_sample = 0
        while True:
            status = with_connection.tick(enabled)
            now = time.monotonic()
            if now >= next_sample:
                print(json.dumps(dict(status, oxygen_enabled=enabled)), flush=True)
                next_sample = now + 1
            if now >= until:
                break
            time.sleep(0.01)
    finally:
        with_connection.close()


def gui():
    from ui import run_ui
    run_ui(Controller(), DATA / 'settings.json', LOG, VERSION, FEATURES)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Native Super Lara')
    parser.add_argument('--version', action='version', version='Super Lara ' + VERSION)
    parser.add_argument('--inspect', action='store_true', help='Read-only live inspection')
    parser.add_argument('--installations', action='store_true', help='Print detected Steam libraries and Proton prefix')
    parser.add_argument('--oxygen', action='store_true', help='Enable oxygen in CLI test')
    parser.add_argument('--seconds', type=float, default=0, help='CLI test duration; SIGUSR1 toggles oxygen')
    args = parser.parse_args()
    if os.geteuid() == 0:
        sys.exit('Run Super Lara as your desktop user, without sudo.')
    if args.seconds < 0 or (args.oxygen and args.seconds <= 0):
        parser.error('--oxygen requires a positive --seconds duration; durations cannot be negative')
    configure_runtime()
    # Prevent two instances of this port writing concurrently. This does not detect other trainers.
    lock = open(PATHS['runtime'] / 'instance.lock', 'a')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        sys.exit('Super Lara is already running. Close the other instance first.')
    try:
        if args.inspect or args.installations or args.oxygen:
            cli(args)
        else:
            gui()
    except KeyboardInterrupt:
        pass
    except Exception as exc:
        logger.error('[%s] %s: %s', getattr(exc, 'stage', 'application'), type(exc).__name__, exc)
        sys.exit(1)
