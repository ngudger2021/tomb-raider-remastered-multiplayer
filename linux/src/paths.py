# SPDX-License-Identifier: GPL-3.0-only
"""Per-user state paths; installed application files remain read-only."""
import os
from pathlib import Path


def user_paths(environ=None, home=None):
    env = os.environ if environ is None else environ
    home = Path(home or Path.home())
    config = Path(env.get('XDG_CONFIG_HOME') or home / '.config') / 'super-lara'
    state = Path(env.get('XDG_STATE_HOME') or home / '.local/state') / 'super-lara'
    runtime = Path(env['XDG_RUNTIME_DIR']) / 'super-lara' if env.get('XDG_RUNTIME_DIR') else state
    return {'config': config, 'state': state, 'runtime': runtime}
