# Listicle reels (the "5 things…" white-box format): stock photo/clip with the title box for 5s,
# then the same shot with "Read the description below" + 👇 for 2s. Total 7s, no CTA screen;
# the list (and the Comment "APP" ask) lives in the caption.
# Usage: python3 make_listicle.py <stock.jpg|mp4> "<title>" <reel_number> <name>
import os, random, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import soundtrack as st
from make_photo_memes import emoji_img

SRC, TITLE, NUM, NAME = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
OUT = os.path.join(HERE, f"smartserve_reel_{NUM:02d}_list_{NAME}.mp4")
W, H, FPS, SR = 1080, 1920, 30, 44100
HOOK, TAIL = 5.0, 2.0
F = "/usr/share/fonts/opentype/inter/"

def cover(im):
    s = max(W / im.width, H / im.height); im = im.resize((int(im.width * s) + 1, int(im.height * s) + 1), Image.LANCZOS)
    x, y = (im.width - W) // 2, (im.height - H) // 2; return im.crop((x, y, x + W, y + H))

def stock_frames():
    n = int((HOOK + TAIL) * FPS)
    if SRC.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
        base = cover(Image.open(SRC).convert("RGB")).resize((int(W * 1.12), int(H * 1.12)), Image.LANCZOS)
        for i in range(n):  # slow push-in
            z = 1.12 - 0.10 * i / n; cw, ch = W * z, H * z
            x0, y0 = (base.width - cw) / 2, (base.height - ch) / 2
            yield base.crop((int(x0), int(y0), int(x0 + cw), int(y0 + ch))).resize((W, H), Image.LANCZOS)
    else:
        p = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-stream_loop", "-1", "-t", str(HOOK + TAIL), "-i", SRC, "-vf",
            f"fps={FPS},scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
            stdout=subprocess.PIPE)
        for _ in range(n):
            buf = p.stdout.read(W * H * 3)
            if len(buf) < W * H * 3: break
            yield Image.frombytes("RGB", (W, H), buf)
        p.wait()

def title_box(img, text=None, emoji=None):
    text = text or TITLE
    d = ImageDraw.Draw(img); f = ImageFont.truetype(F + "Inter-Medium.otf", 60); lines = []
    for w in text.split():
        if lines and d.textlength(lines[-1] + " " + w, font=f) <= 700: lines[-1] += " " + w
        else: lines.append(w)
    lh = 76; bw = max(d.textlength(l, font=f) for l in lines) + 90; bh = lh * len(lines) + 70 + (110 if emoji else 0)
    x0, y0 = (W - bw) / 2, 1020
    d.rectangle([x0, y0, x0 + bw, y0 + bh], fill=(255, 255, 255))
    for i, l in enumerate(lines):
        w = d.textlength(l, font=f); d.text(((W - w) / 2, y0 + 30 + i * lh), l, font=f, fill=(25, 25, 25))
    if emoji:
        e = emoji_img(emoji, 90); e = e.crop(e.getbbox())
        img.paste(e, (int((W - e.width) / 2), int(y0 + 30 + lh * len(lines) + 8)), e)

def soundtrack(path):
    total = HOOK + TAIL; mix = np.zeros(int(total * SR) + SR)
    for k in range(int(total / 0.5)):  # soft plucked bed, one gentle loop
        st.add(mix, st.pluck(st.note((64, 67, 71, 69)[k % 4]), 0.9, 2) * 0.12, k * 0.5)
        if k % 4 == 0: st.add(mix, st.sub(st.note(40 + (k // 4) % 2 * 3), 2.0) * 0.06, k * 0.5)
    st.add(mix, st.sfx_pop() * 0.35, HOOK)  # tiny pop when the text swaps
    st.finish(mix, path, total)

if __name__ == "__main__":
    wav = OUT[:-4] + ".wav"; soundtrack(wav)
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
        "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
        "-shortest", "-movflags", "+faststart", OUT], stdin=subprocess.PIPE)
    for i, fr in enumerate(stock_frames()):
        title_box(fr) if i < HOOK * FPS else title_box(fr, "Read the description below", "👇"); ff.stdin.write(fr.tobytes())
    ff.stdin.close(); ff.wait(); os.remove(wav)
    tmp = OUT[:-4] + "_tmp.mp4"; os.replace(OUT, tmp)   # match the other reels' loudness (~-14 LUFS)
    out = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", tmp, "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True).stderr
    gain = -14.0 - float(out.split("Summary:")[1].split("I:")[1].split("LUFS")[0])
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", tmp, "-c:v", "copy", "-af", f"volume={gain:.2f}dB,alimiter=limit=0.9",
                    "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", OUT], check=True); os.remove(tmp)
    print("done", OUT)
