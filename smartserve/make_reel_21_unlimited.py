# Smart Serve Reel #21 - "unlimited" mandi clip with a live owner's LOSS METER,
# then an offer-report phone end card with the app icon and "Comment APP for the app's name".
# The clip keeps its own Tamil audio and caption.
# Usage: python3 make_reel_21_unlimited.py <clip.mp4>
import math, os, random, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import soundtrack as st
from make_photo_memes import emoji_img

SRC = sys.argv[1]
OUT = os.path.join(HERE, "smartserve_reel_21_unlimited.mp4")
W, H, FPS, SR = 1080, 1920, 30, 44100
F = "/usr/share/fonts/opentype/inter/"
def font(sz, w="Bold"): return ImageFont.truetype(F + f"Inter-{w}.otf", sz)
WHITE, BLACK, RED, GREEN, YEL = (255, 255, 255), (0, 0, 0), (235, 45, 45), (40, 200, 110), (255, 214, 0)
BLUE, NAVY = (24, 63, 191), (8, 18, 58)
LOGO = Image.open(os.path.join(HERE, "assets", "logo.png")).convert("RGBA")
def clamp(x): return max(0.0, min(1.0, x))
def ease(x): x = clamp(x); return 1 - (1 - x) ** 3

CUT = 12.4                    # clip goes to black at ~13s
PRICE = 299
SCOOPS = [0.3, 1.6, 2.3, 3.1, 4.3, 6.1, 7.0, 7.9, 8.8]
PER_SCOOP = 412 / len(SCOOPS)  # ends at the ₹412 the report shows
FACE_T = 9.7                  # the stretched-smile moment
END = 6.0

def served_at(t):
    n = sum(1 for s in SCOOPS if t >= s)
    if n == 0: return 0.0
    last = SCOOPS[n - 1]; prev = (n - 1) * PER_SCOOP
    return prev + PER_SCOOP * ease((t - last) / 0.35)

def meter(img, t, a=1.0):
    if a <= 0: return
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    y0 = 1230; A = lambda c, k=255: c + (int(k * a),)
    d.rounded_rectangle([50, y0, W - 50, y0 + 230], 34, fill=(0, 0, 0, int(185 * a)))
    served = served_at(t); loss = served - PRICE
    d.text((90, y0 + 22), "PLATE PRICE", font=font(28, "Bold"), fill=A((190, 190, 200)))
    d.text((90, y0 + 56), f"₹{PRICE}", font=font(64, "Black"), fill=A(WHITE))
    lab = "FOOD SERVED"; f = font(28, "Bold"); w = d.textlength(lab, font=f)
    d.text((W - 90 - w, y0 + 22), lab, font=f, fill=A((190, 190, 200)))
    col = YEL if served <= PRICE else RED
    txt = f"₹{served:.0f}"; f2 = font(64, "Black"); w = d.textlength(txt, font=f2)
    d.text((W - 90 - w, y0 + 56), txt, font=f2, fill=A(col))
    # bar: green up to the price, red beyond it
    bx0, bx1, by = 90, W - 90, y0 + 160; full = PRICE * 1.5
    d.rounded_rectangle([bx0, by, bx1, by + 34], 17, fill=A((60, 60, 70)))
    px = bx0 + (bx1 - bx0) * PRICE / full
    sx = bx0 + (bx1 - bx0) * min(served, full) / full
    if sx > bx0 + 4: d.rounded_rectangle([bx0, by, min(sx, px), by + 34], 17, fill=A(GREEN))
    if served > PRICE: d.rounded_rectangle([px - 17, by, sx, by + 34], 17, fill=A(RED))
    d.line([px, by - 10, px, by + 44], fill=A(WHITE), width=4)
    if loss > 0:
        f3 = font(40, "Black"); txt = f"LOSS  -₹{loss:.0f}"; w = d.textlength(txt, font=f3)
        pulse = 1 + 0.06 * math.sin(t * 14)
        d.rounded_rectangle([(W - w) / 2 - 24, y0 - 70, (W + w) / 2 + 24, y0 - 10], 18, fill=A(RED))
        d.text(((W - w) / 2, y0 - 66), txt, font=f3, fill=A(WHITE))
    img.paste(lay, (0, 0), lay)

def scoop_pops(img, t):
    d = ImageDraw.Draw(img)
    for s in SCOOPS:
        k = (t - s) / 0.9
        if 0 <= k <= 1:
            y = 470 - 160 * ease(k); col = tuple(int(c * (1 - k) + 0 * k) for c in RED)
            f = font(int(84 * (1 + 0.2 * (1 - k))), "Black"); txt = f"-₹{PER_SCOOP:.0f}"; w = d.textlength(txt, font=f)
            x = 640 + 60 * math.sin(s * 3)
            d.text((x - w / 2, y), txt, font=f, fill=RED if k < 0.7 else col, stroke_width=6, stroke_fill=WHITE)

def face_label(img, t):
    a = ease((t - FACE_T) / 0.3)
    if a <= 0: return
    d = ImageDraw.Draw(img); f = font(64, "Black"); txt = "the owner doing the math"
    e = emoji_img("🙂", 66); w = d.textlength(txt, font=f) + e.width + 16
    y = 1290 + int(40 * (1 - a))
    d.rounded_rectangle([(W - w) / 2 - 36, y, (W + w) / 2 + 36, y + 110], 30, fill=WHITE)
    d.text(((W - w) / 2, y + 18), txt, font=f, fill=BLACK)
    img.paste(e, (int((W + w) / 2 - e.width), y + 22), e)

# ---------------- end card: offer report on a phone ----------------
ROWS = [("Plate price", "₹299", WHITE), ("Avg food served", "₹412", YEL), ("Plates sold today", "38", WHITE),
        ("Loss per plate", "-₹113", RED), ("Lost today", "-₹4,294", RED)]
def end_card(img, t):
    d = ImageDraw.Draw(img)
    for y in range(H):
        k = y / H; d.line([0, y, W, y], fill=(int(8 + 10 * k), int(18 + 30 * k), int(58 + 90 * k)))
    a = ease(t / 0.4); px0, px1 = 170, W - 170; py0 = 150 + int(80 * (1 - a)); py1 = py0 + 1000
    d.rounded_rectangle([px0 - 16, py0 - 16, px1 + 16, py1 + 16], 70, fill=(25, 25, 30))
    d.rounded_rectangle([px0, py0, px1, py1], 56, fill=(16, 20, 34))
    d.rounded_rectangle([W / 2 - 80, py0 + 18, W / 2 + 80, py0 + 46], 14, fill=(25, 25, 30))
    l = LOGO.resize((84, 84), Image.LANCZOS); img.paste(l, (px0 + 40, py0 + 80), l)
    d.text((px0 + 142, py0 + 84), "Offer report", font=font(42, "ExtraBold"), fill=WHITE)
    d.text((px0 + 142, py0 + 134), "Today · auto-updated", font=font(28, "Medium"), fill=(150, 160, 190))
    d.rounded_rectangle([px0 + 36, py0 + 210, px1 - 36, py0 + 290], 22, fill=(35, 42, 66))
    d.text((px0 + 64, py0 + 226), "UNLIMITED MANDI", font=font(40, "Black"), fill=WHITE)
    for i, (k, v, c) in enumerate(ROWS):
        st_ = 0.5 + i * 0.28
        if t < st_: continue
        aa = ease((t - st_) / 0.25); y = py0 + 330 + i * 92 + int(20 * (1 - aa))
        d.text((px0 + 64, y), k, font=font(38, "SemiBold"), fill=(200, 205, 225))
        f = font(44, "Black"); w = d.textlength(v, font=f); d.text((px1 - 64 - w, y - 4), v, font=f, fill=c)
        d.line([px0 + 64, y + 66, px1 - 64, y + 66], fill=(40, 46, 70), width=2)
    if t > 2.1:
        pulse = 1 + 0.04 * math.sin(t * 10); f = font(int(40 * pulse), "Black"); txt = "This offer is eating your profit"; w = d.textlength(txt, font=f)
        d.rounded_rectangle([(W - w) / 2 - 30, py0 + 820, (W + w) / 2 + 30, py0 + 900], 24, fill=RED)
        d.text(((W - w) / 2, py0 + 832), txt, font=f, fill=WHITE)
    if t > 2.9:  # icon + the ask
        aa = ease((t - 2.9) / 0.35); sz = int(150 * (0.6 + 0.4 * aa))
        glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(glow).ellipse([W / 2 - 170, 1210, W / 2 + 170, 1520], fill=(120, 190, 255, int(110 * aa)))
        glow = glow.filter(ImageFilter.GaussianBlur(45)); img.paste(glow, (0, 0), glow)
        l = LOGO.resize((sz, sz), Image.LANCZOS); img.paste(l, (int(W / 2 - sz / 2), int(1300 - sz / 2)), l)
        d = ImageDraw.Draw(img)
        f4 = font(50, "Black"); txt = 'Comment "APP" for the app\'s name'; w = d.textlength(txt, font=f4)
        d.rounded_rectangle([(W - w) / 2 - 30, 1410, (W + w) / 2 + 30, 1500], 24, fill=GREEN)
        d.text(((W - w) / 2, 1422), txt, font=f4, fill=(5, 30, 15))
        f5 = font(36, "SemiBold"); txt = "see which offers make money · free on Play Store"; w = d.textlength(txt, font=f5)
        d.text(((W - w) / 2, 1522), txt, font=f5, fill=(200, 220, 255))

# ---------------- audio ----------------
def soundtrack(path, total):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-t", str(CUT), "-i", SRC, "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"],
                         capture_output=True).stdout
    src = np.frombuffer(raw, np.int16).astype(np.float64) / 32768
    mix = np.zeros(int(total * SR) + SR); n = int(0.5 * SR)
    src = src.copy(); src[-n:] *= np.linspace(1, 0, n); st.add(mix, src * 0.9, 0)
    for i, s in enumerate(SCOOPS):  # coin drop, pitching down as the loss grows
        tt = np.arange(int(0.25 * SR)) / SR; f0 = 1800 - i * 110
        blip = np.sin(2 * np.pi * np.cumsum(f0 * np.exp(-tt * 6)) / SR) * np.exp(-tt / 0.08)
        st.add(mix, blip * 0.35, s)
    cross = next(s for i, s in enumerate(SCOOPS) if (i + 1) * PER_SCOOP > PRICE)
    tt = np.arange(int(0.5 * SR)) / SR; buzz = np.sign(np.sin(2 * np.pi * 140 * tt)) * np.exp(-tt / 0.2)
    st.add(mix, buzz * 0.25, cross)                       # "wrong answer" buzz when it tips into loss
    # end card: light marimba groove
    t0 = CUT; dur = total - t0; seq = (72, 76, 79, 76, 74, 77, 81, 77)
    for k in range(int(dur / 0.25)):
        st.add(mix, st.pluck(st.note(seq[k % 8]), 0.3, 2) * 0.22, t0 + k * 0.25)
        if k % 4 == 0: st.add(mix, st.kick() * 0.35, t0 + k * 0.25)
        if k % 4 == 2: st.add(mix, st.clap() * 0.12, t0 + k * 0.25)
    for i in range(len(ROWS)): st.add(mix, st.sfx_pop() * 0.3, t0 + 0.5 + i * 0.28)
    tt = np.arange(int(0.6 * SR)) / SR; alarm = np.sin(2 * np.pi * 880 * tt) * (np.sin(2 * np.pi * 8 * tt) > 0) * np.exp(-tt / 0.4)
    st.add(mix, alarm * 0.2, t0 + 2.1)
    for j, m in enumerate((84, 88, 91)): st.add(mix, st.pluck(st.note(m), 0.6, 3) * 0.35, t0 + 2.9 + j * 0.07)
    st.finish(mix, path, total)

if __name__ == "__main__":
    total = CUT + END; wav = OUT[:-4] + ".wav"; soundtrack(wav, total)
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
        "-r", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", OUT], stdin=subprocess.PIPE)
    p = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-t", str(CUT), "-i", SRC, "-vf", f"fps={FPS},scale={W}:{H}",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    nb = W * H * 3; i = 0
    while True:
        buf = p.stdout.read(nb)
        if len(buf) < nb: break
        t = i / FPS; fr = Image.frombytes("RGB", (W, H), buf)
        scoop_pops(fr, t)
        meter(fr, t, 1 - ease((t - FACE_T) / 0.3) if t >= FACE_T else 1.0)
        face_label(fr, t)
        ff.stdin.write(fr.tobytes()); i += 1
    p.wait()
    for k in range(int(END * FPS)):
        img = Image.new("RGB", (W, H)); end_card(img, k / FPS); ff.stdin.write(img.tobytes())
    ff.stdin.close(); ff.wait(); os.remove(wav)
    print("done", OUT, total)
