# Preparing a Linux beta release

This document describes local preparation and manual hosting. The scripts do not
push to GitHub, create releases or publish assets.

1. Choose the package maintainer’s name/email and replace the placeholder in
   packaging/release.json, or pass `--maintainer 'Name <email>'` to the builder.
   Do not assign maintenance to burn_sours without their agreement.
2. Update the version in both packaging/release.json and src/app.py. Keep the
   beta designation until the documented compatibility/test limits are addressed.
3. Review supported game hashes and upstream offsets. Do not accept an arbitrary
   new executable/DLL hash without checking compatibility and testing gameplay.
4. Run the tests, build the package, and verify its contents:

   ```sh
   cd linux
   xvfb-run -a python3 -m unittest discover -s tests -v
   python3 tools/build_deb.py --release --maintainer 'Name <email>'
   python3 tools/test_deb.py 'dist/super-lara_0.1.0~beta3_amd64.deb'
   ```

   `--release` only rejects placeholder metadata; it does not publish anything.
5. Test apt install, the application-menu launcher/icon, gameplay, upgrade and
   removal in a clean supported Ubuntu installation. Check the unsupported-build
   failure and that closing/unchecking stops writes. Record actual OS/Steam/Proton
   versions; do not claim untested distributions.
6. The upstream maintainer can manually attach these three matching files to a
   GitHub Release or host them on their website:

   - super-lara_0.1.0~beta3_amd64.deb
   - super-lara_0.1.0~beta3_source.tar.gz
   - super-lara_0.1.0~beta3_SHA256SUMS

   Use the actual version’s filenames after a version bump. Provide the complete
   corresponding GPL source alongside the binary and keep its licence/notices.
   Keep versioned download URLs so checksums continue to identify the right files.

## Source archive safety and rebuilding

UPSTREAM_FILES.json is the pinned upstream file list. The archive builder includes
those files explicitly, plus the Linux runtime, assets, tests, documentation and
build tools. It does not crawl arbitrary untracked checkout files or include local
settings, logs, game binaries, credentials, Frida environments or built packages.

To rebuild a downloaded source archive, extract it, enter its `linux/` directory,
and run the same builder. The sibling `upstream/` directory supplies the original
licence, source and branding. `SOURCE_DATE_EPOCH` can override the deterministic
source timestamp when a maintainer prepares a new version.

Artwork can optionally be reimported with tools/import_branding.py and ImageMagick.
The checked-in artwork is enough for normal builds; ImageMagick is not a runtime
dependency. The asset hash manifest records the original Windows image hashes.

## AppImage

See APPIMAGE.md for the complete prerequisites, pinned dependency downloads and
FUSE-free build/launch instructions. From the repository root:

```sh
python3 linux/tools/build_appimage.py --download
xvfb-run -a python3 linux/tools/test_appimage.py linux/dist/Super_Lara-0.1.0-beta3-x86_64.AppImage --gui
```

The first command creates intermediate Debian archives but does not install them.
Publish the AppImage, its matching native-source archive and SHA256SUMS together
only after agreeing release scope and maintainership. Runtime dependency notices
and source URLs are retained in the image; no auto-update URL is configured.
