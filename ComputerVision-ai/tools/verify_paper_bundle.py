"""Verify the selected paper bundle without executing archived code or loading models."""
from pathlib import Path
from collections import Counter, defaultdict
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote
import argparse
import ast
import csv
import hashlib
import json
import math
import re
import statistics

ROOT = Path(__file__).resolve().parents[1]


def rows(path):
    with path.open(encoding='utf-8-sig', newline='') as handle:
        yield from csv.DictReader(handle)


def data(relative):
    return json.loads((ROOT/relative).read_text(encoding='utf-8-sig'))


def digest(path):
    value=hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda:handle.read(1024*1024),b''):value.update(chunk)
    return value.hexdigest()


def require(value, message):
    if not value:raise ValueError(message)


def close(a,b,message):
    require(math.isclose(float(a),float(b),rel_tol=0,abs_tol=1e-10),message)


def metrics(records):
    counts=Counter((int(r['binary_label']),int(float(r['p_abnormal'])>=.5)) for r in records)
    tn,fp,fn,tp=(counts[0,0],counts[0,1],counts[1,0],counts[1,1])
    normal=2*tn/(2*tn+fn+fp) if 2*tn+fn+fp else 0
    abnormal=2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0
    return {'n':len(records),'tn':tn,'fp':fp,'fn':fn,'tp':tp,'normal_f1':normal,'abnormal_f1':abnormal,
            'binary_macro_f1':(normal+abnormal)/2,'accuracy':(tn+tp)/len(records),
            'abnormal_recall':tp/(tp+fn),'normal_false_positive_rate':fp/(fp+tn)}


def verify(require_all_models=False):
    manifest=list(rows(ROOT/'provenance/PUBLIC_FILES.csv'))
    declared={r['path']:r for r in manifest}
    actual={p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file()}
    require(len(declared)==len(manifest) and actual==declared.keys()|{'provenance/PUBLIC_FILES.csv'},'File coverage')
    hashes={}
    for name,row in declared.items():
        path=(ROOT/name).resolve()
        require(path.is_relative_to(ROOT),'Path escapes bundle')
        require(path.stat().st_size==int(row['bytes']),'Size: '+name)
        hashes[name]=digest(path)
        require(hashes[name]==row['sha256'],'SHA-256: '+name)
        require(path.stat().st_size<100*1024*1024,'GitHub individual file limit: '+name)
        require(path.suffix.lower() not in {'.zip','.tar','.lnk'},'Excluded file: '+name)
    for forbidden in ['fixed_split.csv','provisional_review_manifest.csv','research_inventory.csv','image_inventory.csv','image_cache_full.csv','weights.csv']:
        require(not any(Path(p).name==forbidden for p in actual),'Excluded detailed inventory: '+forbidden)
    lock=data('configs/protocol_lock.json');config=data('configs/common.json')
    require(hashes['configs/common.json']==lock['config_sha256'],'Frozen configuration')
    code=hashlib.sha256()
    for path in sorted((ROOT/'code').rglob('*.py')):
        code.update(path.relative_to(ROOT/'code').as_posix().encode());code.update(path.read_bytes())
    require(code.hexdigest()==lock['code_sha256'],'Frozen code')
    split=data('provenance/SPLIT_SUMMARY.json')
    require(split['fixed_split_sha256']==lock['split_sha256'],'Recorded original split hash')
    train_counts=split['crop_state_counts']['train'];train_n=sum(train_counts.values())
    require(train_n==34622,'Training aggregate count')
    state_counts=Counter()
    for key,count in train_counts.items():state_counts[key.split(':')[1]]+=count
    weights=list(rows(ROOT/'audit/curated_data_report/actual_training_weights.csv'))
    require(len(weights)==16,'16 crop-state weight summaries')
    for row in weights:
        count=train_counts[row['crop']+':'+row['binary_label']]
        require(count==int(row['train_images']),'Training weight population')
        for condition,value in [('A',1),('B',train_n/(2*state_counts[row['binary_label']])),('C',train_n/(16*count))]:
            close(row[condition+'_weight'],value,'Weight formula '+condition)
    registry=list(rows(ROOT/'provenance/MODELS.csv'))
    require(len(registry)==9,'Nine model registry entries')
    included={r['path'] for r in registry if r['included_in_commit']=='true'}
    require(included=={p for p in actual if p.endswith('.pt')},'Model availability registry')
    if require_all_models:require(len(included)==9,'All nine selected models must be included')
    completed_initial=defaultdict(set);runs={};populations=[]
    epochs=updates=skips=0
    for model in registry:
        name=model['run'];condition=model['condition'];seed=int(model['seed'])
        require(name==f'{condition}_seed{seed}' and condition in {'A','B','C'} and seed in {17,42,2026},'Run identity')
        complete=data(f'runs/{name}/completed.json')
        require(complete['best_checkpoint_sha256']==model['sha256'],'Registered selected checkpoint hash')
        if model['path'] in included:require(hashes[model['path']]==model['sha256'],'Selected model bytes: '+name)
        for key in ['code_sha256','config_sha256','split_sha256']:require(complete[key]==lock[key],'Run lock '+name)
        completed_initial[seed].add(complete['initial_model_sha256'])
        history=[json.loads(line) for line in (ROOT/f'runs/{name}/history.jsonl').read_text(encoding='utf-8-sig').splitlines() if line]
        require([r['epoch'] for r in history]==list(range(1,31)),'Epoch sequence '+name)
        chosen=max(history,key=lambda r:(r['validation']['equal_crop_binary_macro_f1'],-r['epoch']))
        require(chosen['epoch']==complete['selected_epoch']==int(model['selected_epoch']),'Validation selection '+name)
        for row in history:
            require(row['updates']+row['amp_skips']==row['epoch']*math.ceil(train_n/config['batch_size']),'Update accounting '+name)
            expected=[config['classifier_lr']] if row['epoch']<=2 else [config['backbone_lr'],config['classifier_lr']]
            if row['epoch']>2:
                progress=(row['epoch']-3)/27
                factor=config['final_lr_ratio']+(1-config['final_lr_ratio'])*(1+math.cos(math.pi*progress))/2
                expected=[v*factor for v in expected]
            require(len(row['lr'])==len(expected),'Learning-rate groups')
            for a,b in zip(row['lr'],expected):close(a,b,'Learning-rate schedule '+name)
        require(history[-1]['updates']==complete['updates'] and history[-1]['amp_skips']==complete['amp_skips'],'Completion accounting')
        epochs+=30;updates+=complete['updates'];skips+=complete['amp_skips']
        predictions=list(rows(ROOT/f'evaluation/{name}/predictions.csv'))
        require(len(predictions)==1884,'Test count '+name)
        population={(r['image_id'],r['crop'],r['binary_label']) for r in predictions}
        require(len(population)==1884,'Unique test population '+name);populations.append(population)
        require(all(0<=float(r['p_abnormal'])<=1 for r in predictions),'Probability range')
        per_crop={crop:metrics([r for r in predictions if r['crop']==crop]) for crop in config['required_crops']}
        pooled=metrics(predictions)
        result={'equal_crop_binary_macro_f1':statistics.mean(m['binary_macro_f1'] for m in per_crop.values()),
                'pooled_binary_macro_f1':pooled['binary_macro_f1'],'overall_accuracy':pooled['accuracy']}
        saved=data(f'evaluation/{name}/metrics.json')
        for key,value in result.items():close(value,saved[key],'Metric '+name+' '+key)
        for crop,values in per_crop.items():
            for key,value in values.items():close(value,saved['per_crop'][crop][key],'Crop metric '+name+' '+crop+' '+key)
        close(result['equal_crop_binary_macro_f1'],model['test_equal_crop_macro_f1'],'Registered model metric')
        runs[name]={**result,'per_crop':per_crop}
    require(all(len(v)==1 for v in completed_initial.values()),'Same initialization within seed')
    require(all(pop==populations[0] for pop in populations),'Same test population across all runs')
    for row in rows(ROOT/'tables/abc_summary.csv'):
        values=[runs[f"{row['condition']}_seed{seed}"][row['metric']] for seed in config['training_seeds']]
        close(statistics.mean(values),row['mean'],'Aggregate mean');close(statistics.stdev(values),row['sample_sd'],'Aggregate SD')
    for row in rows(ROOT/'tables/crop_metrics.csv'):
        values=[runs[f"{row['condition']}_seed{seed}"]['per_crop'][row['crop']][row['metric']] for seed in config['training_seeds']]
        close(statistics.mean(values),row['mean'],'Crop aggregate mean');close(statistics.stdev(values),row['sample_sd'],'Crop aggregate SD')
    for row in rows(ROOT/'tables/paired_deltas.csv'):
        a,b=row['comparison'].split('-')
        def value(condition,seed):
            run=runs[f'{condition}_seed{seed}']
            return run['equal_crop_binary_macro_f1'] if row['crop']=='ALL_EQUAL_CROP' else run['per_crop'][row['crop']]['binary_macro_f1']
        values=[100*(value(a,seed)-value(b,seed)) for seed in config['training_seeds']]
        close(statistics.mean(values),row['mean_percentage_points'],'Paired delta mean');close(statistics.stdev(values),row['sample_sd_percentage_points'],'Paired delta SD')
    links=[]
    class Links(HTMLParser):
        def handle_starttag(self,tag,attrs):
            for key,value in attrs:
                if key in {'href','src'} and value and not value.startswith('#'):
                    parsed=urlsplit(value)
                    if not parsed.scheme and not parsed.netloc and parsed.path:
                        require((self.path.parent/unquote(parsed.path)).is_file(),'HTML link '+str(self.path)+' '+value);links.append(value)
    for path in ROOT.rglob('*.html'):
        parser=Links();parser.path=path;parser.feed(path.read_text(encoding='utf-8-sig'))
    for link in re.findall(r'\]\(([^)]+)\)',(ROOT/'README.md').read_text(encoding='utf-8')):
        require(link.startswith('https:') or (ROOT/link.split('#')[0]).exists(),'README link '+link)
    python_files=list(ROOT.rglob('*.py'))
    for path in python_files:ast.parse(path.read_text(encoding='utf-8-sig'),filename=str(path))
    return {'status':'passed','public_files':len(actual),'public_bytes':sum(p.stat().st_size for p in ROOT.rglob('*') if p.is_file()),
            'selected_model_count':9,'included_model_count':len(included),'epochs_checked':epochs,'test_predictions_checked':9*1884,
            'optimizer_updates':updates,'amp_skips':skips,'aggregate_weight_rows_checked':len(weights),'html_local_links_checked':len(links),
            'python_syntax_files_checked':len(python_files),'source_split_inventory_published':False,'checkpoint_loading_or_training_executed':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--require-all-models',action='store_true')
    print(json.dumps(verify(parser.parse_args().require_all_models),ensure_ascii=False,indent=2))
