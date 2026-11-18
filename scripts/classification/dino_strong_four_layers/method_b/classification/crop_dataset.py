"""Training-only augmentation and normalized specimen crop datasets."""
import random
import math
from PIL import Image, ImageOps
from torch.utils.data import Dataset
from torchvision.transforms import functional as TF
from torchvision.transforms import InterpolationMode

class Crops(Dataset):
    def __init__(self, root, rows, labels, augment, augmentation="baseline"):
        """Initialize the classifier model or crop dataset with the recorded configuration.

        Args:
            root: Root directory containing the prepared crop dataset.
            rows: Specimen manifest records, including record IDs, labels and split membership.
            labels: Class names in checkpoint output order.
            augment: Whether to apply training-only quarter-turns and reflections.

        Returns:
            None: Initializes this instance.
        """
        self.rows = rows
        self.targets = [labels.index(r["sponsor_category"]) for r in rows]
        self.augment = augment
        if augmentation not in ("baseline", "mild", "strong", "geometry"):
            raise ValueError("Unknown augmentation policy")
        self.augmentation = augmentation
        self.images = []
        for row in rows:
            with Image.open(root / row["image_relpath"]) as im:
                side = max(im.size)
                im = ImageOps.pad(im, (side, side), color="white")
                self.images.append(im.resize((224, 224), Image.Resampling.BICUBIC).copy())

    def __len__(self):
        """Return the number of classifier crop records.

        Returns:
            int: Number of specimens.
        """
        return len(self.rows)

    def __getitem__(self, index):
        """Prepare one crop using the recorded augmentation and ImageNet normalization.

        Args:
            index: Zero-based specimen index.

        Returns:
            tuple: Image tensor (3, 224, 224), class index, and specimen index.
        """
        im = self.images[index]
        if self.augment and self.augmentation in ("strong", "geometry"):
            im, _ = strong_transform(im, self.rows[index], stronger_geometry=self.augmentation == "geometry")
        elif self.augment:
            # Quarter-turns and reflections retain the full square specimen crop.
            k = random.randrange(4)
            if k:
                im = im.transpose(
                    [
                        Image.Transpose.ROTATE_90,
                        Image.Transpose.ROTATE_180,
                        Image.Transpose.ROTATE_270,
                    ][k - 1]
                )
            if random.random() < 0.5:
                im = ImageOps.mirror(im)
            if self.augmentation == "mild":
                # White fill matches the recorded square crop background.
                im = TF.affine(im, angle=0.0,
                    translate=[round(random.uniform(-0.05, 0.05) * im.width),
                               round(random.uniform(-0.05, 0.05) * im.height)],
                    scale=random.uniform(0.9, 1.1), shear=[0.0, 0.0],
                    interpolation=InterpolationMode.BILINEAR, fill=255)
                im = TF.adjust_brightness(im, random.uniform(0.9, 1.1))
                im = TF.adjust_contrast(im, random.uniform(0.9, 1.1))
                if random.random() < 0.1:
                    sigma = random.uniform(0.1, 0.5)
                    im = TF.gaussian_blur(im, [3, 3], [sigma, sigma])
        x = TF.normalize(TF.to_tensor(im), [0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
        return x, self.targets[index], index


def strong_transform(im, row, photometric=True, stronger_geometry=False):
    """Reject transforms whose annotated bounding rectangle leaves the image."""
    side=float(row['crop_side_px'])
    cx=(float(row['center_x_px'])-float(row['crop_left_px']))*224/side
    cy=(float(row['center_y_px'])-float(row['crop_top_px']))*224/side
    rx=float(row['radius_x_px'])*224/side; ry=float(row['radius_y_px'])*224/side
    hf=random.random()<.5; vf=random.random()<.5
    if hf: im=ImageOps.mirror(im);cx=224-cx
    if vf: im=ImageOps.flip(im);cy=224-cy
    accepted=False
    for attempt in range(100):
        angle=random.uniform(0,360);scale=random.uniform(.7,1.3) if stronger_geometry else random.uniform(.8,1.2)
        limit=.15 if stronger_geometry else .1
        tx=round(random.uniform(-limit,limit)*224);ty=round(random.uniform(-limit,limit)*224)
        a=math.radians(angle);c=math.cos(a);sn=math.sin(a)
        x=112+scale*(c*(cx-112)-sn*(cy-112))+tx
        y=112+scale*(sn*(cx-112)+c*(cy-112))+ty
        ex=scale*(abs(c)*rx+abs(sn)*ry);ey=scale*(abs(sn)*rx+abs(c)*ry)
        bounds=[x-ex,y-ey,x+ex,y+ey]
        if min(bounds[:2])>=2 and max(bounds[2:])<=222:
            accepted=True;break
    if not accepted:
        angle=0.;scale=1.;tx=ty=0;bounds=[cx-rx,cy-ry,cx+rx,cy+ry]
    im=TF.affine(im,angle=angle,translate=[tx,ty],scale=scale,shear=[0.,0.],interpolation=InterpolationMode.BILINEAR,fill=255)
    meta=dict(angle=angle,scale=scale,tx=tx,ty=ty,hflip=hf,vflip=vf,bounds=bounds,fallback=not accepted,attempts=attempt+1)
    if photometric:
        im=TF.adjust_brightness(im,random.uniform(.8,1.2))
        im=TF.adjust_contrast(im,random.uniform(.8,1.2))
        if random.random()<.2:
            sigma=random.uniform(.1,1.);im=TF.gaussian_blur(im,[3,3],[sigma,sigma])
    return im,meta
