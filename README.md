# utils
Utility tools and scripts

# Release
## Dependencies
### PyInstaller

    pip install pyinstaller tkinterdnd2
    python -m pyinstaller --onefile --windowed --name datestamp datestamp.pyw

## Automated build (GitHub Actions)
Pushing a tag matching `datestamp-v*` triggers [.github/workflows/build-datestamp.yml](.github/workflows/build-datestamp.yml), which builds `datestamp.exe` on a Windows runner and attaches it to a GitHub Release:

    git tag datestamp-v1.0.0
    git push origin datestamp-v1.0.0

The workflow can also be run manually from the Actions tab (`workflow_dispatch`), which builds the exe and uploads it as a workflow artifact without creating a release.