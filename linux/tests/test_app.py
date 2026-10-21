# SPDX-License-Identifier: GPL-3.0-only
"""Read-only CLI semantics and worker/UI queue handoff."""
import contextlib
import io
from pathlib import Path
import queue
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from app import Controller, cli


class AppTests(unittest.TestCase):
    def test_inspection_does_not_register_a_write_toggle(self):
        args = SimpleNamespace(installations=False, oxygen=False, seconds=0)
        with patch('app.discover', return_value=123), patch('app.Connection') as factory, \
                patch('app.signal.signal') as register, contextlib.redirect_stdout(io.StringIO()):
            connection = factory.return_value
            connection.tick.return_value = {'ready': True}
            cli(args)
        register.assert_not_called()
        connection.tick.assert_called_once_with(False)
        connection.close.assert_called_once()

    def test_explicit_oxygen_test_registers_and_restores_toggle(self):
        args = SimpleNamespace(installations=False, oxygen=True, seconds=0.1)
        with patch('app.discover', return_value=123), patch('app.Connection') as factory, \
                patch('app.time.monotonic', side_effect=[0, 1]), \
                patch('app.signal.signal', return_value=0) as register, \
                contextlib.redirect_stdout(io.StringIO()):
            connection = factory.return_value
            connection.tick.return_value = {'ready': True}
            cli(args)
        connection.tick.assert_called_once_with(True)
        self.assertEqual(register.call_count, 2)
        self.assertEqual(register.call_args.args[1], 0)
        connection.close.assert_called_once()

    def test_full_status_queue_keeps_latest_update(self):
        controller = Controller.__new__(Controller)
        controller.events = queue.Queue(maxsize=1)
        controller.events.put_nowait({'state': 'old'})
        controller.emit({'state': 'new'})
        self.assertEqual(controller.events.get_nowait(), {'state': 'new'})

    def test_ui_draining_full_queue_does_not_fail_worker(self):
        class DrainedQueue:
            def __init__(self):
                self.calls = 0
                self.latest = None

            def put_nowait(self, value):
                self.calls += 1
                if self.calls == 1:
                    raise queue.Full
                self.latest = value

            def get_nowait(self):
                raise queue.Empty

        controller = Controller.__new__(Controller)
        controller.events = DrainedQueue()
        controller.emit({'state': 'new'})
        self.assertEqual(controller.events.latest, {'state': 'new'})


if __name__ == '__main__':
    unittest.main()
