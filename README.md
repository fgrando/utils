# utils
Utility tools and scripts

## Scripts
- [datestamp.pyw](datestamp.pyw) — drag & drop files to prepend a live, editable date/time stamp to their filenames.
- [lowres.pyw](lowres.pyw) — drag & drop images to shrink them (aspect ratio preserved) and save alongside the original with a `_lowres` suffix. Choose how: max size in pixels (default 1024x768), a reduction factor (2x, 5x, etc.), or a max file size in KB (default 100 KB, finds the highest resolution that fits).
- [pdfmerger.pyw](pdfmerger.pyw) — drag & drop (or add) PDFs, reorder them, and combine into a single output PDF.

## Serial-to-UDP bridge
A pair of tools for forwarding a Windows COM port's byte stream over UDP and viewing it on the receiving end.

- [serialUdpTx.c](serialUdpTx.c) — reads a Windows COM port and forwards every byte to a UDP endpoint. Exits cleanly on Ctrl+C or once a kill-file appears on disk.

      serialUdpTx.exe <COMx> <baud[,parity[,data[,stop]]]> <dst_ip> <dst_port> <logfile> <killfile>
      serialUdpTx.exe COM3 115200,N,8,1 127.0.0.1 5000 C:\logs\bridge.log C:\tmp\stop.flag

- [serialUdpRx.py](serialUdpRx.py) — listens for the UDP datagrams from `serialUdpTx.exe` and reassembles/prints the serial stream line by line (datagram boundaries don't line up with line boundaries, so it buffers per sender until it sees a newline).

      python serialUdpRx.py                       # listen 0.0.0.0:5000
      python serialUdpRx.py --port 5000 --hex
      python serialUdpRx.py --host 127.0.0.1 --port 5000 --logfile rx.log

# Release
## Dependencies
### PyInstaller

    pip install pyinstaller -r requirements.txt
    python -m pyinstaller --onefile --windowed --name datestamp datestamp.pyw

## Build locally
Run [build.bat](build.bat) to build every `.pyw` script in the repo into a standalone `.exe`. It installs/updates dependencies from `requirements.txt`, builds each script with PyInstaller, and moves the resulting executables into the repo root.

Run `make` (requires a MinGW-w64 `gcc` on `PATH`) to build every `.c` file in the repo into a matching `.exe`, e.g. `serialUdpTx.c` → `serialUdpTx.exe`. See [Makefile](Makefile).

## Automated build (GitHub Actions)
[.github/workflows/release.yml](.github/workflows/release.yml) builds an `.exe` for every `.pyw` and `.c` file in the repo on a Windows runner (the C build uses MinGW-w64/`make` via `msys2/setup-msys2`):

- **Every push to `main`** — builds and uploads the executables as a workflow artifact, so every build is validated and downloadable.
- **Pushing a tag matching `v*`** — builds and additionally attaches the executables to a GitHub Release:

      git tag v1.0.0
      git push origin v1.0.0

- **Manual run** from the Actions tab (`workflow_dispatch`) — builds and uploads the artifact without creating a release.
