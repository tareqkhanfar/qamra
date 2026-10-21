"""The figure's matte from a segmentation model (U²-Net), run locally and free with ONNX Runtime.

The colour cut-out (`qamra_pdf.cutout`) cannot tell a white shoe on cream paper from the paper in shade
(«جوليا»'s workbook, 2026-10-21: her white sneakers came out eaten at the toe and ragged after v4). A salient-
object model sees the whole child, shoes included, with smooth edges; `cutout` takes its matte as the figure's
shape and uses its own paper model only to drop what the model also took that is not drawn (the floor shadow,
a soft patch of wash) and the paper-coloured halo along the edge.

Model: U²-Net (`u2net.onnx`, 176 MB; Qin et al. 2020, Apache-2.0, github.com/xuebinqin/U-2-Net), the ONNX
export that rembg mirrors. Pre/post-processing as rembg's `U2netSession`: RGB scaled to 320 × 320, divided by
its maximum, ImageNet mean/std; the first output, min-max normalized, resized back. Chosen over IS-Net
(general-use: «جوليا»'s waving pose came out with see-through shoes; anime: it keeps the floor shadow) and
BiRefNet-lite (as good, 8 × slower) on her sheet and the sample sheets (docs/decisions.md, 2026-10-21).

Where the weights are: `QAMRA_MATTE_MODEL` (a path; "off" turns the model off), else `/opt/models/u2net.onnx`
(the worker image, fetched at build with its checksum), else `~/.cache/qamra/models/u2net.onnx`
(`scripts/fetch_matte_model.py`). The file's SHA-256 is checked once. When the model or ONNX Runtime is
missing, `figure_matte` returns None and the cut-out falls back to its colour method (and says so:
`Cutout.method`).
"""

from __future__ import annotations

import hashlib
import os
import threading
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

MODEL_ID = "u2net-onnx-8d10d2f3"  # in the cut-outs' cache keys: a different model is a different cut-out
MODEL_FILE = "u2net.onnx"
MODEL_SHA256 = "8d10d2f3bb75ae3b6d527c77944fc5e7dcd94b29809d47a739a7a728a912b491"
MODEL_URL = "https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2net.onnx"
SIZE = 320  # the model's input
MEAN = (0.485, 0.456, 0.406)
STD = (0.229, 0.224, 0.225)
ENV = "QAMRA_MATTE_MODEL"
OFF = "off"  # QAMRA_MATTE_MODEL=off: the colour cut only (the tests' default)
IMAGE_PATH = Path("/opt/models") / MODEL_FILE
CACHE_PATH = Path.home() / ".cache" / "qamra" / "models" / MODEL_FILE

_lock = threading.Lock()


def model_path() -> Path | None:
    """The weights to use, or None when there are none (the colour cut-out is used instead)."""
    env = os.environ.get(ENV, "").strip()
    if env.lower() == OFF:
        return None
    for path in ([Path(env)] if env else []) + [IMAGE_PATH, CACHE_PATH]:
        if path.is_file():
            return path
    return None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


@lru_cache(maxsize=1)
def _session(path: str) -> Any:
    """The ONNX Runtime session (CPU), once per process; None when it cannot be made."""
    try:
        import onnxruntime as ort
    except ImportError:
        return None
    if _sha256(Path(path)) != MODEL_SHA256:
        return None  # not the model the cut-out was tuned with
    options = ort.SessionOptions()
    options.log_severity_level = 3
    return ort.InferenceSession(path, sess_options=options, providers=["CPUExecutionProvider"])


def available() -> bool:
    path = model_path()
    return path is not None and _session(str(path)) is not None


def figure_matte(img: Image.Image) -> np.ndarray | None:
    """The model's matte of `img` (float32 0–1, the size of `img`), or None without the model."""
    path = model_path()
    if path is None:
        return None
    with _lock:  # one inference at a time per process (ONNX Runtime already uses every core)
        session = _session(str(path))
        if session is None:
            return None
        rgb = img.convert("RGB")
        small = np.asarray(rgb.resize((SIZE, SIZE), Image.Resampling.LANCZOS), np.float32)
        small = small / max(float(small.max()), 1e-6)
        x = ((small - np.array(MEAN, np.float32)) / np.array(STD, np.float32)).transpose(2, 0, 1)[None]
        out = session.run(None, {session.get_inputs()[0].name: x.astype(np.float32)})[0][0, 0]
    out = (out - out.min()) / max(float(out.max() - out.min()), 1e-6)
    full = Image.fromarray(out.astype(np.float32), mode="F").resize(rgb.size, Image.Resampling.BILINEAR)
    matte: np.ndarray = np.clip(np.asarray(full, np.float32), 0.0, 1.0)
    return matte
