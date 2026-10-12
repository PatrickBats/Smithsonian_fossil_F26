"""Regression checks for image selection, LoG pixel provenance and merging."""
import numpy as np
from prepare_pipeline_data import positions
from spring_focus_stack import focus_stack,laplacian_of_gaussian
from spring_nms import deduplicate
from spring_types import TileSpec,Detection
import cv2

assert positions(100,3100,1024,921)==[100,1021,1942,2076]
assert positions(0,2048,1024,921)==[0,921,1024]
assert positions(0,500,1024,921)==[]
# The grid function has no specimen-coordinate argument, and includes its
# right/bottom edge positions even if no object lies there.
rng=np.random.default_rng(549);tile=rng.integers(0,256,(24,24,3,4),dtype=np.uint8)
rgb,_=focus_stack(tile,k=5)
responses=np.stack([abs(laplacian_of_gaussian(cv2.cvtColor(tile[:,:,:,z],cv2.COLOR_RGB2GRAY),5)) for z in range(4)])
best=responses.argmax(axis=0)
expected=tile[np.arange(24)[:,None],np.arange(24)[None,:],:,best]
assert np.array_equal(rgb,expected),'Stacked pixels must come from max-abs-LoG plane'
def d(x,score):return Detection(x,0,x+20,20,score,0,0,0,0)
a,b,c=d(0,.5),d(2,.9),d(4,.8)
tiles={TileSpec(0,0,1024,1024,0,0):[a],TileSpec(10,0,1024,1024,10,0):[b],TileSpec(20,0,1024,1024,20,0):[c]}
assert deduplicate(tiles,.5)==[b]
# The paper does not merge detections within the same tile in this pass.
assert len(deduplicate({TileSpec(0,0,1024,1024,0,0):[a,b]},.5))==2
assert len(deduplicate({TileSpec(0,0,1024,1024,0,0):[a],TileSpec(2048,0,1024,1024,2048,0):[b]},.5))==2
print('Abbas grid / LoG pixel identity / boundary-aware union-find checks passed',flush=True)
