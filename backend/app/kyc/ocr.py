"""OCR for KYC photos: RapidOCR on in-memory bytes. Nothing here touches the disk.

Preprocessing:
- the red channel is used as greyscale, which drops the pink "SYNTHETIC SPECIMEN" watermark;
- a Laplacian-variance blur score flags photos too blurry to read;
- deskew: the text slant is estimated from the OCR boxes, small rotations (within ±10°) around it are tried,
  and the most level result wins among those whose mean OCR confidence is within CONF_SLACK of the best.
  Confidence alone is not enough: RapidOCR reads K02's 7° tilt at 0.987 unrotated and 0.981 straightened,
  but the parsers pair labels with values by row, so the page has to be level.
"""
from __future__ import annotations

import math
import threading
from dataclasses import dataclass, field
from statistics import median
from typing import Any

import cv2
import numpy as np

from ..config import settings

# Calibrated on data/kyc_documents: K04's GST certificate scores ~1, every other specimen scores > 800.
BLUR_THRESHOLD = 100.0
MAX_SIDE = 1800        # phone photos are scaled down to this before OCR
MAX_SKEW_DEG = 10.0
MIN_SKEW_DEG = 0.5     # below this, rotating is not worth another OCR pass
CONF_SLACK = 0.02

_engine: Any = None
_engine_lock = threading.Lock()


class ImageDecodeError(ValueError):
    """The bytes are not an image OpenCV can read."""


@dataclass
class OcrLine:
    text: str
    conf: float
    x0: float
    y0: float
    x1: float
    y1: float
    slant_deg: float = 0.0  # angle of the box's top edge (positive = runs downhill to the right)

    @property
    def yc(self) -> float:
        return (self.y0 + self.y1) / 2

    @property
    def height(self) -> float:
        return self.y1 - self.y0


@dataclass
class OcrPage:
    lines: list[OcrLine]
    width: int
    height: int
    blur_score: float
    blurry: bool
    skew_deg: float = 0.0
    mean_conf: float = 0.0
    angles_tried: list[float] = field(default_factory=list)


def _get_engine() -> Any:
    global _engine
    if _engine is None:
        from rapidocr_onnxruntime import RapidOCR  # imported lazily: loading the models takes a second
        # OCR_THREADS caps ONNX Runtime's threads (0 = one per core). On a small host, 1 leaves a core free for the
        # web requests that arrive while a KYC check is running.
        threads = settings.ocr_threads
        _engine = RapidOCR(**({"intra_op_num_threads": threads, "inter_op_num_threads": 1} if threads else {}))
    return _engine


def decode(data: bytes) -> np.ndarray:
    """Image bytes -> BGR array, scaled so the longest side is at most MAX_SIDE."""
    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR) if data else None
    if img is None:
        raise ImageDecodeError("not an image")
    h, w = img.shape[:2]
    scale = MAX_SIDE / max(h, w)
    if scale < 1:
        img = cv2.resize(img, (round(w * scale), round(h * scale)), interpolation=cv2.INTER_AREA)
    return img


def to_grey(img: np.ndarray) -> np.ndarray:
    """Red channel as greyscale: red/pink ink (the watermark) becomes near-white, dark text stays dark."""
    return img[:, :, 2].copy()


def blur_score(grey: np.ndarray) -> float:
    return float(cv2.Laplacian(grey, cv2.CV_64F).var())


def rotate(grey: np.ndarray, angle_deg: float) -> np.ndarray:
    """Rotate counter-clockwise by angle_deg around the centre, padding with white."""
    if abs(angle_deg) < 1e-6:
        return grey
    h, w = grey.shape[:2]
    m = cv2.getRotationMatrix2D((w / 2, h / 2), angle_deg, 1.0)
    return cv2.warpAffine(grey, m, (w, h), flags=cv2.INTER_LINEAR, borderValue=255)


def _run(grey: np.ndarray) -> list[OcrLine]:
    with _engine_lock:
        result, _ = _get_engine()(cv2.cvtColor(grey, cv2.COLOR_GRAY2BGR))
    lines = []
    for box, text, conf in result or []:
        xs = [p[0] for p in box]
        ys = [p[1] for p in box]
        (xa, ya), (xb, yb) = box[0], box[1]  # RapidOCR boxes keep their slant: top-left, top-right, ...
        slant = math.degrees(math.atan2(yb - ya, xb - xa)) if xb - xa > 40 else 0.0
        lines.append(OcrLine(text=str(text).strip(), conf=float(conf), x0=min(xs), y0=min(ys), x1=max(xs), y1=max(ys),
                             slant_deg=slant))
    return lines


def _mean_conf(lines: list[OcrLine]) -> float:
    return sum(ln.conf for ln in lines) / len(lines) if lines else 0.0


def estimate_skew(lines: list[OcrLine]) -> float:
    """Median slant of the wider text boxes, in degrees (positive = text runs downhill to the right)."""
    angles = [ln.slant_deg for ln in lines if ln.x1 - ln.x0 > 120]
    return float(median(angles)) if angles else 0.0


def read_image(data: bytes) -> OcrPage:
    """Decode, score blur, OCR, and deskew. Bytes stay in memory."""
    img = decode(data)
    grey = to_grey(img)
    score = blur_score(grey)
    lines = _run(grey)
    candidates = [(0.0, lines)]
    est = max(-MAX_SKEW_DEG, min(MAX_SKEW_DEG, estimate_skew(lines)))
    if abs(est) >= MIN_SKEW_DEG:
        for angle in (est, est - 0.5, est + 0.5):
            if abs(angle) <= MAX_SKEW_DEG:
                candidates.append((angle, _run(rotate(grey, angle))))
    top_conf = max(_mean_conf(ls) for _, ls in candidates)
    near_best = [(a, ls) for a, ls in candidates if _mean_conf(ls) >= top_conf - CONF_SLACK]
    best_angle, best_lines = min(near_best, key=lambda c: (abs(estimate_skew(c[1])), -_mean_conf(c[1])))
    tried = [round(a, 2) for a, _ in candidates]
    h, w = grey.shape[:2]
    return OcrPage(lines=best_lines, width=w, height=h, blur_score=round(score, 1), blurry=score < BLUR_THRESHOLD,
                   skew_deg=round(best_angle, 1), mean_conf=round(_mean_conf(best_lines), 3), angles_tried=tried)
