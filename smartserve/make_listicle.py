# Listicle reels (the "5 things…" white-box format): stock photo/clip with a title box (3.5s)
# -> transition SFX -> scannable Comment "APP" CTA (3.5s). Total 7s. The list itself goes in the caption.
# Usage: python3 make_listicle.py <stock.jpg|mp4> "<title>" <reel_number> <name>
import os, random, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import soundtrack as st
from make_reel_variations import scene_cta_comment

SRC, TITLE, NUM, NAME = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
OUT = os.path.join(HERE, f"smartserve_reel_{NUM:02d}_list_{NAME}.mp4")
W, H, FPS, SR = 1080, 1920, 30, 44100
HOOK, CTA = 3.5, 3.5
F = "/usr/share/fonts/opentype/inter/"

def cover(im):
    s = max(W / im.width, H / im.height); im = im.resize((int(im.width * s) + 1, int(im.height * s) + 1), Image.LANCZOS)
    x, y = (im.width - W) // 2, (im.height - H) // 2; return im.crop((x, y, x + W, y + H))

def stock_frames():
    n = int(HOOK * FPS)
    if SRC.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
        base = cover(Image.open(SRC).convert("RGB")).resize((int(W * 1.12), int(H * 1.12)), Image.LANCZOS)
        for i in range(n):  # slow push-in
            z = 1.12 - 0.10 * i / n; cw, ch = W * z, H * z
            x0, y0 = (base.width - cw) / 2, (base.height - ch) / 2
            yield base.crop((int(x0), int(y0), int(x0 + cw), int(y0 + ch))).resize((W, H), Image.LANCZOS)
    else:
        p = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-t", str(HOOK), "-i", SRC, "-vf",
            f"fps={FPS},scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
            stdout=subprocess.PIPE)
        for _ in range(n):
            buf = p.stdout.read(W * H * 3)
            if len(buf) < W * H * 3: break
            yield Image.frombytes("RGB", (W, H), buf)
        p.wait()

def title_box(img):
    d = ImageDraw.Draw(img); f = ImageFont.truetype(F + "Inter-Medium.otf", 60); lines = []
    for w in TITLE.split():
        if lines and d.textlength(lines[-1] + " " + w, font=f) <= 700: lines[-1] += " " + w
        else: lines.append(w)
    lh = 76; bw = max(d.textlength(l, font=f) for l in lines) + 90; bh = lh * len(lines) + 70
    x0, y0 = (W - bw) / 2, 1020
    d.rectangle([x0, y0, x0 + bw, y0 + bh], fill=(255, 255, 255))
    for i, l in enumerate(lines):
        w = d.textlength(l, font=f); d.text(((W - w) / 2, y0 + 30 + i * lh), l, font=f, fill=(25, 25, 25))

def soundtrack(path):
    total = HOOK + CTA; mix = np.zeros(int(total * SR) + SR)
    for k in range(int(HOOK / 0.5)):  # soft plucked bed under the stock shot
        st.add(mix, st.pluck(st.note((64, 67, 71, 69)[k % 4]), 0.9, 2) * 0.12, k * 0.5)
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", os.path.join(HERE, "assets", "cta_transition_sfx.wav"),
                          "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"], capture_output=True).stdout
    fx = np.frombuffer(raw, np.int16).astype(np.float64) / 32768; st.add(mix, fx, HOOK)
    m0 = HOOK + min(len(fx) / SR - 0.1, 1.0); st.add(mix, st.music_uplift(total - m0), m0)
    for at, name in ((0.2, "kaching"), (0.05, "sparkle"), (0.6, "pop")):
        fn, g = st.SFX[name]; st.add(mix, fn(), HOOK + at, g)
    st.finish(mix, path, total)

if __name__ == "__main__":
    wav = OUT[:-4] + ".wav"; soundtrack(wav)
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
        "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
        "-shortest", "-movflags", "+faststart", OUT], stdin=subprocess.PIPE)
    for fr in stock_frames(): title_box(fr); ff.stdin.write(fr.tobytes())
    random.seed(NUM)
    for i in range(int(CTA * FPS)):  # CTA pops faster to fit 3.5s
        img = Image.new("RGB", (W, H)); scene_cta_comment(img, 0.4 + i / FPS); ff.stdin.write(img.tobytes())
    ff.stdin.close(); ff.wait(); os.remove(wav); print("done", OUT)
