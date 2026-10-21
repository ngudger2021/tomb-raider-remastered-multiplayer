# Super Lara AppImage

This version contains only infinite oxygen, infinite health, no fall damage and
fixed-strength super jump. It is a subset of Burn's original features, with the
original logo, icons, licence and attribution. See README.md for feature details.

The AppImage bundles Python 3.12 and Tcl/Tk and requires no installation or sudo.
It leaves the installed experimental .deb unchanged. Close any other Super Lara
window first, then run from the directory containing it:

```sh
chmod +x Super_Lara-0.1.0-beta3-x86_64.AppImage
./Super_Lara-0.1.0-beta3-x86_64.AppImage
```

If normal launch reports a FUSE/mount error, use its built-in extraction mode:

```sh
./Super_Lara-0.1.0-beta3-x86_64.AppImage --appimage-extract-and-run
```

A local build is already executable. Downloads/copies can lose that permission.
It is x86_64/glibc Linux and still needs the usual desktop system libraries and
X11/XWayland. It shares XDG settings/logs and the single-instance lock with the
installed app. All mods start off; saved preferences do not enable them. No menu
entry, background service, updater or login autostart is installed by this file.

## Build

From this candidate checkout, with Python 3.12+, dpkg-deb,
desktop-file-validate and zstd available:

```sh
python3 linux/tools/build_appimage.py --download
python3 linux/tools/test_appimage.py linux/dist/Super_Lara-0.1.0-beta3-x86_64.AppImage
```

Only --download permits network downloads. Official versioned dependencies are
pinned by SHA256 in packaging/appimage-deps.json. Later offline builds can omit
--download. Work/cache stays under linux/work; outputs are in linux/dist. The
builder creates an intermediate .deb payload without installing it. It uses a
pinned AppImage runtime rather than fetching an unpinned current runtime.

Python/Tk notices and metadata, the runtime licence, original GPL source and
attribution are included. The unused optional Berkeley DB extension is omitted.
The matching native-source archive includes packaging scripts and dependency pins.

For the virtual-display window test, run:

```sh
xvfb-run -a python3 linux/tools/test_appimage.py linux/dist/Super_Lara-0.1.0-beta3-x86_64.AppImage --gui
```

Package/UI checks are separate from gameplay. These four backend/UI implementations
were previously confirmed in TR I–III in the first Linux beta. The AppImage itself
has not repeated live gameplay on every distribution. Nothing is published by
these commands.
