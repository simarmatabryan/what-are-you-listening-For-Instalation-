import math
import re
import unicodedata


def normalize(value):
    text = unicodedata.normalize('NFKC', str('' if value is None else value)).strip().lower()
    return re.sub(r'\s+', ' ', text.replace('–', '-').replace('—', '-').replace('−', '-'))


def classify(value):
    """Return (category, exact_hours). Ranges never imply an exact duration."""
    text = normalize(value)
    text = re.sub(r'\s*(?:jam|hours?|hrs?|h)\s*$', '', text).strip()
    compact = text.replace(' ', '')
    labels = {'<3': 'LOW', '3-6': 'MIDDLE', '>6': 'HIGH'}
    if compact in labels:
        return labels[compact], None
    if re.fullmatch(r'\d+(?:[.,]\d+)?', text):
        hours = float(text.replace(',', '.'))
        if math.isfinite(hours) and 0 <= hours <= 24:
            return ('LOW' if hours < 3 else 'MIDDLE' if hours <= 6 else 'HIGH'), hours
    return 'REVIEW', None



def classify_row(row, columns):
    def field(name):
        index = columns[name]
        return str(row[index]).strip() if index < len(row) and row[index] is not None else ''
    raw = field('screen_time')
    category, hours = classify(raw)
    return {'schema_version': 3, 'timestamp': field('timestamp'),
            'name': field('name'), 'screen_time_raw': raw,
            'category': category, 'exact_hours': hours,
            'review_required': category == 'REVIEW'}
