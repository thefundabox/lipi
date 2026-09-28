"""Download every OCR model Lipi uses, so the build can bundle them (no downloads on users' PCs)."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from smart_ocr import engines
from smart_ocr.profiles import RAPIDOCR_LANGS

engine = engines.get("rapidocr")
blank = np.full((64, 256), 255, np.uint8)
for lang in RAPIDOCR_LANGS:  # en, hi, en+hi, sa, ur -> CH, DEVANAGARI, ARABIC models
    engine.ocr(blank, lang, None)
    print("model ready for", lang)
