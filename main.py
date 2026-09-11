"""Terminal-only Google Form classification. No phone UI, sensors, or audio."""
import argparse
import json
import logging
import sys
import time
from pathlib import Path
from form_classifier.sources import DEFAULT_COLUMNS, open_sheet, read_config
from form_classifier.storage import Database

LOG = logging.getLogger('form-classifier')


def show(changes, summary):
    c = summary['categories']
    LOG.info('Baru=%s diperbarui=%s dihapus=%s tetap=%s | Total=%s LOW=%s MIDDLE=%s HIGH=%s REVIEW=%s',
             changes['new'], changes['updated'], changes['removed'], changes['unchanged'],
             summary['total'], c['LOW'], c['MIDDLE'], c['HIGH'], c['REVIEW'])


def main(argv=None):
    parser = argparse.ArgumentParser(description='Klasifikasi respons Google Form secara berkelanjutan')
    sub = parser.add_subparsers(dest='command', required=True)
    live = sub.add_parser('watch', help='Baca Google Sheets berulang dan proses respons baru')
    live.add_argument('--config', default='config.json')
    live.add_argument('--once', action='store_true', help='Satu kali sinkronisasi, kemudian berhenti')
    report = sub.add_parser('report', help='Tampilkan klasifikasi terakhir tanpa koneksi internet')
    report.add_argument('--config', default='config.json')
    report.add_argument('--detail', action='store_true', help=argparse.SUPPRESS)
    report.add_argument('--row', type=int, help='Pilih responden berdasarkan nomor baris Sheet')
    offline = sub.add_parser('import-json', help='Uji sistem menggunakan snapshot lokal')
    offline.add_argument('file')
    offline.add_argument('--database', default='data/sample.sqlite3')
    offline.add_argument('--output', default='output/sample')
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(message)s', datefmt='%H:%M:%S')
    db = sheet = None
    try:
        if args.command == 'import-json':
            snapshot = json.loads(Path(args.file).read_text(encoding='utf-8'))
            source = snapshot['source']
            db = Database(args.database)
            changes = db.sync(source, snapshot['rows'], snapshot.get('columns', DEFAULT_COLUMNS))
            summary = db.export(source, args.output)
            show(changes, summary)
            return 0
        config = read_config(args.config)
        if args.command == 'report':
            report_file = Path(config['output_dir']) / 'classification.json'
            report = json.loads(report_file.read_text(encoding='utf-8'))
            summary = report['summary']
            print('KLASIFIKASI GOOGLE FORM | ' + summary['generated_at'])
            print('Total:', summary['total'], '|', summary['categories'])
            print(f"{'BARIS':<6} {'NAMA / INISIAL':<28} {'JAWABAN':<14} KATEGORI")
            selected = [r for r in report['responses'] if args.row is None or r['row_number'] == args.row]
            if not selected:
                raise ValueError('Tidak ada responden yang sesuai nomor baris tersebut')
            for row in selected:
                print(f"{row['row_number']:<6} {row['name']:<28} {row['screen_time_raw']:<14} {row['category']}")
            return 0
        sheet = open_sheet(config)
        db = Database(config['database'])
        LOG.info('Memantau Google Sheets setiap %ss. Ctrl+C untuk berhenti.', config['poll_seconds'])
        failures = 0
        while True:
            try:
                rows = sheet.read()
                changes = db.sync(sheet.identity, rows, config['columns'])
                summary = db.export(sheet.identity, config['output_dir'])
                show(changes, summary)
                failures = 0
                if args.once: return 0
            except Exception as error:
                failures += 1
                LOG.error('Sinkronisasi gagal: %s. Hasil tersimpan tetap tersedia.', error)
                if args.once: raise
            time.sleep(min(60, config['poll_seconds'] * (2 ** min(failures, 5))))
    except KeyboardInterrupt:
        LOG.info('Pemantauan dihentikan; data tersimpan dapat dilanjutkan.')
        return 0
    except Exception as error:
        LOG.error('%s: %s', type(error).__name__, error)
        return 1
    finally:
        if db is not None: db.close()
        if sheet is not None: sheet.close()


if __name__ == '__main__':
    sys.exit(main())
