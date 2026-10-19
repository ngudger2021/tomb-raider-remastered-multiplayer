#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Inspect and exercise a package without installing files on the host system."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('deb', type=Path)
    args = parser.parse_args()
    deb = args.deb.resolve()
    info = subprocess.check_output(['dpkg-deb', '--field', str(deb)], text=True)
    assert 'Architecture: amd64' in info
    assert 'Depends: python3 (>= 3.10), python3-tk' in info
    control = subprocess.check_output(['dpkg-deb', '--ctrl-tarfile', str(deb)])
    with tarfile.open(fileobj=io.BytesIO(control)) as tar:
        assert {p.name.lstrip('./') for p in tar.getmembers()} <= {'', 'control', 'md5sums'}
    data = subprocess.check_output(['dpkg-deb', '--fsys-tarfile', str(deb)])
    with tarfile.open(fileobj=io.BytesIO(data)) as tar:
        for member in tar.getmembers():
            assert member.uid == member.gid == 0, member.name
            assert not member.mode & 0o6022, member.name
            assert not member.issym() and not member.islnk(), member.name
            assert member.name in ('.', './usr') or member.name.startswith('./usr/'), member.name
            assert '__pycache__' not in member.name and '/home/' not in member.name
    (ROOT / 'work').mkdir(exist_ok=True)
    temp = Path(tempfile.mkdtemp(prefix='package-test-', dir=ROOT / 'work'))
    subprocess.run(['dpkg-deb', '--extract', str(deb), str(temp / 'root')], check=True)
    subprocess.run(['dpkg-deb', '--control', str(deb), str(temp / 'control')], check=True)
    for line in (temp / 'control/md5sums').read_text().splitlines():
        digest, name = line.split('  ', 1)
        assert hashlib.md5((temp / 'root' / name).read_bytes()).hexdigest() == digest
    subprocess.run(['desktop-file-validate', str(temp / 'root/usr/share/applications/super-lara.desktop')], check=True)
    desktop = (temp / 'root/usr/share/applications/super-lara.desktop').read_text()
    assert 'Icon=super-lara' in desktop and 'StartupWMClass=Superlara' in desktop
    assets = temp / 'root/usr/lib/super-lara/src/assets'
    branding = json.loads((assets / 'branding.json').read_text())
    for name, digest in branding['original_image_sha256'].items():
        assert hashlib.sha256((assets / name).read_bytes()).hexdigest() == digest
    for size, name in [(128, 'burn.png'), (256, 'burn_256.png')]:
        icon = temp / f'root/usr/share/icons/hicolor/{size}x{size}/apps/super-lara.png'
        assert icon.read_bytes() == (assets / 'images' / name).read_bytes()
    assert (temp / 'root/usr/share/pixmaps/super-lara.png').read_bytes() == (assets / 'images/burn_256.png').read_bytes()
    for name in branding['icons']:
        assert (assets / 'icons' / (name + '.png')).exists()
        assert (assets / 'icons' / (name + '.svg')).exists()
    launcher = temp / 'root/usr/bin/super-lara'
    assert launcher.stat().st_mode & 0o111
    assert '/usr/lib/super-lara/src/app.py' in launcher.read_text()
    assert 'sudo' not in launcher.read_text()
    env = os.environ.copy()
    for key, suffix in [('XDG_CONFIG_HOME', 'config'), ('XDG_STATE_HOME', 'state'), ('XDG_RUNTIME_DIR', 'runtime')]:
        env[key] = str(temp / suffix)
    app = temp / 'root/usr/lib/super-lara/src/app.py'
    version = subprocess.check_output(['/usr/bin/python3', '-B', str(app), '--version'], env=env, text=True)
    assert version.startswith('Super Lara ')
    assert not (temp / 'config').exists(), '--version must be side-effect free'
    installations = subprocess.check_output(['/usr/bin/python3', '-B', str(app), '--installations'], env=env, text=True)
    assert isinstance(json.loads(installations), list)
    assert (temp / 'state/super-lara/super-lara.log').exists()
    assert (temp / 'runtime/super-lara/instance.lock').exists()
    assert not list((temp / 'root').rglob('__pycache__'))
    print('PASS: metadata, ownership, permissions, file checksums, no maintainer scripts, desktop launcher,')
    print('      Windows branding/icon hashes, extracted runtime, --version, Steam discovery, XDG state,')
    print('      no writes beside installed source.')
    print('Test tree retained:', temp)
    print('Not a host/VM installation or dependency-resolution test.')

if __name__ == '__main__':
    main()
