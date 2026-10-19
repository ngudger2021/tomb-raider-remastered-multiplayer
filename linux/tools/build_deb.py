#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Build a deterministic, script-free .deb and its corresponding source archive."""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ['app.py', 'backend.py', 'paths.py', 'ui.py', 'build.json']


def upstream_root():
    for candidate in [ROOT / 'upstream', ROOT.parent / 'upstream', ROOT.parent]:
        if (candidate / 'LICENSE').is_file() and (candidate / 'client').is_dir():
            return candidate
    raise RuntimeError('Pinned upstream source and licence not found')


def add_source(tar, path, name, epoch):
    info = tar.gettarinfo(str(path), arcname=name)
    info.uid = info.gid = 0
    info.uname = info.gname = ''
    info.mtime = epoch
    if path.is_file():
        with path.open('rb') as stream:
            tar.addfile(info, stream)
    else:
        tar.addfile(info)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--release', action='store_true', help='Reject placeholder maintainer metadata; does not publish')
    parser.add_argument('--maintainer', help='Name <email> recorded in DEBIAN/control')
    parser.add_argument('--output', type=Path, default=ROOT / 'dist')
    args = parser.parse_args()
    release = json.loads((ROOT / 'packaging/release.json').read_text())
    version = release['version']
    maintainer = args.maintainer or release['maintainer']
    if not re.fullmatch(r'[0-9][a-zA-Z0-9.+:~\-]*', version):
        parser.error('Invalid Debian version')
    if not re.fullmatch(r'[^\n\r<>]+ <[^\s<>]+@[^\s<>]+>', maintainer):
        parser.error('Maintainer must be Name <email>, without line breaks')
    if f"VERSION = '{version}'" not in (ROOT / 'src/app.py').read_text():
        parser.error('Application VERSION and packaging/release.json must agree')
    if args.release and 'example.invalid' in maintainer:
        parser.error('Set the actual package maintainer before a public release')
    epoch = int(os.environ.get('SOURCE_DATE_EPOCH', release['source_date_epoch']))
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    work = ROOT / 'work'
    work.mkdir(exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='deb-', dir=work))
    def write(name, value, mode=0o644):
        target = stage / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(value.encode() if isinstance(value, str) else value)
        target.chmod(mode)
    for name in RUNTIME:
        write('usr/lib/super-lara/src/' + name, (ROOT / 'src' / name).read_bytes())
    for asset in sorted((ROOT / 'src/assets').rglob('*')):
        if asset.is_file():
            write('usr/lib/super-lara/src/assets/' + str(asset.relative_to(ROOT / 'src/assets')), asset.read_bytes())
    write('usr/bin/super-lara', (ROOT / 'packaging/super-lara').read_bytes(), 0o755)
    write('usr/share/applications/super-lara.desktop', (ROOT / 'packaging/super-lara.desktop').read_bytes())
    write('usr/share/icons/hicolor/256x256/apps/super-lara.png', (ROOT / 'src/assets/images/burn_256.png').read_bytes())
    write('usr/share/icons/hicolor/128x128/apps/super-lara.png', (ROOT / 'src/assets/images/burn.png').read_bytes())
    write('usr/share/pixmaps/super-lara.png', (ROOT / 'src/assets/images/burn_256.png').read_bytes())
    write('usr/share/doc/super-lara/LICENSE', (upstream_root() / 'LICENSE').read_bytes())
    write('usr/share/doc/super-lara/NOTICE', (ROOT / 'NOTICE').read_bytes())
    write('usr/share/doc/super-lara/README.md', (ROOT / 'packaging/README.md').read_bytes())
    write('usr/share/doc/super-lara/UPSTREAM.json', (ROOT / 'UPSTREAM.json').read_bytes())
    write('usr/share/doc/super-lara/copyright', '''Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
Upstream-Name: Burn's Mods — Super Lara Linux adaptation
Source: https://github.com/burn-sours/tomb-raider-remastered-multiplayer

Files: *
Copyright: 2026 burn_sours
           2026 Super Lara Linux contributors
License: GPL-3.0-only
 On Debian systems the complete GPL-3 licence is in
 /usr/share/common-licenses/GPL-3; a copy is included as LICENSE.
''')
    manual = (ROOT / 'packaging/super-lara.1').read_bytes()
    write('usr/share/man/man1/super-lara.1.gz', gzip.compress(manual, mtime=0))
    size = sum(p.stat().st_size for p in stage.rglob('*') if p.is_file())
    write('DEBIAN/control', f'''Package: super-lara
Version: {version}
Section: games
Priority: optional
Architecture: amd64
Maintainer: {maintainer}
Depends: python3 (>= 3.10), python3-tk
Installed-Size: {(size + 1023) // 1024}
Homepage: https://github.com/burn-sours/tomb-raider-remastered-multiplayer
Description: native Super Lara mods for Tomb Raider I-III Remastered
 Linux data-only backend with a native desktop interface for the Steam game.
 Includes infinite oxygen, infinite health, no fall damage and super jump.
 Validates the exact supported game build before writing process memory.
 No Frida, Wine helper, root runtime or security-setting changes required.
''')
    sums = []
    for path in sorted((stage / 'usr').rglob('*')):
        if path.is_file():
            sums.append(hashlib.md5(path.read_bytes()).hexdigest() + '  ' + str(path.relative_to(stage)))
    write('DEBIAN/md5sums', '\n'.join(sums) + '\n')
    for path in sorted(stage.rglob('*'), reverse=True):
        if path.is_dir():
            path.chmod(0o755)
        os.utime(path, (epoch, epoch), follow_symlinks=False)
    stage.chmod(0o755)
    os.utime(stage, (epoch, epoch))
    env = os.environ.copy()
    env['SOURCE_DATE_EPOCH'] = str(epoch)
    deb = output / f'super-lara_{version}_amd64.deb'
    subprocess.run(['dpkg-deb', '--root-owner-group', '--build', str(stage), str(deb)], env=env, check=True)
    # The source is explicit: no user logs/settings, game files, executables, Git data, or Frida runtime.
    source_files = []
    for directory in ['src', 'packaging', 'tests']:
        source_files += [(p, 'linux/' + str(p.relative_to(ROOT))) for p in (ROOT / directory).rglob('*')
                         if p.is_file() and '__pycache__' not in p.parts]
    for name in ['tools/build_deb.py', 'tools/test_deb.py', 'tools/import_branding.py', 'tools/preview_ui.py', 'UPSTREAM.json', 'UPSTREAM_FILES.json', 'NOTICE', 'README.md', 'VERIFICATION.md', 'RELEASE.md', 'run.sh']:
        path = ROOT / name
        if path.exists():
            source_files.append((path, 'linux/' + name))
    original = upstream_root()
    # Include only the pinned upstream file list, never arbitrary files in a user's checkout.
    original = original.resolve()
    for name in json.loads((ROOT / 'UPSTREAM_FILES.json').read_text()):
        relative = Path(name)
        if relative.is_absolute() or '..' in relative.parts:
            raise RuntimeError('Invalid upstream source path')
        path = original / relative
        if not path.is_file() or not path.resolve().is_relative_to(original):
            raise RuntimeError('Missing or unsafe upstream source file: ' + name)
        source_files.append((path, 'upstream/' + name))
    source = output / f'super-lara_{version}_source.tar.gz'
    with source.open('wb') as raw:
        with gzip.GzipFile(filename='', fileobj=raw, mode='wb', mtime=epoch) as compressed:
            with tarfile.open(fileobj=compressed, mode='w', format=tarfile.GNU_FORMAT) as tar:
                for path, name in sorted(source_files, key=lambda item: item[1]):
                    add_source(tar, path, f'super-lara-{version}/' + name, epoch)
    checks = output / f'super-lara_{version}_SHA256SUMS'
    checks.write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest() + '  ' + p.name + '\n' for p in [deb, source]))
    print('Staging tree retained:', stage)
    print('Package:', deb)
    print('Corresponding source:', source)
    print('Checksums:', checks)
    if 'example.invalid' in maintainer:
        print('BETA CANDIDATE ONLY: replace the placeholder Maintainer before public release.')

if __name__ == '__main__':
    main()
