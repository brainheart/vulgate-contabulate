"""Clementine Vulgate loader (Tweedale / VulSearch text, USFX from open-bibles).

Books keep the Clementine order of the source file, its own Latin headings,
and its own chapter/verse numbering: Psalms follow the Greek/Latin count
(Ps 22 = "Dominus regit me"), psalm titles are verse 1, Esther 10:4-16:24,
Daniel 3:24-100, 13 (Susanna) and 14 (Bel), and Baruch 6 (Letter of Jeremiah)
stay where Jerome and the 1592 edition put them. Canonical IDs use the same
OSIS-style book codes as the sibling Bible instances; only the numbering is
the Vulgate's.
"""
import hashlib
import json
import re
import unicodedata

USFM_TO_OSIS = {
    "GEN": "Gen", "EXO": "Exod", "LEV": "Lev", "NUM": "Num", "DEU": "Deut", "JOS": "Josh",
    "JDG": "Judg", "RUT": "Ruth", "1SA": "1Sam", "2SA": "2Sam", "1KI": "1Kgs", "2KI": "2Kgs",
    "1CH": "1Chr", "2CH": "2Chr", "EZR": "Ezra", "NEH": "Neh", "TOB": "Tob", "JDT": "Jdt",
    "EST": "Esth", "JOB": "Job", "PSA": "Ps", "PRO": "Prov", "ECC": "Eccl", "SNG": "Song",
    "WIS": "Wis", "SIR": "Sir", "ISA": "Isa", "JER": "Jer", "LAM": "Lam", "BAR": "Bar",
    "EZK": "Ezek", "DAN": "Dan", "HOS": "Hos", "JOL": "Joel", "AMO": "Amos", "OBA": "Obad",
    "JON": "Jonah", "MIC": "Mic", "NAM": "Nah", "HAB": "Hab", "ZEP": "Zeph", "HAG": "Hag",
    "ZEC": "Zech", "MAL": "Mal", "1MA": "1Macc", "2MA": "2Macc", "MAT": "Matt", "MRK": "Mark",
    "LUK": "Luke", "JHN": "John", "ACT": "Acts", "ROM": "Rom", "1CO": "1Cor", "2CO": "2Cor",
    "GAL": "Gal", "EPH": "Eph", "PHP": "Phil", "COL": "Col", "1TH": "1Thess", "2TH": "2Thess",
    "1TI": "1Tim", "2TI": "2Tim", "TIT": "Titus", "PHM": "Phlm", "HEB": "Heb", "JAS": "Jas",
    "1PE": "1Pet", "2PE": "2Pet", "1JN": "1John", "2JN": "2John", "3JN": "3John", "JUD": "Jude",
    "REV": "Rev",
}
NEW_TESTAMENT = set(list(USFM_TO_OSIS.values())[list(USFM_TO_OSIS).index("MAT"):])
SOURCE_FILE = "lat-clementine.usfx.xml"
# The transcription folds two unnumbered prologues into verse 1 behind a
# "Prologus" marker. They become their own "prol." row (verse 0) so that 1:1
# is the verse the edition numbers 1:1.
PROLOGUE_SPLIT = {"Sir": "Omnis sapientia a Domino", "Lam": "Aleph Quomodo"}
# Latin ";" is a clause break, not a question mark as in Greek.
SENTENCE_RE = r"[.!?]+"


def verify_source_files(directory):
    provenance = json.loads((directory / "provenance.json").read_text())
    for name, info in provenance["files"].items():
        if hashlib.sha256((directory / name).read_bytes()).hexdigest() != info["sha256"]:
            raise ValueError(f"Source checksum mismatch: {directory / name}")
    return provenance


def clean_text(raw):
    text = re.sub(r"<[^>]+>", "", raw)
    text = unicodedata.normalize("NFC", re.sub(r"\s+", " ", text)).strip()
    # VulSearch prints French-style spaces before : ; ? ! -- close them up.
    return re.sub(r"\s+([:;?!])", r"\1", text)


def load_books(source_dir):
    verify_source_files(source_dir)
    src = (source_dir / SOURCE_FILE).read_text(encoding="utf-8")
    books = []
    for match in re.finditer(r'<book id="(\w+)">(.*?)</book>', src, re.S):
        usfm, body = match.groups()
        abbr = USFM_TO_OSIS[usfm]
        heading = re.search(r"<h>(.*?)</h>", body)
        title = unicodedata.normalize("NFC", heading.group(1).strip())
        body = re.sub(r"<h>.*?</h>", "", body)
        verses, seen, previous, chapter = [], set(), (0, 0), 0
        for tok in re.finditer(r'<c id="(\d+)"/>|<v id="(\d+)"/>(.*?)<ve/>', body, re.S):
            if tok.group(1):
                chapter = int(tok.group(1))
                continue
            verse = int(tok.group(2))
            canonical_id = f"{abbr}.{chapter}.{verse}"
            if canonical_id in seen or (chapter, verse) <= previous:
                raise ValueError(f"Duplicate or unordered verse: {canonical_id}")
            seen.add(canonical_id)
            previous = (chapter, verse)
            text = clean_text(tok.group(3))
            if not text:
                raise ValueError(f"Empty source verse: {canonical_id}")
            if text.startswith("Prologus "):
                prologue, sep, rest = text[len("Prologus "):].partition(PROLOGUE_SPLIT[abbr])
                if not sep or (chapter, verse) != (1, 1):
                    raise ValueError(f"Unexpected prologue in {canonical_id}")
                verses.append({"canonical_id": f"{abbr}.1.0", "chapter": 1, "verse": 0,
                               "verse_label": "prol.", "text": prologue.strip()})
                text = sep + rest
            verses.append({"canonical_id": canonical_id, "chapter": chapter, "verse": verse,
                           "verse_label": str(verse), "text": text})
        books.append({
            "abbr": abbr,
            "title": title,
            "genre": "Novum Testamentum" if abbr in NEW_TESTAMENT else "Vetus Testamentum",
            "verses": verses,
        })
    return books
