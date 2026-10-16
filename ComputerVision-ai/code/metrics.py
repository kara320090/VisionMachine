"""Binary image-level metrics; the main average weights eight crops equally."""
from common import CROPS

def binary_metrics(y,p):
    tn=fp=fn=tp=0
    for a,b in zip(y,p):
        if a not in (0,1) or b not in (0,1): raise ValueError('Binary labels required')
        if a==0 and b==0: tn+=1
        elif a==0: fp+=1
        elif b==0: fn+=1
        else: tp+=1
    if len(y)!=len(p) or not y: raise ValueError('Nonempty aligned inputs required')
    f0=2*tn/(2*tn+fp+fn) if 2*tn+fp+fn else 0.0
    f1=2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0.0
    return {'n':len(y),'tn':tn,'fp':fp,'fn':fn,'tp':tp,'normal_f1':f0,'abnormal_f1':f1,
            'binary_macro_f1':(f0+f1)/2,'accuracy':(tn+tp)/len(y),
            'abnormal_recall':tp/(tp+fn) if tp+fn else None,
            'normal_false_positive_rate':fp/(tn+fp) if tn+fp else None}

def evaluate_records(records,threshold=.5):
    per={}
    for c in CROPS:
        rows=[r for r in records if r['crop']==c]
        if {int(r['binary_label']) for r in rows}!={0,1}: raise ValueError(f'Missing binary evaluation class in {c}')
        per[c]=binary_metrics([int(r['binary_label']) for r in rows],[int(float(r['p_abnormal'])>=threshold) for r in rows])
    pooled=binary_metrics([int(r['binary_label']) for r in records],[int(float(r['p_abnormal'])>=threshold) for r in records])
    return {'equal_crop_binary_macro_f1':sum(per[c]['binary_macro_f1'] for c in CROPS)/8,
            'pooled_binary_macro_f1':pooled['binary_macro_f1'],'overall_accuracy':pooled['accuracy'],
            'threshold':threshold,'per_crop':per,'pooled':pooled}
