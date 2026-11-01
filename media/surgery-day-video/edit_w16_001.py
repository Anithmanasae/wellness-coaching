"""W16-001: Ward 16 welcome, built per W16-001-edl.md.

Real MO footage only (no face or voice changes). B-roll is real Ward 16 photos supplied by the ward.

Usage: python3 edit_w16_001.py <mo_camera_original.mp4> <entrance.jpg> <corridor.jpg> <out_dir>
"""
import os
import subprocess
import sys

from PIL import Image, ImageEnhance, ImageFilter

from edit_recovery import make_scene
from edit_tamil import H, W, make_card
import edit_ward

# Modest grade + reframing for the MO shot (as in W16-001-edl.md §5).
MO_VF = ("crop=1024:576:128:144,scale=1920:1080:flags=lanczos,hqdn3d=2:2:4:4,"
         "curves=master='0/0 0.25/0.30 0.5/0.58 0.75/0.82 1/1',eq=contrast=1.06:saturation=1.15,"
         "colorbalance=rs=0.04:gs=0.01:bs=-0.03:rm=0.03:bm=-0.02,unsharp=5:5:0.7:5:5:0,vignette=PI/9")
# His own voice: clean-up and levelling only (EDL §4).
MO_AF = "highpass=f=80,afftdn=nf=-25,acompressor=threshold=-20dB:ratio=3:attack=5:release=100"

TITLE_TA = "எலும்பியல் விடுதி 16க்கு வரவேற்கிறோம்"
SUB_TA = "வணக்கம்! கிளிநொச்சி மாவட்ட பொது வைத்தியசாலையின் எலும்பியல் விடுதி 16க்கு உங்களை அன்புடன் வரவேற்கிறோம்."
SUB_EN = "Hello! A warm welcome to Orthopaedic Ward 16 of District General Hospital Kilinochchi."

# B-roll windows, in seconds of the MO clip. He stays on screen for "வணக்கம்!" and for the closing
# "…உங்களை அன்புடன் வரவேற்கிறோம்". Word timings are estimates: check by ear.
BROLL = [("entrance", 1.3, 3.1), ("corridor", 3.1, 4.7)]


def broll_still(src, dst):
    """Portrait photo centred on a blurred fill of itself, with a modest lift for the dim ward light."""
    ph = Image.open(src).convert("RGB")
    ph = ImageEnhance.Brightness(ph).enhance(1.08)
    ph = ImageEnhance.Contrast(ph).enhance(1.05)
    bg = ph.resize((W, int(ph.height * W / ph.width))).crop((0, 0, W, H)).filter(ImageFilter.GaussianBlur(40))
    bg = ImageEnhance.Brightness(bg).enhance(0.7)
    fh = H
    fw = int(ph.width * fh / ph.height)
    bg.paste(ph.resize((fw, fh), Image.LANCZOS), ((W - fw) // 2, 0))
    bg.save(dst)


def main():
    mo, entrance, corridor, out = sys.argv[1:5]
    tmp = os.path.join(out, "parts")
    os.makedirs(tmp, exist_ok=True)

    graded = os.path.join(tmp, "mo_graded.mp4")
    subprocess.check_call(["ffmpeg", "-y", "-loglevel", "error", "-i", mo, "-vf", MO_VF, "-af", MO_AF,
                           "-c:v", "libx264", "-crf", "14", "-preset", "fast", "-c:a", "aac", "-b:a", "192k", graded])

    stills = {"entrance": entrance, "corridor": corridor}
    inputs, chain, last = ["-i", graded], "[0:v]null[v0]", "v0"
    for k, (name, t0, t1) in enumerate(BROLL, 1):
        png = os.path.join(tmp, f"broll_{name}.png")
        broll_still(stills[name], png)
        d = t1 - t0
        n = int(d * 24) + 2
        inputs += ["-loop", "1", "-t", f"{d:.2f}", "-i", png]
        chain += (f";[{k}:v]scale={W * 2}:{H * 2},zoompan=z='1+0.05*on/{n}':x='iw/2-(iw/zoom/2)':"
                  f"y='ih/2-(ih/zoom/2)':d={n}:s={W}x{H}:fps=24,format=yuva420p,"
                  f"fade=t=in:st=0:d=0.25:alpha=1,fade=t=out:st={d - 0.25:.2f}:d=0.25:alpha=1,"
                  f"setpts=PTS-STARTPTS+{t0}/TB[b{k}];[{last}][b{k}]overlay=eof_action=pass[v{k}]")
        last = f"v{k}"
    with_broll = os.path.join(tmp, "mo_broll.mp4")
    subprocess.check_call(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", chain,
                           "-map", f"[{last}]", "-map", "0:a", "-c:v", "libx264", "-crf", "14", "-preset", "fast",
                           "-c:a", "copy", with_broll])

    edit_ward.TITLE_TA = TITLE_TA
    title = os.path.join(tmp, "title.png")
    edit_ward.title_png(title)
    parts = [os.path.join(tmp, "title.mp4"), os.path.join(tmp, "mo_final.mp4")]
    make_card(title, 5.0, parts[0], tmp)
    dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                         "-of", "default=nw=1:nk=1", with_broll]))
    make_scene(1, {"ta": SUB_TA, "en": SUB_EN, "sub_t": (0.05, dur - 0.1)}, with_broll, parts[1], tmp)
    listing = os.path.join(tmp, "list.txt")
    with open(listing, "w") as f:
        f.writelines(f"file '{p}'\n" for p in parts)
    final = os.path.join(out, "W16-001-ward16-welcome.mp4")
    subprocess.check_call(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", listing,
                           "-c", "copy", "-movflags", "+faststart", final])
    print("wrote", final)


if __name__ == "__main__":
    main()
