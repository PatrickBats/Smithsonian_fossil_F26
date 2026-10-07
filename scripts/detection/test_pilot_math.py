"""Small geometry checks before running on allocated compute."""
import unittest
from types import SimpleNamespace
from run_pilot import box_pixels,iou
class Geometry(unittest.TestCase):
 def test_anisotropic_offset_conversion(self):
  m=SimpleNamespace(x_offset_nm=1000,y_offset_nm=-500,mpp_x=.25,mpp_y=.5,full_width=1000,full_height=2000)
  self.assertEqual(box_pixels([1000,-500],500,m),[498,999,502,1001])
 def test_iou(self):
  self.assertEqual(iou([0,0,10,10],[0,0,10,10]),1)
  self.assertEqual(iou([0,0,10,10],[10,0,20,10]),0)
  self.assertAlmostEqual(iou([0,0,10,10],[0,0,5,10]),.5)
if __name__=='__main__':unittest.main()
