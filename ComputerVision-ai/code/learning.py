"""Aligned A/B/C data loading, two-logit model, and sample-weighted mean CE."""
import collections
import hashlib
import math
import random
import numpy as np
import torch
from torch import nn
from torch.utils.data import Dataset,DataLoader,Sampler
from PIL import Image,ImageOps
from torchvision import transforms,models
from torchvision.transforms import InterpolationMode
from common import CROPS,input_path

def seed_everything(seed):
    random.seed(seed);np.random.seed(seed);torch.manual_seed(seed)
    if torch.cuda.is_available():torch.cuda.manual_seed_all(seed)
    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.benchmark=False
    torch.backends.cudnn.deterministic=True
    torch.backends.cuda.matmul.allow_tf32=False
    torch.backends.cudnn.allow_tf32=False

def sample_weights(rows,condition):
    if condition not in ('A','B','C'):raise ValueError('Unknown condition')
    if any(r['split']!='train' for r in rows):raise ValueError('Weights use train only')
    n=len(rows);states=collections.Counter(int(r['binary_label']) for r in rows)
    groups=collections.Counter((r['crop'],int(r['binary_label'])) for r in rows)
    if any(groups[c,y]==0 for c in CROPS for y in (0,1)):raise ValueError('Every one of 16 training groups must exist')
    w=np.array([1.0 if condition=='A' else n/(2*states[int(r['binary_label'])]) if condition=='B'
                else n/(16*groups[r['crop'],int(r['binary_label'])]) for r in rows],dtype=np.float64)
    if not np.all(np.isfinite(w)) or not np.all(w>0) or not np.isclose(w.sum(),n,rtol=1e-12):raise ValueError('Invalid total sample weights')
    if condition!='A':
        for y in (0,1):
            if not np.isclose(sum(w[i] for i,r in enumerate(rows) if int(r['binary_label'])==y),n/2,rtol=1e-12):raise ValueError('Binary weight sum failed')
    if condition=='C':
        for c in CROPS:
            for y in (0,1):
                if not np.isclose(sum(w[i] for i,r in enumerate(rows) if (r['crop'],int(r['binary_label']))==(c,y)),n/16,rtol=1e-12):raise ValueError('Group weight sum failed')
    return w

def weighted_loss(logits,labels,weights):
    return (nn.functional.cross_entropy(logits,labels,reduction='none')*weights).mean()

def model(pretrained=True):
    net=models.efficientnet_b0(weights=models.EfficientNet_B0_Weights.IMAGENET1K_V1 if pretrained else None)
    net.classifier[1]=nn.Linear(net.classifier[1].in_features,2)
    return net

class Images(Dataset):
    def __init__(self,rows,cfg,train=False,seed=0,epoch=0,weights=None):
        self.rows=rows;self.train=train;self.seed=seed;self.epoch=epoch
        self.weights=np.ones(len(rows)) if weights is None else weights
        self.cache_root=cfg.get('image_cache_root')
        base=[transforms.ToTensor(),transforms.Normalize(cfg['mean'],cfg['std'])]
        if train:
            aug=[transforms.RandomResizedCrop(cfg['image_size'],scale=cfg['crop_scale'],ratio=cfg['crop_ratio'],interpolation=InterpolationMode.BICUBIC),
                 transforms.RandomHorizontalFlip(cfg['horizontal_flip']),transforms.ColorJitter(*cfg['color_jitter'])]
        else:
            aug=[transforms.Resize(cfg['eval_resize'],interpolation=InterpolationMode.BICUBIC),transforms.CenterCrop(cfg['image_size'])]
        self.transform=transforms.Compose(aug+base)
    def __len__(self):return len(self.rows)
    def __getitem__(self,i):
        r=self.rows[i]
        source=input_path(r['processed_relpath'])
        if self.cache_root:
            from image_cache import path_for,RECIPE_ID
            if self.cache_root.get('recipe_id')!=RECIPE_ID:raise ValueError('Image cache recipe mismatch')
            source=path_for(self.cache_root['experiment_root'],r)
            if not source.exists():raise FileNotFoundError('Fixed cache is incomplete: '+str(source))
        with Image.open(source) as im:
            im=ImageOps.exif_transpose(im).convert('RGB')
            # Fork CPU RNG only; this never changes model/dropout RNG in workers=0.
            with torch.random.fork_rng(devices=[]):
                s=int.from_bytes(hashlib.sha256(f'{self.seed}/{self.epoch}/{r["image_id"]}'.encode()).digest()[:8],'big')%(2**63)
                torch.random.default_generator.manual_seed(s)
                x=self.transform(im)
        return x,int(r['binary_label']),float(self.weights[i]),i

def loader(rows,cfg,train,seed,epoch=0,weights=None,start_batch=0):
    ds=Images(rows,cfg,train,seed,epoch,weights)
    generator=torch.Generator().manual_seed(seed+epoch*100003)
    indices=torch.randperm(len(ds),generator=generator).tolist() if train else list(range(len(ds)))
    indices=indices[start_batch*cfg['batch_size']:]
    kw={'num_workers':cfg['workers'],'pin_memory':True,'generator':torch.Generator().manual_seed(seed+epoch)}
    if cfg['workers']>0:kw['prefetch_factor']=cfg['prefetch_factor']
    return DataLoader(ds,batch_size=cfg['batch_size'],sampler=indices,drop_last=False,**kw)

def optimizer_for(net,cfg,head_only):
    for p in net.features.parameters():p.requires_grad_(not head_only)
    if head_only:
        return torch.optim.AdamW(net.classifier.parameters(),lr=cfg['classifier_lr'],weight_decay=cfg['weight_decay'])
    return torch.optim.AdamW([{'params':net.features.parameters(),'lr':cfg['backbone_lr']},
                             {'params':net.classifier.parameters(),'lr':cfg['classifier_lr']}],weight_decay=cfg['weight_decay'])

def set_epoch_lr(opt,cfg,epoch):
    if epoch<cfg['head_epochs']:return
    pos=(epoch-cfg['head_epochs'])/max(1,cfg['epochs']-cfg['head_epochs']-1)
    factor=cfg['final_lr_ratio']+(1-cfg['final_lr_ratio'])*.5*(1+math.cos(math.pi*pos))
    for group,base in zip(opt.param_groups,[cfg['backbone_lr'],cfg['classifier_lr']]):group['lr']=base*factor
