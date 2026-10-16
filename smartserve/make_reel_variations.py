# Smart Serve Reels #3-#7 - five variations of the Reel #2 format:
# specific shock hook -> bold black question bar (pattern interrupt) -> identical Smart Serve CTA.
# Usage: python3 make_reel_variations.py [variation_number ...]   (default: all)
import math, os, random, subprocess, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import soundtrack

W, H, FPS = 1080, 1920, 30
HERE = os.path.dirname(os.path.abspath(__file__))
F = "/usr/share/fonts/opentype/inter/"
def font(sz, w="Bold"): return ImageFont.truetype(F + f"Inter-{w}.otf", sz)
BLUE = (24, 63, 191); WHITE = (255, 255, 255); BLACK = (0, 0, 0); RED = (255, 60, 60)
LOGO = Image.open(os.path.join(HERE, "assets", "logo.png")).convert("RGBA")

def clamp(x): return max(0.0, min(1.0, x))
def ease(x): x = clamp(x); return 1 - (1 - x) ** 3
def pop(t, st, dur=0.25):
    x = clamp((t - st) / dur)
    return 0 if t < st else (1 + 0.25 * math.sin(x * math.pi) if x < 1 else 1)

# ---------- shared pieces (same look as Reel #2) ----------
def caption(img, txt, y, sz=86, col=WHITE, scale=1.0):
    if scale <= 0: return
    d = ImageDraw.Draw(img); f = font(int(sz * scale), "ExtraBold")
    lines = txt.split("\n"); lh = int(sz * scale * 1.15)
    for i, ln in enumerate(lines):
        w = d.textlength(ln, font=f)
        d.text(((W - w) / 2, y + i * lh - lh * (len(lines) - 1) / 2), ln, font=f, fill=col,
               stroke_width=8, stroke_fill=BLACK)

def top_bar(img, lines, bar_h=420):
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, bar_h], fill=WHITE)
    f = font(56, "ExtraBold"); lh = 70
    y0 = bar_h - 40 - lh * len(lines)
    for i, ln in enumerate(lines):
        w = d.textlength(ln, font=f)
        d.text(((W - w) / 2, y0 + i * lh), ln, font=f, fill=BLACK)

def app_icon(img, cx, cy, s, glow=False):
    if glow:
        g = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(g).ellipse([cx - s * 1.6, cy - s * 1.6, cx + s * 1.6, cy + s * 1.6], fill=(150, 210, 255, 170))
        g = g.filter(ImageFilter.GaussianBlur(60)); img.paste(g, (0, 0), g)
    l = LOGO.resize((int(s), int(s)), Image.LANCZOS)
    img.paste(l, (int(cx - s / 2), int(cy - s / 2)), l)

def wrap(lines_txt, f, d, maxw=980):
    out = []
    for word in lines_txt.split():
        if out and d.textlength(out[-1] + " " + word, font=f) <= maxw: out[-1] += " " + word
        else: out.append(word)
    return out

def scene_question(question):
    def fn(img, t):
        shades = [(225, 225, 225), (40, 34, 30), (245, 245, 245), (30, 30, 30), (160, 160, 160), (252, 248, 240)]
        ImageDraw.Draw(img).rectangle([0, 420, W, H], fill=shades[int(t * 6) % len(shades)])
        app_icon(img, W / 2, 1050, 170)
        d = ImageDraw.Draw(img)
        top_bar(img, wrap(question, font(56, "ExtraBold"), d))
    return fn

def rays(img, t):
    cx, cy = W / 2, 1060
    bg = Image.new("RGB", (W, H), (6, 16, 60)); d = ImageDraw.Draw(bg)
    for k in range(24):
        a = math.radians(k * 15 + t * 12)
        d.polygon([(cx, cy), (cx + math.cos(a - .07) * 1600, cy + math.sin(a - .07) * 1600),
                   (cx + math.cos(a + .07) * 1600, cy + math.sin(a + .07) * 1600)], fill=BLUE)
    bg = bg.filter(ImageFilter.GaussianBlur(18))
    glow = Image.new("L", (W, H), 0); pulse = 380 + 60 * math.sin(t * 5)
    ImageDraw.Draw(glow).ellipse([cx - pulse, cy - pulse, cx + pulse, cy + pulse], fill=255)
    img.paste(Image.composite(Image.new("RGB", (W, H), (205, 230, 255)), bg, glow.filter(ImageFilter.GaussianBlur(120))))

CTA_TOP = ["track every bill & every rupee", 'with "smart serve"', "(it's on the play store)"]

def scene_cta(img, t, bottom="type SAME if this happened to you", top=CTA_TOP):  # identical across every variation
    rays(img, t)
    d = ImageDraw.Draw(img)
    a = ease((t - 0.2) / 0.5); y = 1180 + int(80 * (1 - a))
    if t > 0.2:
        d.rounded_rectangle([200, y, W - 200, y + 300], 36, fill=WHITE)
        d.text((250, y + 40), "Today's sale", font=font(40, "Medium"), fill=(110, 110, 120))
        d.text((250, y + 95), "₹48,250", font=font(84, "Black"), fill=(20, 20, 25))
        d.text((250, y + 210), "✓ Cash matched · 0 missing bills", font=font(36, "SemiBold"), fill=(30, 160, 80))
    app_icon(img, W / 2, 880, 280, glow=True)
    top_bar(img, top)
    if t > 0.6: caption(img, bottom, 1640, 52)

def scene_cta_comment(img, t, keyword="APP"):
    """scannable CTA: what it does (top) -> proof (middle) -> one clear action (bottom)."""
    rays(img, t)
    d = ImageDraw.Draw(img)
    # 1) what it does
    d.rectangle([0, 0, W, 400], fill=WHITE)
    def centre(txt, y, f, col):
        w = d.textlength(txt, font=f); d.text(((W - w) / 2, y), txt, font=f, fill=col)
    centre("Track every bill", 95, font(76, "Black"), BLACK)
    centre("& every rupee", 180, font(76, "Black"), BLACK)
    f = font(46, "Bold"); pill = "Smart Serve  ·  free on Play Store"; w = d.textlength(pill, font=f)
    d.rounded_rectangle([(W - w) / 2 - 30, 290, (W + w) / 2 + 30, 360], 35, fill=BLUE)
    d.text(((W - w) / 2, 298), pill, font=f, fill=WHITE)
    # 2) proof
    app_icon(img, W / 2, 700, 230, glow=True)
    a = ease((t - 0.2) / 0.5); y = 920 + int(60 * (1 - a))
    if t > 0.2:
        d.rounded_rectangle([210, y, W - 210, y + 270], 36, fill=WHITE)
        d.text((260, y + 35), "Today's sale", font=font(40, "Medium"), fill=(110, 110, 120))
        d.text((260, y + 85), "₹48,250", font=font(84, "Black"), fill=(20, 20, 25))
        d.text((260, y + 195), "✓ Cash matched · 0 missing bills", font=font(34, "SemiBold"), fill=(30, 160, 80))
    # 3) one clear action
    if t > 0.6:
        s = pop(t, 0.6, 0.3)
        f = font(int(96 * s) or 1, "Black"); txt = f'Comment "{keyword}"'; w = d.textlength(txt, font=f)
        d.rounded_rectangle([(W - w) / 2 - 40, 1300, (W + w) / 2 + 40, 1300 + int(140 * s)], 30, fill=(255, 214, 0))
        d.text(((W - w) / 2, 1312), txt, font=f, fill=BLACK)
        caption(img, "I'll DM you the app link", 1500, 54)
        caption(img, "or tap the link in my bio", 1575, 44, (215, 230, 255))

def hook_captions(img, t, beats, red_from):
    """beats: [(start, text)], shows the latest; beats at index >= red_from go red and pop."""
    idx = max(i for i, (s, _) in enumerate(beats) if t >= s)
    s, txt = beats[idx]
    hot = idx >= red_from
    caption(img, txt, 1250, 104 if hot else 88, RED if hot else WHITE, scale=pop(t, s) if hot else 1)
    return hot and t - s < 0.15

def shake(img, amt):
    if amt <= 0: return
    dx, dy = random.randint(-amt, amt), random.randint(-amt, amt)
    img.paste(img.copy().transform(img.size, Image.AFFINE, (1, 0, dx, 0, 1, dy), fillcolor=BLACK))

def flash(img, col=(200, 0, 0), k=.35):
    img.paste(Image.blend(img, Image.new("RGB", img.size, col), k))

def vignette(img, strength=255):
    m = Image.new("L", (W, H), 0); ImageDraw.Draw(m).ellipse([60, 300, W - 60, H - 200], fill=strength)
    img.paste(Image.composite(img, Image.new("RGB", (W, H), (4, 4, 6)), m.filter(ImageFilter.GaussianBlur(170))))

# ---------- hook scenes (one specific story each) ----------
def receipt(d, x, y, w=260, h=420, amt="₹700"):
    d.rectangle([x, y, x + w, y + h], fill=(246, 244, 236))
    for k in range(7): d.line([x + 24, y + 70 + k * 40, x + w - 24 - (k % 3) * 40, y + 70 + k * 40], fill=(170, 170, 170), width=8)
    d.text((x + 24, y + h - 80), "TOTAL " + amt, font=font(38, "Black"), fill=(40, 40, 40))

def stamp(img, x, y, s, txt="VOID", rot=-18):
    if s <= 0: return
    f = font(int(96 * s), "Black")
    lay = Image.new("RGBA", (int(420 * s) + 40, int(170 * s) + 40), (0, 0, 0, 0)); ld = ImageDraw.Draw(lay)
    ld.rectangle([10, 10, lay.width - 10, lay.height - 10], outline=(220, 30, 30, 235), width=max(2, int(12 * s)))
    tw = ld.textlength(txt, font=f); ld.text(((lay.width - tw) / 2, lay.height / 2 - 60 * s), txt, font=f, fill=(220, 30, 30, 235))
    lay = lay.rotate(rot, expand=True, resample=Image.BICUBIC)
    img.paste(lay, (int(x - lay.width / 2), int(y - lay.height / 2)), lay)

def hook_void(img, t):
    d = ImageDraw.Draw(img); d.rectangle([0, 0, W, H], fill=(48, 36, 28))
    d.rectangle([0, 1500, W, H], fill=(30, 22, 16))
    spots = [(80, 420, 6), (400, 380, -4), (720, 430, 5), (130, 880, -6), (450, 860, 3), (760, 900, -3)]
    for i, (x, y, r) in enumerate(spots):
        st = i * 0.12; a = ease((t - st) / 0.3)
        if t < st: continue
        lay = Image.new("RGBA", (300, 460), (0, 0, 0, 0)); receipt(ImageDraw.Draw(lay), 20, 20)
        lay = lay.rotate(r, expand=True, resample=Image.BICUBIC)
        img.paste(lay, (x, int(y - 260 * (1 - a))), lay)
        if t > 1.5 + i * 0.12: stamp(img, x + 150, y + 220, pop(t, 1.5 + i * 0.12, 0.18))
    vignette(img)
    beats = [(0, "The cashier"), (0.55, "cancelled 6 bills"), (1.5, "AFTER customers paid"), (2.4, "and kept ₹4,200")]
    if hook_captions(img, t, beats, 3): flash(img)
    shake(img, 8 if 1.5 <= t < 1.9 else 0)

def hook_fridge(img, t):
    d = ImageDraw.Draw(img); d.rectangle([0, 0, W, H], fill=(190, 198, 205))
    d.rectangle([60, 200, W - 60, 1700], fill=(225, 232, 238), outline=(150, 158, 165), width=12)
    for k in range(3): d.rectangle([60, 600 + k * 380, W - 60, 616 + k * 380], fill=(160, 168, 175))
    boxes = [(110, 420), (420, 440), (720, 410), (130, 800), (450, 790), (740, 820), (150, 1180), (470, 1170)]
    for i, (x, y) in enumerate(boxes):
        d.rounded_rectangle([x, y, x + 230, y + 170], 18, fill=(250, 250, 248), outline=(200, 200, 200), width=4)
        d.rectangle([x + 40, y + 60, x + 190, y + 110], fill=(255, 245, 200))
        if t > 1.4 + i * 0.08:  # mould spreads
            g = ease((t - 1.4 - i * 0.08) / 1.2)
            rnd = random.Random(i)
            for _ in range(int(14 * g)):
                mx, my = x + rnd.randint(20, 210), y + rnd.randint(20, 150); r = rnd.randint(8, 22)
                d.ellipse([mx - r, my - r, mx + r, my + r], fill=(110, 140, 70))
            d.rectangle([x + 20, y - 34, x + 210, y + 6], fill=(220, 30, 30))
            d.text((x + 34, y - 32), "EXPIRED", font=font(32, "Black"), fill=WHITE)
    # flickering fridge light
    if int(t * 7) % 5 == 0: flash(img, (0, 0, 0), .25)
    beats = [(0, "₹12,000 of paneer"), (0.8, "sat in the fridge"), (1.6, "for 9 days"), (2.5, "nobody noticed")]
    if hook_captions(img, t, beats, 2): flash(img)

def ticket(d_img, x, y, rot, num, lost=False):
    lay = Image.new("RGBA", (240, 380), (0, 0, 0, 0)); ld = ImageDraw.Draw(lay)
    ld.rectangle([10, 10, 230, 370], fill=(255, 250, 225) if not lost else (255, 225, 225))
    ld.text((30, 30), f"KOT #{num}", font=font(40, "Black"), fill=(30, 30, 30))
    for k in range(5): ld.line([30, 110 + k * 45, 200 - (k % 2) * 50, 110 + k * 45], fill=(150, 150, 150), width=8)
    lay = lay.rotate(rot, expand=True, resample=Image.BICUBIC)
    d_img.paste(lay, (int(x - lay.width / 2), int(y)), lay)

def hook_kot(img, t):
    d = ImageDraw.Draw(img); d.rectangle([0, 0, W, H], fill=(28, 24, 22))
    glow = Image.new("RGB", (W, H), (255, 90, 20)); m = Image.new("L", (W, H), 0)
    ImageDraw.Draw(m).ellipse([100, 100, W - 100, 1100], fill=90); img.paste(Image.composite(glow, img, m.filter(ImageFilter.GaussianBlur(150))))
    d = ImageDraw.Draw(img); d.rectangle([40, 300, W - 40, 330], fill=(170, 175, 180))
    for i in range(4):
        x = 170 + i * 250; sway = 5 * math.sin(t * 6 + i)
        falling = i in (1, 3) and t > 1.6 + (i == 3) * 0.3
        if falling:
            ft = t - (1.6 + (i == 3) * 0.3)
            ticket(img, x + 60 * ft, 320 + 900 * ft * ft, sway + 140 * ft, 40 + i, lost=True)
        else:
            ticket(img, x, 320, sway, 40 + i)
    beats = [(0, "Saturday, 9 PM"), (0.6, "42 tables full"), (1.4, "the kitchen LOST"), (2.2, "3 orders"), (2.8, "table 7 walked out")]
    if hook_captions(img, t, beats, 3): flash(img)
    shake(img, 6 if t > 1.6 else 0)

def plate(d, cx, cy, r, col):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(245, 245, 245), outline=(200, 200, 200), width=6)
    d.ellipse([cx - r * .6, cy - r * .6, cx + r * .6, cy + r * .6], fill=col)

def hook_freefood(img, t):
    d = ImageDraw.Draw(img); d.rectangle([0, 0, W, H], fill=(110, 70, 40))
    for k in range(0, H, 90): d.line([0, k, W, k + 30], fill=(100, 62, 34), width=6)
    plates = [(270, 520, (220, 120, 40)), (700, 480, (240, 200, 90)), (300, 900, (190, 60, 40)),
              (760, 880, (120, 160, 70)), (520, 690, (230, 170, 60)), (520, 1110, (200, 90, 50))]
    for i, (x, y, c) in enumerate(plates):
        st = i * 0.18
        if t >= st: plate(d, x, y + int(200 * (1 - ease((t - st) / 0.3))), 150, c)
    if t > 1.7:  # the bill slides in
        a = ease((t - 1.7) / 0.35); x = int(W + 40 - 640 * a)
        d.rounded_rectangle([x, 1370, x + 560, 1720], 20, fill=(250, 248, 240))
        d.text((x + 40, 1400), "TABLE 4  ·  6 items", font=font(38, "Bold"), fill=(60, 60, 60))
        d.text((x + 40, 1480), "TOTAL  ₹0.00", font=font(72, "Black"), fill=(220, 30, 30))
        d.text((x + 40, 1600), "\"he's my friend\"", font=font(40, "SemiBold"), fill=(110, 110, 110))
    vignette(img, 255)
    beats = [(0, "Every Sunday"), (0.7, "the waiter's friends"), (1.5, "ate for FREE"), (2.4, "for 8 months")]
    if hook_captions(img, t, beats, 2): flash(img)

def hook_shutter(img, t):
    d = ImageDraw.Draw(img); d.rectangle([0, 0, W, H], fill=(18, 20, 30))
    d.rectangle([90, 380, W - 90, 1600], fill=(60, 50, 45))
    d.rectangle([150, 640, W - 150, 1540], fill=(255, 200, 120))  # warm window
    for k in range(5):  # busy silhouettes
        x = 220 + k * 150 + 20 * math.sin(t * 3 + k)
        d.ellipse([x, 1180, x + 80, 1260], fill=(40, 30, 25)); d.rectangle([x - 10, 1260, x + 90, 1540], fill=(40, 30, 25))
    d.rectangle([90, 420, W - 90, 590], fill=(30, 28, 26))
    neon = (255, 70, 120) if int(t * 8) % 2 or t < 1.8 else (80, 30, 40)
    d.text((W / 2 - 150, 450), "OPEN", font=font(110, "Black"), fill=neon if t < 2.6 else (80, 30, 40))
    if t > 2.0:  # shutter rolls down
        h = ease((t - 2.0) / 0.9) * 1060
        d.rectangle([90, 600, W - 90, 600 + h], fill=(120, 125, 130))
        for k in range(0, int(h), 40): d.line([90, 600 + k, W - 90, 600 + k], fill=(90, 95, 100), width=8)
        if t > 2.9:
            d.rounded_rectangle([290, 1000, W - 290, 1160], 20, fill=(220, 30, 30))
            d.text((330, 1025), "CLOSED", font=font(100, "Black"), fill=WHITE)
    beats = [(0, "Packed every night"), (0.7, "300 orders a day"), (1.5, "still SHUT DOWN"), (2.4, "in 11 months")]
    hot = hook_captions(img, t, beats, 2)
    if hot: flash(img)

VARIATIONS = {
    3: ("void_bills", hook_void, "restaurant owners, when did you last check your cancelled bills??"),
    4: ("fridge", hook_fridge, "restaurant owners, do you know what's expiring in your fridge right now??"),
    5: ("lost_kot", hook_kot, "restaurant owners, how many orders did your kitchen lose this weekend??"),
    6: ("free_food", hook_freefood, "restaurant owners, who ate for free at your place today??"),
    7: ("busy_but_broke", hook_shutter, "restaurant owners, do you know your REAL profit today??"),
}

SFX_CUES = {
    3: [(i * 0.12, "paper") for i in range(6)] + [(1.5 + i * 0.12, "stamp") for i in range(6)]
       + [(0.55, "pop"), (1.5, "impact"), (2.4, "impact")],
    4: [(k / 7, "buzz") for k in range(0, 25, 5)] + [(0.8, "pop"), (1.6, "impact"), (2.5, "impact")],
    5: [(0.6, "pop"), (1.4, "pop"), (1.6, "whoosh"), (1.9, "whoosh"), (2.2, "impact"), (2.8, "impact")],
    6: [(i * 0.18, "clink") for i in range(6)] + [(0.7, "pop"), (1.5, "impact"), (1.7, "whoosh"), (2.4, "impact")],
    7: [(0.7, "pop"), (1.5, "impact"), (2.0, "shutter"), (2.9, "impact")],
}

def render(num):
    name, hook, question = VARIATIONS[num]
    out = os.path.join(HERE, f"smartserve_reel_{num:02d}_{name}.mp4")
    scenes = [(hook, 3.6), (scene_question(question), 2.6), (scene_cta, 6.0)]
    total = sum(d for _, d in scenes); c1, c2 = scenes[0][1], scenes[0][1] + scenes[1][1]
    wav = out[:-4] + ".wav"
    soundtrack.build(wav, total, c1, c2, SFX_CUES[num])
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", wav,
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
        "-shortest", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    random.seed(num)
    for fn, dur in scenes:
        for i in range(int(dur * FPS)):
            img = Image.new("RGB", (W, H)); fn(img, i / FPS); ff.stdin.write(img.tobytes())
    ff.stdin.close(); ff.wait(); os.remove(wav)
    print("done", out)

if __name__ == "__main__":
    for n in ([int(a) for a in sys.argv[1:]] or sorted(VARIATIONS)): render(n)
