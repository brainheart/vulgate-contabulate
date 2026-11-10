"""English reading aids from Wiktionary: a dictionary form and gloss per word.

Copy this file into an instance as `scripts/glossary.py` and set LANGUAGE and
EXTRACT_SHA256. It reads `source_text/lexicon/wiktionary-extract.json`, the
compact extract that `kaikki_extract.py` (in the contabulate-instances skill)
cuts from kaikki.org's Wiktionary dump, and builds the instance's
`docs/data/glossary.json`.

Unlike an analysis of the text itself, a dictionary cannot tell which word a
spelling is in a given place: Latin "est" is "is" far more often than "eats".
Each written form is therefore assigned to one dictionary word, the candidate
that accounts for most of this text (estimated over all its spellings, with a
form that is itself a headword preferred and a mere variant spelling
distrusted). Every occurrence in a spelling shared with another word is
counted as ambiguous (`amb`), which the page reports.
"""
import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

LANGUAGE = "la"
EXTRACT_FILE = "wiktionary-extract.json"
EXTRACT_SHA256 = "6fbd6f1233872c9b54ebd22c6a3faf8889426efbc0457174bb62f443bb41e162"
ENCLITICS = {"la": ("que", "ne", "ve")}
POS_LABELS = {
    "noun": "noun", "verb": "verb", "adj": "adjective", "adv": "adverb", "prep": "preposition",
    "conj": "conjunction", "pron": "pronoun", "name": "name", "num": "numeral", "det": "determiner",
    "particle": "particle", "intj": "interjection", "article": "article", "postp": "postposition",
    "phrase": "phrase", "prep_phrase": "phrase", "contraction": "contraction",
}
# Words too common in glosses to say what a lemma means. They are indexed
# only for lemmas whose glosses contain nothing else.
STOP_WORDS = frozenset("""
a an the and or of to in on for with by from at as is are was were be been it its he she they them
their his her you your we our us i my me him who whom which that this those these then so but not
no will would shall should may might can could do does did have has had o if when what there than
am one esp etc something someone
""".split())


def normalize(word, language=LANGUAGE):
    """Lookup spelling; must match kaikki_extract.normalize."""
    text = unicodedata.normalize("NFD", word.lower())
    if language == "la":
        text = "".join(c for c in text if not unicodedata.combining(c))
        text = text.replace("j", "i").replace("æ", "ae").replace("œ", "oe")
    return unicodedata.normalize("NFC", text)


def candidates(token, language=LANGUAGE):
    keys = [normalize(token, language)]
    for enclitic in ENCLITICS.get(language, ()):
        if keys[0].endswith(enclitic) and len(keys[0]) > len(enclitic) + 1:
            keys.append(keys[0][: -len(enclitic)])
    return keys


def load_extract(path):
    data = Path(path).read_bytes()
    if hashlib.sha256(data).hexdigest() != EXTRACT_SHA256:
        raise ValueError(f"Source checksum mismatch: {path}")
    return json.loads(data)


def gloss_words(gloss):
    plain = re.sub(r"\([^)]*\)", " ", gloss)
    words = [w for w in re.findall(r"[a-z]+(?:'[a-z]+)?", plain.lower()) if w not in STOP_WORDS]
    return words or re.findall(r"[a-z]+(?:'[a-z]+)?", gloss.lower())


FIRST_SENSE = 1000  # a word in the first sense outranks any later-sense match


def word_index(glosses, count, limit=16):
    """English words weighted by the lemma's frequency. Wiktionary lists many
    senses; a frequent word's fifth sense must not outrank a rarer word's
    first, so first-sense words are weighted a thousandfold."""
    weights = {}
    for position, gloss in enumerate(glosses):
        for word in gloss_words(gloss):
            weight = max(1, count) * (FIRST_SENSE if position == 0 else 1)
            weights[word] = max(weights.get(word, 0), weight)
    return [[w, c] for w, c in sorted(weights.items(), key=lambda wc: (-wc[1], wc[0]))[:limit]]


def short_definition(glosses, limit=70, cap=110):
    """The first sense, with the second where both are brief. Wiktionary
    sometimes explains at length before it translates; a long gloss is cut
    at a word boundary."""
    if not glosses:
        return ""
    text = glosses[0]
    if len(glosses) > 1 and len(text) + len(glosses[1]) + 2 <= limit:
        text += "; " + glosses[1]
    if len(text) > cap:
        text = text[:cap].rsplit(" ", 1)[0].rstrip(",;:") + " …"
    return text


KIND_TRUST = {"self": 3.0, "form": 1.0, "alt": 0.05}
# The search index is lower-cased, so a spelling shared by a common word and
# a proper name ("amor" and "Amor") is more often the common word.
NAME_TRUST = 0.5


def trust(lemma, kind):
    return KIND_TRUST[kind] * (NAME_TRUST if lemma[1] == "name" else 1.0)


def lookup(token, extract):
    """Candidate dictionary words for a written form: {(lemma, pos): kind}."""
    for key in candidates(token):
        found = extract["forms"].get(key)
        if found:
            return {(lemma, pos): kind for lemma, pos, kind in found}
    return {}


def estimate_weights(form_candidates, form_total, rounds=4):
    """How much of the text each dictionary word accounts for, sharing each
    ambiguous spelling among its candidates in proportion to their current
    estimates (a few rounds of expectation-maximization)."""
    weight = defaultdict(lambda: 1.0)
    for _ in range(rounds):
        new = defaultdict(float)
        for form, found in form_candidates.items():
            if not found:
                continue
            scores = {lemma: weight[lemma] * trust(lemma, kind) for lemma, kind in found.items()}
            total = sum(scores.values()) or 1.0
            for lemma, score in scores.items():
                new[lemma] += form_total[form] * score / total
        weight = defaultdict(float, new)
    return weight


def build_glossary(tokens, source_dir):
    """`tokens` is the instance's unigram index: {form: postings}."""
    extract = load_extract(Path(source_dir) / "lexicon" / EXTRACT_FILE)
    glosses = {tuple(key.split("\t")): value for key, value in extract["lemmas"].items()}
    form_total = {form: sum(count for _, count in postings) for form, postings in tokens.items()}
    form_candidates = {form: lookup(form, extract) for form in tokens}

    weight = estimate_weights(form_candidates, form_total)
    stats = Counter()
    assigned = {}
    for form, found in form_candidates.items():
        stats["words"] += form_total[form]
        if not found:
            stats["words_without_lemma"] += form_total[form]
            stats["forms_without_lemma"] += 1
            form_candidates[form] = []
            continue
        ranked = sorted(found, key=lambda lemma: -weight[lemma] * trust(lemma, found[lemma]))
        form_candidates[form] = ranked
        assigned[form] = ranked[0]
        if len(ranked) > 1:
            stats["words_in_shared_spellings"] += form_total[form]

    lemma_forms = defaultdict(Counter)
    lemma_shared = Counter()
    for form, lemma in assigned.items():
        lemma_forms[lemma][form] += form_total[form]
        if len(form_candidates[form]) > 1:
            lemma_shared[lemma] += form_total[form]
    ordered = sorted(lemma_forms, key=lambda k: (-sum(lemma_forms[k].values()), k))
    index = {lemma: i for i, lemma in enumerate(ordered)}
    lemmas = []
    for lemma in ordered:
        word, pos = lemma
        count = sum(lemma_forms[lemma].values())
        senses = glosses.get(lemma, [])
        entry = {
            "lemma": word,
            "pos": POS_LABELS.get(pos, pos),
            "n": count,
            "def": short_definition(senses),
            "en": senses[2:4] if len(senses) > 2 else [],
            "w": word_index(senses, count),
            "forms": [[f, c] for f, c in sorted(lemma_forms[lemma].items(), key=lambda fc: (-fc[1], fc[0]))],
        }
        if lemma_shared[lemma]:
            entry["amb"] = lemma_shared[lemma]
        lemmas.append(entry)
    forms = {}
    for form in sorted(tokens):
        found = form_candidates[form]
        shown = []
        for lemma in found[:2]:
            text = short_definition(glosses.get(lemma, []))
            if text and text not in shown:
                shown.append(text)
        forms[form] = [form_total[form], shown, [index[l] for l in found[:3] if l in index]]
    stats["lemmas"] = len(lemmas)
    stats["forms"] = len(forms)
    return {"forms": forms, "lemmas": lemmas}, stats, extract["source"]
