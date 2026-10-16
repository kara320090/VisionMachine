import argparse
import unittest
from pathlib import Path
from common import *

def run(root):
    root=initialize(root)
    import test_pipeline
    suite=unittest.defaultTestLoader.loadTestsFromModule(test_pipeline)
    path=root/'reproducibility'/'test_results.txt'
    with path.open('w') as stream:result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    print(path.read_text())
    write_json(root/'reproducibility'/'test_results.json',{'checked_at':utc(),'run':result.testsRun,
        'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),'passed':result.wasSuccessful(),
        'code_sha256':code_hash()},root)
    return 0 if result.wasSuccessful() else 1

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);raise SystemExit(run(Path(p.parse_args().root)))
