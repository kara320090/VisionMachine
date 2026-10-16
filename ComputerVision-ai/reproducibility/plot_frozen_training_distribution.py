"""Render frozen training counts without reading images or changing protocol files."""
import collections
import csv
import hashlib
import json
import os
from pathlib import Path

root = Path(__file__).resolve().parents[1]
os.environ['MPLCONFIGDIR'] = str(root / 'cache/matplotlib')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

lock = json.loads((root / 'configs/protocol_lock.json').read_text())
split = root / 'manifests/fixed_split.csv'
assert hashlib.sha256(split.read_bytes()).hexdigest() == lock['split_sha256']
cfg = json.loads((root / 'configs/common.json').read_text())
with split.open(encoding='utf-8-sig', newline='') as stream:
    rows = [r for r in csv.DictReader(stream) if r['split'] == 'train']
counts = collections.Counter((r['crop'], int(r['binary_label'])) for r in rows)
output = root / 'tables/frozen_training_distribution.csv'
with output.open('w', encoding='utf-8', newline='') as stream:
    writer = csv.writer(stream)
    writer.writerow(['crop', 'normal', 'abnormal', 'total'])
    for crop in cfg['required_crops']:
        writer.writerow([crop, counts[crop, 0], counts[crop, 1], counts[crop, 0] + counts[crop, 1]])

fig, ax = plt.subplots(figsize=(11, 5.5))
x = list(range(8))
for label, offset, color, name in [(0, -.2, '#237d91', 'Normal (0)'), (1, .2, '#d37337', 'Abnormal (1)')]:
    values = [counts[crop, label] for crop in cfg['required_crops']]
    bars = ax.bar([i + offset for i in x], values, width=.38, color=color, label=name)
    ax.bar_label(bars, fontsize=8, padding=3)
ax.set_xticks(x, cfg['required_crops'], rotation=25)
ax.set_ylabel('Training image entries')
ax.set_title(f'Frozen training population: {len(rows):,} images, 16 crop-state groups')
ax.legend()
ax.margins(y=.15)
fig.text(.5, .015, 'Counts are image entries, not independent plants. Single-AI visual labels include kale and some other normals.', ha='center', fontsize=8)
fig.tight_layout(rect=(0, .04, 1, 1))
for suffix in ('png', 'svg'):
    fig.savefig(root / f'figures/frozen_training_distribution.{suffix}', dpi=200)
plt.close(fig)
print(output)
