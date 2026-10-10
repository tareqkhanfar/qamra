"""Lightweight photo quality check (OpenCV + YuNet face detector). Runs before any upload/AI call."""

from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

MIN_SIDE_PX = 512
MIN_FACE_RATIO = 0.12  # face width / image width
MIN_SHARPNESS = 60.0  # variance of Laplacian on the face crop
BRIGHTNESS_RANGE = (60.0, 205.0)

MESSAGES: dict[str, tuple[str, str]] = {
    "unreadable": (
        "لم نستطع فتح الصورة. جرّبوا صورة أخرى بصيغة JPG أو PNG.",
        "We couldn't open this image. Please try a JPG or PNG photo.",
    ),
    "too_small": (
        "الصورة صغيرة قليلًا. اختاروا صورة أوضح بدقّة أعلى.",
        "This photo is a bit small. Please choose a higher-resolution photo.",
    ),
    "no_face": (
        "لم نجد وجه الطفل بوضوح. صوّروا الطفل من الأمام والوجه ظاهر.",
        "We couldn't find your child's face. Please use a front-facing photo.",
    ),
    "many_faces": (
        "في الصورة أكثر من وجه. نحتاج صورة للطفل وحده.",
        "There's more than one face in this photo. Please use a photo of your child alone.",
    ),
    "face_small": (
        "وجه الطفل بعيد قليلًا. اقتربوا أكثر ليظهر الوجه كبيرًا.",
        "Your child's face is a bit far. Please move closer so the face is larger.",
    ),
    "face_cut": (
        "جزء من الوجه خارج الإطار. حرّكوا الصورة أو صغّروها حتى يظهر الوجه كاملًا داخل الشكل البيضوي.",
        "Part of the face is outside the frame. "
        "Move the photo or zoom out so the whole face sits inside the oval.",
    ),
    "crop_small": (
        "كبّرتم الصورة كثيرًا فلم تعد واضحة بما يكفي للرسم. "
        "صغّروها قليلًا، أو اختاروا صورة يظهر فيها الوجه أكبر.",
        "You've zoomed in a lot, so the photo isn't sharp enough to draw from. "
        "Zoom out a little, or choose a photo where the face is bigger.",
    ),
    "blurry": (
        "الصورة غير واضحة (مهزوزة). جرّبوا صورة أثبت.",
        "The photo looks blurry. Please try a steadier shot.",
    ),
    "dark": (
        "الصورة معتمة. صوّروا في مكان فيه ضوء أكثر.",
        "The photo is too dark. Please take it somewhere brighter.",
    ),
    "bright": (
        "الصورة ساطعة جدًا. ابتعدوا عن الضوء المباشر.",
        "The photo is too bright. Please avoid direct light.",
    ),
}


@dataclass(frozen=True)
class PhotoIssue:
    code: str

    @property
    def message_ar(self) -> str:
        return MESSAGES[self.code][0]

    @property
    def message_en(self) -> str:
        return MESSAGES[self.code][1]


@dataclass
class PhotoCheck:
    ok: bool
    issues: list[PhotoIssue] = field(default_factory=list)
    face_box: tuple[int, int, int, int] | None = None
    metrics: dict[str, float] = field(default_factory=dict)


YUNET_MODEL = Path(__file__).resolve().parents[1] / "models_data" / "face_detection_yunet_2023mar.onnx"
MIN_FACE_SCORE = 0.8


def detect_faces(img: np.ndarray) -> np.ndarray:
    """YuNet (MIT license, OpenCV zoo) → rows of [x, y, w, h, 10 landmark coords, score]."""
    h, w = img.shape[:2]
    detector = cv2.FaceDetectorYN.create(str(YUNET_MODEL), "", (w, h), MIN_FACE_SCORE, 0.3, 50)
    _, faces = detector.detect(img)
    return faces if faces is not None else np.empty((0, 15), dtype=np.float32)


def decode_image(data: bytes) -> np.ndarray | None:
    arr = np.frombuffer(data, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    return img if img is not None and img.size else None


def check_photo(data: bytes, min_side: int = MIN_SIDE_PX) -> PhotoCheck:
    """`min_side`: the shortest side allowed (a framed cut-out of the photo has its own, `photo_crop`)."""
    img = decode_image(data)
    if img is None:
        return PhotoCheck(ok=False, issues=[PhotoIssue("unreadable")])
    h, w = img.shape[:2]
    metrics: dict[str, float] = {"width": w, "height": h}
    if min(h, w) < min_side:
        return PhotoCheck(ok=False, issues=[PhotoIssue("too_small")], metrics=metrics)

    scale = 1024 / max(h, w) if max(h, w) > 1024 else 1.0
    small = cv2.resize(img, None, fx=scale, fy=scale) if scale < 1 else img
    faces = detect_faces(small)
    metrics["faces"] = len(faces)
    if len(faces) == 0:
        return PhotoCheck(ok=False, issues=[PhotoIssue("no_face")], metrics=metrics)
    if len(faces) > 1:
        return PhotoCheck(ok=False, issues=[PhotoIssue("many_faces")], metrics=metrics)

    sw, sh = small.shape[1], small.shape[0]
    x, y, fw, fh = (int(v) for v in faces[0][:4])
    x, y = max(0, x), max(0, y)
    fw, fh = min(fw, sw - x), min(fh, sh - y)
    face = cv2.cvtColor(small[y : y + fh, x : x + fw], cv2.COLOR_BGR2GRAY)
    metrics["face_score"] = round(float(faces[0][-1]), 3)
    metrics["face_ratio"] = round(fw / sw, 3)
    metrics["sharpness"] = round(float(cv2.Laplacian(face, cv2.CV_64F).var()), 1)
    metrics["brightness"] = round(float(face.mean()), 1)

    issues: list[PhotoIssue] = []
    if metrics["face_ratio"] < MIN_FACE_RATIO:
        issues.append(PhotoIssue("face_small"))
    if metrics["sharpness"] < MIN_SHARPNESS:
        issues.append(PhotoIssue("blurry"))
    if metrics["brightness"] < BRIGHTNESS_RANGE[0]:
        issues.append(PhotoIssue("dark"))
    elif metrics["brightness"] > BRIGHTNESS_RANGE[1]:
        issues.append(PhotoIssue("bright"))
    box = tuple(int(v / scale) for v in (x, y, fw, fh))
    return PhotoCheck(ok=not issues, issues=issues, face_box=box, metrics=metrics)  # type: ignore[arg-type]
