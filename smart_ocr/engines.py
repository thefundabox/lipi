"""OCR engines behind one interface: ocr(image, lang, profile) -> (text, confidence 0..1)."""
import base64
import os
import shutil

import cv2

from .profiles import LANGUAGES, RAPIDOCR_LANGS


class EngineUnavailable(Exception):
    pass


class TesseractEngine:
    name = "tesseract"

    def __init__(self):
        if not shutil.which("tesseract"):
            raise EngineUnavailable("tesseract binary not found (install: brew install tesseract tesseract-lang)")
        import pytesseract
        self.pt = pytesseract

    def supports(self, lang):
        installed = set(self.pt.get_languages(config=""))
        return all(code in installed for code in LANGUAGES[lang][1].split("+"))

    def ocr(self, img, lang, profile):
        config = f"--oem 1 --psm {profile.tesseract_psm} {profile.tesseract_extra}".strip()
        code = LANGUAGES[lang][1]
        data = self.pt.image_to_data(img, lang=code, config=config, output_type=self.pt.Output.DICT)
        confs = [float(c) for c, t in zip(data["conf"], data["text"]) if t.strip() and float(c) >= 0]
        text = self.pt.image_to_string(img, lang=code, config=config)
        return text.strip(), (sum(confs) / len(confs) / 100) if confs else 0.0


class RapidOCREngine:
    """PaddleOCR PP-OCRv5 models via ONNX Runtime; pure pip install, strong on photos and varied fonts."""
    name = "rapidocr"

    def __init__(self):
        try:
            import rapidocr
        except ImportError as e:
            raise EngineUnavailable("pip install rapidocr") from e
        self.rapidocr = rapidocr
        self.engines = {}  # one engine per recognition model, created on first use

    def supports(self, lang):
        return lang in RAPIDOCR_LANGS

    def _engine(self, lang):
        model = RAPIDOCR_LANGS[lang]
        if model not in self.engines:
            r = self.rapidocr
            self.engines[model] = r.RapidOCR(params={
                # Cap detection size: uncapped 400-DPI pages crash ONNX Runtime.
                # Recognition still reads full-resolution crops.
                "Det.limit_side_len": 2048,
                "Det.limit_type": "max",
                # Pages are already deskewed; the 180-degree classifier flips short words (e.g. "होंगे।").
                "Global.use_cls": False,
                "Rec.ocr_version": r.OCRVersion.PPOCRV5,
                "Rec.model_type": r.ModelType.MOBILE,
                "Rec.lang_type": r.LangRec[model],
            })
        return self.engines[model]

    def ocr(self, img, lang, profile):
        if img.ndim == 2:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        out = self._engine(lang)(img)
        if out.txts is None or not len(out.txts):
            return "", 0.0
        result = list(zip(out.boxes.tolist(), out.txts, out.scores))
        return _lines_from_boxes(result), sum(float(r[2]) for r in result) / len(result)


def _lines_from_boxes(result):
    """Group detected boxes into reading-order lines (top-to-bottom, left-to-right).

    Boxes are quadrilaterals (top-left, top-right, bottom-right, bottom-left). Using the midpoint
    of the left edge and the true edge height keeps tilted lines apart, where axis-aligned
    bounding rectangles of neighbouring tilted lines overlap.
    """
    items = []
    for (tl, tr, br, bl), text, _ in result:
        items.append(((tl[1] + bl[1]) / 2, abs(bl[1] - tl[1]), (tl[0] + bl[0]) / 2, text))
    items.sort(key=lambda t: (t[0], t[2]))
    # Compare against a typical line height so one oversized noise box can't swallow the page.
    line_h = sorted(h for _, h, _, _ in items)[len(items) // 2]
    lines, current, cur_y = [], [], None
    for y, _, x, text in items:
        if current and y - cur_y > line_h * 0.6:
            lines.append(current)
            current = []
        if not current:
            cur_y = y
        current.append((x, text))
    if current:
        lines.append(current)
    return "\n".join(" ".join(t for _, t in sorted(line)) for line in lines)


class ClaudeVisionEngine:
    """Claude reads the page image. Best for handwriting, complex tables and badly degraded pages."""
    name = "claude"
    MODEL = "claude-opus-5"

    def __init__(self):
        try:
            import anthropic
        except ImportError as e:
            raise EngineUnavailable("pip install anthropic") from e
        if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")
                or os.path.isdir(os.path.expanduser("~/.config/anthropic"))):
            raise EngineUnavailable("no Anthropic credentials (set ANTHROPIC_API_KEY or run `ant auth login`)")
        self.client = anthropic.Anthropic()

    def supports(self, lang):
        return True

    def ocr(self, img, lang, profile):
        ok, png = cv2.imencode(".png", img)
        if not ok:
            raise RuntimeError("could not encode page image")
        prompt = (
            f"Transcribe all text on this document page. Expected language: {LANGUAGES[lang][0]}. "
            "Output only the transcription, preserving reading order, paragraphs and line breaks. "
            "Do not summarize, translate, correct spelling, or add commentary. "
            "If a word is unreadable write [illegible] rather than guessing. "
            + profile.claude_hint
        )
        with self.client.beta.messages.stream(
            model=self.MODEL,
            max_tokens=32000,
            thinking={"type": "adaptive"},
            output_config={"effort": "medium"},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            messages=[{"role": "user", "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/png",
                                             "data": base64.standard_b64encode(png.tobytes()).decode()}},
                {"type": "text", "text": prompt},
            ]}],
        ) as stream:
            msg = stream.get_final_message()
        if msg.stop_reason == "refusal":
            return "", 0.0
        text = "".join(b.text for b in msg.content if b.type == "text").strip()
        # Claude gives no per-word confidence; score by share of words not marked illegible.
        words = text.split()
        illegible = text.count("[illegible]")
        return text, (1 - illegible / len(words)) if words else 0.0


ENGINE_CLASSES = {c.name: c for c in (TesseractEngine, RapidOCREngine, ClaudeVisionEngine)}
_cache: dict[str, object] = {}


def get(name):
    """Return an engine instance, or raise EngineUnavailable (cached either way)."""
    if name not in _cache:
        try:
            _cache[name] = ENGINE_CLASSES[name]()
        except EngineUnavailable as e:
            _cache[name] = e
    result = _cache[name]
    if isinstance(result, EngineUnavailable):
        raise result
    return result


def availability():
    status = {}
    for name in ENGINE_CLASSES:
        try:
            get(name)
            status[name] = "available"
        except EngineUnavailable as e:
            status[name] = f"unavailable: {e}"
    return status
