"""Fourth GHEMI video: welcome to Orthopaedic Ward 16.

Usage: python3 edit_ward.py <out_dir> <scene1.mp4> ...
"""
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw

from edit_recovery import make_scene
from edit_tamil import EN_MED, H, TA_BOLD, W, font, make_card
from fix_moving_sign import fix_sign

TITLE_TA = "எலும்பியல் விடுதி பதினாறுக்கு வரவேற்கிறோம்"
TITLE_EN = "Welcome to Orthopaedic Ward 16"
NAVY = (40, 40, 90)

SCENES = [
    {"ta": "வணக்கம்! கிளிநொச்சி மாவட்ட பொது வைத்தியசாலையின் எலும்பியல் விடுதி பதினாறுக்கு உங்களை அன்புடன் வரவேற்கிறோம்.",
     "en": "Hello! A warm welcome to Orthopaedic Ward 16 of District General Hospital Kilinochchi.",
     # Opening shot: the ward sign's Tamil lines are garbled; tracked and rewritten.
     "sign": dict(ref_t=0.05, sign_box=(570, 95, 1365, 295), patch_box=(712, 108, 1358, 214), until_t=1.5,
                  lines=[("கிளிநொச்சி மாவட்ட பொது வைத்தியசாலை", TA_BOLD, NAVY),
                         ("எலும்பியல் விடுதி 16", TA_BOLD, NAVY)])},
]


SUB_TA, SUB_EN = SCENES[0]["ta"], SCENES[0]["en"]

# Other takes of the same welcome, each made into its own video.
TAKES = {
    "ward16-welcome-tamil-b": {"ta": SUB_TA, "en": SUB_EN,
                               # opens on a misspelled caption and sign; start at the cut to Vikash
                               "trim": (2.0, 10.0), "sub_t": (0.2, 8.0)},
    "ward16-welcome-tamil-c": {"ta": SUB_TA, "en": SUB_EN,
                               # its own opening caption is correct; subtitle starts after it
                               "sub_t": (1.5, 10.0)},
}


def title_png(path):
    ys = np.linspace(0, 1, H)[:, None, None]
    top, bot = np.array([18, 128, 110]), np.array([14, 52, 60])
    im = Image.fromarray((top * (1 - ys) + bot * ys).repeat(W, axis=1).astype(np.uint8), "RGB")
    d = ImageDraw.Draw(im)
    f = font(TA_BOLD, 84)
    while f.getlength(TITLE_TA) > W - 200:
        f = font(TA_BOLD, f.size - 2)
    d.text((W / 2, 480), TITLE_TA, font=f, fill="white", anchor="mm")
    d.text((W / 2, 585), TITLE_EN, font=font(EN_MED, 54), fill=(205, 236, 228), anchor="mm")
    d.rectangle([W / 2 - 70, 650, W / 2 + 70, 655], fill=(255, 214, 140))
    im.save(path)


def build_take(out, name, src):
    tmp = os.path.join(out, "parts")
    os.makedirs(tmp, exist_ok=True)
    title = os.path.join(tmp, "w_title.png")
    title_png(title)
    parts = [os.path.join(tmp, "w_title.mp4"), os.path.join(tmp, f"{name}.mp4")]
    make_card(title, 5.0, parts[0], tmp)
    make_scene(1, TAKES[name], src, parts[1], tmp)
    listing = os.path.join(tmp, f"{name}.txt")
    with open(listing, "w") as f:
        f.writelines(f"file '{p}'\n" for p in parts)
    final = os.path.join(out, f"{name}.mp4")
    subprocess.check_call(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", listing,
                           "-c", "copy", "-movflags", "+faststart", final])
    print("wrote", final)


def main():
    if sys.argv[1] == "--take":
        return build_take(sys.argv[2], sys.argv[3], sys.argv[4])
    out, *sources = sys.argv[1:]
    tmp = os.path.join(out, "parts")
    os.makedirs(tmp, exist_ok=True)
    title = os.path.join(tmp, "w_title.png")
    title_png(title)
    parts = [os.path.join(tmp, "w_title.mp4")]  # opens on the title card (no GHEMI logo card)
    make_card(title, 5.0, parts[0], tmp)
    for i, (sc, src) in enumerate(zip(SCENES, sources), 1):
        if "sign" in sc:
            fixed = os.path.join(tmp, f"w_sign{i:02d}.mp4")
            fix_sign(src, fixed, **sc["sign"])
            src = fixed
        part = os.path.join(tmp, f"w_scene{i:02d}.mp4")
        print(f"scene {i}: {make_scene(i, sc, src, part, tmp):.1f}s", flush=True)
        parts.append(part)
    listing = os.path.join(tmp, "w_list.txt")
    with open(listing, "w") as f:
        f.writelines(f"file '{p}'\n" for p in parts)
    final = os.path.join(out, "ward16-welcome-tamil.mp4")
    subprocess.check_call(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", listing,
                           "-c", "copy", "-movflags", "+faststart", final])
    print("wrote", final)


if __name__ == "__main__":
    main()
