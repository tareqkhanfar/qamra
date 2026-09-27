"""Generate synthetic photographed-drawing fixtures: crayon creature on paper, on a table, tilted, shadowed.

Run: uv run packages/ai/tests/fixtures/make_drawings.py
"""

from pathlib import Path

import cv2
import numpy as np

OUT = Path(__file__).parent / "drawings"
PAPER_W, PAPER_H = 840, 1188  # A4 ratio
CRAYON = [(209, 111, 155), (40, 140, 242), (151, 165, 47), (63, 210, 255), (91, 38, 192)]  # BGR


def crayon_line(
    img: np.ndarray, pts: np.ndarray, color: tuple[int, int, int], rng: np.random.Generator
) -> None:
    for _ in range(3):  # wobbly multi-stroke like a crayon
        jitter = pts + rng.normal(0, 2.5, pts.shape)
        cv2.polylines(img, [jitter.astype(np.int32)], True, color, int(rng.integers(5, 9)), cv2.LINE_AA)


def creature(seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    paper = np.full((PAPER_H, PAPER_W, 3), (236, 244, 248), np.uint8)
    body = CRAYON[seed % 5]
    cx, cy = PAPER_W // 2, PAPER_H // 2
    t = np.linspace(0, 2 * np.pi, 60)
    r = 220 + 30 * np.sin(3 * t + seed)
    outline = np.stack([cx + r * np.cos(t), cy + r * 1.1 * np.sin(t)], axis=1)
    fill = paper.copy()
    cv2.fillPoly(fill, [outline.astype(np.int32)], body)
    paper = cv2.addWeighted(fill, 0.55, paper, 0.45, 0)  # crayon fill is never solid
    crayon_line(paper, outline, (60, 40, 40), rng)
    n_eyes = 1 + seed % 3
    for i in range(n_eyes):
        ex = cx - 90 * (n_eyes - 1) // 2 + 90 * i
        cv2.circle(paper, (ex, cy - 60), 34, (255, 255, 255), -1)
        cv2.circle(paper, (ex, cy - 60), 34, (40, 30, 30), 5, cv2.LINE_AA)
        cv2.circle(paper, (ex + 8, cy - 55), 13, (20, 20, 20), -1)
    cv2.ellipse(paper, (cx, cy + 60), (80, 40), 0, 0, 180, (40, 30, 150), 7, cv2.LINE_AA)
    for i in range(2 + seed % 3):  # legs
        lx = cx - 120 + 240 * i // max(1, 1 + seed % 3)
        cv2.line(
            paper,
            (lx, cy + 230),
            (lx + int(rng.integers(-30, 30)), cy + 360),
            CRAYON[(seed + 2) % 5],
            12,
            cv2.LINE_AA,
        )
    return paper


def photograph(paper: np.ndarray, seed: int) -> np.ndarray:
    rng = np.random.default_rng(100 + seed)
    W, H = 1600, 1600
    table = np.zeros((H, W, 3), np.uint8)
    table[:] = (60 + seed * 5, 100, 140)  # wood-ish
    noise = rng.normal(0, 10, (H, W, 1)).astype(np.int16)
    table = np.clip(table.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    src = np.float32([[0, 0], [PAPER_W, 0], [PAPER_W, PAPER_H], [0, PAPER_H]])
    j = lambda: rng.uniform(-90, 90)  # noqa: E731
    dst = np.float32(
        [
            [330 + j(), 160 + j()],
            [1270 + j(), 200 + j()],
            [1330 + j(), 1450 + j()],
            [260 + j(), 1420 + j()],
        ]
    )
    m = cv2.getPerspectiveTransform(src, dst)
    warped = cv2.warpPerspective(paper, m, (W, H))
    mask = cv2.warpPerspective(np.full(paper.shape[:2], 255, np.uint8), m, (W, H))
    photo = np.where(mask[..., None] > 0, warped, table)
    # soft shadow gradient across the frame (phone held over the paper)
    xs = np.linspace(0.55 + 0.05 * seed, 1.0, W)[None, :, None]
    ys = np.linspace(1.0, 0.8, H)[:, None, None]
    return np.clip(photo * xs * ys, 0, 255).astype(np.uint8)


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    for i in range(1, 6):
        cv2.imwrite(
            str(OUT / f"drawing-{i}.jpg"),
            photograph(creature(i), i),
            [cv2.IMWRITE_JPEG_QUALITY, 88],
        )
    print(f"wrote 5 fixtures to {OUT}")
