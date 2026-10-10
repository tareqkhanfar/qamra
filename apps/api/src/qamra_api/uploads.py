"""Photo and drawing uploads: size limit, re-encoding without metadata, and the face check with a friendly
Arabic/English reason when the photo won't work."""

import io

from fastapi import UploadFile
from PIL import Image, ImageOps, UnidentifiedImageError

from qamra_ai.pipeline.photo_check import PhotoCheck, check_photo
from qamra_api.errors import ApiError

MAX_UPLOAD = 10 * 1024 * 1024
PHOTO_MAX_SIDE = 2048


def clean_image(data: bytes, max_side: int = PHOTO_MAX_SIDE) -> bytes:
    """Re-encode as JPEG: validates the file, applies the EXIF rotation, and drops all metadata (GPS)."""
    if len(data) > MAX_UPLOAD:
        raise ApiError("file_too_large", 413)
    try:
        with Image.open(io.BytesIO(data)) as original:
            if original.format not in ("JPEG", "PNG", "WEBP"):
                raise ApiError("invalid_photo", 422, {"reason": "format"})
            im = ImageOps.exif_transpose(original).convert("RGB")
            im.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
            buf = io.BytesIO()
            im.save(buf, format="JPEG", quality=92)
            return buf.getvalue()
    except (UnidentifiedImageError, OSError) as e:
        raise ApiError("invalid_photo", 422, {"reason": "unreadable"}) from e


async def read_upload(upload: UploadFile) -> bytes:
    data = await upload.read(MAX_UPLOAD + 1)
    if len(data) > MAX_UPLOAD:
        raise ApiError("file_too_large", 413)
    return data


def require_face(data: bytes) -> None:
    """One clear, front-facing child's face, or a friendly reason why not."""
    require_ok(check_photo(data))


def require_ok(check: PhotoCheck) -> None:
    """A failed photo check as the friendly Arabic/English reason the photo step shows."""
    if not check.ok:
        issue = check.issues[0]
        raise ApiError(
            "invalid_photo", 422, {"reason": issue.code, "ar": issue.message_ar, "en": issue.message_en}
        )
