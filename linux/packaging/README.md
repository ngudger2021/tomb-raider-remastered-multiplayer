# Super Lara for Linux — beta

Native Ubuntu application providing infinite oxygen, infinite health, no fall
damage and super jump for Tomb Raider I–III Remastered on Steam/Proton.
Based on Burn's Mods v2.5.5 by burn_sours, GPL-3.0-only.

## Install and launch

On a 64-bit x86 Ubuntu desktop, download the `.deb` and run from its directory:

```sh
sudo apt install ./super-lara_0.1.0~beta2_amd64.deb
```

Open **Burn’s Mods — Super Lara** in your application menu, or run `super-lara`. Start your game
normally in Steam; Snap Steam and ordinary Steam library locations are detected.
Never run Super Lara with sudo. The installer does not change Steam, Proton,
ptrace, AppArmor, Snap permissions, game files or saves. No background service,
network listener or login autostart is installed. Apt may install Python/Tk if absent.

Every mod starts off. Check a box to enable it. Unchecking stops that feature's
writes; closing the app stops all writes. Loading screens, menus and dead/invalid
player state suspend writes. A connection error disarms every feature. Health
already restored and jump momentum are left for the game's simulation to handle.
Do not use another trainer simultaneously.

Settings: `~/.config/super-lara/settings.json`.
Logs: `~/.local/state/super-lara/super-lara.log`, or **View diagnostic log**.
Standard XDG overrides are supported. Previous prototype files in the source
folder are preserved and are not silently migrated. Application removal leaves
per-user settings/logs intact:

```sh
sudo apt remove super-lara
```

Upgrade by installing the newer `.deb` with the same apt command. Close the app
before upgrading, then relaunch it. Desktop files/icons are managed by the package.

## Supported build and limits

Only Steam build **25209630**, upstream patch **5.4**, is accepted. All four mapped
PE files must match `src/build.json`. The executable hash comes from upstream;
DLL hashes pin the verified local Steam installation and are not upstream-published
hashes. The game is x64, so the package is `amd64` despite its Python implementation.
A game update fails closed; it requires reviewed compatibility work.

Tested live on Ubuntu **26.04**, Snap Steam, Proton Experimental: the user confirmed
all four controls in TR1, TR2 and TR3. Oxygen enabling/disabling and game switching
were also recorded in backend telemetry. Other Ubuntu releases, ordinary Steam,
all levels, long play sessions and every transition are not yet gameplay-verified.
The installer candidate needs clean-machine installation testing before a stable
release. This is four local mods, not all Burn's features or multiplayer.

## Build from source

Requires Python 3.10+, `dpkg-deb`, and `desktop-file-validate` for package checks.
From this Linux source folder:

```sh
python3 -m unittest discover -s tests -v
python3 tools/build_deb.py --maintainer 'Your Name <your-email@example.com>'
python3 tools/test_deb.py 'dist/super-lara_0.1.0~beta2_amd64.deb'
```

Build outputs include the `.deb`, corresponding GPL source archive and SHA256SUMS.
No root is needed to build. `packaging/release.json` defines the version, default
maintainer and deterministic source timestamp. Update VERSION in src/app.py along
with that version. Placeholder maintainer identities are for local candidates only.

The upstream source is pinned in UPSTREAM.json. The native backend adapts data
behaviour/offsets from client/features and client/games/trr-123; it uses validated
Linux process memory access rather than injected Frida or Windows API calls.
It requires no Frida, Electron or Wine helper at runtime.

The binary package installs only under `/usr/bin`, `/usr/lib/super-lara` and
`/usr/share`. It has no maintainer scripts and no sudo/runtime privilege grants.
Read-only checks: `super-lara --version`, `super-lara --installations`,
`super-lara --inspect`. See `super-lara --help` and `man super-lara`.

## Original Windows artwork

The application logo, flame app icons, original ICO, and inline SVG icon geometry
are reused from the pinned upstream Windows launcher. The original PNG/ICO files
are byte-identical; PNG renditions of the SVG icons are included for native Tk.
The desktop icon uses the upstream 256 px and 128 px flame PNGs. The window keeps
the upstream dark/orange colours, logo and author links, with clear Linux-adaptation
attribution. Branding is not a claim that this is an official upstream release.

Reimporting artwork is optional development work: `python3 tools/import_branding.py`
requires ImageMagick. Building/running the app uses the checked-in assets and does
not require an image converter. Original asset hashes are in src/assets/branding.json.
