# smart_ocr: input-aware PDF to text

You tell it what kind of PDF you have, and it re-tunes itself: render resolution, image cleanup, which OCR engine runs first, and when to escalate to a stronger one.

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
brew install tesseract tesseract-lang     # optional backup engine (not needed for Hindi)
export ANTHROPIC_API_KEY=...              # optional: Claude vision for handwriting and tables
.venv/bin/python -m smart_ocr --engines   # shows which engines are ready
```

The first run for each language downloads its PP-OCRv5 model once (checked against a fixed SHA-256 hash), so it needs internet access that first time.

## Web app (Lipi)

```bash
.venv/bin/python -m smart_ocr.web
```

Then open http://127.0.0.1:8000. Drop in a PDF, pick the document type and language, and watch the pages convert. Review each page next to the original, edit the text, and export to Word, Markdown or plain text. The server only listens on this computer. Uploaded PDFs stay in a temporary folder so the page previews can show, and only the 10 most recent jobs are kept.

## Windows app (for sharing)

GitHub builds a Windows installer automatically; see `.github/workflows/build-windows.yml`. Every push to `main` builds `Lipi.exe` on a Windows machine, bundles the OCR models (so nothing downloads on the user's PC), and runs a self-test on the built app covering English and Hindi OCR, Kruti Dev conversion, Word export and the web page. It then produces two files:

- **`Lipi-Setup.exe`**: a normal installer with a Start-menu and desktop shortcut and an uninstaller. It needs no admin rights.
- **`Lipi-portable-windows.zip`**: unzip it anywhere and run `Lipi.exe`.

Download them from the **Actions** tab (open the latest run, then **Artifacts**). To publish a version on a Releases page, push a tag such as `v0.1.0`; the files are attached to that release.

**For the person installing it:** Windows may show "Windows protected your PC", because the app isn't code-signed. Click **More info → Run anyway**. When Lipi starts, a small black window opens and the browser shows Lipi. Keep that window open while using Lipi, and click **Quit** in Lipi (or close the window) to stop it.

## Command line

```bash
.venv/bin/python -m smart_ocr file.pdf                       # asks input type, language, cloud use
.venv/bin/python -m smart_ocr file.pdf -t phone_photo -l en  # no questions
.venv/bin/python -m smart_ocr notice.pdf -t clean_scan -l hi             # Hindi
.venv/bin/python -m smart_ocr file.pdf -t tables -l en+hi --allow-cloud -p 1-3
```

It writes `file.txt` (with page separators) and `file.report.json` (the engine used and the confidence for each page). Pages that need a human check are listed at the end.

## Input types

| Type | Cleanup | Engine order | Escalates to |
|---|---|---|---|
| `digital` | none | embedded text layer; OCR instead if it's garbled | – |
| `clean_scan` | deskew | RapidOCR → Tesseract | Claude if confidence < 80% |
| `poor_scan` | speck filter, deskew | RapidOCR → Tesseract | Claude if < 85% |
| `phone_photo` | deskew (lighting-robust) | RapidOCR → Tesseract | Claude if < 85% |
| `tables` | deskew; Tesseract in block mode, spacing kept | Claude (Markdown tables) → RapidOCR → Tesseract | – |
| `handwriting` | shadow flattening | Claude only | – |
| `auto` | per page: text layer if it's genuine, otherwise OCR | RapidOCR → Tesseract | Claude if < 80% |

The cleanup column is for the neural engines, RapidOCR and Claude. Tesseract gets its own heavier black-and-white pipeline (upscale, denoise, contrast, adaptive threshold). That pipeline cost the neural model up to 40 points of accuracy on Hindi, which is why each engine family has its own.
Claude is **off unless you allow it**, because it sends page images to the Anthropic API and costs money per page.

## Languages

| Code | Language | Local model |
|---|---|---|
| `en` | English | PP-OCRv5 |
| `hi` | Hindi | PP-OCRv5 Devanagari |
| `en+hi` | English + Hindi on the same page | PP-OCRv5 Devanagari (also reads Latin script) |
| `sa` | Sanskrit | PP-OCRv5 Devanagari (not yet tested) |
| `ur` | Urdu | PP-OCRv5 Arabic script (not yet tested) |

**Broken Hindi text layers.** Many "digital" Hindi PDFs carry text that looks right on screen but extracts as garbage: `राज˳ान` for `राजस्थान` from fonts with broken Unicode mapping, or `jktLFkku` from legacy fonts such as Kruti Dev. The converter checks each text layer against the chosen language. When it's garbled, the converter OCRs the page instead and says so in the report.

**Kruti Dev and DevLys PDFs.** Many government documents are typed in these legacy fonts. Lipi converts their text straight to Unicode Hindi instead of running OCR, so the result is exactly what was typed, typos included. This happens automatically on any typed (non-scanned) page, whatever document type you picked.

**Hindi spelling repair.** On scanned Hindi pages, the OCR model makes a few kinds of mistakes over and over: it drops the र् (निर्धारित → निधरित), mangles conjuncts (द्वारा → द्ारा), and mixes up look-alike letters (ब/व, ष/प, म/भ). Lipi checks each word against a Hindi word list of about 117,000 words. It repairs a word only when a clearly better real word is one or two of these typical slips away. It leaves known words, acronyms (एनसीबी) and anything ambiguous untouched, and lists every change on the page so you can check it. It's on by default; turn it off under **More options** or with `--no-spellfix`.

On a real faded government scan, words read correctly went from 80% to 84.5%. The repair made 14 correct fixes and 1 debatable one, and it changed nothing when given correct text.

The word list comes from the [Leipzig Corpora Collection](https://wortschatz.uni-leipzig.de/en/download) (Hindi news 2020 and Wikipedia 2021, 100K sentences each), licensed CC BY 4.0. It's stored as `smart_ocr/data/hi_words.tsv.gz`.

## Measured accuracy (local engines only, no Claude)

`samples/make_samples.py` and `samples/make_hindi_samples.py` build test PDFs with known text. `samples/evaluate.py` scores them by character accuracy (1 − edit distance ÷ length):

| Sample | English | Hindi | Hindi + English |
|---|---|---|---|
| digital (Hindi ones have a garbled text layer) | 100% | 99.7% | 99.4% |
| clean scan (1.5° tilt) | 100% | 99.7% | 99.4% |
| phone photo (4° tilt, uneven light) | 100% | 99.7% | 98.9% |
| poor scan (faded, noisy, blurred, 3° skew) | 96.6% | 95.6% | 95.4% |

These are synthetic pages set in one typeface, so expect lower numbers on real-world scans, unusual fonts or dense layouts.

## Adding a new input type

Add a `Profile` in `smart_ocr/profiles.py`. The cleanup steps are the functions in `smart_ocr/preprocess.py`.
