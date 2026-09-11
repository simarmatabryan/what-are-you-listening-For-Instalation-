import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from form_classifier.classification import classify, classify_row
from form_classifier.sources import DEFAULT_COLUMNS, validate_headers, read_config
from form_classifier.storage import Database
from main import main

HEADER = ['Timestamp', 'Name', 'Age', 'Screen time', 'Apps']

def row(screen='< 3 Jam', name='AA'):
    return ['09/09/2026 12:00:00', name, '21', screen, 'Instagram, Wa']


class ClassificationTests(unittest.TestCase):
    def test_real_form_labels(self):
        for text, expected in [('< 3 Jam','LOW'),('3 - 6 Jam','MIDDLE'),('> 6 Jam','HIGH'), (' 3 – 6 JAM ', 'MIDDLE')]:
            self.assertEqual(classify(text), (expected, None))

    def test_numeric_boundaries(self):
        for hours, expected in [(0,'LOW'),(2.99,'LOW'),(3,'MIDDLE'),(6,'MIDDLE'),(6.01,'HIGH'),(24,'HIGH')]:
            self.assertEqual(classify(str(hours))[0], expected)
        self.assertEqual(classify('3,5 jam'), ('MIDDLE', 3.5))

    def test_invalid_is_review_never_guessed(self):
        for value in ['',None,'nan','inf','-1','25','2 - 8 jam','<= 3 jam','six']:
            self.assertEqual(classify(value), ('REVIEW', None))

    def test_only_screen_time_is_classified(self):
        response = row('3 - 6 Jam')
        response[2] = 'invalid age'
        response[4] = 'Unknown App'
        result = classify_row(response, DEFAULT_COLUMNS)
        self.assertEqual(result['category'], 'MIDDLE')
        self.assertFalse(result['review_required'])
        self.assertEqual(set(result), {'schema_version', 'timestamp', 'name',
                         'screen_time_raw', 'category', 'exact_hours', 'review_required'})


class PersistenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'test.sqlite3'
        self.db = Database(self.path)

    def tearDown(self):
        self.db.close(); self.tmp.cleanup()

    def sync(self, rows):
        return self.db.sync('test', [HEADER, *rows], DEFAULT_COLUMNS)

    def test_append_restart_and_no_duplicate(self):
        self.assertEqual(self.sync([row()])['new'], 1)
        self.db.close(); self.db = Database(self.path)
        result = self.sync([row(), row('> 6 Jam','BB')])
        self.assertEqual(result['new'],1)
        self.assertEqual(result['unchanged'],1)
        self.assertEqual(len(self.db.results('test')),2)
        self.assertEqual(self.sync([row(),row('> 6 Jam','BB')])['new'],0)

    def test_edit_reclassifies_without_increasing_total(self):
        self.sync([row()]); result=self.sync([row('> 6 Jam')])
        self.assertEqual(result['updated'],1)
        self.assertEqual(len(self.db.results('test')),1)
        self.assertEqual(self.db.results('test')[0]['category'],'HIGH')

    def test_same_timestamp_different_responses_not_collapsed(self):
        self.sync([row(),row()])
        self.assertEqual(len(self.db.results('test')),2)

    def test_removed_rows_retained_in_history(self):
        self.sync([row(),row('> 6 Jam','BB')])
        self.assertEqual(self.sync([row()])['removed'],1)
        self.assertEqual(len(self.db.results('test')),1)
        self.assertEqual(self.db.connection.execute('SELECT COUNT(*) FROM responses').fetchone()[0],2)

    def test_bad_snapshot_preserves_old_data(self):
        self.sync([row()])
        with self.assertRaises(ValueError): self.db.sync('test', [], DEFAULT_COLUMNS)
        self.assertEqual(len(self.db.results('test')),1)

    def test_export_counts_and_null_hours_for_ranges(self):
        self.sync([row(),row('3 - 6 Jam'),row('> 6 Jam'),row('unknown')])
        summary=self.db.export('test',self.tmp.name)
        self.assertEqual(summary['categories'],{'LOW':1,'MIDDLE':1,'HIGH':1,'REVIEW':1})
        self.assertEqual(summary['percentages']['LOW'],25)
        report=json.loads((Path(self.tmp.name)/'classification.json').read_text())
        self.assertIsNone(report['responses'][0]['exact_hours'])
        self.assertEqual(report['summary']['total'],len(report['responses']))


class SourceTests(unittest.TestCase):
    def test_reordered_headers_rejected(self):
        config={'columns':DEFAULT_COLUMNS,'expected_headers':{'screen_time':'Screen time'}}
        validate_headers([HEADER],config)
        with self.assertRaises(ValueError):
            validate_headers([['Timestamp','Name','Age','Apps','Screen time']],config)

    def test_config_resolves_relative_paths(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'config.json'
            path.write_text(json.dumps({'spreadsheet_id':'example','mode':'public_csv','gid':123}))
            config=read_config(path)
            self.assertEqual(config['database'],str((Path(temp)/'data/live.sqlite3').resolve()))

    def test_poll_error_then_new_data(self):
        class FakeSheet:
            identity='fake'
            def __init__(self): self.calls=0
            def read(self):
                self.calls+=1
                if self.calls==1: raise OSError('temporary network failure')
                return [HEADER,row(), *([row('> 6 Jam','BB')] if self.calls>=3 else [])]
            def close(self): pass
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'config.json'
            path.write_text(json.dumps({'spreadsheet_id':'example','mode':'public_csv','gid':123}))
            calls=[]
            def sleep(delay):
                calls.append(delay)
                if len(calls)==3: raise KeyboardInterrupt
            with patch('main.open_sheet',return_value=FakeSheet()), patch('main.time.sleep',side_effect=sleep):
                self.assertEqual(main(['watch','--config',str(path)]),0)
            report=json.loads((Path(temp)/'output/live/summary.json').read_text())
            self.assertEqual(report['total'],2)
            self.assertEqual(calls,[10,5,5])

    def test_public_download_rejects_html(self):
        from form_classifier.sources import PublicGoogleSheet
        from unittest.mock import MagicMock
        response=MagicMock(); response.__enter__.return_value=response
        response.headers={'Content-Type':'text/html'}
        with patch('urllib.request.urlopen',return_value=response):
            with self.assertRaises(ValueError):
                PublicGoogleSheet({'spreadsheet_id':'abc','gid':1,'columns':DEFAULT_COLUMNS}).read()

if __name__ == '__main__': unittest.main()
