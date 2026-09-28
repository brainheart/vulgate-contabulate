"""Corpus integrity, native Vulgate numbering, tokenizer, and metadata tests."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import unicodedata
import unittest

import build

ROOT = Path(__file__).resolve().parents[1]


def read(name):
    return json.loads((ROOT / name).read_text())


class CorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.books = read('docs/data/plays.json')
        cls.chunks = read('docs/data/chunks.json')
        cls.lines = read('docs/lines/all_lines.json')
        cls.tokens = read('docs/data/tokens.json')
        cls.text = {r['canonical_id']: r['text'] for r in cls.lines}

    def test_source_checksum(self):
        provenance = build.verify_source_files(ROOT / 'source_text')
        self.assertEqual(provenance['commit'], 'e310b178189e30443c44f2338022aab73546b274')

    def test_corpus_totals_and_hierarchy(self):
        self.assertEqual(len(self.books), 73)
        self.assertEqual(sum(b['num_acts'] for b in self.books), 1334)
        self.assertEqual(len(self.chunks), 35811)
        self.assertEqual(sum(b['total_words'] for b in self.books), 612225)
        self.assertEqual(len(self.tokens), 46380)
        self.assertEqual(Counter(b['genre'] for b in self.books),
                         {'Vetus Testamentum': 46, 'Novum Testamentum': 27})
        self.assertEqual(self.books[0]['location'], '01.Gen')
        self.assertEqual(self.books[-1]['location'], '73.Rev')
        self.assertEqual([r['canonical_id'] for r in self.chunks], [r['canonical_id'] for r in self.lines])
        self.assertEqual(len({r['scene_id'] for r in self.chunks}), len(self.chunks))
        self.assertEqual(len({r['canonical_id'] for r in self.chunks}), len(self.chunks))
        self.assertEqual(len({r['location'] for r in self.chunks}), len(self.chunks))
        self.assertEqual([r['location'] for r in self.chunks], sorted(r['location'] for r in self.chunks))
        for chunk, line in zip(self.chunks, self.lines):
            self.assertIn(chunk['play_id'], range(1, 74))
            self.assertEqual(chunk['scene_id'], line['line_num'])
            self.assertEqual(chunk['total_words'], len(build.tokenize(line['text'])))

    def test_clementine_order_and_latin_titles(self):
        order = [b['abbr'] for b in self.books]
        self.assertEqual(order[12:25], ['1Chr', '2Chr', 'Ezra', 'Neh', 'Tob', 'Jdt', 'Esth', 'Job',
                                        'Ps', 'Prov', 'Eccl', 'Song', 'Wis'])
        self.assertEqual(order[25:30], ['Sir', 'Isa', 'Jer', 'Lam', 'Bar'])
        self.assertEqual(order[44:47], ['1Macc', '2Macc', 'Matt'])
        titles = {b['abbr']: b['title'] for b in self.books}
        self.assertEqual(titles['1Kgs'], 'Regum III')
        self.assertEqual(titles['1Chr'], 'Paralipomenon I')
        self.assertEqual(titles['Sir'], 'Ecclesiasticus')
        self.assertEqual(titles['Rev'], 'Apocalypsis')
        self.assertNotIn('PrMan', titles)  # the source has no appendix (Oratio Manassæ, 3-4 Esdræ)

    def test_native_vulgate_numbering(self):
        self.assertTrue(self.text['Ps.22.1'].startswith('Psalmus David. Dominus regit me, et nihil mihi deerit'))
        self.assertTrue(self.text['Ps.50.3'].startswith('Miserere mei, Deus, secundum magnam misericordiam tuam'))
        self.assertTrue(self.text['Ps.113.9'].startswith('Non nobis, Domine'))
        self.assertEqual(sum(1 for r in self.chunks if r['play_abbr'] == 'Ps' and r['scene'] == 1), 150)
        self.assertNotIn('Ps.151.1', self.text)
        self.assertEqual(max(r['act'] for r in self.chunks if r['play_abbr'] == 'Esth'), 16)
        self.assertIn('Esth.16.24', self.text)
        self.assertIn('Dan.3.100', self.text)
        self.assertTrue(self.text['Dan.13.1'].startswith('Et erat vir habitans in Babylone'))
        self.assertTrue(self.text['Dan.14.1'].startswith('Erat autem Daniel conviva regis'))
        self.assertTrue(self.text['Bar.6.1'].startswith('Propter peccata'))
        self.assertIn('Pater, Verbum, et Spiritus Sanctus', self.text['1John.5.7'])
        self.assertEqual(self.lines[0]['text'], 'In principio creavit Deus cælum et terram.')
        self.assertEqual(self.lines[-1]['canonical_id'], 'Rev.22.21')

    def test_prologues_are_their_own_rows(self):
        for book, start in [('Sir', 'Multorum nobis'), ('Lam', 'Et factum est, postquam')]:
            prologue = next(r for r in self.chunks if r['canonical_id'] == f'{book}.1.0')
            self.assertEqual(prologue['scene_label'], 'prol.')
            self.assertTrue(prologue['location'].endswith('.001.000'))
            self.assertTrue(self.text[f'{book}.1.0'].startswith(start))
        self.assertTrue(self.text['Sir.1.1'].startswith('Omnis sapientia a Domino Deo est'))
        self.assertTrue(self.text['Lam.1.1'].startswith('Aleph Quomodo sedet sola civitas'))
        self.assertNotIn('Prologus', ' '.join(self.text.values()))

    def test_text_normalization(self):
        for text in self.text.values():
            self.assertEqual(text, unicodedata.normalize('NFC', text))
            self.assertNotRegex(text, r'[<>0-9]|\s[:;?!]|\s{2}')

    def test_latin_tokens_and_sentences(self):
        self.assertEqual(build.tokenize('Cælum, cujus Israël? Beth-horon.'),
                         ['cælum', 'cujus', 'israël', 'beth', 'horon'])
        self.assertEqual(build.count_sentences('Quis est? Ego sum; tu: ille. Amen!'), 3)
        self.assertGreater(sum(c for _, c in self.tokens['caritas']), 0)
        self.assertNotIn('caelum', self.tokens)

    def test_browser_and_python_tokenizers_agree_on_entire_corpus(self):
        code = """
        global.window = global;
        require('./docs/js/utils.js');
        const fs = require('fs'); const crypto = require('crypto');
        const lines = JSON.parse(fs.readFileSync('./docs/lines/all_lines.json'));
        const stream = lines.map(l => tokenizeLineText(l.text).join(' ')).join('\\n');
        process.stdout.write(crypto.createHash('sha256').update(stream).digest('hex'));
        """
        actual = subprocess.check_output(['node', '-e', code], cwd=ROOT, text=True)
        stream = '\n'.join(' '.join(build.tokenize(row['text'])) for row in self.lines)
        self.assertEqual(actual, hashlib.sha256(stream.encode()).hexdigest())

    def test_postings_totals_do_not_cross_verse_boundaries(self):
        by_id = {r['scene_id']: r for r in self.chunks}
        for n, filename in [(1, 'tokens'), (2, 'tokens2'), (3, 'tokens3')]:
            index = read(f'docs/data/{filename}.json')
            totals = Counter()
            for term, postings in index.items():
                self.assertEqual(len(term.split()), n)
                for scene_id, count in postings:
                    self.assertGreater(count, 0)
                    totals[scene_id] += count
            for scene_id, chunk in by_id.items():
                self.assertEqual(totals[scene_id], max(0, chunk['total_words'] - n + 1))

    def test_metrics_metadata_and_disabled_capabilities(self):
        instance = read('docs/instance.json')
        meta = read('instance-meta.json')
        self.assertEqual(instance['schema'], 1)
        self.assertEqual(instance['id'], 'vulgate')
        self.assertEqual(instance['created'], '2026-09-28')
        self.assertEqual(instance['language'], 'Latin')
        self.assertEqual(instance['url'], 'https://vulgate.contabulate.org/')
        self.assertEqual((ROOT / 'docs/CNAME').read_text().strip(), 'vulgate.contabulate.org')
        self.assertEqual(instance['stats'], {
            'texts': 73, 'text_label': 'books', 'segments': 35811, 'segment_label': 'verses',
            'words': 612225, 'distinct_words': 46380, 'commentaries': 0, 'comments': 0})
        self.assertEqual(instance['sample_queries'], meta['sample_queries'])
        self.assertIn(len(instance['sample_queries']), (3, 4))
        for sample in instance['sample_queries']:
            self.assertTrue(sample['url'].startswith('https://vulgate.contabulate.org/?'))
        self.assertEqual(sum(c['hapax_count'] for c in self.chunks),
                         sum(sum(count for _, count in p) == 1 for p in self.tokens.values()))
        for chunk in self.chunks:
            self.assertGreater(chunk['char_count'], 0)
            self.assertGreater(chunk['rarity_sum'], 0)
            self.assertNotIn('commentary_interest', chunk)
        self.assertEqual(read('docs/data/characters.json'), [])
        self.assertFalse(read('docs/data/character_name_filter_config.json')['enabled'])
        self.assertEqual(read('docs/data/commentary_interest.json')['metadata']['commentators'], [])


if __name__ == '__main__':
    unittest.main()
