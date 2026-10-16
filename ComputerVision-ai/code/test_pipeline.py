"""Focused correctness and safety tests. Synthetic data are never research results."""
import copy
import os
import random
import tempfile
import unittest
from pathlib import Path
from common import *

class ResearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import torch
        torch.set_num_threads(2)
    def setUp(self):
        self.previous_tempdir=tempfile.tempdir
        self.previous_environment={key:os.environ.get(key) for key in
            ('TMPDIR','TEMP','TMP','TORCH_HOME','XDG_CACHE_HOME','MPLCONFIGDIR','PIP_CACHE_DIR','NUMBA_CACHE_DIR')}
    def tearDown(self):
        # initialize() deliberately changes process caches. Temporary test
        # experiments must not leave the next test pointing to a deleted tmp.
        tempfile.tempdir=self.previous_tempdir
        for key,value in self.previous_environment.items():
            if value is None:os.environ.pop(key,None)
            else:os.environ[key]=value
    def rows(self):
        return [{'crop':c,'binary_label':y,'split':'train'} for ci,c in enumerate(CROPS) for y in (0,1) for _ in range(2+ci+2*y)]
    def test_weight_conservation(self):
        from learning import sample_weights
        r=self.rows()
        for cond in 'ABC':
            w=sample_weights(r,cond);self.assertAlmostEqual(float(w.sum()),len(r))
            if cond in 'BC':
                for y in (0,1):self.assertAlmostEqual(sum(w[i] for i,x in enumerate(r) if x['binary_label']==y),len(r)/2)
            if cond=='C':
                for c in CROPS:
                    for y in (0,1):self.assertAlmostEqual(sum(w[i] for i,x in enumerate(r) if (x['crop'],x['binary_label'])==(c,y)),len(r)/16)
    def test_missing_training_crop_is_rejected(self):
        from learning import sample_weights
        with self.assertRaises(ValueError):sample_weights([r for r in self.rows() if r['crop']!='kale'],'C')
    def test_test_counts_are_rejected(self):
        from learning import sample_weights
        r=self.rows();r[0]['split']='test'
        with self.assertRaises(ValueError):sample_weights(r,'B')
    def test_batch_denominator_is_image_count(self):
        import torch,math
        from learning import weighted_loss
        logits=torch.zeros((2,2),requires_grad=True);labels=torch.tensor([0,1]);w=torch.tensor([1.,3.])
        loss=weighted_loss(logits,labels,w)
        self.assertAlmostEqual(float(loss.detach()),2*math.log(2),places=6)
        loss.backward();self.assertTrue(torch.allclose(logits.grad,torch.tensor([[-.25,.25],[.75,-.75]])))
    def test_hand_computed_metrics(self):
        from metrics import binary_metrics
        m=binary_metrics([0,0,1,1],[0,1,1,1]);self.assertEqual((m['tn'],m['fp'],m['fn'],m['tp']),(1,1,0,2))
        self.assertAlmostEqual(m['binary_macro_f1'],(.6666666666666666+.8)/2)
        self.assertEqual(m['normal_false_positive_rate'],.5)
    def test_crop_average_is_not_pooled(self):
        from metrics import evaluate_records
        rows=[]
        for ci,c in enumerate(CROPS):
            for y in (0,1):
                for _ in range(100 if ci==0 else 1):
                    rows.append({'crop':c,'binary_label':y,'p_abnormal':y if ci==0 else 1-y})
        m=evaluate_records(rows);self.assertAlmostEqual(m['equal_crop_binary_macro_f1'],1/8)
        self.assertGreater(m['pooled_binary_macro_f1'],.9)
    def test_half_threshold(self):
        from metrics import evaluate_records
        rows=[{'crop':c,'binary_label':y,'p_abnormal':.5} for c in CROPS for y in (0,1)]
        self.assertEqual(evaluate_records(rows)['per_crop']['kale']['tp'],1)
    def test_output_and_input_escape(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            with self.assertRaises(ValueError):safe_output(root/'..'/'escape',root)
            outside=root.parent/'external_for_test'
            (root/'escape').symlink_to(outside,target_is_directory=True)
            with self.assertRaises(ValueError):safe_output(root/'escape'/'file',root)
        with self.assertRaises(ValueError):input_path('../raw/image.jpg')
        with self.assertRaises(ValueError):input_path('raw-kale:../other.jpg')
        with self.assertRaises(ValueError):safe_output('/home/data/new_experiment','/home/data/new_experiment')
    def fixture_split(self):
        return [dict(image_id=f'{c}_{y}_{i}',crop=c,binary_label=y,sha256=f'{c}_{y}_{i}',
                     parent_image_id=f'p_{c}_{y}_{i}',leakage_group_id=f'g_{c}_{y}_{i}',
                     width=224,height=224,processed_relpath=f'{c}/normal/{i}.jpg')
                for c in CROPS for y in (0,1) for i in range(60)]
    def test_fixed_group_split(self):
        from prepare import split_rows,validate_split
        r=split_rows(self.fixture_split());validate_split(r)
        self.assertEqual([(x['image_id'],x['split']) for x in r],[(x['image_id'],x['split']) for x in split_rows(self.fixture_split())])
    def test_group_leakage_is_rejected(self):
        from prepare import split_rows,validate_split
        r=split_rows(self.fixture_split());a=r[0];b=next(x for x in r if x['split']!=a['split']);b['leakage_group_id']=a['leakage_group_id']
        with self.assertRaises(ValueError):validate_split(r)
    def test_uncertain_labels_block(self):
        from prepare import approved_rows
        with tempfile.TemporaryDirectory() as temp:
            root=initialize(temp);write_json(root/'review'/'approval.json',{'approved':False},root)
            with self.assertRaises(ValueError):approved_rows(root)
    def test_exact_conflict_is_rejected(self):
        from prepare import deduplicate
        base={'sha256':'same','leakage_group_id':'same','parent_image_id':'same','crop':'kale','binary_label':0}
        with self.assertRaises(ValueError):deduplicate([base,dict(base,binary_label=1)])
    def test_confirmed_crop_error_blocks_even_renamed_copy(self):
        from source_guard import validate_source_corrections
        with tempfile.TemporaryDirectory() as temp:
            root=initialize(temp)
            write_csv(root/'review'/'confirmed_crop_source_conflicts.csv',[
                {'image_id':'wrong','local_sha256':'squash-photo','source_crop':'squash','evidence':'primary source'}],root)
            with self.assertRaises(ValueError):
                validate_source_corrections(root,[{'image_id':'wrong','sha256':'squash-photo','crop':'kale'}])
            with self.assertRaises(ValueError):
                validate_source_corrections(root,[{'image_id':'renamed','sha256':'squash-photo','crop':'kale'}])
            validate_source_corrections(root,[{'image_id':'valid','sha256':'other-photo','crop':'kale'}])
    def test_checkpoint_resume_matches_uninterrupted_update(self):
        import torch
        from train import rng_state,restore_rng,save_checkpoint
        torch.manual_seed(17)
        net=torch.nn.Sequential(torch.nn.Linear(3,5),torch.nn.Dropout(.5),torch.nn.Linear(5,2))
        opt=torch.optim.AdamW(net.parameters(),lr=.01);x=torch.randn(4,3);y=torch.tensor([0,1,0,1])
        def step(n,o):o.zero_grad();torch.nn.functional.cross_entropy(n(x),y).backward();o.step()
        step(net,opt)
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);save_checkpoint(root/'checkpoint.pt',{'model':net.state_dict(),'optimizer':opt.state_dict(),'rng':rng_state()},root)
            step(net,opt);expected=copy.deepcopy(net.state_dict())
            ck=torch.load(root/'checkpoint.pt',weights_only=False)
            other=copy.deepcopy(net);other.load_state_dict(ck['model']);newopt=torch.optim.AdamW(other.parameters(),lr=.01);newopt.load_state_dict(ck['optimizer'])
            restore_rng(ck['rng']);step(other,newopt)
            for k,v in expected.items():self.assertTrue(torch.equal(v,other.state_dict()[k]),k)
    def test_stateless_augmentation_does_not_change_parent_rng(self):
        import torch
        state=torch.get_rng_state().clone()
        with torch.random.fork_rng(devices=[]):torch.manual_seed(99);torch.rand(20)
        self.assertTrue(torch.equal(state,torch.get_rng_state()))
    def test_bktree_candidate_distance(self):
        from near_duplicates import BKTree
        tree=BKTree();tree.add(0,'zero');tree.add(3,'two');tree.add(255,'eight')
        self.assertEqual(set(tree.query(0,2)),{('zero',0),('two',2)})
    def test_multiprocessing_socket_path(self):
        if os.name!='posix':self.skipTest('Unix socket check')
        from multiprocessing.connection import Listener
        with Listener(family='AF_UNIX') as listener:self.assertLess(len(listener.address.encode()),108)

if __name__=='__main__':unittest.main(verbosity=2)
