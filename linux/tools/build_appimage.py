#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Build a portable x86_64 AppImage with checksum-pinned Python and Tk.

Only --download allows dependency downloads. All work stays under linux/work;
no packages are installed and the existing system installation is untouched.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    with path.open('rb') as stream:
        value = hashlib.sha256()
        for block in iter(lambda: stream.read(1024*1024), b''):
            value.update(block)
    return value.hexdigest()


def dependency(spec, cache, download=False):
    name = Path(unquote(urlsplit(spec['url']).path)).name
    target = cache / name
    if target.exists():
        if digest(target) != spec['sha256']:
            raise RuntimeError('Cached dependency checksum mismatch: ' + name)
        return target
    if not download:
        raise RuntimeError('Missing pinned dependency: ' + name + '; rerun with --download')
    partial = target.with_name(name + '.part')
    request = urllib.request.Request(spec['url'], headers={'User-Agent':'Super-Lara-local-builder'})
    print('Downloading pinned dependency:', name, flush=True)
    with urllib.request.urlopen(request, timeout=120) as response, partial.open('wb') as output:
        shutil.copyfileobj(response, output)
    if digest(partial) != spec['sha256']:
        raise RuntimeError('Downloaded dependency checksum mismatch: ' + name)
    partial.replace(target)
    return target


def unpack_python(archive, destination):
    # The tar is trusted only after checksum validation; still reject unsafe paths/links.
    with tarfile.open(archive) as tar:
        for member in tar.getmembers():
            path = Path(member.name)
            if path.is_absolute() or '..' in path.parts or not path.parts or path.parts[0] != 'python':
                raise RuntimeError('Unsafe Python archive path: ' + member.name)
            if not (member.isdir() or member.isfile() or member.issym() or member.islnk()):
                raise RuntimeError('Unexpected Python archive entry: ' + member.name)
        # Data filtering permits legitimate internal ../ links but rejects escapes.
        if sys.version_info < (3,12):
            raise RuntimeError('AppImage builder requires Python 3.12+ for safe tar extraction')
        tar.extractall(destination, filter='data')


def python_notices(archive, destination):
    destination.mkdir(parents=True,exist_ok=True)
    process = subprocess.Popen(['zstd','-dc',str(archive)],stdout=subprocess.PIPE)
    count = 0
    try:
        with tarfile.open(fileobj=process.stdout,mode='r|') as tar:
            for member in tar:
                if not member.isfile() or not (member.name.startswith('python/licenses/') or member.name=='python/PYTHON.json'):
                    continue
                relative = Path(member.name).relative_to('python')
                if '..' in relative.parts or member.size > 4*1024*1024:
                    raise RuntimeError('Unsafe Python notice entry')
                target = destination/relative
                target.parent.mkdir(parents=True,exist_ok=True)
                target.write_bytes(tar.extractfile(member).read())
                count += 1
        if process.wait() or count < 2:
            raise RuntimeError('Python metadata/licences could not be extracted')
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--download', action='store_true')
    parser.add_argument('--output', type=Path, default=ROOT/'dist')
    parser.add_argument('--prepare-only', action='store_true', help='Prepare AppDir without invoking appimagetool')
    args = parser.parse_args()
    if os.uname().machine != 'x86_64':
        parser.error('This pinned build supports x86_64 only')
    deps = json.loads((ROOT/'packaging/appimage-deps.json').read_text())
    release = json.loads((ROOT/'packaging/release.json').read_text())
    version = release['version']
    work = ROOT/'work/appimage'
    cache = work/'downloads'
    cache.mkdir(parents=True, exist_ok=True)
    paths = {key:dependency(deps[key],cache,args.download) for key in ('python','python_metadata','appimagetool','runtime','runtime_license')}
    paths['appimagetool'].chmod(0o755)
    stage = Path(tempfile.mkdtemp(prefix='build-',dir=work))
    inputs = stage/'inputs'
    # Reuse the reviewed .deb payload, licences and icons without installing it.
    subprocess.run([sys.executable,str(ROOT/'tools/build_deb.py'),'--output',str(inputs)],check=True)
    appdir = stage/'SuperLara.AppDir'
    subprocess.run(['dpkg-deb','--extract',str(inputs/f'super-lara_{version}_amd64.deb'),str(appdir)],check=True)
    home = appdir/'usr/lib/super-lara'
    unpack_python(paths['python'],home)
    # Super Lara does not use Berkeley DB. Omit that optional extension rather
    # than distribute its statically linked database implementation unnecessarily.
    for extension in (home/'python/lib').glob('python*/lib-dynload/_dbm*.so'):
        extension.unlink()
    tcl = list((home/'python/lib').glob('tcl*/init.tcl'))
    tk = list((home/'python/lib').glob('tk*/tk.tcl'))
    if len(tcl)!=1 or len(tk)!=1:
        raise RuntimeError('Expected one bundled Tcl and Tk library')
    tcl_relative = tcl[0].parent.relative_to(appdir).as_posix()
    tk_relative = tk[0].parent.relative_to(appdir).as_posix()
    (home/'bootstrap.py').write_text('''# SPDX-License-Identifier: GPL-3.0-only
import runpy
import sys
from pathlib import Path
source = Path(__file__).resolve().parent / "src"
sys.path.insert(0, str(source))
runpy.run_path(str(source / "app.py"), run_name="__main__")
''')
    # Isolated Python ignores user PYTHONPATH/PYTHONHOME/site packages; never writes .pyc.
    (appdir/'usr/bin/super-lara').write_text('''#!/bin/sh
set -eu
APP_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
export TCL_LIBRARY="$APP_ROOT/@TCL@"
export TK_LIBRARY="$APP_ROOT/@TK@"
exec "$APP_ROOT/usr/lib/super-lara/python/bin/python3" -I -B "$APP_ROOT/usr/lib/super-lara/bootstrap.py" "$@"
'''.replace('@TCL@',tcl_relative).replace('@TK@',tk_relative))
    (appdir/'usr/bin/super-lara').chmod(0o755)
    (appdir/'AppRun').write_text('''#!/bin/sh
set -eu
APP_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec "$APP_ROOT/usr/bin/super-lara" "$@"
''')
    (appdir/'AppRun').chmod(0o755)
    shutil.copy2(appdir/'usr/share/applications/super-lara.desktop',appdir/'super-lara.desktop')
    shutil.copy2(appdir/'usr/share/icons/hicolor/256x256/apps/super-lara.png',appdir/'super-lara.png')
    (appdir/'.DirIcon').symlink_to('super-lara.png')
    docs = appdir/'usr/share/doc/super-lara'
    python_notices(paths['python_metadata'],docs/'python-build-standalone')
    shutil.copy2(paths['runtime_license'],docs/'type2-runtime-LICENSE')
    shutil.copy2(ROOT/'packaging/appimage-deps.json',docs/'appimage-deps.json')
    if (ROOT/'APPIMAGE.md').exists():
        shutil.copy2(ROOT/'APPIMAGE.md',docs/'APPIMAGE.md')
    (docs/'APPIMAGE-THIRD-PARTY.txt').write_text(
        'Python, Tcl/Tk and dependency licences are retained under python-build-standalone/licenses and usr/lib/super-lara/python.\n'
        'The AppImage runtime is from the official pinned type2-runtime release.\n'
        'The optional Berkeley DB (_dbm) extension is omitted; Super Lara does not use it.\n'
        'See appimage-deps.json for exact releases, source URLs and SHA256 checksums.\n')
    print('Prepared AppDir:',appdir,flush=True)
    (work/'last-build.json').write_text(json.dumps({'stage':str(stage),'appdir':str(appdir),'dependencies':{k:str(v) for k,v in paths.items()}},indent=2)+'\n')
    if args.prepare_only:
        return
    output = args.output.resolve()
    output.mkdir(parents=True,exist_ok=True)
    name = 'Super_Lara-'+version.replace('~','-')+'-x86_64.AppImage'
    target = output/name
    env = os.environ.copy()
    env.update(ARCH='x86_64',VERSION=version,SOURCE_DATE_EPOCH=str(release['source_date_epoch']),TMPDIR=str(stage))
    subprocess.run([str(paths['appimagetool']),'--appimage-extract-and-run',
                    '--runtime-file',str(paths['runtime']),
                    '--mksquashfs-opt=-processors','--mksquashfs-opt=2',
                    str(appdir),str(target)],env=env,check=True)
    target.chmod(0o755)
    source = output/(name+'.source.tar.gz')
    shutil.copy2(inputs/f'super-lara_{version}_source.tar.gz',source)
    (output/(name+'.SHA256SUMS')).write_text(''.join(digest(p)+'  '+p.name+'\n' for p in (target,source)))
    print('AppImage:',target)
    print('Corresponding native source:',source)
    print('AppDir retained:',appdir)


if __name__=='__main__':
    main()
