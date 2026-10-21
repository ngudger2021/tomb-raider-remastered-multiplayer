# Verification and compatibility limits

The Linux port adapts four existing Burn’s Mods cheats from v2.5.5, revision
78ea92cccb5fad00256781b4332c097cd801cb0c. Only the exact Steam patch 5.4 executable
and three DLL hashes recorded in src/build.json are accepted. The executable hash
matches the upstream manifest; DLL hashes pin the locally tested Steam build
25209630 and are not upstream-published hashes.

## Gameplay evidence

On Ubuntu 26.04 with Snap Steam and Proton Experimental, the contributor confirmed
infinite oxygen, infinite health, no fall damage and super jump in TR I, II and III.
Backend telemetry independently recorded switching between their DLLs.

Underwater oxygen remained at 1899–1900 when enabled. After disabling, 24 samples
decreased from 1884 to 1188 with no further writes. A live wrong-expected-hash test
rejected the process as unsupported before opening a writable memory descriptor.

These observations were made with the earlier four-feature Linux beta. The
backend, UI, paths and supported-build manifest in 0.1.0~beta3 retain that code.
Controller changes handle a worker/UI queue race and restrict the CLI oxygen
signal toggle to explicit oxygen tests; inspection no longer registers that toggle.
The beta3 packaging/controller changes have not repeated every live gameplay check.

## Automated checks for 0.1.0~beta3

From the repository root:

```sh
xvfb-run -a python3 -m unittest discover -s linux/tests -v
python3 linux/tools/build_deb.py
python3 linux/tools/test_deb.py 'linux/dist/super-lara_0.1.0~beta3_amd64.deb'
python3 linux/tools/build_appimage.py --download
xvfb-run -a python3 linux/tools/test_appimage.py linux/dist/Super_Lara-0.1.0-beta3-x86_64.AppImage --gui
```

There are 20 tests: 11 backend guard tests, two path tests, three UI tests and four
CLI/controller tests. They cover exact intended write fields, disabled/loading/
dead-player states, selector/level changes, write bounds, feature separation,
XDG paths, branding, settings, disarming, read-only CLI behaviour and a UI queue
handoff race. Backend/UI unit tests use mocks and do not write game memory.

Package checks inspect permissions, checksums, absence of maintainer scripts,
original artwork, desktop metadata and extracted startup. AppImage checks use
isolated test state and verify the bundled interpreter/Tk, relocation with spaces,
licences/source/checksums, and actual window startup/shutdown on a virtual display.
The window starts with every feature off; the verifier rejects any mod-write log.

The matching Debian source archive is extracted/rebuilt separately, with package
byte comparison. AppImage outputs are checked for repeatable builds; these are
packaging checks, not clean-machine or new live gameplay tests.

## Installation history and remaining checks

The earlier .deb installed successfully through apt on the contributor's host,
resolved dependencies and connected to the game. Its installed files, desktop
metadata and icons were checked. An isolated fakeroot/dpkg install/remove cycle
and repeatable builds were also checked. Neither proves a clean-machine beta3
upgrade/remove cycle; that remains a release check.

Long play sessions, every level/transition, other distributions, non-Snap Steam,
clean-machine installation and full Windows feature parity remain unverified.
The AppImage has not independently repeated live gameplay. A public maintainer
identity is deliberately unset until agreed. Unknown game files have no bypass.
Memory checks and repeated identity reads reduce transition races; the game keeps
running, so this is not an atomic engine transaction or a guarantee against all races.

## Why the backend differs from the Windows launcher

Native Linux Frida failed during injection bootstrap with
`unable to perform ptrace pokedata: Input/output error`; the game exited during
that investigation. Windows Frida launched through Protontricks could not see the
running game in its Windows process list. The underlying cause remains unresolved.

This port instead validates mapped PE files and uses bounded Linux process-data
reads/writes. It injects no script and calls no Windows APIs. It does not change
security settings. If the OS denies access, the app reports failure; compatibility
with a different game/environment must be reviewed rather than forced.
