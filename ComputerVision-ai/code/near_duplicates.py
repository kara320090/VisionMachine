"""Perceptual-hash candidates only; no automatic duplicate declarations."""
import argparse
import collections
from pathlib import Path
from common import *

class BKTree:
    def __init__(self):self.root=None
    def add(self,value,identifier):
        if self.root is None:self.root=[value,[identifier],{}];return
        node=self.root
        while True:
            d=(value^node[0]).bit_count()
            if d==0:node[1].append(identifier);return
            if d not in node[2]:node[2][d]=[value,[identifier],{}];return
            node=node[2][d]
    def query(self,value,radius):
        stack=[] if self.root is None else [self.root]
        while stack:
            node=stack.pop();d=(value^node[0]).bit_count()
            if d<=radius:
                for identifier in node[1]:yield identifier,d
            stack.extend(n for dist,n in node[2].items() if d-radius<=dist<=d+radius)

def run(root,radius=4):
    root=initialize(root);rows=read_csv(root/'audit'/'image_inventory.csv');tree=BKTree()
    # Query indices must refer to original inventory rows, including duplicates.
    # One indexed pass avoids materializing an N x N matrix.
    tree=BKTree();seen_sha=set();pairs=[]
    for index,r in enumerate(rows):
        if not r.get('phash') or r['sha256'] in seen_sha:continue
        value=int(r['phash'],16)
        for other_index,d in tree.query(value,radius):
            other=rows[other_index]
            pairs.append({'image_id_a':other['image_id'],'image_id_b':r['image_id'],'hamming_distance':d,
                'crop_a':other['crop'],'crop_b':r['crop'],'cross_crop':other['crop']!=r['crop'],
                'relationship':'candidate_only','adjudication':'pending'})
        tree.add(value,index);seen_sha.add(r['sha256'])
    write_csv(root/'review'/'perceptual_candidates.csv',pairs,root,
        ['image_id_a','image_id_b','hamming_distance','crop_a','crop_b','cross_crop','relationship','adjudication'])
    write_json(root/'audit'/'perceptual_candidate_summary.json',{'radius':radius,'bits':64,
        'unique_sha_images_searched':len(seen_sha),'candidate_pairs':len(pairs),
        'cross_crop_pairs':sum(r['cross_crop'] for r in pairs),'confirmed_duplicates':0,
        'limitations':'Rotation, crop, color conversion and repeated scenes may evade pHash; candidates require image/provenance review.'},root)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);a=p.parse_args();run(Path(a.root))
