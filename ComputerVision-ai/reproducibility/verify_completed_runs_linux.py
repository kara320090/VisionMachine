"""Read completed artifacts independently; never launch training or edit frozen inputs."""
import collections
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def read_csv(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def binary_metrics(rows):
    tn = fp = fn = tp = 0
    for row in rows:
        p = float(row['p_abnormal'])
        assert math.isfinite(p) and 0 <= p <= 1
        y = int(row['binary_label'])
        assert y in (0, 1)
        prediction = int(p >= .5)
        tn += y == 0 and prediction == 0
        fp += y == 0 and prediction == 1
        fn += y == 1 and prediction == 0
        tp += y == 1 and prediction == 1
    assert rows
    return {'n': len(rows), 'tn': tn, 'fp': fp, 'fn': fn, 'tp': tp,
            'normal_f1': 2 * tn / (2 * tn + fp + fn) if 2 * tn + fp + fn else 0.,
            'abnormal_f1': 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.}


def main():
    cfg = read_json(ROOT / 'configs/common.json')
    lock = read_json(ROOT / 'configs/protocol_lock.json')
    assert digest(ROOT / 'configs/common.json') == lock['config_sha256']
    assert digest(ROOT / 'manifests/fixed_split.csv') == lock['split_sha256']
    code = hashlib.sha256()
    for path in sorted((ROOT / 'code').rglob('*.py')):
        code.update(str(path.relative_to(ROOT / 'code')).encode())
        code.update(path.read_bytes())
    assert code.hexdigest() == lock['code_sha256']
    rows = read_csv(ROOT / 'manifests/fixed_split.csv')
    train = [row for row in rows if row['split'] == 'train']
    test = {row['image_id']: row for row in rows if row['split'] == 'test'
            and row['evaluation_representative'].lower() == 'true'}
    n = len(train)
    states = collections.Counter(row['binary_label'] for row in train)
    groups = collections.Counter((row['crop'], row['binary_label']) for row in train)
    initial_hashes = {}
    results = []
    for seed in cfg['training_seeds']:
        for condition in 'ABC':
            name = f'{condition}_seed{seed}'
            folder = ROOT / 'runs' / name
            if not (folder / 'completed.json').exists():
                results.append({'run': name, 'status': 'not_completed'})
                continue
            done = read_json(folder / 'completed.json')
            history = read_json(folder / 'history.json')
            assert done['epochs'] == cfg['epochs'] == 30
            assert [row['epoch'] for row in history] == list(range(1, 31))
            assert done['condition'] == condition and done['seed'] == seed
            for key in ('config_sha256', 'split_sha256', 'code_sha256'):
                assert done[key] == lock[key]
            selected = max(history, key=lambda row: row['validation']['equal_crop_binary_macro_f1'])
            assert done['selected_epoch'] == selected['epoch']
            assert done['best_validation_equal_crop_binary_macro_f1'] == selected['validation']['equal_crop_binary_macro_f1']
            assert digest(folder / 'checkpoints/best.pt') == done['best_checkpoint_sha256']
            assert done['updates'] + done['amp_skips'] == cfg['epochs'] * math.ceil(n / cfg['batch_size'])
            assert math.isfinite(done['elapsed_seconds']) and done['elapsed_seconds'] > 0
            if seed in initial_hashes:
                assert initial_hashes[seed] == done['initial_model_sha256']
            initial_hashes[seed] = done['initial_model_sha256']
            weights = read_csv(folder / 'weights.csv')
            assert len(weights) == n
            for row, weight in zip(train, weights):
                assert all(row[key] == weight[key] for key in ('image_id', 'crop', 'binary_label'))
                expected = (1. if condition == 'A' else n / (2 * states[row['binary_label']])
                            if condition == 'B' else n / (16 * groups[row['crop'], row['binary_label']]))
                assert math.isclose(float(weight['weight']), expected, rel_tol=1e-12)
            evaluation = ROOT / 'evaluation' / name
            test_verified = False
            if (evaluation / 'metrics.json').exists():
                metrics = read_json(evaluation / 'metrics.json')
                predictions = read_csv(evaluation / 'predictions.csv')
                assert len(predictions) == len(test) and {row['image_id'] for row in predictions} == set(test)
                for row in predictions:
                    assert all(row[key] == test[row['image_id']][key] for key in ('crop', 'binary_label', 'leakage_group_id'))
                assert metrics['threshold'] == .5 and metrics['selected_epoch'] == done['selected_epoch']
                assert metrics['checkpoint_sha256'] == done['best_checkpoint_sha256']
                assert metrics['split_sha256'] == lock['split_sha256']
                assert set(metrics['per_crop']) == set(cfg['required_crops'])
                crop_f1 = []
                for crop in cfg['required_crops']:
                    values = binary_metrics([row for row in predictions if row['crop'] == crop])
                    for key, value in values.items():
                        assert math.isclose(metrics['per_crop'][crop][key], value, abs_tol=1e-12)
                    crop_f1.append((values['normal_f1'] + values['abnormal_f1']) / 2)
                pooled = binary_metrics(predictions)
                assert math.isclose(metrics['equal_crop_binary_macro_f1'], sum(crop_f1) / 8, abs_tol=1e-12)
                assert math.isclose(metrics['pooled_binary_macro_f1'], (pooled['normal_f1'] + pooled['abnormal_f1']) / 2, abs_tol=1e-12)
                assert math.isclose(metrics['overall_accuracy'], (pooled['tn'] + pooled['tp']) / pooled['n'], abs_tol=1e-12)
                test_verified = True
            results.append({'run': name, 'status': 'completed_artifacts_verified',
                            'selected_epoch': done['selected_epoch'], 'test_verified': test_verified})
    report = {'checked_at': datetime.now(timezone.utc).isoformat(), 'runs': results,
              'all_nine_training_verified': sum(row['status'] == 'completed_artifacts_verified' for row in results) == 9,
              'all_nine_test_verified': sum(row.get('test_verified', False) for row in results) == 9,
              'delivery_verified': False,
              'scope': 'Completed run integrity and prediction-derived metrics. Does not prove figures, paper, source preservation or destination delivery.'}
    (ROOT / 'reproducibility/completed_runs_integrity_linux.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
