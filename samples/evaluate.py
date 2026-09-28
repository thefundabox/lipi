"""Run each sample through its matching profile and report character accuracy vs ground truth."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from smart_ocr.converter import convert
from smart_ocr.profiles import PROFILES

here = Path(__file__).parent


def char_accuracy(ref, hyp):
    """1 - (Levenshtein edits / reference length), the standard OCR character accuracy."""
    prev = list(range(len(hyp) + 1))
    for i, a in enumerate(ref, 1):
        cur = [i]
        for j, b in enumerate(hyp, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (a != b)))
        prev = cur
    return max(0.0, 1 - prev[-1] / len(ref))


def norm(s):
    return re.sub(r"\s+", " ", s).strip()


# (sample pdf, input type, language, ground truth file)
CASES = [
    ("digital.pdf", "digital", "en", "ground_truth.txt"),
    ("clean_scan.pdf", "clean_scan", "en", "ground_truth.txt"),
    ("poor_scan.pdf", "poor_scan", "en", "ground_truth.txt"),
    ("phone_photo.pdf", "phone_photo", "en", "ground_truth.txt"),
] + [
    (f"{name}_{kind}.pdf", kind, lang, f"ground_truth_{name}.txt")
    for name, lang in [("hindi", "hi"), ("mixed", "en+hi")]
    for kind in ["digital", "clean_scan", "poor_scan", "phone_photo"]
]

only = sys.argv[1:]
for pdf, kind, lang, gt in CASES:
    if only and not any(o in pdf for o in only):
        continue
    truth = norm((here / gt).read_text())
    [r] = convert(here / pdf, PROFILES[kind], lang, allow_cloud=False, log=lambda *_: None)
    acc = char_accuracy(truth, norm(r.text))
    print(f"{pdf:<24} {kind:<12} {lang:<6} engine={r.source:<10} conf={r.confidence:.0%}  "
          f"char-accuracy={acc:.1%}  {r.note}", flush=True)
