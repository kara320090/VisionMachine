"""Create a dedicated environment; never modify a shared Python installation."""
import argparse
import os
import subprocess
import sys
from pathlib import Path
from common import initialize, write_json, utc

def main(root,resume=False):
    root=initialize(root); envroot=root/'.venv'
    if envroot.exists() and not resume:
        raise RuntimeError('Environment already exists. Inspect it; do not overwrite.')
    if not envroot.exists():subprocess.run([sys.executable,'-m','venv',str(envroot)],check=True)
    os.environ['PIP_DEFAULT_TIMEOUT']='180'
    os.environ['PIP_RETRIES']='8'
    os.environ['PIP_PROGRESS_BAR']='off'
    python=str(envroot/'bin/python')
    steps=[
      [python,'-m','pip','install','torch==2.9.0','torchvision==0.24.0','--index-url','https://download.pytorch.org/whl/cu128'],
      [python,'-m','pip','install','numpy==2.2.6','Pillow==12.0.0','pandas==2.3.3',
       'scikit-learn==1.7.2','scipy==1.15.3','matplotlib==3.10.8','PyYAML==6.0.3']]
    for cmd in steps:
        print('INSTALL',cmd,flush=True)
        subprocess.run(cmd,check=True)
    freeze=subprocess.check_output([python,'-m','pip','freeze'],text=True)
    (root/'reproducibility'/'requirements.lock.txt').write_text(freeze)
    subprocess.run([python,'-m','pip','check'],check=True)
    write_json(root/'reproducibility'/'environment_install.json',
               {'completed_at':utc(),'python':python,'commands':steps,'shared_environment_modified':False},root)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--resume-install',action='store_true')
    a=p.parse_args();main(Path(a.root),a.resume_install)
