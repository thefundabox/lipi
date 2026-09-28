"""Command line: asks what kind of PDF it is (unless given via flags) and converts it to text."""
import argparse
import json
import sys
from pathlib import Path

from . import engines
from .converter import convert
from .profiles import LANGUAGES, PROFILES


def choose(title, options):
    """options: list of (key, label, description). Returns the chosen key."""
    print(f"\n{title}")
    for i, (_, label, desc) in enumerate(options, 1):
        print(f"  {i}. {label:<18} {desc}")
    while True:
        raw = input(f"Choose 1-{len(options)}: ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return options[int(raw) - 1][0]
        print("  Please enter a number from the list.")


def parse_pages(spec):
    pages = set()
    for part in spec.split(","):
        a, _, b = part.partition("-")
        pages.update(range(int(a), int(b or a) + 1))
    return sorted(pages)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="smart_ocr", description="PDF to text with input-aware OCR.")
    ap.add_argument("pdf", nargs="?", help="input PDF")
    ap.add_argument("-t", "--type", choices=PROFILES, help="input type (asked interactively if omitted)")
    ap.add_argument("-l", "--lang", choices=LANGUAGES, help="document language (asked if omitted)")
    ap.add_argument("-o", "--output", help="output .txt path (default: next to the PDF)")
    ap.add_argument("-p", "--pages", help="page selection, e.g. 1-3,7")
    cloud = ap.add_mutually_exclusive_group()
    cloud.add_argument("--allow-cloud", action="store_true", help="allow Claude vision (sends page images to the API)")
    cloud.add_argument("--no-cloud", action="store_true", help="never send pages off this machine")
    ap.add_argument("--no-spellfix", action="store_true", help="don't auto-correct common Hindi OCR slips")
    ap.add_argument("--engines", action="store_true", help="show which OCR engines are available and exit")
    args = ap.parse_args(argv)

    if args.engines:
        for name, status in engines.availability().items():
            print(f"{name:<10} {status}")
        return 0
    if not args.pdf:
        ap.error("a PDF path is required")
    pdf = Path(args.pdf)
    if not pdf.is_file():
        ap.error(f"file not found: {pdf}")

    profile_key = args.type or choose(
        "What kind of PDF is this?", [(p.key, p.label, p.description) for p in PROFILES.values()])
    lang = args.lang or choose(
        "What language is the text in?", [(k, v[0], "") for k, v in LANGUAGES.items()])
    profile = PROFILES[profile_key]

    if args.allow_cloud:
        allow_cloud = True
    elif args.no_cloud or not sys.stdin.isatty():
        allow_cloud = False
    else:
        needs = "claude" in profile.engines or profile.fallback_engine == "claude"
        allow_cloud = needs and input(
            "\nAllow Claude vision for hard pages? Page images are sent to the Anthropic API "
            "(costs per page). [y/N]: ").strip().lower() == "y"
    if profile.engines == ("claude",) and not allow_cloud:
        print("Note: this input type relies on Claude vision; with cloud disabled pages will come back empty.")

    print(f"\nConverting {pdf.name} as '{profile.label}' ({LANGUAGES[lang][0]})...")
    results = convert(pdf, profile, lang, allow_cloud, parse_pages(args.pages) if args.pages else None,
                      fix_spelling=not args.no_spellfix)

    out = Path(args.output) if args.output else pdf.with_suffix(".txt")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n\n".join(f"===== Page {r.number} =====\n{r.text}" for r in results) + "\n", encoding="utf-8")
    report = out.with_suffix(".report.json")
    report.write_text(json.dumps({
        "input": str(pdf), "type": profile.key, "language": lang, "cloud_allowed": allow_cloud,
        "pages": [r.__dict__ for r in results],
    }, indent=2, ensure_ascii=False), encoding="utf-8")

    flagged = [r.number for r in results if r.review]
    print(f"\nText:   {out}\nReport: {report}")
    if flagged:
        print(f"Pages to review: {', '.join(map(str, flagged))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
