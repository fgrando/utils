# utils
Utility tools and scripts

## Scripts
- [datestamp.pyw](datestamp.pyw) — drag & drop files to prepend a live, editable date/time stamp to their filenames.
- [lowres.pyw](lowres.pyw) — drag & drop images to shrink them (aspect ratio preserved) and save alongside the original with a `_lowres` suffix. Choose how: max size in pixels (default 1024x768), a reduction factor (2x, 5x, etc.), or a max file size in KB (default 100 KB, finds the highest resolution that fits).

# Release
## Dependencies
### PyInstaller

    pip install pyinstaller -r requirements.txt
    python -m pyinstaller --onefile --windowed --name datestamp datestamp.pyw

## Automated build (GitHub Actions)
Pushing a tag matching `v*` triggers [.github/workflows/release.yml](.github/workflows/release.yml), which builds an `.exe` for every `.pyw` script in the repo on a Windows runner and attaches them all to a GitHub Release:

    git tag v1.0.0
    git push origin v1.0.0

The workflow can also be run manually from the Actions tab (`workflow_dispatch`), which builds the executables and uploads them as a single workflow artifact without creating a release.
