"""Create deterministic contact sheets for source and visible-state review."""
import argparse
import collections
from pathlib import Path
from common import *


def run(root):
    root=initialize(root)
    from PIL import Image,ImageOps,ImageDraw
    from image_cache import path_for
    rows=read_csv(research_inventory(root))
    target=root/'review'/'visual_panels';target.mkdir(exist_ok=True)
    selected=[r for r in rows if r.get('input_kind')=='raw_candidate' and str(r.get('day')) in ('10','20')]
    selected.sort(key=lambda r:(r['candidate_individual_id'],int(r['day'])))
    # Each pair shows the same plant on days 10 and 20. Panel labels are IDs,
    # never inferred ground truth; soil/background colour is not a health label.
    inventories=[]
    for start in range(0,len(selected),64):
        page=selected[start:start+64];canvas=Image.new('RGB',(8*240,8*218),'white');draw=ImageDraw.Draw(canvas)
        for i,r in enumerate(page):
            p=path_for(root,r)
            if not p.exists():p=input_path(r['processed_relpath'])
            with Image.open(p) as im:
                im=ImageOps.exif_transpose(im).convert('RGB');w,h=im.size
                # Keep the complete source for context. Zooming decisions are
                # made by the reviewer against the source after triage.
                im.thumbnail((234,175));x=(i%8)*240;y=(i//8)*218;canvas.paste(im,(x,y))
            draw.text((x+2,y+177),r['candidate_individual_id']+' D'+str(r['day'])+'\n'+r['image_id'],fill='black')
            inventories.append(dict(panel=f'raw_{start:04d}.jpg',cell=i,**r))
        canvas.save(target/f'raw_{start:04d}.jpg',quality=92)
    for crop in ('rosemary','bok_choy'):
        families={}
        for r in rows:
            if r['crop']==crop and r.get('candidate_label')=='0':
                families.setdefault((r['source'],r['filename_family']),r)
        selected=sorted(families.values(),key=lambda r:(r['source'],r['filename_family']))
        for start in range(0,len(selected),48):
            page=selected[start:start+48];canvas=Image.new('RGB',(8*220,6*210),'white');draw=ImageDraw.Draw(canvas)
            for i,r in enumerate(page):
                p=path_for(root,r)
                if not p.exists():p=input_path(r['processed_relpath'])
                with Image.open(p) as im:
                    im=ImageOps.exif_transpose(im).convert('RGB');im.thumbnail((214,165));x=(i%8)*220;y=(i//8)*210;canvas.paste(im,(x,y))
                draw.text((x+2,y+167),str(start+i)+' '+r['image_id']+'\n'+r['filename_family'][:30],fill='black')
                inventories.append(dict(panel=f'{crop}_{start:04d}.jpg',cell=i,**r))
            canvas.save(target/f'{crop}_{start:04d}.jpg',quality=92)
    write_csv(target/'panel_inventory.csv',inventories,root)
    write_json(target/'status.json',{'created_at':utc(),'panels':len(list(target.glob('*.jpg'))),
        'labels_assigned':0,'purpose':'Manual source/state review, not automatic annotation'},root)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);run(Path(p.parse_args().root))
