import datetime
import json
import math
import re
import unicodedata
from pathlib import Path

from scripts.source import SENTENCE_RE, load_books, verify_source_files  # noqa: F401

TOKEN_RE = re.compile(r"[^\W\d_]+(?:[̀-ͯ]+[^\W\d_]*)*", re.UNICODE)
APOSTROPHES = str.maketrans({c: "'" for c in "’ʼ᾽"})
SENT_RE = re.compile(SENTENCE_RE)
ROOT = Path(__file__).resolve().parent


def tokenize(text):
    return TOKEN_RE.findall(unicodedata.normalize("NFC", (text or "").translate(APOSTROPHES).lower()))


def count_sentences(text):
    return len(SENT_RE.findall(text or ""))


def mattr(tokens, window=50):
    """Moving-average type-token ratio: lexical diversity comparable across lengths."""
    if not tokens:
        return 0.0
    if len(tokens) < window:
        return len(set(tokens)) / len(tokens)
    ratios = [
        len(set(tokens[i:i + window])) / window
        for i in range(len(tokens) - window + 1)
    ]
    return sum(ratios) / len(ratios)


def clean_dir_json_files(path):
    path.mkdir(parents=True, exist_ok=True)
    for json_path in path.glob("*.json"):
        json_path.unlink()


def format_location(book_id, book_abbr, chapter=None, verse_label=None):
    """Sortable location: 01.Gen.001.001; a lettered verse sorts after its
    number (002.035 < 002.035a < 002.036) and a title (0) before verse 1."""
    location = f"{int(book_id):02d}.{book_abbr}"
    if chapter is not None:
        location = f"{location}.{int(chapter):03d}"
    if verse_label is not None:
        match = re.fullmatch(r"(\d+)([a-z]*)", str(verse_label))
        location = f"{location}.{int(match[1]):03d}{match[2]}" if match else f"{location}.000"
    return location


def write_json(path, payload):
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def build(source_path: Path, out_dir: Path):
    books = load_books(source_path)

    data_dir = out_dir / "data"
    lines_dir = out_dir / "lines"
    clean_dir_json_files(data_dir)
    clean_dir_json_files(lines_dir)

    plays = []
    chunks = []
    all_lines = []
    tokens = {}
    tokens2 = {}
    tokens3 = {}
    seen_ids = set()
    verse_id = 0

    for book_id, book in enumerate(books, start=1):
        book_abbr = book["abbr"]
        book_title = book["title"]
        genre = book["genre"]
        verses = book["verses"]
        chapter_numbers = sorted({v["chapter"] for v in verses})
        book_total_words = 0
        book_tokens = []  # ordered token stream for book-level MATTR

        for verse in verses:
            text = verse["text"]
            toks = tokenize(text)
            if not toks:
                raise ValueError(f"Verse without tokens: {verse['canonical_id']}")
            canonical_id = verse["canonical_id"]
            if canonical_id in seen_ids:
                raise ValueError(f"Duplicate canonical id: {canonical_id}")
            seen_ids.add(canonical_id)
            verse_id += 1
            chapter_num = int(verse["chapter"])
            verse_num = int(verse["verse"])
            verse_label = verse.get("verse_label") or str(verse_num)
            chapter_label = verse.get("chapter_label")
            location = format_location(book_id, book_abbr, chapter_num, verse_label)
            total_words = len(toks)
            book_total_words += total_words
            book_tokens.extend(toks)

            chunk_row = {
                "scene_id": verse_id,
                "canonical_id": canonical_id,
                "location": location,
                "play_id": book_id,
                "play_title": book_title,
                "play_abbr": book_abbr,
                "genre": genre,
                "act": chapter_num,
                "scene": verse_num,
                "heading": f"{book_title} {chapter_label or chapter_num}:{verse_label}",
                "total_words": total_words,
                "unique_words": len(set(toks)),
                "num_speeches": 0,
                "num_lines": 1,
                "verse_count": 1,
                "characters_present_count": 0,
                "sentence_count": count_sentences(text),
            }
            line_row = {
                "play_id": book_id,
                "canonical_id": canonical_id,
                "location": location,
                "act": chapter_num,
                "scene": verse_num,
                "line_num": verse_id,
                "speaker": "",
                "text": text,
            }
            if verse_label != str(verse_num):
                chunk_row["scene_label"] = line_row["scene_label"] = verse_label
            if chapter_label:
                chunk_row["act_label"] = line_row["act_label"] = chapter_label
            chunks.append(chunk_row)
            all_lines.append(line_row)

            for n, index in ((1, tokens), (2, tokens2), (3, tokens3)):
                counts = {}
                for idx in range(len(toks) - n + 1):
                    term = " ".join(toks[idx:idx + n])
                    counts[term] = counts.get(term, 0) + 1
                for term, count in counts.items():
                    index.setdefault(term, []).append([verse_id, count])

        plays.append({
            "play_id": book_id,
            "location": format_location(book_id, book_abbr),
            "title": book_title,
            "abbr": book_abbr,
            "genre": genre,
            "first_performance_year": None,
            "num_acts": len(chapter_numbers),
            "num_scenes": len(verses),
            "num_speeches": 0,
            "total_words": book_total_words,
            "total_lines": len(verses),
            "verse_count": len(verses),
            "mattr_50": round(mattr(book_tokens), 3),
        })

    # Additive metric fields (char_count, rarity_sum, hapax_count) per verse.
    # The UI derives ratio metrics at any aggregation level by summing these
    # and dividing by total words.
    corpus_freq = {tok: sum(c for _, c in postings) for tok, postings in tokens.items()}
    corpus_total = sum(corpus_freq.values()) or 1
    tok_rarity = {tok: -math.log10(f / corpus_total) for tok, f in corpus_freq.items()}
    verse_chars, verse_rarity, verse_hapax = {}, {}, {}
    for tok, postings in tokens.items():
        length = len(tok)
        rarity = tok_rarity[tok]
        is_hapax = corpus_freq[tok] == 1
        for vid, count in postings:
            verse_chars[vid] = verse_chars.get(vid, 0) + length * count
            verse_rarity[vid] = verse_rarity.get(vid, 0.0) + rarity * count
            if is_hapax:
                verse_hapax[vid] = verse_hapax.get(vid, 0) + count
    for chunk_row in chunks:
        vid = chunk_row["scene_id"]
        chunk_row["char_count"] = verse_chars.get(vid, 0)
        chunk_row["rarity_sum"] = round(verse_rarity.get(vid, 0.0), 3)
        chunk_row["hapax_count"] = verse_hapax.get(vid, 0)

    instance_meta = json.loads((ROOT / "instance-meta.json").read_text(encoding="utf-8"))
    instance_payload = {
        "schema": 1,
        **instance_meta,
        "updated": datetime.date.today().isoformat(),
        "stats": {
            "texts": len(plays),
            "text_label": instance_meta.get("text_label", "books"),
            "segments": len(chunks),
            "segment_label": instance_meta.get("segment_label", "verses"),
            "words": sum(p["total_words"] for p in plays),
            "distinct_words": len(tokens),
            "commentaries": 0,
            "comments": 0,
        },
    }
    instance_payload.pop("text_label", None)
    instance_payload.pop("segment_label", None)
    (out_dir / "instance.json").write_text(
        json.dumps(instance_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    write_json(data_dir / "plays.json", plays)
    write_json(data_dir / "chunks.json", chunks)
    write_json(data_dir / "characters.json", [])
    write_json(data_dir / "tokens.json", tokens)
    write_json(data_dir / "tokens2.json", tokens2)
    write_json(data_dir / "tokens3.json", tokens3)
    write_json(data_dir / "tokens_char.json", {})
    write_json(data_dir / "tokens_char2.json", {})
    write_json(data_dir / "tokens_char3.json", {})
    write_json(data_dir / "commentary_interest.json", {
        "metadata": {"commentators": []},
        "summary": {"note": "No commentary is attached to this edition's numbering yet.",
                    "total_commentators": 0, "verses_with_interest": 0, "total_interest": 0},
    })
    write_json(data_dir / "character_name_filter_config.json", {
        "enabled": False,
        "notes": ["Disabled: this corpus does not yet have a reviewed proper-name list."],
        "global_additions": [],
        "global_removals": [],
        "play_additions": {},
        "play_removals": {},
    })
    write_json(lines_dir / "all_lines.json", all_lines)

    return {
        "book_count": len(plays),
        "verse_count": len(chunks),
        "word_count": instance_payload["stats"]["words"],
        "distinct_words": len(tokens),
    }


if __name__ == "__main__":
    source_path = ROOT / "source_text"
    out_dir = ROOT / "docs"
    print(f"Building from {source_path} -> {out_dir}")
    result = build(source_path, out_dir)
    print(
        "Done: "
        f"{result['book_count']} books, {result['verse_count']} verses, "
        f"{result['word_count']} words, {result['distinct_words']} distinct words"
    )
