# utils
Utility tools and scripts

## Scripts
- [datestamp.pyw](datestamp.pyw) — drag & drop files to prepend a live, editable date/time stamp to their filenames.
- [lowres.pyw](lowres.pyw) — drag & drop images to shrink them (aspect ratio preserved) and save alongside the original with a `_lowres` suffix. Choose how: max size in pixels (default 1024x768), a reduction factor (2x, 5x, etc.), or a max file size in KB (default 100 KB, finds the highest resolution that fits).
- [pdfmerger.pyw](pdfmerger.pyw) — drag & drop (or add) PDFs, reorder them, and combine into a single output PDF.
- screenreader.pyw - takes a screenshot and parses the text selected by the user. Uses Tesseract-OCR to convert image to text. Tesseract-OCR is splitted into several zip files. Before running screenreader, right click Tesseract-OCR.zip.001 and select Extract Here. The Tesseract-OCR directory will be created with the expected files already in place. This folder must exist at the same level of screenreader.
- [imagecompare.py](imagecompare.py) — command-line tool that compares two images via SSIM, prints the similarity score, and (optionally) highlights/saves/shows the differing regions. `imagecompare.exe -a imgA.png -b imgB.png [-v] [-s]`
- [ccallseq.py](ccallseq.py) — command-line tool that scans C/C++ source for function definitions and call sites, then prints a call tree (no compiler required, best-effort regex-based scan).

      ccallseq.exe <paths...> [--start NAME[(path)]] [--max-depth N] [--show-files] [--dot PATH] [--drawio PATH]
      # or: python ccallseq.py <paths...> [same options]

  - `paths` — files or directories to scan.
  - `--start` — function to start from. Omit it to print a tree for every function found. If the name was defined in more than one file, a tree is printed per definition unless narrowed down with `NAME(path)` (path matched as a substring, either slash style), e.g. `--start "main(unix/plink.c)"` — copy-paste straight from the tool's own output.
  - `--show-files` — show the defining file after each function name, e.g. `main(unix/plink.c)`.
  - `--dot PATH` — write a Graphviz DOT file instead of printing. Render with `dot -Tsvg PATH -o graph.svg`, or import into draw.io (Extras > Edit Diagram).
  - `--drawio PATH` — write a draw.io (mxGraph XML) file, laid out with the pure-Python `grandalf` package (`pip install grandalf` if running from source) — no Graphviz install needed. Open the file directly in draw.io. The layout gets slow beyond roughly a thousand nodes, so narrow the graph with `--start`/`--max-depth` for large codebases.

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
Run [build.bat](build.bat) to build every `.pyw` script plus `imagecompare.py` and `ccallseq.py` into standalone `.exe` files. It installs/updates dependencies from `requirements.txt` (which includes `grandalf`, so `ccallseq.exe`'s `--drawio` option works out of the box), checks that `Tesseract-OCR` has been extracted (required by `screenreader.exe` at runtime, see above), builds each script with PyInstaller, and moves the resulting executables into the repo root.

Run `make` (requires a MinGW-w64 `gcc` on `PATH`) to build every `.c` file in the repo into a matching `.exe`, e.g. `serialUdpTx.c` → `serialUdpTx.exe`. See [Makefile](Makefile).

## Automated build (GitHub Actions)
[.github/workflows/release.yml](.github/workflows/release.yml) builds an `.exe` for every `.pyw` file, `imagecompare.py`, `ccallseq.py`, and every `.c` file in the repo on a Windows runner (the C build uses MinGW-w64/`make` via `msys2/setup-msys2`):

- **Every push to `main`** — builds and uploads the executables as a workflow artifact, so every build is validated and downloadable.
- **Pushing a tag matching `v*`** — builds and additionally attaches the executables to a GitHub Release:

      git tag v1.0.0
      git push origin v1.0.0

- **Manual run** from the Actions tab (`workflow_dispatch`) — builds and uploads the artifact without creating a release.
