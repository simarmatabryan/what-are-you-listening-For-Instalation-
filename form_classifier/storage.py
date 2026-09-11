import hashlib
import json
import os
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from .classification import classify_row


def now():
    return datetime.now(timezone.utc).isoformat()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    os.replace(temporary, path)


class Database:
    def __init__(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path)
        self.connection.execute('PRAGMA journal_mode=WAL')
        self.connection.executescript('''
        CREATE TABLE IF NOT EXISTS responses (
            source TEXT NOT NULL, row_number INTEGER NOT NULL,
            fingerprint TEXT NOT NULL, payload TEXT NOT NULL,
            active INTEGER NOT NULL DEFAULT 1,
            PRIMARY KEY(source, row_number));
        CREATE TABLE IF NOT EXISTS changes (
            id INTEGER PRIMARY KEY AUTOINCREMENT, source TEXT NOT NULL,
            row_number INTEGER NOT NULL, kind TEXT NOT NULL, time TEXT NOT NULL,
            payload TEXT NOT NULL);
        ''')

    def sync(self, source, rows, columns):
        """Apply a complete Sheet snapshot atomically, keyed by source + sheet row."""
        if not rows or len(rows[0]) <= max(columns.values()):
            raise ValueError('Header Sheet kosong/kurang kolom; snapshot tidak diterapkan')
        counts = Counter(new=0, updated=0, removed=0, unchanged=0)
        current = set()
        with self.connection:
            for number, row in enumerate(rows[1:], start=2):
                if not any(str(cell).strip() for cell in row):
                    continue
                current.add(number)
                payload = {'source': source, 'row_number': number, **classify_row(row, columns)}
                packed = json.dumps(payload, ensure_ascii=False, sort_keys=True)
                fingerprint = hashlib.sha256(packed.encode()).hexdigest()
                previous = self.connection.execute(
                    'SELECT fingerprint, active FROM responses WHERE source=? AND row_number=?',
                    (source, number)).fetchone()
                if previous and previous == (fingerprint, 1):
                    counts['unchanged'] += 1
                    continue
                kind = 'updated' if previous else 'new'
                self.connection.execute('''INSERT INTO responses VALUES (?, ?, ?, ?, 1)
                    ON CONFLICT(source, row_number) DO UPDATE SET
                    fingerprint=excluded.fingerprint, payload=excluded.payload, active=1''',
                    (source, number, fingerprint, packed))
                self.connection.execute('INSERT INTO changes(source,row_number,kind,time,payload) VALUES(?,?,?,?,?)',
                                        (source, number, kind, now(), packed))
                counts[kind] += 1
            active = self.connection.execute('SELECT row_number,payload FROM responses WHERE source=? AND active=1', (source,)).fetchall()
            for number, packed in active:
                if number not in current:
                    self.connection.execute('UPDATE responses SET active=0 WHERE source=? AND row_number=?', (source, number))
                    self.connection.execute('INSERT INTO changes(source,row_number,kind,time,payload) VALUES(?,?,?,?,?)',
                                            (source, number, 'removed', now(), packed))
                    counts['removed'] += 1
        return dict(counts)

    def results(self, source):
        return [json.loads(row[0]) for row in self.connection.execute(
            'SELECT payload FROM responses WHERE source=? AND active=1 ORDER BY row_number', (source,))]

    def export(self, source, directory):
        results = self.results(source)
        counts = Counter(row['category'] for row in results)
        latest_change = self.connection.execute('SELECT MAX(id) FROM changes WHERE source=?', (source,)).fetchone()[0]
        summary = {
            'source': source, 'generated_at': now(), 'last_change_id': latest_change,
            'total': len(results), 'classified': len(results) - counts['REVIEW'],
            'categories': {key: counts[key] for key in ['LOW', 'MIDDLE', 'HIGH', 'REVIEW']},
            'percentages': {key: round(counts[key] / len(results) * 100, 2) if results else 0
                            for key in ['LOW', 'MIDDLE', 'HIGH', 'REVIEW']},
            'responses_needing_review': sum(row.get('review_required', False) for row in results),
            'latest_response': results[-1] if results else None,
        }
        root = Path(directory)
        # A single authoritative snapshot keeps summary and records consistent.
        write_json(root / 'classification.json', {'summary': summary, 'responses': results})
        write_json(root / 'summary.json', summary)
        return summary

    def close(self):
        self.connection.close()
