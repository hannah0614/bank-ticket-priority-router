"""Run frozen final evaluation and save each live prediction immediately.

No gold label enters the classifier. API failures stop without a fabricated
prediction. Rerunning resumes saved tickets only when all frozen inputs match.
New runs default to reruns/final_200; submitted results are never overwritten.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import ticket_router as router

ROOT=Path(__file__).resolve().parent

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def write_json(path,value):
    """Atomically replace a JSON checkpoint; never store an API key."""
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
    temp.replace(path)

def frozen_inputs():
    """Verify the reviewed test set, original classifier and frozen baselines."""
    lock=json.loads((ROOT/'data/test_freeze.json').read_text(encoding='utf-8'))
    for name,field in [('data/test.csv','data_sha256'),('ticket_router.py','classifier_code_sha256'),('baseline_frozen.json','baseline_frozen_file_sha256')]:
        if sha(ROOT/name)!=lock[field]:
            raise ValueError(f'Frozen file changed: {name}. Do not silently compare a different run.')
    rows=router.load_data(ROOT/'data/test.csv')
    if len(rows)!=200 or Counter(r['gold_priority'] for r in rows)!=lock['label_counts']:
        raise ValueError('Expected 200 confirmed labels with the frozen class counts.')
    frozen=json.loads((ROOT/'baseline_frozen.json').read_text(encoding='utf-8'))
    settings={'dataset_version':lock['dataset_version'],'data_sha256':lock['data_sha256'],
        'baseline_sha256':router.digest(frozen),'classifier_code_sha256':lock['classifier_code_sha256'],
        'prompt_sha256':router.digest(router.SYSTEM_PROMPT_V2),'prompt_version':'v2',
        'threshold':0.80,'api_provider':'openrouter','requested_model':'openai/gpt-4o-mini',
        'label_provenance':'AI-assisted suggestions manually reviewed and confirmed unchanged by user'}
    return rows,frozen,settings

def batch_llm(rows,settings,directory,predictor=None):
    """Resume exact predictions; a failed call leaves its ticket unfinished."""
    predictor=predictor or router.llm_predict
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    marker=directory/'checkpoint_manifest.json';cache=directory/'predictions.json'
    if marker.exists():
        if json.loads(marker.read_text())!=settings:
            raise ValueError('Checkpoint uses different data/model/prompt/threshold. Keep runs separate.')
    elif cache.exists():
        raise ValueError('Prediction cache exists without its configuration marker.')
    else:write_json(marker,settings)
    items=json.loads(cache.read_text()) if cache.exists() else []
    allowed={r['ticket_id'] for r in rows}
    ids=[r['ticket_id'] for r in items]
    if len(ids)!=len(set(ids)) or not set(ids)<=allowed or any(r['system']!='llm' for r in items):
        raise ValueError('Checkpoint IDs are duplicated, unknown, or from a different system.')
    done=set(ids)
    for index,row in enumerate(rows,1):
        if row['ticket_id'] in done:continue
        # This call intentionally receives only text, never the answer key.
        prediction=predictor(row['text'],threshold=settings['threshold'],provider=settings['api_provider'],
            model=settings['requested_model'],prompt_version=settings['prompt_version'])
        items.append({'ticket_id':row['ticket_id'],'system':'llm',**prediction})
        write_json(cache,items)
        print(f"{len(items)}/{len(rows)} {row['ticket_id']}: {prediction['final_priority']}",flush=True)
    by_id={r['ticket_id']:r for r in items}
    return [by_id[r['ticket_id']] for r in rows]

def finish(rows,items,settings,directory):
    """Write full-set metrics only after every labelled ticket has a result."""
    metrics=router.evaluate(rows,items)
    directory=Path(directory)
    write_json(directory/'predictions.json',items)
    write_json(directory/'metrics.json',metrics)
    write_json(directory/'run_manifest.json',{**settings,'rows':len(rows),'labelled_rows':len(rows),
        'unlabelled_rows':0,'prediction_records':len(items),'evaluation_status':'complete'})
    print(json.dumps(metrics,ensure_ascii=False,indent=2))
    print('Saved:',directory)
    return metrics

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['baselines','llm'])
    p.add_argument('--output-dir',type=Path,default=ROOT/'reruns/final_200',
        help='New baseline/LLM run directory; must be outside submitted results/.')
    args=p.parse_args()
    output=args.output_dir.resolve()
    submitted=(ROOT/'results').resolve()
    if output==submitted or submitted in output.parents:
        p.error('Use a separate output directory. Submitted results/ is read-only evidence.')
    rows,frozen,settings=frozen_inputs()
    if args.action=='baselines':
        items=router.baseline_results(rows,frozen)
        settings={**settings,'action':'baselines','api_provider':None,'requested_model':None,'prompt_version':None,'prompt_sha256':None,'threshold':None}
        finish(rows,items,settings,output/'baselines_final_200')
    else:
        directory=output/'llm_final_200'
        try:items=batch_llm(rows,{**settings,'action':'llm'},directory)
        except (RuntimeError,ValueError) as exc:
            print('Stopped:',str(exc))
            print('Saved predictions are retained. Fix the issue and rerun the same command to resume.')
            raise SystemExit(1) from None
        finish(rows,items,{**settings,'action':'llm'},directory)

if __name__=='__main__':main()
