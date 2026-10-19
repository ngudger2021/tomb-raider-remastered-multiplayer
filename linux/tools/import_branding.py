#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Copy original Windows branding and render its existing inline SVG icons."""
from html.parser import HTMLParser
from pathlib import Path
import hashlib
import json
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = next((p for p in [ROOT / 'upstream', ROOT.parent / 'upstream', ROOT.parent]
                 if (p / 'client/ui/images').is_dir()), None)
if UPSTREAM is None:
    raise RuntimeError('Original upstream artwork directory not found')
ASSETS = ROOT / 'src/assets'

class Icons(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.context = None
        self.depth = 0
        self.parts = []
        self.icons = {}
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in ('a', 'button') and attrs.get('id'):
            self.context = attrs['id']
        if tag == 'svg' and self.context:
            self.depth = 1
            self.parts = [self.get_starttag_text()]
        elif self.depth:
            self.depth += 1
            self.parts.append(self.get_starttag_text())
    def handle_startendtag(self, tag, attrs):
        if self.depth:
            self.parts.append(self.get_starttag_text())
    def handle_endtag(self, tag):
        if self.depth:
            self.parts.append('</' + tag + '>')
            self.depth -= 1
            if self.depth == 0:
                self.icons[self.context] = ''.join(self.parts)
        if tag in ('a', 'button'):
            self.context = None
    def handle_data(self, value):
        if self.depth:
            self.parts.append(value)


def main():
    for name in ['images', 'icons']:
        (ASSETS / name).mkdir(parents=True, exist_ok=True)
    originals = {}
    for path in sorted((UPSTREAM / 'client/ui/images').iterdir()):
        if path.is_file():
            target = ASSETS / 'images' / path.name
            shutil.copyfile(path, target)
            originals['images/' + path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    parser = Icons()
    parser.feed((UPSTREAM / 'client/ui/launcher.html').read_text())
    for name, svg in parser.icons.items():
        source = ASSETS / 'icons' / (name + '.svg')
        source.write_text(svg + '\n')
        # Preserve the SVG geometry; resolve the CSS text colour for Tk's PNG display.
        rendered = svg.replace('currentColor', '#9ca3af')
        rendered = re.sub(r'width="\d+"', 'width="24"', rendered, count=1)
        rendered = re.sub(r'height="\d+"', 'height="24"', rendered, count=1)
        subprocess.run(['magick', '-background', 'none', 'msvg:-', '-depth', '8', str(source.with_suffix('.png'))],
                       input=rendered.encode(), check=True)
    (ASSETS / 'branding.json').write_text(json.dumps({
        'upstream_commit': '78ea92cccb5fad00256781b4332c097cd801cb0c',
        'source': 'client/ui/images and inline SVGs from client/ui/launcher.html',
        'original_image_sha256': originals,
        'icons': sorted(parser.icons),
        'licence': 'GPL-3.0-only; preserve burn_sours attribution; no claim of official endorsement'
    }, indent=2) + '\n')
    print('Copied', len(originals), 'original images; imported', len(parser.icons), 'existing SVG icons.')

if __name__ == '__main__':
    main()
