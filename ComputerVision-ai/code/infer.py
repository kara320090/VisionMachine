"""Inference accepts an image only, with no crop input."""
import argparse
from pathlib import Path
from common import *

def main(root,checkpoint,relpath):
    root=initialize(root)
    import torch
    from learning import model,Images
    cfg=read_json(root/'configs'/'common.json')
    ck=safe_output(checkpoint,root)
    net=model(False);net.load_state_dict(torch.load(ck,map_location='cpu',weights_only=False)['model']);net.eval()
    # Metadata below is a dataset-adapter placeholder, never a model input.
    ds=Images([{'image_id':'inference','processed_relpath':relpath,'binary_label':0}],cfg)
    with torch.inference_mode():p=net(ds[0][0].unsqueeze(0)).softmax(1)[0].tolist()
    print(json.dumps({'normal':p[0],'abnormal':p[1],'label':int(p[1]>=.5)}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--checkpoint',required=True);p.add_argument('--processed-relpath',required=True)
    a=p.parse_args();main(Path(a.root),Path(a.checkpoint),a.processed_relpath)
