# Sources, licenses and provenance

| Item | Detail |
|---|---|
| Edition | Clementine Vulgate, *Biblia Sacra Vulgatae Editionis* (1592), 73 books |
| Transcription | Clementine Vulgate Project (Michael Tweedale et al., VulSearch) |
| File | `source_text/lat-clementine.usfx.xml` |
| Upstream | https://github.com/seven1m/open-bibles @ `e310b178189e30443c44f2338022aab73546b274` |
| URL | https://raw.githubusercontent.com/seven1m/open-bibles/e310b178189e30443c44f2338022aab73546b274/lat-clementine.usfx.xml |
| SHA-256 | `5da5f3c07fa6896d4a2b45f5f309c3ece43e554fd059b31b8ae3688bbd182baf` |
| License | Public domain |

The file was copied from `polyglot-contabulate/sources/raw/vulgate/`, where the
same URL and hash are pinned in `sources/manifest.json`. `build.py` verifies the
hash on every build.

## Processing

- Book order, Latin book headings (`<h>`), chapter and verse numbers are taken
  from the file unchanged. Canonical IDs use the OSIS-style book codes of the
  sibling Bible instances (`Ps.22.1`), with Vulgate numbering.
- Text: markup removed, whitespace collapsed, Unicode NFC, and the
  French-style space before `: ; ? !` closed up. Spelling (æ, œ, j, ë) is kept.
- The transcription prefixes the unnumbered prologues of Ecclesiasticus and
  Lamentations to verse 1 with the marker "Prologus". The build removes the
  marker and gives each prologue its own row (`Sir.1.0`, `Lam.1.0`, label
  `prol.`), so 1:1 is the verse the edition numbers 1:1.

## Known limits

- The Clementine appendix (Prayer of Manasseh, 3–4 Esdras) is not in the source.
- No commentary counts: the HCF commentary used by KJV/Luther is keyed to KJV
  numbering and has not been mapped to Vulgate versification.
- No reviewed proper-name list, so "Hide proper names" is disabled.
