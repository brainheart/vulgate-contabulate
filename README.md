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
