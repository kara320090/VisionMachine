"""Recompute A/B/C discussion from frozen public predictions, without training."""
from pathlib import Path
from collections import Counter
import csv
import json
import math
import statistics as stats

ROOT = Path(__file__).resolve().parents[2]
SEEDS = (17, 42, 2026)
CROPS = ('basil', 'bok_choy', 'cucumber', 'kale', 'lettuce', 'pepper', 'rosemary', 'tomato')


def read_csv(path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def metrics(rows):
    cm = Counter((int(r['binary_label']), int(float(r['p_abnormal']) >= .5)) for r in rows)
    tn, fp, fn, tp = (cm[0, 0], cm[0, 1], cm[1, 0], cm[1, 1])
    normal_f1 = 2 * tn / (2 * tn + fp + fn)
    abnormal_f1 = 2 * tp / (2 * tp + fp + fn)
    return {'macro_f1': (normal_f1 + abnormal_f1) / 2,
            'abnormal_recall': tp / (tp + fn), 'normal_fpr': fp / (fp + tn)}


def summarize(values, scale=100):
    return {'mean': scale * stats.mean(values), 'sample_sd': scale * stats.stdev(values),
            'by_seed': {str(s): scale * v for s, v in zip(SEEDS, values)}}


def reproduce():
    scores = {}
    population = None
    for condition in 'ABC':
        for seed in SEEDS:
            rows = read_csv(ROOT / f'evaluation/{condition}_seed{seed}/predictions.csv')
            current = {r['image_id']: (r['crop'], r['binary_label'], r['leakage_group_id']) for r in rows}
            assert len(rows) == len(current) == 1884
            if population is None:
                population = current
            assert current == population, 'Paired evaluation populations differ'
            crops = {c: metrics([r for r in rows if r['crop'] == c]) for c in CROPS}
            scores[condition, seed] = {
                'equal_crop': stats.mean(crops[c]['macro_f1'] for c in CROPS),
                'pooled': metrics(rows)['macro_f1'], 'crops': crops,
            }
    condition_summary = {c: {m: summarize([scores[c, s][m] for s in SEEDS])
                             for m in ('equal_crop', 'pooled')} for c in 'ABC'}
    comparisons = {}
    for a, b in (('B', 'A'), ('C', 'B'), ('C', 'A')):
        comparisons[a + '-' + b] = {
            **{m: summarize([scores[a, s][m] - scores[b, s][m] for s in SEEDS])
               for m in ('equal_crop', 'pooled')},
            'per_crop': {c: summarize([scores[a, s]['crops'][c]['macro_f1'] - scores[b, s]['crops'][c]['macro_f1'] for s in SEEDS]) for c in CROPS},
        }
    # Validate against the separately archived published table, not hard-coded new results.
    metric_names = {'equal_crop_binary_macro_f1': 'equal_crop', 'pooled_binary_macro_f1': 'pooled'}
    for row in read_csv(ROOT / 'tables/abc_summary.csv'):
        if row['metric'] in metric_names:
            computed = condition_summary[row['condition']][metric_names[row['metric']]]
            for k, field in (('mean', 'mean'), ('sample_sd', 'sample_sd')):
                assert math.isclose(computed[k], 100 * float(row[field]), abs_tol=1e-10)
    for row in read_csv(ROOT / 'tables/paired_deltas.csv'):
        block = comparisons[row['comparison']]
        computed = block['equal_crop'] if row['crop'] == 'ALL_EQUAL_CROP' else block['per_crop'][row['crop']]
        assert math.isclose(computed['mean'], float(row['mean_percentage_points']), abs_tol=1e-10)
        assert math.isclose(computed['sample_sd'], float(row['sample_sd_percentage_points']), abs_tol=1e-10)
    split = json.loads((ROOT / 'provenance/SPLIT_SUMMARY.json').read_text(encoding='utf-8'))
    counts = split['crop_state_counts']['train']
    n = sum(counts.values())
    state_counts = {str(y): sum(v for k, v in counts.items() if k.endswith(':' + str(y))) for y in (0, 1)}
    assert n == 34622 and len(counts) == 16
    group_weight_mass = {}
    for condition in 'ABC':
        group_weight_mass[condition] = {}
        for key, count in counts.items():
            y = key.split(':')[1]
            weight = 1 if condition == 'A' else n / (2 * state_counts[y]) if condition == 'B' else n / (16 * count)
            group_weight_mass[condition][key] = count * weight
        assert math.isclose(sum(group_weight_mass[condition].values()), n, abs_tol=1e-8)
    crop_details = {c: {crop: {m: summarize([scores[c, s]['crops'][crop][m] for s in SEEDS])
                               for m in ('macro_f1', 'abnormal_recall', 'normal_fpr')}
                       for crop in CROPS} for c in 'ABC'}
    return {'description': 'Fixed public test predictions; no training, label editing, model loading or new independent test.',
            'unit': 'percent for scores; percentage points for paired differences',
            'seeds': list(SEEDS), 'test_images': 1884, 'threshold': .5,
            'condition_summary': condition_summary, 'comparisons': comparisons,
            'crop_details': crop_details, 'training_images': n,
            'training_state_counts': state_counts,
            'B_per_image_weights': {y: n / (2 * count) for y, count in state_counts.items()},
            'group_weight_mass': group_weight_mass,
            'weight_mass_note': 'Sum of sample weights, not observed loss or gradient; those also depend on predictions.',
            'C_minus_B_crop_signs': {label: sum(predicate(comparisons['C-B']['per_crop'][c]['mean']) for c in CROPS)
                                   for label, predicate in [('positive', lambda x: x > 1e-10), ('zero', lambda x: abs(x) <= 1e-10), ('negative', lambda x: x < -1e-10)]}}


if __name__ == '__main__':
    print(json.dumps(reproduce(), ensure_ascii=False, indent=2, sort_keys=True))
