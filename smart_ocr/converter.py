"""Page-by-page conversion driven by the chosen input profile."""
from dataclasses import dataclass

import re

import numpy as np
import pymupdf

from . import engines, hindi_spell, legacy_fonts, preprocess
from .profiles import SCRIPTS, Profile


@dataclass
class PageResult:
    number: int
    text: str
    source: str        # "text-layer", "legacy-font" (converted Kruti Dev/DevLys) or engine name
    confidence: float
    note: str = ""
    review: bool = False  # a person should check this page


def render(page, dpi):
    pix = page.get_pixmap(dpi=dpi, colorspace=pymupdf.csRGB)
    rgb = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3)
    return rgb[:, :, ::-1].copy()  # RGB -> BGR for OpenCV


SCRIPT_RANGES = {
    "latin": [],
    "devanagari": [(0x0900, 0x097F), (0xA8E0, 0xA8FF)],
    "arabic": [(0x0600, 0x06FF), (0x0750, 0x077F), (0xFB50, 0xFDFF), (0xFE70, 0xFEFF)],
}
COMMON = set("₹–—‘’“”•…°×·")


def text_layer_problem(text, lang):
    """Return why an embedded text layer can't be trusted, or None if it looks genuine.

    Hindi PDFs very often carry broken layers: fonts without proper Unicode mapping yield
    'राज˳ान' for 'राजस्थान', and legacy fonts such as Kruti Dev yield Latin gibberish ('jktLFkku').
    """
    chars = [c for c in text if not c.isspace()]
    if len(chars) < 40:
        return "too little text"
    ranges = SCRIPT_RANGES[SCRIPTS[lang]]
    in_script = lambda c: any(a <= ord(c) <= b for a, b in ranges)
    stray = sum(1 for c in chars if not (c.isascii() or in_script(c) or c in COMMON))
    if stray / len(chars) > 0.02:
        return f"garbled text layer ({stray} unmapped glyphs)"
    if lang in ("hi", "sa", "ur") and sum(map(in_script, chars)) / len(chars) < 0.3:
        return "text layer is not in the expected script (legacy font encoding?)"
    if sum(c.isalnum() or in_script(c) for c in chars) / len(chars) < 0.5:
        return "text layer is mostly symbols"
    return None


def is_scanned(page):
    """True when an image covers most of the page, i.e. the text is a picture, not typed text."""
    area = abs(page.rect)
    return any(abs(pymupdf.Rect(i["bbox"]) & page.rect) > 0.5 * area for i in page.get_image_info())


def embedded_text(page, lang):
    """The page's own typed text as (text, source, problem); problem is None when it can be trusted."""
    if legacy_fonts.uses_legacy_font(page):
        text, source = legacy_fonts.page_text(page), "legacy-font"
    else:
        text, source = page.get_text().strip(), "text-layer"
    return text, source, text_layer_problem(text, lang)


def tidy(text, lang):
    """Small OCR clean-ups that never change a word."""
    if SCRIPTS[lang] == "devanagari":
        text = re.sub(r"[ \t]+([।॥,])", r"\1", text)  # "जाये ।" -> "जाये।"
    return text


def _run_engine(name, img, lang, profile):
    engine = engines.get(name)
    if not engine.supports(lang):
        raise engines.EngineUnavailable(f"{name} has no model for this language")
    return engine.ocr(img, lang, profile)


def convert_page(page, number, profile: Profile, lang, allow_cloud, log=print, fix_spelling=True):
    layer_note = ""
    # Typed (non-scanned) pages use their own text whatever type was chosen: it is exact, OCR is not.
    if profile.use_text_layer or not is_scanned(page):
        text, source, problem = embedded_text(page, lang)
        if problem is None:
            note = "converted exactly from Kruti Dev/DevLys font text" if source == "legacy-font" else ""
            return PageResult(number, text, source, 1.0, note=note)
        if text and problem != "too little text":
            layer_note = f"{problem}; used OCR"
            log(f"  page {number}: {layer_note}")

    image = render(page, profile.dpi)
    best, skipped = None, []

    for name in profile.engines:
        if name == "claude" and not allow_cloud:
            skipped.append("claude (cloud disabled)")
            continue
        steps = profile.preprocess if name == "tesseract" else profile.neural_preprocess
        try:
            text, conf = _run_engine(name, preprocess.run(image, steps), lang, profile)
            best = PageResult(number, text, name, conf)
            break  # first available engine in the profile's order wins
        except engines.EngineUnavailable as e:
            skipped.append(f"{name} ({e})")

    fb = profile.fallback_engine
    if fb and (best is None or best.confidence < profile.min_confidence) and (best is None or best.source != fb):
        if fb == "claude" and not allow_cloud:
            skipped.append("claude fallback (cloud disabled)")
        else:
            try:
                log(f"  page {number}: confidence {best.confidence if best else 0:.0%} is low, re-reading with {fb}")
                text, conf = _run_engine(fb, preprocess.run(image, profile.neural_preprocess), lang, profile)
                if text:
                    best = PageResult(number, text, fb, conf, note="fallback")
            except engines.EngineUnavailable as e:
                skipped.append(f"{fb} ({e})")

    if best is None:
        return PageResult(number, "", "none", 0.0, note="no engine available: " + "; ".join(skipped), review=True)
    best.text = tidy(best.text, lang)
    if fix_spelling and SCRIPTS[lang] == "devanagari" and best.source != "claude":
        best.text, fixes = hindi_spell.correct_with_log(best.text)
        if fixes:
            shown = ", ".join(f"{a}→{b}" for a, b in fixes[:12]) + (", …" if len(fixes) > 12 else "")
            best.note = (best.note + f" Fixed {len(fixes)} common OCR slip{'s' if len(fixes) > 1 else ''}: {shown}").strip()
    if best.confidence < profile.min_confidence:
        best.note = (best.note + " low confidence, review manually").strip()
        best.review = True
    elif layer_note:
        best.note = (best.note + " " + layer_note).strip()
    return best


def convert(pdf_path, profile: Profile, lang="en", allow_cloud=False, pages=None, log=print, on_page=None,
            fix_spelling=True):
    """Convert the selected pages (1-based; all by default). on_page(result, index, total) reports progress."""
    results = []
    with pymupdf.open(pdf_path) as doc:
        numbers = [n for n in (pages or range(1, doc.page_count + 1)) if 1 <= n <= doc.page_count]
        for i, n in enumerate(numbers, 1):
            r = convert_page(doc[n - 1], n, profile, lang, allow_cloud, log, fix_spelling)
            log(f"  page {n}: {r.source:<10} confidence {r.confidence:.0%} {r.note}")
            results.append(r)
            if on_page:
                on_page(r, i, len(numbers))
    return results
