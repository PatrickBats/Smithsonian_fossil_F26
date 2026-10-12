"""Pretrained one-class detector, native RF-DETR 1.6.4 trainer.

Internal COCO metrics are partial-label diagnostics, never whole-scene AP.
"""
import argparse,collections,json,os,traceback,time
from pathlib import Path
from pipeline_common import validate_inputs,sha,save

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--config',required=True);ap.add_argument('--smoke',action='store_true');ap.add_argument('--resume');a=ap.parse_args()
    c,records,mapping=validate_inputs(a.config);root=Path(c['workspace']);data=root/'dataset';out=root/('detector_smoke' if a.smoke else 'detector')
    assert sha(c['detector_pretrained'])==c['detector_pretrained_sha256']
    for shard in range(c['export_shards']):assert json.loads((root/f'export_shard_{shard}.json').read_text())['status']=='export_complete'
    for split in ['train','valid']:
        coco={'images':[],'annotations':[],'categories':[{'id':1,'name':'eligible_palynomorph'}]};seen=set()
        for idx,path in enumerate(sorted((data/split).glob('*.json')),1):
            if path.name=='_annotations.coco.json':continue
            r=json.loads(path.read_text());png=path.with_suffix('.png');assert sha(png)==r['png_sha256']
            assert r['split']==('val' if split=='valid' else 'train')
            coco['images'].append({'id':idx,'file_name':png.name,'width':r['size'],'height':r['size']})
            seen.update(r['anchors'])
            for obj in r['objects']:
                coco['annotations'].append({'id':len(coco['annotations'])+1,'image_id':idx,'category_id':1,'bbox':obj['bbox'],'area':obj['area'],'iscrowd':0})
        references=[x for shard in range(c['export_shards']) for x in json.loads((root/f'export_shard_{shard}_references.json').read_text())]
        expected={r['record_id'] for r in references if r['split']==('val' if split=='valid' else 'train')}
        assert seen==expected and coco['images'],'Missing adopted anchor'
        save(data/split/'_annotations.coco.json',coco)
    # The adapter builds a test dataset even with run_test=False. Supply an empty
    # dataset, not a validation alias and never the reserved test images.
    save(data/'test/_annotations.coco.json',{'images':[],'annotations':[],'categories':[{'id':1,'name':'eligible_palynomorph'}]})
    out.mkdir(parents=True,exist_ok=True);os.environ['HF_HOME']=str(root/'cache/hf');os.environ['TORCH_HOME']=str(root/'cache/torch');os.environ['NO_ALBUMENTATIONS_UPDATE']='1'
    import importlib.metadata,torch
    assert importlib.metadata.version('rfdetr')=='1.6.4' and torch.cuda.is_available()
    from rfdetr_plus.models.detection import RFDETR2XLarge
    settings=dict(dataset_dir=str(data),output_dir=str(out),epochs=1 if a.smoke else c['epochs'],batch_size=1,grad_accum_steps=16,num_workers=2,multi_scale=False,expanded_scales=False,use_ema=True,early_stopping=not a.smoke,early_stopping_patience=10,tensorboard=False,wandb=False,run_test=False,seed=c['seed'],checkpoint_interval=10,lr=1e-4,lr_encoder=1e-5,lr_drop=30,compute_val_loss=True,log_per_class_metrics=False)
    if a.resume:settings['resume']=a.resume
    save(out/'run_contract.json',{'config':c,'train':settings,'gpu':torch.cuda.get_device_name(0),'job_id':os.environ.get('SLURM_JOB_ID'),'pretrained_sha256':sha(c['detector_pretrained']),'label_scope':'partial-label training and validation diagnostics; test not used'})
    model=RFDETR2XLarge(pretrain_weights=c['detector_pretrained'],num_classes=1,resolution=c['detector_resolution'])
    save(out/'status.json',{'status':'training','job_id':os.environ.get('SLURM_JOB_ID')})
    model.train(**settings)
    assert (out/'checkpoint_best_total.pth').is_file()
    save(out/'status.json',{'status':'completed','max_epochs':settings['epochs'],'early_stopping':settings['early_stopping'],'actual_epoch_source':'metrics.csv and checkpoint metadata','job_id':os.environ.get('SLURM_JOB_ID'),'test_evaluated':False})

if __name__=='__main__':
    try:main()
    except Exception:
        import sys
        try:
            config=json.loads(Path(sys.argv[sys.argv.index('--config')+1]).read_text())
            save(Path(config['workspace'])/'training_failure.json',{'status':'failed','job_id':os.environ.get('SLURM_JOB_ID'),'traceback':traceback.format_exc()})
        except Exception:pass
        traceback.print_exc();raise
