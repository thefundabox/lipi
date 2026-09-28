"""Convert Hindi typed in legacy 'Kruti Dev' / 'DevLys' fonts to real Unicode.

Many Indian government PDFs are typed in these fonts. They draw Devanagari shapes over plain
Latin codes, so the PDF's text layer reads 'jktLFkku ljdkj' where the page shows 'राजस्थान सरकार'.
Because the underlying keystrokes are exact, converting them gives a perfect transcription,
better than OCR of the rendered page.

The mapping follows the widely used Kruti Dev 010 layout (DevLys 010 shares it).
"""
import re

# Fonts that use the Kruti Dev 010 keyboard layout (matched against the PDF font name).
KRUTI_FONT = re.compile(r"kruti|devlys", re.I)

# Ordered (legacy, unicode) pairs, applied as sequential global replacements. Order matters:
# multi-key conjuncts must be replaced before the single keys they contain.
# 'f' (the ि sign typed before its consonant) and 'Z' (reph, typed after its syllable) are
# left in place here and repositioned afterwards.
PAIRS = [
    # Word/Office auto-correct turns these keys into curly quotes; the font draws श् / ष् for both.
    ("‘", "'"), ("’", "'"), ("“", '"'), ("”", '"'),
    # Doubled single-quote keys are how quotation marks are typed. Map them to curly quotes,
    # because straight " is the ष् key and would be converted again below.
    ("^^", "“"), ("**", "”"),
    ("ñ", "॰"), ("Q+Z", "QZ+"), ("sas", "sa"), ("aa", "a"), (")Z", "र्द्ध"), ("ZZ", "Z"),
    ("å", "०"), ("ƒ", "१"), ("„", "२"), ("…", "३"), ("†", "४"), ("‡", "५"), ("ˆ", "६"), ("‰", "७"), ("Š", "८"), ("‹", "९"),
    ("¶+", "फ़्"), ("d+", "क़"), ("[+k", "ख़"), ("[+", "ख़्"), ("x+", "ग़"), ("T+", "ज़्"), ("t+", "ज़"),
    ("M+", "ड़"), ("<+", "ढ़"), ("Q+", "फ़"), (";+", "य़"), ("j+", "ऱ"), ("u+", "ऩ"),
    ("Ùk", "त्त"), ("Ù", "त्त्"), ("ä", "क्त"), ("–", "दृ"), ("—", "कृ"), ("é", "न्न"), ("™", "न्न्"),
    ("=kk", "=k"), ("f=k", "f="),
    ("à", "ह्न"), ("á", "ह्य"), ("â", "हृ"), ("ã", "ह्म"), ("ºz", "ह्र"), ("º", "ह्"), ("í", "द्द"),
    ("{k", "क्ष"), ("{", "क्ष्"), ("=", "त्र"), ("«", "त्र्"),
    ("Nî", "छ्य"), ("Vî", "ट्य"), ("Bî", "ठ्य"), ("Mî", "ड्य"), ("<î", "ढ्य"),
    ("|", "द्य"), ("K", "ज्ञ"), ("}", "द्व"), ("J", "श्र"),
    ("Vª", "ट्र"), ("Mª", "ड्र"), ("<ªª", "ढ्र"), ("Nª", "छ्र"), ("Ø", "क्र"), ("Ý", "फ्र"),
    ("nzZ", "र्द्र"), ("æ", "द्र"), ("ç", "प्र"), ("Á", "प्र"), ("xz", "ग्र"), ("#", "रु"), (":", "रू"),
    # independent vowels
    ("v‚", "ऑ"), ("vks", "ओ"), ("vkS", "औ"), ("vk", "आ"), ("v", "अ"),
    ("b±", "ईं"), ("Ã", "ई"), ("bZ", "ई"), ("b", "इ"), ("m", "उ"), ("Å", "ऊ"), (",s", "ऐ"), (",", "ए"), ("_", "ऋ"),
    # consonants (full form = half form + 'k')
    ("ô", "क्क"), ("d", "क"), ("Dk", "क"), ("D", "क्"), ("[k", "ख"), ("[", "ख्"),
    ("x", "ग"), ("Xk", "ग"), ("X", "ग्"), ("Ä", "घ"), ("?k", "घ"), ("?", "घ्"), ("³", "ङ"),
    ("pkS", "चै"), ("p", "च"), ("Pk", "च"), ("P", "च्"), ("N", "छ"), ("t", "ज"), ("Tk", "ज"), ("T", "ज्"),
    (">", "झ"), ("÷", "झ्"), ("¥", "ञ"),
    ("ê", "ट्ट"), ("ë", "ट्ठ"), ("V", "ट"), ("B", "ठ"), ("ì", "ड्ड"), ("ï", "ड्ढ"), ("M", "ड"), ("<", "ढ"), (".k", "ण"), (".", "ण्"),
    ("r", "त"), ("Rk", "त"), ("R", "त्"), ("Fk", "थ"), ("F", "थ्"), (")", "द्ध"), ("n", "द"),
    ("/k", "ध"), ("èk", "ध"), ("/", "ध्"), ("è", "ध्"), ("u", "न"), ("Uk", "न"), ("U", "न्"),
    ("i", "प"), ("Ik", "प"), ("I", "प्"), ("Q", "फ"), ("¶", "फ्"), ("c", "ब"), ("Ck", "ब"), ("C", "ब्"),
    ("Hk", "भ"), ("H", "भ्"), ("e", "म"), ("Ek", "म"), ("E", "म्"),
    (";", "य"), ("¸", "य्"), ("j", "र"), ("y", "ल"), ("Yk", "ल"), ("Y", "ल्"), ("G", "ळ"),
    ("o", "व"), ("Ok", "व"), ("O", "व्"), ("'k", "श"), ("'", "श्"), ('"k', "ष"), ('"', "ष्"),
    ("l", "स"), ("Lk", "स"), ("L", "स्"), ("g", "ह"),
    ("È", "ीं"), ("z", "्र"), ("ª", "्र"),
    ("Ì", "द्द"), ("Í", "ट्ट"), ("Î", "ट्ठ"), ("Ï", "ड्ड"), ("Ñ", "कृ"), ("Ò", "भ"), ("Ó", "्य"), ("Ô", "ड्ढ"),
    ("Ö", "झ्"), ("Ü", "श्"), ("Ú", "क्"), ("Û", "न्"),
    # vowel signs and marks
    ("‚", "ॉ"), ("ks", "ो"), ("kS", "ौ"), ("k", "ा"), ("h", "ी"), ("q", "ु"), ("w", "ू"), ("`", "ृ"),
    ("s", "े"), ("S", "ै"), ("a", "ं"), ("¡", "ँ"), ("±", "Zं"), ("W", "ॅ"), ("•", "ऽ"), ("·", "ऽ"), ("~", "्"), ("+", "़"),
    # punctuation
    # "-" is the full-stop key, so map it before "&" produces hyphens.
    ("%", ":"), ("-", "."), ("&", "-"), ("A", "।"), ("]", ","), ("@", "/"), ("^", "‘"), ("*", "’"),
    ("Þ", "“"), ("ß", "”"), ("¼", "("), ("½", ")"), ("¿", "{"), ("À", "}"),
]

CONSONANT = "कखगघङचछजझञटठडढणतथदधनपफबभमयरलळवशषसहक़ख़ग़ज़ड़ढ़फ़य़ऱऩ"
MATRAS = "ािीुूृेैोौंँःॅॉ़"


def _place_i_sign(text):
    # 'f' precedes the consonant it belongs to; put ि after that consonant...
    text = re.sub(r"f(.)", r"\1ि", text, flags=re.S)
    # ...and past any half consonants that follow (e.g. कि्र -> क्रि).
    prev = None
    while prev != text:
        prev, text = text, re.sub(r"ि्(.)", r"्\1ि", text)
    return text


def _place_reph(text):
    # 'Z' is typed after the syllable; र् belongs before its consonant cluster.
    out = list(text)
    i = 0
    while i < len(out):
        if out[i] != "Z":
            i += 1
            continue
        j = i - 1
        while j >= 0 and out[j] in MATRAS:
            j -= 1
        while j >= 2 and out[j - 1] == "्" and out[j - 2] in CONSONANT:
            j -= 2
        del out[i]
        if j >= 0:
            out[j:j] = ["र", "्"]
            i += 2
    return "".join(out)


def kruti_to_unicode(text):
    for legacy, uni in PAIRS:
        text = text.replace(legacy, uni)
    text = _place_i_sign(text)
    text = _place_reph(text)
    # Typists often key the anusvara/chandrabindu before a vowel sign; Unicode wants it after.
    text = re.sub(r"([ंँ])([ािीुूृेैोौॉ])", r"\2\1", text)
    # ु/ू typed before ्र (गु्रप): Unicode needs the ्र conjunct first (ग्रुप).
    text = re.sub(r"([ुू])्र", r"्र\1", text)
    # ा + ॅ is how the font draws ॉ (as in लॉ, कॉर्डिनेशन).
    text = text.replace("ाॅ", "ॉ")
    # PDF text sometimes splits a vowel sign from its consonant with a space ("स े").
    text = re.sub(r"(?<=[\u0915-\u0939\u093C\u094D]) (?=[\u093E-\u094C\u0901\u0902])", "", text)
    return text


def uses_legacy_font(page):
    return any(KRUTI_FONT.search(f[3]) for f in page.get_fonts())


def page_text(page):
    """Page text with legacy-font spans converted and other fonts (English, digits) left as they are."""
    lines = []
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            parts = [kruti_to_unicode(s["text"]) if KRUTI_FONT.search(s["font"]) else s["text"]
                     for s in line["spans"]]
            lines.append("".join(parts).rstrip())
    return "\n".join(lines).strip()
