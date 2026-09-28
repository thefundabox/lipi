"""Dictionary-based correction of Hindi OCR output.

The Devanagari OCR model makes a handful of systematic mistakes: it drops the reph (निर्धारित ->
निधरित), mangles conjuncts (द्वारा -> द्ारा), and confuses look-alike letters (ब/व, ष/प, म/भ).
For each word that isn't a known Hindi word, this module tries small edits (with those known
confusions counting as cheaper) and replaces the word only when a clearly better, reasonably
common dictionary word is found. Known words, names that happen to be known, numbers and Latin
text are never touched.

Word list: Leipzig Corpora Collection (Hindi news 2020 + Wikipedia 2021), CC BY 4.0.
"""
import gzip
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

WORDS_FILE = Path(__file__).parent / "data" / "hi_words.tsv.gz"

CONSONANTS = "कखगघङचछजझञटठडढणतथदधनपफबभमयरलवशषसह"
SIGNS = "ािीुूृेैोौंँः्"
ALPHABET = CONSONANTS + SIGNS + "अआइईउऊएऐओऔ"
LETTERS = CONSONANTS + "अआइईउऊएऐओऔ"

# Look-alike substitutions the model makes, as (wrong, right).
CONFUSIONS = [
    ("व", "ब"), ("ब", "व"), ("प", "ष"), ("ष", "प"), ("म", "भ"), ("भ", "म"), ("र", "स्"),
    ("घ", "ध"), ("ध", "घ"), ("द्र", "द्ध"), ("ां", "ों"),
    ("ि", "ी"), ("ी", "ि"), ("ु", "ू"), ("ू", "ु"), ("्", "्र"),
]
# Insertions the model needs most often: the reph र्, the ्र of क्र/प्र, the व of द्व, and ं.
INSERTS = ["र्", "्र", "्व", "व", "ं", "्"]
VOWEL_SIGNS = "ािीुूेैोौं"

# Candidates are tried in tiers: one typical slip, then two slips, then (long words only) any single
# edit. The first tier with a clear winner decides, and frequency only ranks words within a tier,
# so a rare but right word (प्रेषित) doesn't lose to a common unrelated one (प्रेरित).
MIN_FREQ = (5, 3, 200)  # minimum corpus frequency of a replacement, per tier
MIN_RATIO = 2.0         # the winner must be this many times more frequent than the runner-up
MIN_LEN_ANY_EDIT = 5    # words shorter than this only get typical-slip corrections
# Hindi spellings of acronyms (एनसीबी, एएनटीएफ, एनकॉर्ड) aren't in any dictionary; leave them alone.
ACRONYM = re.compile(r"^(ए|एन|एफ|एस|एम|एल|आर|आई|ओ)[^ािीुूृेैोौ]?")

TOKEN = re.compile(r"[ऀ-ॣॱ-ॿ]+")


@lru_cache(maxsize=1)
def _lexicon():
    freq = {}
    with gzip.open(WORDS_FILE, "rt", encoding="utf-8") as f:
        for line in f:
            w, c = line.rstrip("\n").split("\t")
            freq[w] = int(c)
    return freq


def _edits(w, alphabet):
    splits = [(w[:i], w[i:]) for i in range(len(w) + 1)]
    out = {a + b[1:] for a, b in splits if b and b[0] in alphabet}           # delete
    out |= {a + c + b[1:] for a, b in splits if b for c in alphabet}         # substitute
    out |= {a + c + b for a, b in splits for c in alphabet}                  # insert
    return out


def _slips(w):
    """The model's typical mistakes: look-alike letters, missing र्/्र/्व/ं, dropped or extra vowel signs."""
    out = set()
    for wrong, right in CONFUSIONS:
        for m in re.finditer(re.escape(wrong), w):
            out.add(w[:m.start()] + right + w[m.end():])
    for i in range(1, len(w) + 1):
        for ins in INSERTS + list(VOWEL_SIGNS):
            out.add(w[:i] + ins + w[i:])
    out |= {w[:i] + "र" + w[i:] for i in range(len(w)) if w[i] == "्"}         # भा्गव -> भार्गव
    out |= {w[:i] + w[i + 1:] for i in range(len(w)) if w[i] == "ा"}             # भाषणा -> भाषण
    if w[0] in SIGNS:                                  # word lost its first letter: ्वारा -> द्वारा
        out |= {c + w for c in CONSONANTS}
    out.discard(w)
    return out


def _tiers(w):
    slips = _slips(w)
    yield 0, slips
    yield 1, set().union(*(_slips(c) for c in slips))
    if len(w) >= MIN_LEN_ANY_EDIT:
        # Any single substitution or insertion, never at the first letter and never a deletion:
        # dictionary gaps (आसूचना) must not be trimmed into different common words (सूचना).
        # Letters only: vowel-sign swaps here would just "standardise" spellings (डेशबोर्ड -> डैशबोर्ड).
        yield 2, {c for c in _edits(w, LETTERS) if len(c) >= len(w) and c[0] == w[0]}


def correct_word(w):
    # A trailing ः is used as a colon in headings (विभागः–); correct the word, keep the mark.
    if w.endswith("ः"):
        return correct_word(w[:-1]) + "ः"
    lex = _lexicon()
    if len(w) < 3 or w in lex or ACRONYM.match(w):
        return w
    short = len(w) <= 3  # many real words sit one slip away from a short one: be stricter
    for tier, cands in _tiers(w):
        if short and tier > 0:
            break
        min_freq = 50 if short else MIN_FREQ[tier]
        found = sorted(((lex[c], c) for c in cands
                        if lex.get(c, 0) >= min_freq and len(c) >= len(w) - 1), reverse=True)
        if not found:
            continue
        if len(found) > 1 and found[0][0] < MIN_RATIO * found[1][0]:
            return w  # ambiguous: leave it for the reviewer rather than guess
        return found[0][1]
    return w


def correct_with_log(text):
    """Correct unknown Hindi words; everything else is left exactly as it was.

    Returns (text, [(wrong, fixed), ...]).
    """
    fixes = []

    def fix(m):
        w = m.group(0)
        c = correct_word(w)
        if c != w:
            fixes.append((w, c))
        return c

    return TOKEN.sub(fix, unicodedata.normalize("NFC", text)), fixes


def correct(text):
    return correct_with_log(text)[0]
