"""Input-type profiles: each one recalibrates rendering, preprocessing and engine choice."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Profile:
    key: str
    label: str
    description: str
    dpi: int = 300
    use_text_layer: bool = False      # trust the PDF's embedded text when present
    # Cleanup steps (from preprocess.STEPS) per engine family. Tesseract wants crisp black-on-white
    # pages; neural engines (RapidOCR, Claude) read better from lightly cleaned greyscale, and
    # binarizing thin Devanagari strokes cost them up to 40 points of accuracy in testing.
    preprocess: tuple = ()
    neural_preprocess: tuple = ("grayscale", "deskew")
    engines: tuple = ("rapidocr", "tesseract")  # tried in order; first available wins
    fallback_engine: str | None = None  # used when confidence < min_confidence
    min_confidence: float = 0.80
    tesseract_psm: int = 3            # 3 = auto layout, 6 = uniform block (tables), 4 = columns
    tesseract_extra: str = ""
    claude_hint: str = ""             # extra instruction when Claude vision is used


PROFILES: dict[str, Profile] = {p.key: p for p in [
    Profile(
        key="digital",
        label="Digital PDF",
        description="Exported from Word/browser; text is selectable. No OCR needed.",
        use_text_layer=True,
        preprocess=("grayscale",),
    ),
    Profile(
        key="clean_scan",
        label="Clean scan",
        description="Printed pages scanned on a flatbed/office scanner, good contrast.",
        dpi=300,
        preprocess=("grayscale", "deskew", "otsu"),
        fallback_engine="claude",
    ),
    Profile(
        key="poor_scan",
        label="Poor / old scan",
        description="Faded, noisy, low-resolution, photocopied or faxed pages.",
        dpi=300,
        preprocess=("grayscale", "upscale", "denoise", "clahe", "deskew", "adaptive_threshold", "remove_specks"),
        neural_preprocess=("grayscale", "median", "deskew"),
        fallback_engine="claude",
        min_confidence=0.85,
    ),
    Profile(
        key="phone_photo",
        label="Phone photo",
        description="Pages photographed with a phone: uneven light, shadows, slight tilt.",
        dpi=300,
        preprocess=("grayscale", "remove_shadows", "denoise", "deskew", "adaptive_threshold"),
        fallback_engine="claude",
        min_confidence=0.85,
    ),
    Profile(
        key="tables",
        label="Tables / forms",
        description="Invoices, forms, statements, mark-sheets with rows and columns.",
        dpi=350,
        preprocess=("grayscale", "deskew", "otsu"),
        tesseract_psm=6,
        tesseract_extra="-c preserve_interword_spaces=1",
        engines=("claude", "rapidocr", "tesseract"),
        claude_hint="Reproduce every table as a GitHub-flavored Markdown table, keeping rows and columns aligned. "
                    "Render form fields as 'Label: value'.",
    ),
    Profile(
        key="handwriting",
        label="Handwritten",
        description="Handwritten notes, letters or annotated pages.",
        dpi=300,
        neural_preprocess=("grayscale", "remove_shadows"),
        engines=("claude",),  # local OCR engines are unreliable on handwriting
        claude_hint="The page is handwritten. Transcribe exactly what is written; mark illegible words as [illegible].",
    ),
    Profile(
        key="auto",
        label="Mixed / not sure",
        description="Detects each page: uses the text layer where present, OCR elsewhere.",
        use_text_layer=True,
        preprocess=("grayscale", "deskew", "otsu"),
        fallback_engine="claude",
    ),
]}

# Tesseract language codes (install packs with: brew install tesseract-lang)
LANGUAGES: dict[str, tuple[str, str]] = {
    "en": ("English", "eng"),
    "hi": ("Hindi", "hin"),
    "en+hi": ("English + Hindi", "eng+hin"),
    "sa": ("Sanskrit", "san"),
    "ur": ("Urdu", "urd"),
}

# RapidOCR recognition model per language. The Devanagari model also reads Latin text,
# so it serves mixed Hindi-English pages.
RAPIDOCR_LANGS = {"en": "CH", "hi": "DEVANAGARI", "en+hi": "DEVANAGARI", "sa": "DEVANAGARI", "ur": "ARABIC"}

# Unicode blocks a genuine text layer in each language should mostly consist of.
SCRIPTS = {"en": "latin", "hi": "devanagari", "en+hi": "devanagari", "sa": "devanagari", "ur": "arabic"}
