# SPDX-License-Identifier: GPL-3.0-only
"""Linux data-only port of Burn's Mods. No injection and no remote API calls."""
import hashlib
import json
import os
import re
import struct
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUILD = json.loads((ROOT / 'src/build.json').read_text())
APPID = '2478970'

class StageError(RuntimeError):
    def __init__(self, stage, message):
        super().__init__(message)
        self.stage = stage


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def steam_installations(home=None):
    home = Path(home or Path.home())
    candidates = [os.environ.get('STEAM_DIR'), home / 'snap/steam/common/.local/share/Steam',
                  home / '.local/share/Steam', home / '.steam/steam']
    found = []
    for candidate in candidates:
        if not candidate:
            continue
        steam = Path(candidate).expanduser().resolve()
        libraries = [steam]
        vdf = steam / 'steamapps/libraryfolders.vdf'
        if vdf.exists():
            libraries += [Path(p.replace('\\\\', '\\')) for p in
                          re.findall(r'"path"\s*"([^"]+)"', vdf.read_text())]
        for library in libraries:
            manifest = library / f'steamapps/appmanifest_{APPID}.acf'
            if not manifest.exists():
                continue
            content = manifest.read_text()
            match = re.search(r'"installdir"\s*"([^"]+)"', content)
            if not match:
                continue
            game = library / 'steamapps/common' / match[1]
            if any(x['game'] == str(game) for x in found):
                continue
            compat = library / f'steamapps/compatdata/{APPID}'
            # Steam sometimes keeps prefixes in its primary library.
            if not compat.exists():
                compat = steam / f'steamapps/compatdata/{APPID}'
            config = compat / 'config_info'
            found.append(dict(steam=str(steam), library=str(library), game=str(game),
                              compatdata=str(compat), prefix=str(compat / 'pfx'),
                              proton_config=config.read_text() if config.exists() else None,
                              buildid=(re.search(r'"buildid"\s*"([^"]+)"', content) or [None, None])[1]))
    return found


def discover(proc=Path('/proc')):
    result = []
    for entry in proc.iterdir():
        if not entry.name.isdigit():
            continue
        try:
            if entry.stat().st_uid != os.getuid():
                continue
            comm = (entry / 'comm').read_text().strip()
            if comm.lower() == 'tomb123.exe':
                result.append(int(entry.name))
        except (OSError, ValueError):
            continue
    if len(result) > 1:
        raise StageError('process discovery', 'Multiple tomb123.exe processes; close the extra game sessions.')
    return result[0] if result else None


def maps_for(pid):
    entries = []
    for line in Path(f'/proc/{pid}/maps').read_text().splitlines():
        cols = line.split(maxsplit=5)
        start, end = (int(n, 16) for n in cols[0].split('-'))
        entries.append(dict(start=start, end=end, perms=cols[1], offset=int(cols[2], 16),
                            dev=cols[3], inode=int(cols[4]), path=cols[5] if len(cols) == 6 else ''))
    return entries


def covers(maps, address, size, permission='r'):
    return any(m['start'] <= address and address + size <= m['end'] and permission in m['perms'] for m in maps)


class Connection:
    def __init__(self, pid, log=lambda *args: None):
        self.pid, self.log, self.fd, self.wfd = pid, log, None, None
        self.modules, self.fingerprints = {}, {}
        self.writes = 0
        self.jump_active = False
        self.last_feature_tick = {}
        self.last_verify = 0
        try:
            self.log('attachment', f'Opening read-only memory for PID {pid}')
            self.fd = os.open(f'/proc/{pid}/mem', os.O_RDONLY | os.O_CLOEXEC)
            self.starttime = self.identity()
            self.validate()
            self.log('script injection', 'Not used: Linux data-only backend; no Windows API/ABI calls')
        except Exception:
            self.close()
            raise

    def identity(self):
        # comm may contain spaces; fields after its final closing parenthesis start at field 3.
        return Path(f'/proc/{self.pid}/stat').read_text().rsplit(')', 1)[1].split()[19]

    def read(self, address, fmt):
        size = struct.calcsize(fmt)
        if not covers(self.maps, address, size):
            raise StageError('memory read', f'Unmapped read {address:#x}')
        data = os.pread(self.fd, size, address)
        if len(data) != size:
            raise StageError('memory read', 'Short read; game may have exited')
        return struct.unpack(fmt, data)[0]

    def validate(self):
        if self.identity() != self.starttime:
            raise StageError('process discovery', 'PID was reused; reconnect required')
        self.maps = maps_for(self.pid)
        modules = {}
        for name, spec in BUILD['modules'].items():
            candidates = [m for m in self.maps if Path(m['path']).name == name and m['offset'] == 0]
            if len(candidates) != 1:
                raise StageError('module discovery', f'Expected one mapped {name}; found {len(candidates)}')
            m = candidates[0]
            file = Path(f'/proc/{self.pid}/root') / m['path'].lstrip('/')
            st = file.stat()
            dev = f'{os.major(st.st_dev):x}:{os.minor(st.st_dev):x}'
            if st.st_ino != m['inode'] or tuple(int(x, 16) for x in dev.split(':')) != tuple(int(x, 16) for x in m['dev'].split(':')):
                raise StageError('unsupported build', f'{name}: mapped file identity differs')
            fingerprint = (str(file), st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns)
            if self.fingerprints.get(name) != fingerprint:
                if sha256(file) != spec['sha256']:
                    raise StageError('unsupported build', f'{name}: SHA-256 not in the pinned supported build; writes blocked')
                self.fingerprints[name] = fingerprint
            with file.open('rb') as stream:
                disk = stream.read(4096)
            pe = struct.unpack_from('<I', disk, 0x3c)[0]
            if disk[:2] != b'MZ' or disk[pe:pe+4] != b'PE\0\0' or struct.unpack_from('<H', disk, pe+4)[0] != 0x8664:
                raise StageError('unsupported build', f'{name}: expected x64 PE image')
            header = os.pread(self.fd, 4096, m['start'])
            # Validate PE machine/timestamp and image size, not relocated pointers.
            if header[:2] != b'MZ' or header[pe:pe+24] != disk[pe:pe+24] or header[pe+24+56:pe+24+60] != disk[pe+24+56:pe+24+60]:
                raise StageError('unsupported build', f'{name}: loaded PE header differs from verified disk image')
            modules[name] = m['start']
        if modules != self.modules:
            self.log('module discovery', json.dumps({k: hex(v) for k, v in modules.items()}))
        self.modules = modules
        self.last_verify = time.monotonic()

    def addr(self, module, field):
        return self.modules[module] + BUILD['modules'][module]['variables'][field]

    def snapshot(self):
        # Refresh writable ranges every tick; recheck file identity and hashes on change each second.
        self.maps = maps_for(self.pid)
        if time.monotonic() - self.last_verify >= 1:
            self.validate()
        exe = 'tomb123.exe'
        version = self.read(self.addr(exe, 'GameVersion'), '<i')
        level = self.read(self.addr(exe, 'Level'), '<i')
        exiting = self.read(self.addr(exe, 'ExitingGame'), '<b')
        if version not in (0, 1, 2):
            raise StageError('unsupported build', f'Unexpected game selector {version}; writes blocked')
        module = f'tomb{version+1}.dll'
        lara = self.read(self.addr(module, 'MainPlayerEntity'), '<Q')
        oxygen = self.read(self.addr(module, 'PlayerOxygen'), '<h')
        room = self.read(self.addr(module, 'RoomType'), '<h')
        valid_lara = lara != 0 and covers(self.maps, lara, 0xe50, 'w')
        health = self.read(lara + 0x26, '<h') if valid_lara else None
        menu = 24 if version == 0 else 63
        max_level = (19, 23, 26)[version]
        ready = not exiting and 0 <= level <= max_level and level != menu and valid_lara and health is not None and 0 < health <= 2000 and -1 <= oxygen <= 1900
        speed = self.read(lara + 0x24, '<h') if valid_lara else None
        return dict(pid=self.pid, patch=BUILD['patch'], module=module, level=level, lara=hex(lara),
                    oxygen=oxygen, health=health, room=room, vertical_speed=speed, ready=ready, writes=self.writes)

    def tick(self, enabled=False):
        features = enabled if isinstance(enabled, dict) else {'infinite-oxygen': enabled}
        enabled = any(features.values())
        s = self.snapshot()
        if enabled and s['ready']:
            # Check selector, level and entity again just before writing to reduce level-transition races.
            if (self.read(self.addr('tomb123.exe', 'GameVersion'), '<i') != int(s['module'][4])-1 or
                self.read(self.addr('tomb123.exe', 'Level'), '<i') != s['level'] or
                self.read(self.addr(s['module'], 'MainPlayerEntity'), '<Q') != int(s['lara'], 16)):
                return s
            now = time.monotonic()
            lara = int(s['lara'], 16)
            if features.get('infinite-oxygen') and self.due('oxygen', now, 0.01):
                self.write_s16(self.addr(s['module'], 'PlayerOxygen'), 1900)
            if features.get('infinite-health') and self.due('health', now, 0.01):
                self.write_s16(lara + 0x26, 2000)
            if features.get('no-fall-damage') and s['room'] == 0 and self.due('fall', now, 0.05):
                if s['vertical_speed'] > 130:
                    self.write_s16(lara + 0x24, 130)
            if features.get('super-jump') and s['room'] == 0 and self.due('jump', now, 0.005):
                current = s['vertical_speed']
                if self.jump_active and current < 0:
                    speed = max(-175, current - 25)
                    self.write_s16(lara + 0x24, speed)
                    if speed <= -175:
                        self.jump_active = False
                elif current == 0:
                    self.jump_active = True
            s['writes'] = self.writes
        elif not enabled or not s['ready']:
            self.disable()
        if not features.get('super-jump') or not s['ready']:
            self.jump_active = False
        return s

    def due(self, key, now, interval):
        if now - self.last_feature_tick.get(key, -100) < interval:
            return False
        self.last_feature_tick[key] = now
        return True

    def write_s16(self, address, value):
        if not covers(self.maps, address, 2, 'w'):
            raise StageError('memory write', f'Address {address:#x} is not writable; writes blocked')
        if self.wfd is None:
            self.wfd = os.open(f'/proc/{self.pid}/mem', os.O_RDWR | os.O_CLOEXEC)
            self.log('memory write', 'Opened validated data fields for writing')
        if os.pwrite(self.wfd, struct.pack('<h', value), address) != 2:
            raise StageError('memory write', 'Short data write')
        self.writes += 1

    def disable(self):
        if self.wfd is not None:
            os.close(self.wfd)
            self.wfd = None
            self.log('memory write', 'Disabled: stopped all writes; game resumes normal simulation')

    def close(self):
        self.disable()
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None
