"""Finish cache diagnostics and resume our deferred source hash verification."""
import argparse
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from common import *

def run(root,job,hash_pid):
    root=initialize(root);status=None
    try:
        while True:
            status=read_json(Path('/home/user/codex_gpu_jobs/runs')/job/'status.json')
            if status.get('state') in ('completed','failed','stopped'):break
            time.sleep(20)
    finally:
        proc=Path(f'/proc/{hash_pid}')
        try:
            args=(proc/'cmdline').read_bytes().split(b'\0')
            if proc.stat().st_uid==os.getuid() and str(root).encode() in args and any(a.endswith(b'verify_source.py') for a in args):
                os.kill(hash_pid,signal.SIGCONT)
                write_json(root/'reproducibility'/'preservation_resumed.json',{'at':utc(),'pid':hash_pid,'reason':'Cache reached terminal state'},root)
        except FileNotFoundError:pass
    if status['state']!='completed':raise RuntimeError('Cache failed; do not enable incomplete cache')
    subprocess.run([sys.executable,'-B','-u',str(root/'code'/'io_speed_check.py'),'--root',str(root),'--cache'],check=True)
    cfg=read_json(root/'configs'/'common.json')
    from image_cache import RECIPE_ID,RECIPE
    if (root/'configs'/'protocol_lock.json').exists():raise ValueError('Cannot change frozen protocol')
    cfg['image_cache_root']={'experiment_root':str(root),'recipe_id':RECIPE_ID}
    cfg['input_cache_recipe']=RECIPE
    write_json(root/'configs'/'common.json',cfg,root)
    write_json(root/'reproducibility'/'cache_ready.json',{'at':utc(),'recipe_id':RECIPE_ID,
        'all_candidates_cached':True,'research_training_started':False,'label_gate_still_required':True},root)
    print('Cache ready. No research run launched without the label/split gate.',flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--cache-job',required=True);p.add_argument('--hash-pid',type=int,required=True);a=p.parse_args();run(Path(a.root),a.cache_job,a.hash_pid)
