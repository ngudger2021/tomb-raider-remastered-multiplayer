# Verification and compatibility limits

The Linux port is derived from Burn’s Mods v2.5.5, revision
78ea92cccb5fad00256781b4332c097cd801cb0c, and preserves GPL-3.0-only attribution.
It accepts only the Steam patch 5.4 executable and the three exact DLL hashes
recorded in src/build.json. The executable hash matches the upstream manifest;
the DLL hashes pin the locally verified Steam build 25209630.

## Completed before this contribution

On Ubuntu 26.04 with Snap Steam and Proton Experimental:

- The user confirmed oxygen, health, no fall damage and super jump in TR1, TR2
  and TR3. Backend telemetry independently showed switching between their DLLs.
- Underwater oxygen remained at 1899–1900 while enabled. After disabling it,
  24 underwater samples decreased from 1884 to 1188 with an unchanged write count.
- A live wrong-expected-hash test rejected the process as unsupported before
  opening any write descriptor.
- The branded beta .deb installed successfully through apt with dependency
  resolution. Its installed application opened and connected to the running TR3
  game. Installed file checksums, original branding hashes, menu-file validation
  and window identity were checked. A manual launch through the desktop app grid
  remains a useful user check.
- An isolated fakeroot/dpkg installation and removal cycle passed. The real app
  was not uninstalled. Two package builds were byte-identical.

## Checks from this checkout

```sh
cd linux
xvfb-run -a python3 -m unittest discover -s tests -v
python3 tools/build_deb.py
python3 tools/test_deb.py 'dist/super-lara_0.1.0~beta2_amd64.deb'
```

All 16 tests and the package verifier passed from the fork checkout. The generated
source archive was extracted and rebuilt successfully, and that rebuilt package
also passed verification. The original-source archive entries matched the pinned
UPSTREAM_FILES.json list exactly.

The tests cover backend write guards and feature separation, XDG paths, native
window branding, controls, persistence, disable-all behaviour and error display.
The package verifier checks ownership, permissions, file checksums, absence of
maintainer scripts, desktop/window identity, original artwork hashes and extracted
runtime startup. UI tests use a fake controller and never access the game.

## Remaining limits

This is an experimental four-feature native backend, not Linux parity with the
Windows launcher, multiplayer or other TR releases. There is no manual build
bypass. Game updates require compatibility review. Long-duration play, every
level/transition, other distributions, clean-machine installation and non-Snap
Steam gameplay are not yet verified. There is a public maintainer-identity
placeholder in packaging/release.json until a maintainer is chosen.

Native Linux Frida injection was tested and failed during bootstrap with
`unable to perform ptrace pokedata: Input/output error`, before a script could
be injected. The game exited during that investigation. The existing Windows
Frida runtime, launched through Protontricks with the correct prefix, could not
see the running game in its Windows process list. The underlying isolation cause
remains unresolved. This backend avoids that path: it validates mapped PE data
and uses bounded Linux process-memory reads/writes, with no injected script,
remote Windows API calls or ABI assumptions. It does not change security settings.
