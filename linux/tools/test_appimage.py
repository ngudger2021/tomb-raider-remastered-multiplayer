#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Verify an AppImage without installing it or enabling game mods.

Use xvfb-run -a python3 tools/test_appimage.py FILE --gui for an actual window
startup/shutdown test. All test state stays under linux/work.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tarfile
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    value=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):value.update(block)
    return value.hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image',type=Path)
    parser.add_argument('--gui',action='store_true')
    args=parser.parse_args()
    image=args.image.resolve()
    assert image.stat().st_mode & 0o111
    with image.open('rb') as stream:
        header=stream.read(11)
    assert header[:4]==b'\x7fELF' and header[8:11]==b'AI\x02'
    sums=image.with_name(image.name+'.SHA256SUMS')
    for line in sums.read_text().splitlines():
        expected,name=line.split('  ',1)
        assert sha(image.parent/name)==expected,name
    source=image.with_name(image.name+'.source.tar.gz')
    with tarfile.open(source) as tar:
        names=tar.getnames()
        for suffix in ['/linux/tools/build_appimage.py','/linux/packaging/appimage-deps.json','/linux/APPIMAGE.md','/upstream/LICENSE']:
            assert any(name.endswith(suffix) for name in names),suffix
    work=ROOT/'work';work.mkdir(exist_ok=True)
    temp=Path(tempfile.mkdtemp(prefix='appimage-test-',dir=work))
    env=os.environ.copy()
    env.update(XDG_CONFIG_HOME=str(temp/'config'),XDG_STATE_HOME=str(temp/'state'),
               XDG_RUNTIME_DIR=str(temp/'runtime'),TMPDIR=str(temp),PYTHONHOME='/invalid-python-home',PYTHONPATH='/invalid-python-path')
    version=subprocess.check_output([str(image),'--appimage-extract-and-run','--version'],env=env,text=True,timeout=45)
    assert version.startswith('Super Lara '),version
    assert not (temp/'config').exists(),'--version must not create state'
    subprocess.run([str(image),'--appimage-extract'],cwd=temp,stdout=subprocess.DEVNULL,check=True,timeout=45)
    appdir=temp/'AppDir with spaces'
    (temp/'squashfs-root').rename(appdir)
    output=subprocess.check_output([str(appdir/'AppRun'),'--version'],env=env,text=True,timeout=15)
    assert output==version
    data=subprocess.check_output([str(appdir/'AppRun'),'--installations'],env=env,text=True,timeout=15)
    assert isinstance(json.loads(data),list)
    assert (temp/'state/super-lara/super-lara.log').is_file()
    runtime=appdir/'usr/lib/super-lara/python'
    actual=json.loads(subprocess.check_output([str(runtime/'bin/python3'),'-I','-c',
        'import sys,tkinter,_tkinter,json;print(json.dumps([sys.version,sys.executable,_tkinter.__file__]))'],env=env,text=True))
    assert actual[0].startswith('3.12.')
    assert str(runtime) in actual[1] and str(runtime) in actual[2],actual
    subprocess.run(['desktop-file-validate',str(appdir/'super-lara.desktop')],check=True)
    assert (appdir/'super-lara.png').read_bytes()==(ROOT/'src/assets/images/burn_256.png').read_bytes()
    assert (appdir/'usr/lib/super-lara/src/build.json').read_bytes()==(ROOT/'src/build.json').read_bytes()
    docs=appdir/'usr/share/doc/super-lara'
    assert (docs/'LICENSE').is_file() and (docs/'NOTICE').is_file()
    assert (docs/'type2-runtime-LICENSE').is_file()
    assert (docs/'python-build-standalone/PYTHON.json').is_file()
    assert len(list((docs/'python-build-standalone/licenses').iterdir()))>=2
    assert not list((appdir/'usr/lib/super-lara/src').rglob('__pycache__'))
    if args.gui:
        if not env.get('DISPLAY'):raise RuntimeError('--gui needs DISPLAY, e.g. xvfb-run -a')
        log=temp/'gui.log'
        with log.open('w') as stream:
            process=subprocess.Popen([str(image),'--appimage-extract-and-run'],env=env,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
            try:
                time.sleep(4)
                if process.poll() is not None:raise RuntimeError('GUI exited early: '+log.read_text())
                # Signal the process group: extraction wrapper and Python share it.
                os.killpg(process.pid,signal.SIGTERM)
                process.wait(timeout=12)
            finally:
                if process.poll() is None:
                    os.killpg(process.pid,signal.SIGTERM)
                    process.wait(timeout=12)
        assert '[memory write]' not in log.read_text(),log.read_text()
        assert 'Traceback' not in log.read_text(),log.read_text()
        print('PASS: actual AppImage window remained running and shut down; no mod writes enabled')
    print('PASS: AppImage checksums, GPL source, extraction-mode startup, bundled Python/Tk,')
    print('      relocation with spaces, isolated Python/XDG state, icons, desktop entry and licences')
    print('Version:',version.strip())
    print('Test files retained:',temp)
    print('Live gameplay and other distributions are not verified by this test.')


if __name__=='__main__':main()
