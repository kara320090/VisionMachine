"""One preselected endpoint per raw plant, with original-resolution canopy views.

No labels are generated. Endpoint day20 was chosen before manual state review;
other dates are not used as extra independent evaluation examples.
"""
import argparse
from pathlib import Path
from common import *


def run(root,day=20):
    root=initialize(root)
    from PIL import Image,ImageOps,ImageDraw
    import numpy as np
    rows=sorted([r for r in read_csv(root/'audit/raw_kale_candidates.csv') if r['day']==str(day)],
                key=lambda r:(r['stage'],r['species'],int(r['candidate_individual_id'].rsplit('_',1)[1])))
    if len(rows)!=320 or len({r['candidate_individual_id'] for r in rows})!=320:
        raise ValueError('Expected 320 unique endpoint plant IDs')
    target=root/'review'/f'kale_day{day}';target.mkdir(exist_ok=True)
    output=[]
    for start in range(0,len(rows),20):
        canvas=Image.new('RGB',(1800,1480),'white');draw=ImageDraw.Draw(canvas)
        for cell,r in enumerate(rows[start:start+20]):
            source=input_path(r['processed_relpath'])
            with Image.open(source) as im:
                im=ImageOps.exif_transpose(im).convert('RGB');w,h=im.size
                small=im.copy();small.thumbnail((800,800));arr=np.asarray(small).astype(float)
                mask=(arr[:,:,1]>1.07*arr[:,:,0])&(arr[:,:,1]>1.12*arr[:,:,2])&(arr[:,:,1]>35)
                sh,sw=mask.shape;mask[:int(sh*.08)]=False;mask[int(sh*.94):]=False
                mask[:,:int(sw*.08)]=False;mask[:,int(sw*.92):]=False
                yy,xx=np.where(mask)
                if len(xx)<100:box=(0,0,w,h)
                else:
                    x0,x1=np.quantile(xx,[.003,.997]);y0,y1=np.quantile(yy,[.003,.997])
                    box=(max(0,int((x0-10)*w/sw)),max(0,int((y0-10)*h/sh)),
                         min(w,int((x1+10)*w/sw)),min(h,int((y1+10)*h/sh)))
                review=im.crop(box);review.thumbnail((350,325))
            x=(cell%5)*360;y=(cell//5)*370;canvas.paste(review,(x,y))
            draw.text((x+3,y+327),str(start+cell)+' '+r['candidate_individual_id']+'\n'+r['image_id'],fill='black')
            output.append(dict(r,review_index=start+cell,panel=f'day{day}_{start:03d}.jpg',cell=cell,
                               review_crop_box=str(box),label_status='awaiting_visual_review'))
        canvas.save(target/f'day{day}_{start:03d}.jpg',quality=94)
        print('Endpoint canopy views',start+len(rows[start:start+20]),'/320',flush=True)
    write_csv(target/'inventory.csv',output,root)
    write_json(target/'selection.json',{'at':utc(),'day':day,'images':320,'candidate_plant_groups':320,
        'selection_before_health_annotation':True,'health_labels_assigned':0,
        'review_display_only_crop':True,'training_inputs_still_use_full_source_image':True},root)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--day',type=int,choices=(10,20),default=20);a=p.parse_args();run(Path(a.root),a.day)
