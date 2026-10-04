"""Recreate the 200-row selection from captured source rows and AI suggestions.

This checks preprocessing snapshots and selection provenance, not label validity.
It does not call a model, regenerate annotation suggestions or modify test data.
"""
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import random

import ticket_router as router

ROOT = Path(__file__).resolve().parent


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def main():
    provenance = ROOT/'data/provenance'
    manifest = read(provenance/'selection_manifest.json')
    mapping = read(provenance/'raw/source_map.json')
    aliases = {r['original_filename']: r['repository_filename'] for r in mapping}
    for source in manifest['sources']:
        payload = (provenance/'raw'/aliases[source['filename']]).read_bytes()
        if hashlib.sha256(payload).hexdigest() != source['sha256']:
            raise ValueError('Raw supplied attachment hash changed.')
    source = read(provenance/'source_rows_230.json')
    suggestions = read(provenance/'ai_suggestions_230.json')
    if len(source) != 230 or len(suggestions) != 230:
        raise ValueError('Expected the captured 230-row candidate pool.')
    combined = []
    for row, annotation in zip(source, suggestions):
        if row['source_line'] != annotation['source_line'] or annotation['evidence'] not in row['text']:
            raise ValueError('Suggestion does not align with its captured source evidence.')
        combined.append({**row, **annotation})
    exclude = set(manifest['conservatively_excluded_for_provisional_selection'])
    eligible = [r for r in combined if r['suggested_priority'] and r['ticket_id'] not in exclude]
    if len(eligible) != 215:
        raise ValueError('Eligible candidate count changed.')
    rng = random.Random(manifest['selection_seed'])
    selected = []
    for label, count in [('High', 60), ('Medium', 138), ('Low', 2)]:
        unflagged = [r for r in eligible if r['suggested_priority'] == label and not r['review_flag']]
        flagged = [r for r in eligible if r['suggested_priority'] == label and r['review_flag']]
        rng.shuffle(unflagged); rng.shuffle(flagged)
        selected.extend((unflagged + flagged)[:count])
    selected.sort(key=lambda r: r['source_line'])
    if [r['ticket_id'] for r in selected] != manifest['selected_ids']:
        raise ValueError('Reconstructed selection does not match historical selected IDs.')
    gold = router.load_data(ROOT/'data/test.csv')
    if len(gold) != 200:
        raise ValueError('Final set must contain 200 tickets.')
    for candidate, confirmed in zip(selected, gold):
        if (candidate['ticket_id'], candidate['text'], candidate['suggested_priority']) != (
                confirmed['ticket_id'], confirmed['text'], confirmed['gold_priority']):
            raise ValueError('Confirmed set differs from selected texts or accepted labels.')
    with (provenance/'candidate_review_230.csv').open(encoding='utf-8-sig', newline='') as f:
        review = list(csv.DictReader(f))
    if [r['ticket_id'] for r in review if r['selected_for_provisional_200'] == 'True'] != manifest['selected_ids']:
        raise ValueError('Historical review worksheet selection differs.')
    dev = router.load_data(ROOT/'data/dev.csv')
    if {r['text'].strip() for r in dev} & {r['text'].strip() for r in gold}:
        raise ValueError('Exact development/test narrative overlap found.')
    print('Raw attachment hashes, selected IDs, texts, accepted labels and exact split separation verified.')
    print('Final label counts:', dict(Counter(r['gold_priority'] for r in gold)))
    print('Selection reproduction does not establish independent annotation agreement.')


if __name__ == '__main__':
    main()
