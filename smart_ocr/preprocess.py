"""Image preprocessing steps. Each takes and returns a numpy uint8 image."""
import cv2
import numpy as np


def grayscale(img):
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img


def upscale(img):
    # Small glyphs OCR badly; aim for ~30px x-height by enlarging low-res pages.
    h, w = img.shape[:2]
    return cv2.resize(img, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC) if max(h, w) < 4000 else img


def denoise(img):
    return cv2.fastNlMeansDenoising(img, None, h=12, templateWindowSize=7, searchWindowSize=21)


def median(img):
    # Removes salt-and-pepper specks that OCR reads as stray punctuation.
    return cv2.medianBlur(img, 3)


def clahe(img):
    return cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(img)


def remove_shadows(img):
    # Divide by a blurred background estimate to flatten uneven lighting.
    bg = cv2.medianBlur(cv2.dilate(img, np.ones((7, 7), np.uint8)), 21)
    return cv2.normalize(255 - cv2.absdiff(img, bg), None, 0, 255, cv2.NORM_MINMAX)


def otsu(img):
    return cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]


def adaptive_threshold(img):
    return cv2.adaptiveThreshold(img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 15)


def remove_specks(img):
    # Morphological open on inverted image removes isolated dots without eating text.
    inv = 255 - img
    inv = cv2.morphologyEx(inv, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    return 255 - inv


def deskew(img):
    """Find the rotation (within ±10°) whose horizontal projection has the sharpest text lines.

    Projection profiles are robust to noise specks, which throw off bounding-box methods.
    """
    h, w = img.shape[:2]
    scale = 1000 / max(h, w)
    small = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    # Adaptive (local) threshold so uneven lighting in photos doesn't swamp the text.
    binary = cv2.adaptiveThreshold(small, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 25, 15)
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    sh, sw = binary.shape

    def sharpness(a):
        m = cv2.getRotationMatrix2D((sw / 2, sh / 2), a, 1.0)
        return np.var(cv2.warpAffine(binary, m, (sw, sh)).sum(axis=1, dtype=np.float64))

    coarse = max(np.arange(-10, 10.01, 1.0), key=sharpness)
    angle = max(np.arange(coarse - 1, coarse + 1.01, 0.1), key=sharpness)
    if abs(angle) < 0.2:
        return img
    m = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    return cv2.warpAffine(img, m, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)


STEPS = {f.__name__: f for f in [
    grayscale, upscale, denoise, median, clahe, remove_shadows, otsu, adaptive_threshold, remove_specks, deskew,
]}


def run(img, steps):
    for name in steps:
        img = STEPS[name](img)
    return img
