"""Input adapters, recorded-result replay, and resumable live demo jobs.

The evaluated classifier is imported unchanged. Gold labels never enter live
requests. UI jobs are separate from frozen final-evaluation output directories.
"""
import csv
import hashlib
import json
import os
from pathlib import Path
import uuid

import ticket_router as router

ROOT = Path(__file__).resolve().parent
REPLAY = 'Recorded examples'
LIVE = 'Live OpenRouter classification'
SETTINGS = dict(provider='openrouter', model='openai/gpt-4o-mini',
                prompt_version='v2', threshold=0.80)
COLUMNS = ['ticket_id', 'final_priority', 'raw_priority', 'confidence',
           'reason', 'review_trigger', 'status', 'source']


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write_json(path, value):
    path = Path(path)
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    tmp.replace(path)


def verified_records():
    """Match replay records to the exact reviewed data and evaluated prompt."""
    lock = read_json(ROOT/'data/test_freeze.json')
    for path, field in [('data/test.csv', 'data_sha256'),
                        ('ticket_router.py', 'classifier_code_sha256')]:
        if hashlib.sha256((ROOT/path).read_bytes()).hexdigest() != lock[field]:
            raise ValueError('Frozen demo files have changed. Extract the original demo package again.')
    rows = router.load_data(ROOT/'data/test.csv')
    records = read_json(ROOT/'results/llm_final_200/predictions.json')
    if (len(rows) != 200 or len(records) != 200 or
            len({r['ticket_id'] for r in records}) != 200 or
            {r['ticket_id'] for r in records} != {r['ticket_id'] for r in rows}):
        raise ValueError('The saved final-evaluation results are incomplete.')
    if any(r['prompt_sha256'] != router.digest(router.SYSTEM_PROMPT_V2)
           or r['threshold'] != 0.80 or r['requested_model'] != SETTINGS['model']
           for r in records):
        raise ValueError('Recorded-result settings do not match the evaluated configuration.')
    return rows, {r['ticket_id']: r for r in records}


ROWS, RECORDED = verified_records()
BY_TEXT = {r['text'].strip(): RECORDED[r['ticket_id']] for r in ROWS}
EXAMPLE_IDS = ['NEW001', 'NEW003', 'NEW055', 'NEW022']


def sample_text(ticket_id):
    return next(r['text'] for r in ROWS if r['ticket_id'] == ticket_id)


def predict(text, mode, predictor=None):
    """Replay only exact stored text; live mode passes text and fixed settings."""
    text = (text or '').strip()
    if not text:
        raise ValueError('Please provide a ticket narrative.')
    if mode == REPLAY:
        if text not in BY_TEXT:
            raise ValueError('No recorded result exists for this text. Choose a provided single-ticket example.')
        return {**BY_TEXT[text], 'source': 'recorded_final_test'}
    if mode != LIVE:
        raise ValueError('Unknown execution mode.')
    if predictor is None and not os.environ.get('OPENROUTER_API_KEY', '').strip():
        raise ValueError('OpenRouter key is missing. Enter it in the Colab hidden input and restart the demo.')
    result = (predictor or router.llm_predict)(text, **SETTINGS)
    return {**result, 'system': 'llm', 'source': 'live_openrouter'}


def upload_rows(path):
    """Read project CSVs or the CFPB narrative column; omit all answer labels."""
    if not path:
        raise ValueError('Please upload a CSV file.')
    path = Path(path)
    if path.stat().st_size > 20_000_000:
        raise ValueError('Upload a CSV no larger than 20 MB, with at most 200 tickets.')
    try:
        with path.open(encoding='utf-8-sig', newline='') as f:
            reader = csv.DictReader(f)
            names = reader.fieldnames or []
            text_col = next((c for c in ['text', 'Consumer complaint narrative'] if c in names), None)
            id_col = next((c for c in ['ticket_id', 'Complaint ID'] if c in names), None)
            if text_col is None:
                raise ValueError('CSV requires a text column or the CFPB Consumer complaint narrative column.')
            rows = []
            seen = set()
            for index, row in enumerate(reader, 1):
                if index > 200:
                    raise ValueError('Each batch supports at most 200 tickets. Split larger files first.')
                text = (row.get(text_col) or '').strip()
                ticket_id = (row.get(id_col) or '').strip() if id_col else f'DEMO{index:03d}'
                if not text:
                    raise ValueError(f'Ticket {index} has an empty narrative. Remove the row or provide text.')
                if not ticket_id or ticket_id in seen:
                    raise ValueError(f'Ticket {index} has a missing or duplicate ID.')
                seen.add(ticket_id)
                rows.append({'ticket_id': ticket_id, 'text': text})
    except UnicodeDecodeError:
        raise ValueError('Save the file as CSV UTF-8 and upload it again.') from None
    if not rows:
        raise ValueError('The CSV contains no tickets.')
    return rows


def validate_replay(rows, mode):
    """Validate the entire batch before replay, avoiding a misleading partial run."""
    if mode == REPLAY and any(r['text'] not in BY_TEXT for r in rows):
        raise ValueError('Recorded lookup supports only the exact evaluated narratives.')


def prepare_job(rows, mode, previous=None):
    fingerprint = router.digest({'rows': rows, 'mode': mode, 'settings': SETTINGS})
    jobs = ROOT/'demo_runs'
    jobs.mkdir(exist_ok=True)
    if previous:
        path = Path(previous).resolve()
        if path.parent == jobs.resolve() and (path/'job.json').exists():
            if read_json(path/'job.json')['fingerprint'] == fingerprint:
                return path
    path = jobs/uuid.uuid4().hex
    path.mkdir()
    write_json(path/'job.json', {'fingerprint': fingerprint, 'mode': mode,
                               'settings': SETTINGS, 'total': len(rows)})
    write_json(path/'predictions.json', [])
    return path


def export_csv(job, records):
    """Export completed predictions, protecting spreadsheet formula cells."""
    destination = Path(job)/'predictions.csv'
    with destination.open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        for row in records:
            values = {k: row.get(k, '') for k in COLUMNS}
            for key, value in values.items():
                if isinstance(value, str) and value.lstrip().startswith(('=', '+', '-', '@')):
                    values[key] = "'" + value
            writer.writerow(values)
    return destination


def run_job(rows, mode, job, predictor=None):
    """Yield saved snapshots; network errors stop without fabricated predictions."""
    records = read_json(Path(job)/'predictions.json')
    done = {r['ticket_id'] for r in records}
    if len(done) != len(records) or not done <= {r['ticket_id'] for r in rows}:
        raise ValueError('Saved job IDs are invalid. Upload the CSV again.')
    for row in rows:
        if row['ticket_id'] in done:
            continue
        result = predict(row['text'], mode, predictor)
        records.append({**result, 'ticket_id': row['ticket_id']})
        write_json(Path(job)/'predictions.json', records)
        export_csv(job, records)
        yield records.copy()
    export_csv(job, records)


def summary(records, total):
    counts = {p: sum(r['final_priority'] == p for r in records)
              for p in ['High', 'Medium', 'Low', 'Escalate']}
    return (f"Completed {len(records)}/{total} tickets · High {counts['High']} · "
            f"Medium {counts['Medium']} · Low {counts['Low']} · Escalate {counts['Escalate']}")
