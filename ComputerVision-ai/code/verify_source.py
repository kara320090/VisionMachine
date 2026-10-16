"""Detect source edits without changing image/label/link content."""
import argparse
import concurrent.futures
from pathlib import Path
from common import *

def verify(root,full=False):
    rows=read_csv(research_inventory(root))
    def one(r):
        p=input_path(r['processed_relpath']);problems=[]
        try:
            st=p.stat()
            if st.st_size!=int(r['size_bytes']) or st.st_mtime_ns!=int(r['mtime_ns']):problems.append('stat_changed')
            if str(p.resolve())!=r['resolved_path']:problems.append('target_changed')
            if full and digest(p)!=r['sha256']:problems.append('sha256_changed')
        except Exception as e:problems.append(str(e))
        return {'image_id':r['image_id'],'problems':'|'.join(problems)} if problems else None
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        issues=[r for r in pool.map(one,rows) if r]
    from audit import walk_entries,EXT
    current={p.relative_to(DATA).as_posix() for kind,p in walk_entries() if kind=='file' and p.suffix.lower() in EXT}
    previous={r['processed_relpath'] for r in rows if not r['processed_relpath'].startswith('raw-kale:')}
    if current!=previous:issues.append({'inventory_added':sorted(current-previous),'inventory_missing':sorted(previous-current)})
    for r in read_csv(root/'audit'/'symlinks.csv'):
        p=DATA/r['path']
        if not p.is_symlink() or os.readlink(p)!=r['target']:issues.append({'changed_link':r['path']})
    for r in read_csv(root/'audit'/'metadata_inventory.csv'):
        p=DATA/r['path']
        if not p.exists() or digest(p)!=r['sha256']:issues.append({'changed_metadata':r['path']})
    result={'checked_at':utc(),'full_image_hash_check':full,'image_entries':len(rows),'issues':issues,'passed':not issues}
    stamp=utc().replace(':','').replace('+','_')
    write_json(root/'audit'/f'preservation_{stamp}.json',result,root)
    if issues:raise ValueError('Source preservation verification failed')
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--full',action='store_true');a=p.parse_args()
    print(json.dumps(verify(initialize(a.root),a.full)))
