import argparse
import importlib.metadata
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from common import *

def main(root):
    root=initialize(root)
    import torch, torchvision
    result={'created_at':utc(),'hostname':platform.node(),'platform':platform.platform(),
            'python':sys.version,'executable':sys.executable,'prefix':sys.prefix,
            'packages':{n:importlib.metadata.version(n) for n in ['torch','torchvision','numpy','Pillow','pandas','scikit-learn','scipy','matplotlib','PyYAML']},
            'cuda_runtime':torch.version.cuda,'cuda_available':torch.cuda.is_available(),
            'cudnn':torch.backends.cudnn.version(),'cpu_count':os.cpu_count(),
            'gpu':subprocess.check_output(['nvidia-smi','--query-gpu=name,memory.total,memory.used,driver_version','--format=csv'],text=True),
            'disk':{str(p):shutil.disk_usage(p)._asdict() for p in [root,DATA]},
            'torch_home':os.environ['TORCH_HOME'],'code_sha256':code_hash()}
    write_json(root/'reproducibility'/'environment.json',result,root)
    print(json.dumps(result,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);main(Path(p.parse_args().root))
