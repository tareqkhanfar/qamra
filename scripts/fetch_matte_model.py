"""Download the cut-out's segmentation model (U²-Net, Apache-2.0) and check its SHA-256.

    uv run python scripts/fetch_matte_model.py [DEST]

DEST defaults to `~/.cache/qamra/models/u2net.onnx`, where `qamra_pdf.matte` looks after `QAMRA_MATTE_MODEL`
and `/opt/models/u2net.onnx` (the worker image fetches it there at build). Free: no API, no account.
"""

from __future__ import annotations

import hashlib
import sys
import urllib.request
from pathlib import Path

from qamra_pdf.matte import CACHE_PATH, MODEL_SHA256, MODEL_URL


def main() -> int:
    dest = Path(sys.argv[1]) if len(sys.argv) > 1 else CACHE_PATH
    if dest.is_file() and hashlib.sha256(dest.read_bytes()).hexdigest() == MODEL_SHA256:
        print(f"already there: {dest}")
        return 0
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_suffix(".part")
    print(f"downloading {MODEL_URL} (176 MB)")
    urllib.request.urlretrieve(MODEL_URL, part)
    digest = hashlib.sha256(part.read_bytes()).hexdigest()
    if digest != MODEL_SHA256:
        part.unlink()
        print(f"checksum mismatch: {digest}", file=sys.stderr)
        return 1
    part.rename(dest)
    print(f"saved {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
