"""Explicit scenario estimates from measured compute and source IO diagnostics."""
import argparse
import math
from pathlib import Path
from common import *

def run(root,cached=False):
    root=initialize(root);models=read_json(root/'reproducibility'/'model_speed_comparison_v2.json')
    io_path=root/'reproducibility'/('io_speed_cached.json' if cached else 'io_speed_diagnostic.json')
    if cached and not io_path.exists():io_path=root/'reproducibility'/'io_speed_cached_available.json'
    io=read_json(io_path)
    suffix='_cached' if cached else ''
    n=read_json(root/'audit'/'summary.json')['unique_sha256']
    nv=round(n*.2);nt=n-2*nv;rows=[]
    train_rate=io['results'][0]['images_per_second'];eval_rate=io['results'][1]['images_per_second']
    for r in models['results']:
        train_io=nt/train_rate;val_io=nv/eval_rate
        train_gpu=math.ceil(nt/64)*r['mean_step_seconds'];val_gpu=math.ceil(nv/64)*r['inference_batch64_seconds']
        optimistic=30*(max(train_io,train_gpu)+max(val_io,val_gpu))+max(val_io,val_gpu)
        serial=30*(train_io+train_gpu+val_io+val_gpu)+val_io+val_gpu
        rows.append({'model':r['model'],'training_step_ms_batch64':1000*r['mean_step_seconds'],
            'one_image_gpu_inference_ms':1000*r['inference_single_image_seconds'],
            'training_images_assumed':nt,'validation_images_assumed':nv,'test_images_assumed':nv,
            'one_run_30_epochs_overlap_hours':optimistic/3600,'one_run_30_epochs_serial_hours':serial/3600,
            'nine_runs_overlap_hours':9*optimistic/3600,'nine_runs_serial_hours':9*serial/3600,
            'one_run_planning_low_hours':optimistic*1.10/3600,'one_run_planning_high_hours':serial*1.30/3600,
            'nine_runs_planning_low_hours':9*optimistic*1.10/3600,'nine_runs_planning_high_hours':9*serial*1.30/3600,
            'all_images_inference_gpu_only_seconds':math.ceil(n/64)*r['inference_batch64_seconds'],
            'all_images_inference_io_plus_compute_seconds':n/eval_rate+math.ceil(n/64)*r['inference_batch64_seconds']})
    write_csv(root/'tables'/f'model_time_scenarios{suffix}.csv',rows,root)
    result={'created_at':utc(),'scenario':'Current processed unique SHA count, hypothetical 60/20/20; NOT the final reviewed split',
        'input_images':n,'raw_candidates_included':False,'epochs':30,'runs_per_model':9,'gpu':'RTX 4090',
        'io_diagnostic_file':str(io_path.relative_to(root)),'uses_resized_png_cache':cached,
        'train_io_images_per_second':train_rate,'evaluation_io_images_per_second':eval_rate,
        'measured':'Short GPU-resident synthetic model timings and separate 4096-image existing-source loader timings',
        'estimated':'30 epochs and nine runs; no full real-data training run has been measured',
        'planning_margin':'10% above perfect IO/compute overlap through 30% above serial IO+compute. Assumed scheduling/checkpoint allowance, NOT a confidence interval.',
        'limitations':['Final reviewed counts/scene representatives may be smaller; approved raw additions may increase counts.',
                       'Uses full fine-tuning step timing for all 30 epochs; actual first two epochs freeze the backbone.',
                       'Source IO sample, cache state, JPEG sizes, GPU occupancy and transfer speed can change wall time.',
                       'Same B0 bicubic image pipeline held fixed for resource comparison; model-specific deployment transforms may differ.',
                       'Does not estimate label adjudication time, model accuracy, or time to scientific approval.'],
        'results':rows}
    write_json(root/'reproducibility'/f'model_time_estimates{suffix}.json',result,root)
    table='\n'.join(f"{r['model']}: 30epoch {r['one_run_planning_low_hours']:.2f}-{r['one_run_planning_high_hours']:.2f} h; 9runs {r['nine_runs_planning_low_hours']:.2f}-{r['nine_runs_planning_high_hours']:.2f} h; one-image GPU {r['one_image_gpu_inference_ms']:.2f} ms" for r in rows)
    (root/'reproducibility'/f'MODEL_TIMING{suffix}.txt').write_text(json.dumps({k:v for k,v in result.items() if k!='results'},ensure_ascii=False,indent=2)+'\n\n'+table,encoding='utf-8')
    print(json.dumps(result,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--cached',action='store_true');a=p.parse_args();run(Path(a.root),a.cached)
