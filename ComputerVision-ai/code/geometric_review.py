"""Verify duplicate candidates with SIFT geometry and aligned image pixels.

Filename/pHash similarity alone never sets a confirmed relationship. Even a
strong geometric relation is not a crop-label decision or proof that different
photos are independent. Original photo decisions remain explicitly reviewable.
"""
from __future__ import annotations
import argparse
import collections
import concurrent.futures
import functools
import itertools
import threading
from pathlib import Path
from common import *

def run(root):
    root=initialize(root)
    import cv2,numpy as np
    from PIL import Image,ImageOps
    from image_cache import path_for
    cv2.setNumThreads(1)
    rows=read_csv(root/'audit'/'image_inventory.csv');lookup={r['image_id']:r for r in rows}
    unique={}
    for r in rows:unique.setdefault(r['sha256'],r['image_id'])
    families=collections.defaultdict(list)
    for r in rows:
        if unique[r['sha256']]==r['image_id']:families[r['filename_family']].append(r['image_id'])
    pairs=set()
    for name,ids in families.items():
        if len(ids)<=24:pairs.update(tuple(sorted(p)) for p in itertools.combinations(ids,2))
        else:
            # Avoid quadratic generic names. Compare source anchors and each
            # source's variants; remaining pairs stay unconfirmed candidates.
            by_source=collections.defaultdict(list)
            for i in ids:by_source[(lookup[i]['crop'],lookup[i]['source'].replace('_train','').replace('_valid','').replace('_test',''))].append(i)
            anchors=[sorted(g)[0] for g in by_source.values()]
            pairs.update(tuple(sorted(p)) for p in itertools.combinations(anchors,2))
            for g in by_source.values():pairs.update(tuple(sorted((g[0],i))) for i in g[1:])
    for r in read_csv(root/'review'/'perceptual_candidates.csv'):pairs.add(tuple(sorted((r['image_id_a'],r['image_id_b']))))
    pairs=sorted(pairs)
    @functools.lru_cache(maxsize=2500)
    def features(identifier):
        r=lookup[identifier];p=path_for(root,r)
        if not p.exists():p=input_path(r['processed_relpath'])
        with Image.open(p) as im:
            im=ImageOps.exif_transpose(im).convert('L');im.thumbnail((384,384));gray=np.asarray(im).copy()
        keypoints,desc=cv2.SIFT_create(nfeatures=700).detectAndCompute(gray,None)
        points=np.float32([k.pt for k in keypoints])
        return gray,points,desc
    geometry_lock=threading.Lock()
    def inspect(pair):
        a,b=pair;ra,rb=lookup[a],lookup[b]
        result={'image_id_a':a,'image_id_b':b,'crop_a':ra['crop'],'crop_b':rb['crop'],
            'candidate_type':'filename_or_phash','relation':'unconfirmed','good_matches':0,'inliers':0,
            'inlier_ratio':0.,'coverage_a':0.,'coverage_b':0.,'pixel_correlation':0.,'aligned_mae':999.,'overlap':0.,'error':''}
        try:
            ga,pa,da=features(a);gb,pb,db=features(b)
            if da is None or db is None or len(da)<10 or len(db)<10:return result
            neighbors=cv2.BFMatcher().knnMatch(da,db,k=2)
            good=[m for m,n in neighbors if m.distance<.70*n.distance]
            result['good_matches']=len(good)
            if len(good)<15:return result
            aa=np.float32([pa[m.queryIdx] for m in good]);bb=np.float32([pb[m.trainIdx] for m in good])
            with geometry_lock:
                cv2.setRNGSeed(20261016);H,mask=cv2.findHomography(aa,bb,cv2.RANSAC,2.5,maxIters=2000,confidence=.999)
            if H is None or mask is None:return result
            keep=mask.ravel().astype(bool);n=int(keep.sum());ratio=n/len(good)
            result.update(inliers=n,inlier_ratio=ratio)
            if n<15 or ratio<.7:return result
            ca=cv2.contourArea(cv2.convexHull(aa[keep]))/ga.size;cb=cv2.contourArea(cv2.convexHull(bb[keep]))/gb.size
            result.update(coverage_a=ca,coverage_b=cb)
            if min(ca,cb)<.10:return result
            h,w=gb.shape;warped=cv2.warpPerspective(ga,H,(w,h));valid=cv2.warpPerspective(np.ones_like(ga),H,(w,h),flags=cv2.INTER_NEAREST)>0
            valid=cv2.erode(valid.astype(np.uint8),np.ones((5,5),np.uint8))>0
            overlap=float(valid.mean());result['overlap']=overlap
            if valid.sum()<3000:return result
            x=warped[valid].astype(float);y=gb[valid].astype(float)
            if x.std()<5 or y.std()<5:return result
            corr=float(np.corrcoef(x,y)[0,1]);scale=float(np.dot(x-x.mean(),y-y.mean())/np.dot(x-x.mean(),x-x.mean()))
            adjusted=x*scale+(y.mean()-scale*x.mean());mae=float(np.mean(np.abs(adjusted-y)))
            result.update(pixel_correlation=corr,aligned_mae=mae,relation='shared_scene_candidate')
            if corr>=.995 and mae<=3.0 and overlap>=.60:result['relation']='same_photo_supported_by_geometry_and_pixels'
        except Exception as e:result['error']=f'{type(e).__name__}: {e}'
        return result
    output=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        for i,r in enumerate(pool.map(inspect,pairs)):
            output.append(r)
            if (i+1)%1000==0:print(f'Geometric candidate checks {i+1}/{len(pairs)}',flush=True)
    write_csv(root/'review'/'geometric_candidate_checks.csv',output,root)
    confirmed=[r for r in output if r['relation']=='same_photo_supported_by_geometry_and_pixels']
    cross=[r for r in confirmed if r['crop_a']!=r['crop_b']]
    write_json(root/'audit'/'geometric_review_summary.json',{'created_at':utc(),'pairs_tested':len(output),
        'same_photo_supported_pairs':len(confirmed),'shared_scene_candidates':sum(r['relation']=='shared_scene_candidate' for r in output),
        'cross_crop_supported_pairs':len(cross),'crop_labels_changed':0,'independence_claimed':False,
        'automatic_admission_to_training':False,'thresholds':{'minimum_good_matches':15,'minimum_inliers':15,'inlier_ratio':.70,
        'min_feature_coverage_each_image':.10,'pixel_correlation':.995,'aligned_mae':3.,'pixel_overlap':.60}},root)
    # Concrete visual evidence for the first 12 cross-crop supported matches.
    from PIL import ImageDraw
    for i,pair in enumerate(cross[:12]):
        sheet=Image.new('RGB',(800,435),'white');draw=ImageDraw.Draw(sheet)
        for col,key in enumerate(('image_id_a','image_id_b')):
            r=lookup[pair[key]]
            with Image.open(input_path(r['processed_relpath'])) as im:
                im=ImageOps.exif_transpose(im).convert('RGB');im.thumbnail((390,370));sheet.paste(im,(col*400,0))
            draw.text((col*400+4,375),r['crop']+' / '+r['source']+'\n'+r['image_id'],fill='black')
        sheet.save(root/'review'/f'confirmed_cross_crop_{i:02d}.jpg',quality=90)
    print(f'Checked {len(output)} pairs; {len(confirmed)} have strong geometry+pixel evidence; {len(cross)} cross crops.',flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);run(Path(p.parse_args().root))
