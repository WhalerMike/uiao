# deps/ — Pre-downloaded pip wheels for offline install

This folder contains pre-downloaded `.whl` files that allow the UIAO CLI to be
installed on machines with no internet access (proxy 407 / air-gap networks).

## Contents

| File | Version | Purpose |
|---|---|---|
| `setuptools-82.0.1-py3-none-any.whl` | 82.0.1 | Build backend required by `pip install .` |
| `wheel-0.47.0-py3-none-any.whl` | 0.47.0 | Wheel build support |
| `build-1.5.0-py3-none-any.whl` | 1.5.0 | PEP 517 build frontend |

> Additional runtime dependency wheels are downloaded by `Download-UIAODeps.ps1`
> (run on an internet-connected machine) and by the CI `source-zip-build.yml`
> workflow before assembling `uiao.zip`.

## Usage

**On the target machine (no internet needed):**

```powershell
# Install build tooling first, then the package:
python -m pip install --no-index --find-links deps\ setuptools wheel build
python -m pip install --no-index --find-links deps\ .

# Or use the one-shot installer:
.\Install-UIAO.ps1
```

## Why these are tracked in git

`.whl` files are normally gitignored (they are build outputs).  The files in
this directory are **intentionally committed** — they are upstream build
tooling (not UIAO outputs), and bundling them here guarantees the offline
install works without any network access, even for the build-system bootstrap
step that pip performs before running `setup.py` / `build-backend`.

The root `.gitignore` has `!deps/*.whl` to allow tracking.
