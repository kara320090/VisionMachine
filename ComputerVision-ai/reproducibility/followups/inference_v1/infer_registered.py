"""Versioned inference adapter using frozen registered image and cache metadata."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'code'))
from common import digest, read_csv, read_json, safe_output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--checkpoint', required=True, type=Path)
    parser.add_argument('--processed-relpath', required=True)
    args = parser.parse_args()
    from train import load_protocol
    cfg, rows, lock = load_protocol(ROOT, main=True)
    matches = [row for row in rows if row['processed_relpath'] == args.processed_relpath]
    if len(matches) != 1:
        raise ValueError('Inference requires exactly one registered frozen-manifest image')
    checkpoint = safe_output(args.checkpoint, ROOT)
    import torch
    from learning import Images, model
    torch.set_num_threads(cfg['cpu_threads'])
    state = torch.load(checkpoint, map_location='cpu', weights_only=False)
    protocol = read_json(ROOT / 'configs/protocol_lock.json')
    for key in ('config_sha256', 'split_sha256', 'code_sha256'):
        if state[key] != protocol[key]:
            raise ValueError('Checkpoint protocol mismatch: ' + key)
    done_path = checkpoint.parent.parent / 'completed.json'
    if not done_path.exists() or read_json(done_path)['best_checkpoint_sha256'] != digest(checkpoint):
        raise ValueError('Use a completed run validation-selected best checkpoint')
    image, _, _, _ = Images(matches, cfg, train=False)[0]
    net = model(False)
    net.load_state_dict(state['model'])
    net.eval()
    with torch.inference_mode():
        probabilities = net(image.unsqueeze(0)).softmax(1)[0].tolist()
    print(json.dumps({'normal': probabilities[0], 'abnormal': probabilities[1],
                      'label': int(probabilities[1] >= .5), 'threshold': .5,
                      'checkpoint_sha256': digest(checkpoint),
                      'adapter_version': 'inference_v1'}))


if __name__ == '__main__':
    main()
