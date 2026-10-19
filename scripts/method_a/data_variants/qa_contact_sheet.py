"""Read-only visual QA of exported crop pixels and transformed annotation boxes."""

from PIL import Image, ImageDraw
from common import ROOT, load, write

plans = [load(p) for p in sorted((ROOT / "plan").glob("*.json"))]
selected = []
for p in plans:
    if p["index"] % 3:
        continue
    for c in p["crops"]:
        path = ROOT / "images/crops" / f"{c['tile_id']}.png"
        if path.is_file() and path.with_suffix(".json").is_file():
            selected.append((p, c, path))
            break
    if len(selected) == 8:
        break
assert len(selected) >= 4
sheet = Image.new("RGB", (4 * 320, 2 * 350), "#ededed")
draw = ImageDraw.Draw(sheet)
for i, (p, c, path) in enumerate(selected):
    with Image.open(path) as image:
        panel = image.convert("RGB")
        d = ImageDraw.Draw(panel)
        for obj in c["objects"]:
            x, y, w, h = obj["bbox"]
            d.rectangle((x, y, x + w, y + h), outline="red", width=3)
        panel = panel.resize((320, 320))
        x = (i % 4) * 320
        y = (i // 4) * 350
        sheet.paste(panel, (x, y))
        draw.text(
            (x + 4, y + 321),
            f"slide {p['index']} | crop {c['side']} | YES boxes {len(c['objects'])}",
            fill="black",
        )
path = ROOT / "audit/crop_qa_contact_sheet.jpg"
assert not path.exists()
sheet.save(path, quality=92)
write(
    ROOT / "audit/crop_qa_contact_sheet.json",
    {
        "status": "rendered",
        "sampled_slide_indices": [p["index"] for p, c, path in selected],
        "sampled_tiles": [c["tile_id"] for p, c, path in selected],
        "note": "Red boxes are existing YES annotations. Other visible grains remain unreviewed.",
    },
)
print(path, flush=True)
