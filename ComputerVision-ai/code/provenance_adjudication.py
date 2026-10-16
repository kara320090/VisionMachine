"""Record a source-label conflict using full-image evidence plus visual review."""
import argparse
from pathlib import Path
from common import *

def run(root):
    root=initialize(root);matches=read_csv(root/'review'/'reference_correspondence_candidates.csv')
    if len(matches)!=129 or len({r['local_image_id'] for r in matches})!=129:
        raise ValueError('Expected unique correspondence evidence for all 129 disputed files')
    errors=[]
    for r in matches:
        if not (int(r['phash_distance'])<=8 and float(r['pixel_mae_after_resize'])<.04 and float(r['pixel_correlation'])>.96):
            raise ValueError('Insufficient whole-image correspondence; keep as unresolved')
        errors.append({'image_id':r['local_image_id'],'processed_relpath':r['processed_relpath'],
            'existing_crop':'kale','source_crop':'squash','binary_health_label_from_source':1,
            'correction':'not eligible as kale; outside the specified eight crops',
            'inclusion_status':'source_crop_conflict_do_not_train_as_kale',
            'original_files_modified':False,'evidence':r['reference_github_url'],
            'reference_class':r['reference_class'],'local_sha256':r['local_sha256'],
            'reference_sha256':r['reference_sha256'],'pixel_mae':r['pixel_mae_after_resize'],
            'pixel_correlation':r['pixel_correlation'],
            'review_basis':'1-to-1 source correspondence with whole-image pixel agreement; visual inspection of leaf outline, veins, lesion pattern and background in representative/worst-error pair',
            'reviewer':'Codex source-provenance audit'})
    write_csv(root/'review'/'confirmed_crop_source_conflicts.csv',errors,root)
    write_json(root/'audit'/'confirmed_crop_source_conflicts.json',{'created_at':utc(),
        'misassigned_kale_images':len(errors),'verified_source_crop':'Squash',
        'primary_source':'https://github.com/spMohanty/PlantVillage-Dataset/tree/master/raw/color/Squash___Powdery_mildew',
        'method':'Perceptual candidates were followed by one-to-one whole-image pixel agreement and visual photograph comparison.',
        'worst_pixel_mae_0to1':max(float(r['pixel_mae']) for r in errors),
        'minimum_full_image_correlation':min(float(r['pixel_correlation']) for r in errors),
        'reference_photos_admitted_to_training':0,'original_files_changed':0,
        'eight_crop_research_still_requires_valid_kale_abnormal_images':True},root)
    # A correction overlay is factual; it is not a final inclusion decision or
    # a fabricated approval of the still-ambiguous remaining kale sources.
    overlays=[{'image_id':r['image_id'],'corrected_crop':'squash','binary_label':1,
               'label_status':'confirmed_source_crop_conflict','train_eligible_as_kale':False,
               'evidence':r['evidence'],'original_files_modified':False} for r in errors]
    write_csv(root/'manifests'/'verified_corrections_overlay.csv',overlays,root)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);run(Path(p.parse_args().root))
