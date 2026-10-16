"""Temporarily suspend only our read-only hash job during IO timing."""
import argparse
import os
import signal
import subprocess
import sys
from pathlib import Path
from common import *

def ours(pid,root):
    try:
        p=Path(f'/proc/{pid}')
        args=(p/'cmdline').read_bytes().split(b'\0')
        return p.stat().st_uid==os.getuid() and str(root).encode() in args and any(a.endswith(b'verify_source.py') for a in args)
    except FileNotFoundError:return False

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--hash-pid',type=int,required=True);a=p.parse_args();root=initialize(a.root)
    paused=ours(a.hash_pid,root)
    def interrupted(*args):raise KeyboardInterrupt('Graceful diagnostic interruption')
    signal.signal(signal.SIGTERM,interrupted)
    if paused:os.kill(a.hash_pid,signal.SIGSTOP)
    try:
        subprocess.run([sys.executable,'-B','-u',str(root/'code'/'io_speed_check.py'),'--root',str(root)],check=True)
    finally:
        if paused and ours(a.hash_pid,root):os.kill(a.hash_pid,signal.SIGCONT)
        write_json(root/'reproducibility'/'io_isolation.json',{'time':utc(),'hash_job_temporarily_paused':paused,'hash_pid':a.hash_pid,'resume_requested':paused},root)
