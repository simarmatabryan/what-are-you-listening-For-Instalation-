import csv
import io
import json
import re
import ssl
import urllib.request
import math
from pathlib import Path

DEFAULT_COLUMNS = {'timestamp': 0, 'name': 1, 'age': 2, 'screen_time': 3, 'apps': 4}


def read_config(path):
    path = Path(path).resolve()
    config = json.loads(path.read_text(encoding='utf-8'))
    if not config.get('spreadsheet_id') or config['spreadsheet_id'] == 'ISI_ID_GOOGLE_SHEETS':
        raise ValueError('Isi spreadsheet_id dengan ID Google Sheets tujuan Form')
    seconds = float(config.get('poll_seconds', 5))
    if not math.isfinite(seconds) or seconds < 1:
        raise ValueError('poll_seconds minimal 1 detik')
    config['poll_seconds'] = seconds
    if not re.fullmatch(r'[A-Za-z0-9_-]+', config['spreadsheet_id']):
        raise ValueError('spreadsheet_id harus berupa ID, bukan URL lengkap')
    config.setdefault('mode', 'service_account')
    if config['mode'] not in ['public_csv', 'service_account']:
        raise ValueError('mode harus public_csv atau service_account')
    if config['mode'] == 'public_csv' and not str(config.get('gid', '')).isdigit():
        raise ValueError('gid tab Google Sheets harus berupa angka')
    config.setdefault('max_host', '127.0.0.1')
    config['max_port'] = int(config.get('max_port', 8000))
    config['osc_enabled'] = bool(config.get('osc_enabled', True))
    if not 1 <= config['max_port'] <= 65535:
        raise ValueError('max_port harus 1..65535')
    columns = config.get('columns', DEFAULT_COLUMNS)
    if set(columns) != set(DEFAULT_COLUMNS) or any(type(v) is not int or v < 0 for v in columns.values()) or len(set(columns.values())) != 5:
        raise ValueError('columns harus berisi lima indeks kolom berbeda, mulai dari 0')
    config['columns'] = columns
    for name, default in [('database', 'data/live.sqlite3'), ('output_dir', 'output/live'), ('credentials_file', 'credentials.json')]:
        config[name] = str((path.parent / config.get(name, default)).resolve())
    config.setdefault('sheet_name', 'Form Responses 1')
    return config


class GoogleSheet:
    def __init__(self, config):
        from google.oauth2.service_account import Credentials
        from googleapiclient.discovery import build
        from google_auth_httplib2 import AuthorizedHttp
        import httplib2
        self.config = config
        credentials = Credentials.from_service_account_file(config['credentials_file'],
            scopes=['https://www.googleapis.com/auth/spreadsheets.readonly'])
        self.service = build('sheets', 'v4', http=AuthorizedHttp(credentials, http=httplib2.Http(timeout=15)), cache_discovery=False)
        self.identity = 'sheets:' + config['spreadsheet_id'] + ':' + config['sheet_name']

    def read(self):
        # Read the complete tab so no newly appended rows fall outside a fixed range.
        name = self.config['sheet_name'].replace("'", "''")
        result = self.service.spreadsheets().values().get(
            spreadsheetId=self.config['spreadsheet_id'], range="'" + name + "'",
            valueRenderOption='FORMATTED_VALUE').execute(num_retries=2)
        rows = result.get('values', [])
        validate_headers(rows, self.config)
        return rows

    def close(self):
        self.service.close()


class PublicGoogleSheet:
    """Read the provided Sheet's existing anonymous export; never changes sharing."""
    def __init__(self, config):
        self.config = config
        self.identity = 'sheets:' + config['spreadsheet_id'] + ':' + str(config['gid'])
        self.url = ('https://docs.google.com/spreadsheets/d/' + config['spreadsheet_id']
                    + '/export?format=csv&gid=' + str(config['gid']))

    def read(self):
        request = urllib.request.Request(self.url, headers={'Cache-Control': 'no-cache'})
        context = ssl.create_default_context()
        # Some macOS Python installers omit their own CA bundle. Use the OS CA
        # bundle when present; certificate and hostname verification stay enabled.
        defaults = ssl.get_default_verify_paths()
        if defaults.cafile is None and defaults.capath is None and Path('/etc/ssl/cert.pem').is_file():
            context.load_verify_locations(cafile='/etc/ssl/cert.pem')
        with urllib.request.urlopen(request, timeout=20, context=context) as response:
            content_type = response.headers.get('Content-Type', '')
            if 'text/csv' not in content_type and 'application/csv' not in content_type:
                raise ValueError('Google tidak mengembalikan CSV; akses Sheet mungkin membutuhkan login')
            raw = response.read().decode('utf-8-sig')
        rows = list(csv.reader(io.StringIO(raw)))
        validate_headers(rows, self.config)
        return rows

    def close(self):
        pass


def validate_headers(rows, config):
    if not rows or len(rows[0]) <= max(config['columns'].values()):
        raise ValueError('Header Sheet hilang/tidak sesuai; data lama dipertahankan')
    expected = config.get('expected_headers', {})
    for field, header in expected.items():
        if field not in config['columns']:
            raise ValueError('expected_headers mengandung kolom tidak dikenal: ' + field)
        index = config['columns'][field]
        actual = rows[0][index]
        if ' '.join(actual.split()) != ' '.join(header.split()):
            raise ValueError('Header kolom ' + field + ' berubah. Sesuaikan konfigurasi sebelum sinkronisasi.')


def open_sheet(config):
    return PublicGoogleSheet(config) if config['mode'] == 'public_csv' else GoogleSheet(config)
