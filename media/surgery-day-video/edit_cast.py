"""Third patient video: plaster cast care, built from Veo clips with the same tools as edit_recovery.py.

Usage: python3 edit_cast.py <edit_tamil parts dir> <out_dir> <scene1.mp4> <scene2.mp4> ...
Set WITH_CREDITS=1 to add the credits card at the end.
"""
import os
import subprocess
import sys

from PIL import Image, ImageDraw

from edit_recovery import make_scene
from edit_tamil import EN_BOLD, EN_MED, H, W, font, make_card

TITLE = "Mastering Your Plaster"
SUBTITLE = "How to Care for Your POP Cast"


LOGO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "ghemi-logo.jpg")


def logo_png(path):
    """Full-screen GHEMI logo card (the logo has a white background)."""
    im = Image.new("RGB", (W, H), "white")
    lg = Image.open(LOGO).convert("RGB")
    lg.thumbnail((H - 60, H - 60), Image.LANCZOS)
    im.paste(lg, ((W - lg.size[0]) // 2, (H - lg.size[1]) // 2))
    im.save(path)


def title_png(path, logo=None):
    """Opening card: the GHEMI logo (when supplied) and the title."""
    import numpy as np
    ys = np.linspace(0, 1, H)[:, None, None]
    top, bot = np.array([18, 128, 110]), np.array([14, 52, 60])
    im = Image.fromarray((top * (1 - ys) + bot * ys).repeat(W, axis=1).astype(np.uint8), "RGB")
    d = ImageDraw.Draw(im)
    y = 120
    if logo and os.path.exists(logo):
        lg = Image.open(logo).convert("RGBA")
        lg.thumbnail((420, 420))
        mask = Image.new("L", lg.size, 0)
        ImageDraw.Draw(mask).ellipse([0, 0, lg.size[0] - 1, lg.size[1] - 1], fill=255)
        d.ellipse([W / 2 - lg.size[0] / 2 - 10, y - 10, W / 2 + lg.size[0] / 2 + 10, y + lg.size[1] + 10], fill="white")
        im.paste(lg, (int(W / 2 - lg.size[0] / 2), y), mask)
        y += lg.size[1] + 70
    else:
        y = 470
    d.text((W / 2, y), TITLE, font=font(EN_BOLD, 96), fill="white", anchor="mm")
    d.text((W / 2, y + 100), SUBTITLE, font=font(EN_MED, 54), fill=(205, 236, 228), anchor="mm")
    d.rectangle([W / 2 - 70, y + 160, W / 2 + 70, y + 165], fill=(255, 214, 140))
    im.save(path)

ORANGE, WHITE, TEAL = (245, 168, 28), (255, 255, 255), (32, 172, 200)

# ta/en None = subtitle not supplied yet.
SCENES = [
    {"ta": None, "en": None,
     # Veo wrote "DO NOT RUIN YOUR YOUR CAST!" (YOUR twice): erase it and redraw it correctly.
     "erase": [(12, 290, 738, 375, 1.95, 2.7),    # wider while the title animates in
               (130, 290, 620, 375, 2.7, 6.4)],
     "fix_t": (2.04, 6.4),
     "fix": [(130, 300, 620, 120, "DO NOT", 112, "title", ORANGE),
             (130, 410, 620, 115, "RUIN YOUR", 100, "title", WHITE),
             (130, 520, 620, 125, "CAST!", 118, "title", TEAL)]},
    {"ta": None, "en": None},   # 2: 48-hour drying rule
    {"ta": None, "en": None},   # 3: plastic cover
    {"ta": None, "en": None},   # 4: ruler warning
    {"ta": None, "en": None},   # 5: hair dryer
    {"ta": None, "en": None},   # 6: raise the limb on pillows
    {"ta": None, "en": None},   # 7: move fingers and toes
    {"ta": None, "en": None},   # 8: warning signs (pain, numbness, blue toes/fingers)
    # 9: closing thumbs up. Veo writes "Uertntroch" across him from 5.0 s, so the clip ends just before.
    {"ta": None, "en": None, "trim": (0, 4.95)},
]


def main():
    prev_parts, out, *sources = sys.argv[1:]
    tmp = os.path.join(out, "parts")
    os.makedirs(tmp, exist_ok=True)
    title = os.path.join(tmp, "c_title.png")
    title_png(title)
    logo = os.path.join(tmp, "c_logo.png")
    logo_png(logo)
    # New series: GHEMI logo, then the title card (no hospital intro clip).
    parts = [os.path.join(tmp, "c_logo.mp4"), os.path.join(tmp, "c_title.mp4")]
    make_card(logo, 4.0, parts[0], tmp)
    make_card(title, 5.0, parts[1], tmp)
    for i, (sc, src) in enumerate(zip(SCENES, sources), 1):
        part = os.path.join(tmp, f"c_scene{i:02d}.mp4")
        print(f"scene {i}: {make_scene(i, sc, src, part, tmp):.1f}s", flush=True)
        parts.append(part)
    if os.environ.get("WITH_CREDITS") == "1":
        parts.append(os.path.join(prev_parts, "p_credits.mp4"))
    listing = os.path.join(tmp, "c_list.txt")
    with open(listing, "w") as f:
        f.writelines(f"file '{p}'\n" for p in parts)
    final = os.path.join(out, "cast-care-tamil.mp4")
    subprocess.check_call(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", listing,
                           "-c", "copy", "-movflags", "+faststart", final])
    print("wrote", final)


if __name__ == "__main__":
    main()
