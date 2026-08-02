# utils
Utility tools and scripts

## Scripts
- [datestamp.pyw](datestamp.pyw) — drag & drop files to prepend a live, editable date/time stamp to their filenames.
- [lowres.pyw](lowres.pyw) — drag & drop images to shrink them (aspect ratio preserved) and save alongside the original with a `_lowres` suffix. Choose how: max size in pixels (default 1024x768), a reduction factor (2x, 5x, etc.), or a max file size in KB (default 100 KB, finds the highest resolution that fits).
- [pdfmerger.pyw](pdfmerger.pyw) — drag & drop (or add) PDFs, reorder them, and combine into a single output PDF.

# Release
## Dependencies
### PyInstaller

    pip install pyinstaller -r requirements.txt
    python -m pyinstaller --onefile --windowed --name datestamp datestamp.pyw

## Build locally
Run [build.bat](build.bat) to build every `.pyw` script in the repo into a standalone `.exe`. It installs/updates dependencies from `requirements.txt`, builds each script with PyInstaller, and moves the resulting executables into the repo root.

## Automated build (GitHub Actions)
[.github/workflows/release.yml](.github/workflows/release.yml) builds an `.exe` for every `.pyw` script in the repo on a Windows runner:

- **Every push to `main`** — builds and uploads the executables as a workflow artifact, so every build is validated and downloadable.
- **Pushing a tag matching `v*`** — builds and additionally attaches the executables to a GitHub Release:

      git tag v1.0.0
      git push origin v1.0.0

- **Manual run** from the Actions tab (`workflow_dispatch`) — builds and uploads the artifact without creating a release.
