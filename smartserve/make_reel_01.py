import math, subprocess, sys
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1920, 30
OUT = sys.argv[1]
F = "/usr/share/fonts/opentype/inter/"
def font(sz, w="Black"): return ImageFont.truetype(F + f"Inter-{w}.otf", sz)

BG = (18, 18, 22); WHITE = (255, 255, 255); YEL = (255, 204, 0)
RED = (255, 72, 72); GRN = (46, 214, 120); GREY = (150, 150, 160)

def clamp(x): return max(0.0, min(1.0, x))
def ease(x): x = clamp(x); return 1 - (1 - x) ** 3
def pop(t, start, dur=0.35):
    """scale for a pop-in: overshoot then settle"""
    x = clamp((t - start) / dur)
    if x <= 0: return 0
    return 1 + 0.15 * math.sin(x * math.pi) if x < 1 else 1

def text_c(img, txt, y, sz, col=WHITE, w="Black", scale=1.0, alpha=1.0, box=None):
    if scale <= 0 or alpha <= 0: return
    f = font(max(1, int(sz * scale)), w)
    d = ImageDraw.Draw(img)
    lines = txt.split("\n")
    lh = int(sz * scale * 1.18)
    y0 = y - lh * len(lines) // 2
    for i, ln in enumerate(lines):
        bw = d.textlength(ln, font=f)
        x = (W - bw) / 2
        if box:
            pad = 22
            d.rounded_rectangle([x - pad, y0 + i * lh - 8, x + bw + pad, y0 + i * lh + lh - 4], 18, fill=box)
        c = tuple(int(BG[k] + (col[k] - BG[k]) * alpha) for k in range(3))
        d.text((x, y0 + i * lh), ln, font=f, fill=c)

def pizza(img, cx, cy, r, slice_gap=0.0):
    d = ImageDraw.Draw(img)
    for k in range(8):
        a0 = k * 45; mid = math.radians(a0 + 22.5)
        ox, oy = math.cos(mid) * slice_gap, math.sin(mid) * slice_gap
        bb = [cx - r + ox, cy - r + oy, cx + r + ox, cy + r + oy]
        d.pieslice(bb, a0, a0 + 45, fill=(214, 150, 70))
        bb2 = [cx - r * .86 + ox, cy - r * .86 + oy, cx + r * .86 + ox, cy + r * .86 + oy]
        d.pieslice(bb2, a0 + 1, a0 + 44, fill=(250, 205, 90))
        for rr, aa in ((.55, 10), (.35, 30), (.7, 35)):
            px = cx + ox + math.cos(math.radians(a0 + aa)) * r * rr
            py = cy + oy + math.sin(math.radians(a0 + aa)) * r * rr
            d.ellipse([px - r * .08, py - r * .08, px + r * .08, py + r * .08], fill=(190, 40, 40))

def progress_bar(img, t, total):
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W * t / total, 10], fill=YEL)


ORANGE = (255, 122, 0)
def bowl(img, cx, cy, r, t):
    d = ImageDraw.Draw(img)
    d.ellipse([cx - r, cy - r * .55, cx + r, cy + r * .35], fill=(240, 170, 60))   # rice mound
    for k in range(40):
        a = k * 2.4; rr = (k % 7) / 7 * r * .8
        x = cx + math.cos(a) * rr; y = cy - r * .15 + math.sin(a) * rr * .35
        d.ellipse([x - 9, y - 5, x + 9, y + 5], fill=(255, 235, 190))
    for k in range(5):
        x = cx - r * .5 + k * r * .25; y = cy - r * .3 + (k % 2) * 30
        d.ellipse([x - 22, y - 14, x + 22, y + 14], fill=(150, 60, 20))
    d.chord([cx - r * 1.15, cy - r * .2, cx + r * 1.15, cy + r * 1.1], 0, 180, fill=(120, 60, 30))
    d.rectangle([cx - r * 1.15, cy + r * .43, cx + r * 1.15, cy + r * .47], fill=(90, 45, 20))

def scene1(img, t):  # hook
    bowl(img, W / 2, 1100, 300, t)
    text_c(img, "Customer paid", 380, 84, scale=pop(t, 0.0))
    text_c(img, "₹500 on the app", 520, 120, YEL, scale=pop(t, 0.2))
    text_c(img, "How much did the restaurant get?", 1600, 58, WHITE, scale=pop(t, 1.5), box=(200, 30, 30))

DEDUCT = [("Commission (25%)", 125), ("GST on commission", 23), ("Discount you funded", 50), ("Ads / visibility", 25)]
def scene2(img, t):  # app deductions
    text_c(img, "Order: ₹500", 320, 90, scale=pop(t, 0.0))
    left = 500.0
    for i, (n, v) in enumerate(DEDUCT):
        st = 0.6 + i * 0.9
        if t > st:
            a = ease((t - st) / 0.3)
            text_c(img, f"− ₹{v}   {n}", 500 + i * 120, 60, RED, alpha=a)
            left -= v * ease((t - st) / 0.5)
    text_c(img, "Hits your bank:", 1120, 64, GREY, w="Bold")
    text_c(img, f"₹{left:.0f}", 1290, 190, GRN if left > 300 else YEL)

COSTS2 = [("Food cost (30%)", 150), ("Packaging", 20)]
def scene3(img, t):  # own costs
    text_c(img, "Now your own costs…", 320, 84, scale=pop(t, 0.0))
    left = 277.0
    for i, (n, v) in enumerate(COSTS2):
        st = 0.6 + i * 0.9
        if t > st:
            a = ease((t - st) / 0.3)
            text_c(img, f"− ₹{v}   {n}", 520 + i * 120, 62, RED, alpha=a)
            left -= v * ease((t - st) / 0.5)
    text_c(img, f"₹{left:.0f}", 1050, 230, RED if left < 120 else YEL)
    text_c(img, "left… and you still owe", 1260, 64, WHITE, w="Bold", scale=pop(t, 2.6))
    text_c(img, "rent, staff, gas\nand electricity", 1450, 70, YEL, scale=pop(t, 3.0))

def scene4(img, t):  # reveal
    text_c(img, "A ₹500 order", 600, 90, scale=pop(t, 0.0))
    text_c(img, "= ₹107", 790, 200, RED, scale=pop(t, 0.4))
    text_c(img, "More orders ≠ more profit", 1100, 66, WHITE, w="Bold", scale=pop(t, 1.4))
    text_c(img, "Problem: you don't know\nwhich orders lose money", 1420, 62, YEL, scale=pop(t, 2.6), box=(0, 0, 0))

def phone(img, t):
    d = ImageDraw.Draw(img)
    px0, py0, px1, py1 = 210, 470, W - 210, 1430
    d.rounded_rectangle([px0, py0, px1, py1], 60, fill=(250, 250, 252), outline=(60, 60, 70), width=14)
    d.rounded_rectangle([px0 + 40, py0 + 50, px1 - 40, py0 + 150], 24, fill=ORANGE)
    f = font(46, "Black"); fm = font(34, "SemiBold"); fs = font(30, "Medium")
    d.text((px0 + 70, py0 + 72), "Smart Serve", font=f, fill=WHITE)
    d.text((px0 + 50, py0 + 185), "Real profit per order · today", font=fs, fill=(120, 120, 130))
    rows = [("Dine-in", "₹212", GRN), ("Takeaway", "₹188", GRN), ("Swiggy", "₹96", YEL), ("Zomato (offer)", "₹41", RED)]
    for i, (n, m, c) in enumerate(rows):
        st = 0.3 + i * 0.35
        if t < st: continue
        a = ease((t - st) / 0.3)
        y = py0 + 250 + i * 160 + int(30 * (1 - a))
        d.rounded_rectangle([px0 + 40, y, px1 - 40, y + 130], 24, fill=(240, 240, 245))
        d.text((px0 + 70, y + 40), n, font=fm, fill=(30, 30, 35))
        bw = d.textlength(m, font=f)
        d.text((px1 - 70 - bw, y + 36), m, font=f, fill=c)

def scene5(img, t):  # CTA
    text_c(img, "See the REAL profit", 250, 70, scale=pop(t, 0.0))
    text_c(img, "on every order.", 350, 76, YEL, scale=pop(t, 0.2))
    phone(img, t)
    if t > 2.4:
        s = pop(t, 2.4)
        text_c(img, "Comment  PROFIT", 1560, 96, BG, scale=s, box=YEL)
        text_c(img, "Smart Serve free download link ↓", 1690, 48, WHITE, w="Bold", scale=s)

SCENES = [(scene1, 3.0), (scene2, 5.5), (scene3, 5.0), (scene4, 4.5), (scene5, 6.5)]
TOTAL = sum(d for _, d in SCENES)

ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
    "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
    "-f", "lavfi", "-t", str(TOTAL), "-i", "anullsrc=r=44100:cl=stereo",
    "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
    "-c:a", "aac", "-shortest", "-movflags", "+faststart", OUT], stdin=subprocess.PIPE)
start = 0.0
for fn, dur in SCENES:
    for i in range(int(dur * FPS)):
        t = i / FPS
        img = Image.new("RGB", (W, H), BG)
        fn(img, t)
        progress_bar(img, start + t, TOTAL)
        ff.stdin.write(img.tobytes())
    start += dur
ff.stdin.close(); ff.wait()
print("done", TOTAL, "s")
