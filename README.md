# Latin Vulgate Contabulate

A static [Contabulate](https://contabulate.org/) instance for the Clementine
Vulgate (1592): a sortable, filterable table of all 73 books by testament, book,
chapter, verse, word, bigram, and trigram, with search-term and text-metric
columns. Canonical URL (not yet deployed): https://vulgate.contabulate.org/

- Books, order, Latin titles, and chapter/verse numbers are the Vulgate's own
  (Psalm 22 = *Dominus regit me*; Esther 10:4–16:24; Daniel 13–14).
- Text: Clementine Vulgate Project transcription via `seven1m/open-bibles`,
  pinned and checksummed in `source_text/provenance.json`. See `SOURCES.md`.

## Build and test

```sh
python3 build.py                     # regenerates docs/data, docs/lines, docs/instance.json
python3 -m unittest discover -v      # corpus, numbering, tokenizer, metadata checks
npm ci && npx playwright test        # browser tests against python3 -m http.server 8781
```

Generated files under `docs/data`, `docs/lines`, and `docs/instance.json` are
build output; edit `scripts/source.py`, `build.py`, or `instance-meta.json` and rebuild.

## License

Code: MIT (see `LICENSE`). Latin text: public domain.

## English lookup and glosses

For readers without Latin, a lookup box above the term field finds Latin words by English meaning and inserts them as search terms; the word views add English and Dictionary form columns.

- The data is English Wiktionary (CC BY-SA 3.0 / GFDL) as published by kaikki.org. `source_text/lexicon/wiktionary-extract.json` is the part of that 1.25 GB dictionary this text needs, cut by `kaikki_extract.py` in the contabulate-instances skill and pinned by SHA-256 in `scripts/glossary.py`.
- `scripts/glossary.py` writes `docs/data/glossary.json` during `python3 build.py`. A dictionary cannot disambiguate a spelling in context, so each written form is filed under its likeliest dictionary word and shared spellings are counted (`amb`).
- It is display-only: nothing in it is searched or counted, and the page works without it. `docs/js/glossary.js` is shared verbatim with the other non-English Contabulate instances.
