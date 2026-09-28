# Vulgate + Septuagint Contabulate: build report (2026-09-28)

**Built locally (nothing pushed; no GitHub repos, DNS, or hub edits):**
- `~/Projects/vulgate-contabulate` (5 commits): Clementine Vulgate, 73 books, Clementine order, Latin titles, native numbering (Ps 22:1 = "Psalmus David. Dominus regit me…"). CNAME vulgate.contabulate.org, emoji 🦁.
- `~/Projects/septuagint-contabulate` (5 commits): Swete LXX (OGL First1KGreek), 55 books in Swete's own order (read from TEI volume/page), native numbering, incl. 1 Esdras, 1–4 Maccabees, Psalms of Solomon, Odes, Ps 151, OG + Theodotion Daniel/Susanna/Bel. CNAME septuagint.contabulate.org, emoji 📜.
- Both use the gnt-contabulate UI shell (commentary columns hidden when there's no commentary data), a shared `build.py`, pinned and hash-checked sources, SOURCES.md, sources.html, and generated `instance.json` (created 2026-09-28, stats, sample queries).

**Tests (all passing; no failures):**
- Vulgate: 10/10 Python data tests, 18/18 Playwright, audit_instance PASS.
- Septuagint: 10/10 Python data tests, 19/19 Playwright, audit_instance PASS.
- New checks: book counts and order, Ps 22:1 Vulgate text, LXX-only books present, Greek accented/NFD/uppercase search matches, unaccented search finds nothing (the gnt behavior), Latin regex, full-corpus Python/JS tokenizer agreement, sample-query deep links.

**Counts:** Vulgate 73 books / 1,334 chapters / 35,811 verses / 612,225 words / 46,380 distinct. Septuagint 55 books / 1,136 chapters / 29,357 verses / 587,557 words / 57,103 distinct.

**Sample queries:** Vulgate: caritas vs dilectio by book; "Dominus regit me" → Ps 22:1; "Miserere mei, Deus" → Ps 50/55/56. LXX: ἔλεος by book; ἀγάπη (Song of Songs leads); ᾅδης by book; "Κύριος ποιμαίνει με" → Ps 22:1.

**Screenshots:** `~/.openclaw/workspace/media/vulgate/` (vulgate-books, vulgate-caritas-dilectio, vulgate-psalm22 .png); `~/.openclaw/workspace/media/septuagint/` (septuagint-books, septuagint-eleos, septuagint-psalm22 .png).

**Judgment calls and known gaps:**
- Vulgate source has no Clementine appendix (Prayer of Manasseh, 3–4 Esdras). The unnumbered prologues of Sirach and Lamentations get their own `prol.` rows. Spelling is kept as printed (cælum, cujus, Israël), so "caelum" finds nothing; the page suggests a regex.
- LXX: Ecclesiastes is missing upstream; Judges is Codex A only. Esdras B stays one book (23 chapters). Ode 4's two printed parts are chapters 4a/4b of one Ode 4. Esther additions keep the transcription's labels (1a…).
- LXX OCR: 17 numbering repairs (logged in docs/data/source_repairs.json) plus deterministic cleanups (sigla, roman numerals, detached breathings, hyphenation). About 200 tokens with Latin letters remain. Five verse-1 divisions lost their text upstream and are omitted (Exod 20:1, Num 17:1, 19:1, 3 Kgdms 14:1, 16:1).
- LXX data is CC BY-SA 4.0 (DATA-LICENSE.md); site code is MIT.
- Greek search keeps accents and breathings, like gnt, so enclitic ἔλεός is a separate word; the samples use regexes to combine forms.
- No commentary or proper-name data in either instance.

**Still needs Reinhard:** review, then create the GitHub repos, enable Pages, set up Cloudflare DNS, and add both to the contabulate.org hub (docs/instances.json + README).
