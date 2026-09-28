"""Desktop launcher used by the packaged app (Lipi.exe): start Lipi and open it in the browser.

    Lipi.exe                         start Lipi (or just open the browser if it's already running)
    Lipi.exe --selftest <pdf>        check the build: OCR, Hindi, Kruti Dev, Word export; exit 0/1
"""
import json
import sys
import threading
import urllib.request
import webbrowser

PORT = 8765
URL = f"http://127.0.0.1:{PORT}"


def _already_running():
    try:
        with urllib.request.urlopen(URL + "/api/options", timeout=1) as r:
            return "types" in json.load(r)
    except Exception:
        return False


def selftest(pdf_path):
    """Exercise every bundled part without a browser. Used by the build pipeline."""
    import difflib
    import io
    import os

    from docx import Document

    from . import hindi_spell
    from .converter import convert
    from .legacy_fonts import kruti_to_unicode
    from .profiles import PROFILES

    import rapidocr
    models = os.path.join(os.path.dirname(rapidocr.__file__), "models")
    checks = []

    def check(name, ok, detail=""):
        checks.append(ok)
        print(f"[{'PASS' if ok else 'FAIL'}] {name} {detail}")

    needed = ["devanagari_PP-OCRv5_rec_mobile.onnx", "ch_PP-OCRv5_rec_mobile.onnx"]
    present = os.listdir(models) if os.path.isdir(models) else []
    check("OCR models bundled", all(n in present for n in needed), str(sorted(present)))

    expected = {1: "The Rajasthan Public Service Commission conducts the State and Subordinate Services",
                2: "राजस्थान लोक सेवा आयोग राज्य एवं अधीनस्थ सेवा संयुक्त प्रतियोगी परीक्षा का आयोजन करता है।"}
    for page, lang in [(1, "en"), (2, "hi")]:
        [r] = convert(pdf_path, PROFILES["clean_scan"], lang, pages=[page], log=lambda *_: None)
        first = r.text.splitlines()[0] if r.text else ""
        ratio = difflib.SequenceMatcher(None, expected[page], first).ratio()
        check(f"OCR page {page} ({lang})", ratio > 0.9, f"{ratio:.0%}")

    check("Kruti Dev conversion", kruti_to_unicode("jktLFkku ljdkj") == "राजस्थान सरकार")
    check("Hindi spelling repair", hindi_spell.correct("द्ारा") == "द्वारा")

    doc = Document()
    doc.add_paragraph("राजस्थान")
    buf = io.BytesIO()
    doc.save(buf)
    check("Word export", buf.tell() > 1000)

    from .web import app
    client = app.test_client()
    check("Web page served", client.get("/").status_code == 200 and client.get("/api/options").status_code == 200)
    return 0 if all(checks) else 1


def main():
    # Windows consoles default to a legacy code page that can't print Hindi.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

    if len(sys.argv) >= 3 and sys.argv[1] == "--selftest":
        sys.exit(selftest(sys.argv[2]))

    if _already_running():
        webbrowser.open(URL)
        return

    from .web import app
    print("Lipi is running. Your browser will open at", URL)
    print("Keep this window open while you use Lipi. Close it, or click Quit in Lipi, to stop.")
    threading.Timer(1.5, lambda: webbrowser.open(URL)).start()
    app.run(host="127.0.0.1", port=PORT, threaded=True)


if __name__ == "__main__":
    main()
