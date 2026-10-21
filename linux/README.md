# Burn’s Mods — Super Lara for Linux

A native Linux application for **Tomb Raider I–III Remastered on Steam/Proton**.
It provides infinite oxygen, infinite health, no fall damage and super jump, with
a Debian `.deb` installer and an application-menu launcher.

This is an independent **beta** adaptation of [Burn’s Mods](https://github.com/burn-sours/tomb-raider-remastered-multiplayer)
by **burn_sours**, distributed under **GPL-3.0-only**. It reuses the Windows
version’s original logo, flame icons and link artwork. The existing Windows
launcher and server are separate and keep their existing build process.

## Contribution scope

This beta implements four existing cheats: infinite oxygen, infinite health,
no fall damage and fixed-strength super jump. It is a subset of the Windows
launcher’s features. No additional gameplay cheats or multiplayer are included.
A portable AppImage is also provided; see [APPIMAGE.md](APPIMAGE.md).

## Compatibility

| Item | Current support |
| --- | --- |
| Game | Tomb Raider I–III Remastered, Steam app `2478970` |
| Verified game release | Steam build `25209630`, upstream patch `5.4` |
| Package architecture | `amd64` — 64-bit x86 Linux |
| Runtime | Python 3.10 or later and Tk |
| Gameplay tested on | Ubuntu 26.04, Snap Steam, Proton Experimental |
| Features | Four local Super Lara mods; no multiplayer |

All four controls were confirmed in TR1, TR2 and TR3 during live testing. Other
Ubuntu/Debian releases, non-Snap Steam gameplay, every level and long play sessions
are not yet verified. See [VERIFICATION.md](VERIFICATION.md) for the evidence and
remaining limits.

The known Steam build identifies the tested release. **Compatibility is enforced
by exact executable and DLL hashes**, rather than trusting the Steam build number
alone. A game update that changes those files will be rejected until its memory
layout has been reviewed and tested.

## Install the Debian package

Download the `.deb`, then open a terminal in the download directory:

```sh
sudo apt install ./super-lara_0.1.0~beta3_amd64.deb
```

Apt installs Python/Tk dependencies if needed. The package registers the original
flame icon and **Burn’s Mods — Super Lara** in your application menu. You can also
launch it from a terminal:

```sh
super-lara
```

The installer places the command in `/usr/bin`, application files in
`/usr/lib/super-lara`, and the launcher, icons and documentation under `/usr/share`.
There is no background service or login autostart.

**Use sudo for installation only. Run the application as your normal desktop user.**

## Using the mods

1. Start the game normally through Steam and load a playable level.
2. Open **Burn’s Mods — Super Lara**. The app finds the game automatically.
3. Wait for **Connected — mods off**, then select the features you want.
4. Uncheck a feature to stop its writes, or use **Disable all mods**.
5. Close the app to stop all writes and disconnect.

Every new app session starts with all features off. Saved preferences are shown
for reference and must be enabled again. Selecting a feature requests it; writes
start only when a compatible game and valid live player are available. The app
can also be opened before the game and wait for it to start.

| Feature | How it works |
| --- | --- |
| Infinite oxygen | Repeatedly refills Lara’s oxygen field to the upstream value of `1900`. |
| Infinite health | Repeatedly refills health to `2000` while Lara is alive; it does not resurrect her. |
| No fall damage | Limits downward speed to `130` on dry ground, following upstream behaviour. |
| Super jump | Boosts upward speed toward `-175`, following upstream behaviour. |

Disabling a feature **stops future writes**. It does not rewind the game: health
already added and existing jump momentum remain for the game to handle. Oxygen
starts depleting naturally again underwater. Fall protection does not prevent
scripted deaths or other hazards. Avoid running another trainer at the same time.

## How the Linux backend works

The interface is a native **Python/Tk** window. A worker thread handles the game
connection and feature updates, while the interface remains responsive.

The connection follows these steps:

1. **Find the game.** Scan Linux `/proc` for a `tomb123.exe` process owned by the
   current user. Multiple matching game processes produce a clear error.
2. **Find its modules.** Read the process memory map to locate `tomb123.exe`,
   `1/tomb1.dll`, `2/tomb2.dll` and `3/tomb3.dll`. Resolve their backing files
   through the target process’s root, which accounts for container path mappings.
3. **Validate the build.** Compare the four files’ SHA-256 hashes with
   [src/build.json](src/build.json). Check their mapped-file identities and loaded
   x64 PE headers. Open the process memory read-only initially.
4. **Read the current game state.** Use upstream-derived offsets to identify TR1,
   TR2 or TR3, its level, Lara’s current entity pointer, oxygen, health and room
   state. The module selection changes automatically when switching games.
5. **Apply selected features.** Open write access only when a selected feature
   needs a write. Update the specific signed 16-bit data fields using bounded
   `pread`/`pwrite` access to `/proc/<pid>/mem`. Recheck game, level and Lara pointer
   before applying updates. Menus, exiting/dead/invalid player states suspend writes.
6. **Monitor and disconnect.** Refresh memory mappings and periodically revalidate
   the modules. Connection errors stop writes, disarm all features and show the
   failing stage. The app retries the connection, but features require explicit
   re-enabling after an error. Closing the app releases its memory descriptors.

The executable hash comes from the upstream patch manifest. The three DLL hashes
were recorded from the locally verified Steam installation; they are additional
build pinning, not hashes published by upstream. Offsets and feature behaviour
are adapted from `client/games/trr-123/` and `client/features/`. Their source
revision is recorded in [UPSTREAM.json](UPSTREAM.json).

The app changes **live process data**. It does not patch game executables, DLLs,
saves or Steam settings. It makes no remote Windows API calls and injects no
script. It does not require Frida, Electron or a Proton-side helper at runtime.
The installer does not change ptrace, AppArmor, Snap permissions or other system
security settings. If the operating system denies process-memory access, the app
reports that failure instead of escalating privileges.

### Why this differs from the Windows launcher

In the tested setup, the Windows launcher’s Frida runtime under Protontricks could
not discover the running game. Native Linux Frida attachment was also investigated
and failed during injection bootstrap. The underlying cause is unresolved; Snap
or Wine isolation has not been established as the cause.

The data-only backend above passed the live oxygen test and avoids depending on
that injection path. It also avoids assuming that Windows module discovery, APIs
or calling conventions work unchanged inside a Linux Frida agent.

## Connection states and troubleshooting

| State | Meaning and next step |
| --- | --- |
| Game not running | Start app `2478970` through Steam. The app keeps checking. |
| Connecting | The process has been found and its modules are being validated. |
| Connected — mods off | The player is ready; select the features you want. |
| Connected — waiting for a playable level | A valid live player is not available; load a level or finish the transition. |
| Mods active | Selected features are enabled for a valid player; individual writes depend on each feature’s conditions. |
| Unsupported build | The expected build or state could not be validated. Do not force another patch or edit hashes to bypass the check. |
| Connection failure | Read the reported stage and diagnostic log. After reconnecting, enable the desired features again. |

Common checks:

- **No game detected:** use Steam to start the game and run the app as the same
  desktop user. Close extra game sessions.
- **Permission denied:** check the diagnostic log and your environment. Do not run
  the app as root or disable security settings as a workaround.
- **Unsupported build after an update:** the new game files need compatibility
  review and an updated release; accepting a new hash alone does not prove the
  existing offsets are correct.
- **App already running:** close the other installed/source instance. They share
  a per-user lock, so both cannot control the game at once.

Use **Diagnostic log** in the window to view recent messages. Repeated identical
messages are rate limited. Logs rotate at approximately 2 MB with three backups.

You can check the version at any time. Close the GUI before using
`--installations` or `--inspect`, because those commands share its instance lock:

```sh
super-lara --version
super-lara --installations
super-lara --inspect --seconds 10
```

`--installations` reports detected Steam libraries, the game’s Proton prefix and
its recorded Proton configuration. It checks Snap Steam, conventional Steam
locations, extra libraries in `libraryfolders.vdf`, and an optional `STEAM_DIR`.
`--inspect` reads live player state without enabling mods. See `super-lara --help`
or `man super-lara` for additional options.

## Settings and logs

| Data | Default location |
| --- | --- |
| Saved preferences | `~/.config/super-lara/settings.json` |
| Diagnostic log | `~/.local/state/super-lara/super-lara.log` |
| Instance lock | `$XDG_RUNTIME_DIR/super-lara/instance.lock`, or the state directory if no runtime directory is set |

`XDG_CONFIG_HOME` and `XDG_STATE_HOME` override the default config/state locations.
Settings and logs belong to the desktop user, not the installed application
folder. Files from the earlier project-local prototype are preserved and are not
silently migrated.

## Upgrade or uninstall

Close the app, install the newer `.deb` with `sudo apt install ./<new-package>.deb`,
then launch it again. The package manager handles the desktop entry and icons.

To remove the application:

```sh
sudo apt remove super-lara
```

Per-user settings and logs remain. Game files and saves are not package-owned.

## Run and build from this repository

From the repository root:

```sh
cd linux
./run.sh
```

For a source run, install Python 3.10+ and Tk. To build and check the installer on
Ubuntu/Debian, the development tools are:

```sh
sudo apt install python3 python3-tk dpkg-dev desktop-file-utils xvfb xauth
```

Then, from `linux/`:

```sh
xvfb-run -a python3 -m unittest discover -s tests -v
python3 tools/build_deb.py --maintainer 'Your Name <your-email@example.com>'
python3 tools/test_deb.py 'dist/super-lara_0.1.0~beta3_amd64.deb'
```

The Xvfb tests use a fake controller and never attach to the game. Package checks
extract the installer into an isolated directory rather than installing it on
the host. Running the builder and tests does not require root.

Build outputs in `linux/dist/` are:

- `super-lara_0.1.0~beta3_amd64.deb`
- `super-lara_0.1.0~beta3_source.tar.gz` — corresponding GPL source
- `super-lara_0.1.0~beta3_SHA256SUMS`

Build output, test working directories and Python caches are ignored by Git.
The source archive uses an explicit upstream file list; it excludes unrelated
local files, personal state and built installers.

For public releases, replace the placeholder maintainer identity and follow
[RELEASE.md](RELEASE.md). The builder’s `--release` flag rejects the current
placeholder; it does not upload or publish anything. Update both
`packaging/release.json` and `src/app.py` when changing the app version.

## Source layout

| Path | Purpose |
| --- | --- |
| `src/backend.py` | Process/module discovery, version checks and guarded feature writes |
| `src/app.py` | Connection worker, CLI, diagnostics and instance lock |
| `src/ui.py` | Native window and feature controls |
| `src/paths.py` | Per-user XDG paths |
| `src/build.json` | Supported hashes and upstream-derived memory offsets |
| `src/assets/` | Original artwork, SVG icons and native PNG renditions |
| `packaging/` | Package metadata, launcher, desktop entry and manual page |
| `tools/build_deb.py` | Build the installer, corresponding source and checksums |
| `tools/test_deb.py` | Verify package contents and extracted runtime |
| `tests/` | Backend, path and native-window tests |

## Licence, artwork and attribution

The original project is **Burn’s Mods & Multiplayer by burn_sours**. The pinned
revision is `78ea92cccb5fad00256781b4332c097cd801cb0c` (v2.5.5).
The original PNG/ICO files are preserved byte-for-byte, and inline SVG geometry
is retained with PNG renditions for Tk. Image hashes are recorded in
`src/assets/branding.json`.

Reimporting artwork with `python3 tools/import_branding.py` is optional development
work and requires ImageMagick. Normal builds and runtime use the included assets.

The Linux adaptation is distributed under **GPL-3.0-only**; see [NOTICE](NOTICE)
and the [repository licence](../LICENSE). Release source archives include that
licence under `upstream/LICENSE`. Reusing the branding does not imply an official
upstream release or endorsement.
