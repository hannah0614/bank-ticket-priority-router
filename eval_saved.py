"""Recompute the submitted evaluation offline and export inspectable analysis.

Uses the reviewed frozen labels and actual saved predictions. Validates frozen
inputs, settings, complete prediction coverage and the saved metric values.
No API call, model judge, generated prediction or dependency installation occurs.
"""
import argparse
from collections import Counter
import csv
import json
from pathlib import Path
import statistics

import run_final
import ticket_router as router

ROOT = Path(__file__).resolve().parent


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def audit_saved():
    """Return results only after saved metrics and frozen configurations match."""
    rows, frozen, settings = run_final.frozen_inputs()
    baselines = read(ROOT/'results/baselines_final_200/predictions.json')
    llm = read(ROOT/'results/llm_final_200/predictions.json')
    if baselines != router.baseline_results(rows, frozen):
        raise ValueError('Saved baseline predictions differ from the frozen rules.')
    for folder, predictions in [('baselines_final_200', baselines), ('llm_final_200', llm)]:
        measured = router.evaluate(rows, predictions)
        if measured != read(ROOT/'results'/folder/'metrics.json'):
            raise ValueError(f'Saved metrics do not reproduce: {folder}')
        manifest = read(ROOT/'results'/folder/'run_manifest.json')
        for field in ['dataset_version', 'data_sha256', 'baseline_sha256', 'classifier_code_sha256']:
            if manifest[field] != settings[field]:
                raise ValueError(f'Run manifest mismatch: {folder}/{field}')
    for item in llm:
        if item['system'] != 'llm':
            raise ValueError('Unexpected system in LLM predictions.')
        for field in ['prompt_sha256', 'threshold', 'requested_model', 'prompt_version', 'api_provider']:
            if item[field] != settings[field]:
                raise ValueError(f'LLM configuration mismatch: {item["ticket_id"]}/{field}')
    if (ROOT/'prompts/v2.txt').read_text().strip() != router.SYSTEM_PROMPT_V2.strip():
        raise ValueError('V2 prompt snapshot does not match the actual classifier.')
    return rows, baselines + llm, router.evaluate(rows, baselines + llm)


def write_csv(path, rows, columns):
    """Write human-readable analysis, escaping cells interpreted as formulas."""
    with Path(path).open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=columns)
        w.writeheader()
        for row in rows:
            values = {k: row.get(k, '') for k in columns}
            for k, value in values.items():
                if isinstance(value, str) and value.lstrip().startswith(('=', '+', '-', '@')):
                    values[k] = "'" + value
            w.writerow(values)


def export_analysis(destination):
    """Export confusion counts, error/abstention rows and recorded telemetry."""
    rows, predictions, metrics = audit_saved()
    gold = {r['ticket_id']: r['gold_priority'] for r in rows}
    llm = [r for r in predictions if r['system'] == 'llm']
    confusion = Counter((gold[r['ticket_id']], r['final_priority']) for r in llm)
    table = {g: {p: confusion[(g, p)] for p in ['High', 'Medium', 'Low', 'Escalate']}
             for g in router.LABELS}
    annotated = [{**p, 'gold_priority': gold[p['ticket_id']]} for p in llm]
    errors = [p for p in annotated if p['final_priority'] != p['gold_priority']]
    abstained = [p for p in annotated if p['final_priority'] == 'Escalate']
    raw_errors = [p for p in annotated if p['raw_priority'] in router.LABELS
                  and p['raw_priority'] != p['gold_priority']]
    telemetry = {'recorded_api_cost_usd': sum((p.get('usage') or {}).get('cost', 0) or 0 for p in llm),
                 'mean_request_latency_seconds': statistics.mean(p['latency_seconds'] for p in llm),
                 'n': len(llm), 'raw_error_n': len(raw_errors),
                 'final_error_or_abstention_n': len(errors),
                 'cost_scope': 'Saved final-run API usage only; excludes development, labelling and hosting.'}
    destination = Path(destination); destination.mkdir(parents=True, exist_ok=True)
    for name, payload in [('metrics_comparison.json', metrics), ('llm_confusion.json', table),
                          ('recorded_telemetry.json', telemetry)]:
        run_final.write_json(destination/name, payload)
    fields = ['ticket_id', 'gold_priority', 'raw_priority', 'final_priority', 'confidence',
              'reason', 'review_trigger', 'status']
    write_csv(destination/'llm_errors.csv', errors, fields)
    write_csv(destination/'llm_abstentions.csv', abstained, fields)
    markdown = '| System | High recall | Macro-F1 | Accuracy | Escalate rate |\n|---|---:|---:|---:|---:|\n'
    for key in ['majority', 'keyword', 'llm']:
        m = metrics[key]
        markdown += f'| {key} | {m["high_recall"]:.2%} | {m["macro_f1"]:.4f} | {m["accuracy"]:.2%} | {m["escalate_rate"]:.2%} |\n'
    markdown += '\nThese metrics reproduce the saved final run. No external API was called.\n'
    (destination/'metrics_comparison.md').write_text(markdown, encoding='utf-8')
    print(markdown)
    print(f'Validated all 600 saved predictions. Analysis saved to {destination}.')
    return metrics


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=ROOT/'reruns/saved_analysis')
    args = parser.parse_args()
    return export_analysis(args.out)


if __name__ == '__main__':
    main()
