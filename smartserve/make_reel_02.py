# Smart Serve Reel #2 - "shock hook -> casual question -> app pitch" format (India)
import math, random, subprocess, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1080, 1920, 30
OUT = sys.argv[1]
F = "/usr/share/fonts/opentype/inter/"
def font(sz, w="Bold"): return ImageFont.truetype(F + f"Inter-{w}.otf", sz)
ORANGE = (255, 122, 0); WHITE = (255, 255, 255); BLACK = (0, 0, 0)
random.seed(7)

def clamp(x): return max(0.0, min(1.0, x))
def ease(x): x = clamp(x); return 1 - (1 - x) ** 3

def caption(img, txt, y, sz=78, col=WHITE):
    d = ImageDraw.Draw(img); f = font(sz, "ExtraBold")
    w = d.textlength(txt, font=f)
    d.text(((W - w) / 2, y), txt, font=f, fill=col, stroke_width=7, stroke_fill=BLACK)

def top_bar(img, lines, bar_h=420):
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, bar_h], fill=WHITE)
    f = font(50, "Medium"); lh = 64
    y0 = bar_h - 40 - lh * len(lines)
    for i, ln in enumerate(lines):
        w = d.textlength(ln, font=f)
        d.text(((W - w) / 2, y0 + i * lh), ln, font=f, fill=BLACK)

def app_icon(img, cx, cy, s, glow=False):
    if glow:
        g = Image.new("RGBA", img.size, (0, 0, 0, 0)); gd = ImageDraw.Draw(g)
        gd.ellipse([cx - s * 1.6, cy - s * 1.6, cx + s * 1.6, cy + s * 1.6], fill=(255, 200, 80, 150))
        img.paste(g.filter(ImageFilter.GaussianBlur(60)), (0, 0), g.filter(ImageFilter.GaussianBlur(60)))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([cx - s / 2, cy - s / 2, cx + s / 2, cy + s / 2], s * .23, fill=ORANGE)
    # cloche (serving dome) glyph
    r = s * .28
    d.chord([cx - r, cy - r * .9, cx + r, cy + r * 1.1], 180, 360, fill=WHITE)
    d.rectangle([cx - r * 1.25, cy + r * .1, cx + r * 1.25, cy + r * .25], fill=WHITE)
    d.ellipse([cx - s * .05, cy - r * 1.05, cx + s * .05, cy - r * .85], fill=WHITE)

def note(d, x, y, ang, col=(170, 140, 190)):
    # simple ₹500 note, rotated rectangle
    w, h = 300, 140; c, s_ = math.cos(ang), math.sin(ang)
    pts = [(x + px * c - py * s_, y + px * s_ + py * c) for px, py in ((-w/2,-h/2),(w/2,-h/2),(w/2,h/2),(-w/2,h/2))]
    d.polygon(pts, fill=col, outline=(90, 70, 110))
    d.text((x - 50, y - 30), "₹500", font=font(44, "Black"), fill=(70, 50, 90))

NOTES = [(random.uniform(200, 880), random.uniform(820, 1350), random.uniform(-.6, .6)) for _ in range(14)]
def galla(img, t, zoom):
    """dark cash-drawer close-up with notes, slow push-in"""
    base = Image.new("RGB", (W, H), (22, 18, 14)); d = ImageDraw.Draw(base)
    d.rectangle([90, 700, 990, 1480], fill=(60, 42, 28))           # drawer
    d.rectangle([120, 740, 960, 1450], fill=(38, 28, 20))
    for k in range(1, 4): d.line([120 + k * 210, 740, 120 + k * 210, 1450], fill=(60, 42, 28), width=10)
    for (x, y, a) in NOTES: note(d, x, y, a)
    lamp = Image.new("L", (W, H), 0); ImageDraw.Draw(lamp).ellipse([140, 500, 940, 1700], fill=255)
    lamp = lamp.filter(ImageFilter.GaussianBlur(160))
    base = Image.composite(base, Image.new("RGB", (W, H), (5, 4, 3)), lamp)
    z = 1 + zoom; cw, ch = W / z, H / z
    sx = random.uniform(-6, 6) * (t > 2.4); sy = random.uniform(-6, 6) * (t > 2.4)
    box = (int((W - cw) / 2 + sx), int((H - ch) / 2 + sy), int((W + cw) / 2 + sx), int((H + ch) / 2 + sy))
    img.paste(base.crop(box).resize((W, H)))

HOOK = [(0.0, "After closing"), (0.7, "the owner counted"), (1.4, "the galla"), (2.1, "₹8,400"), (2.5, "was missing")]
def scene_hook(img, t):
    galla(img, t, 0.12 * t / 3.4)
    cur = [w for (s, w) in HOOK if t >= s][-1]
    col = (255, 70, 70) if cur in ("₹8,400", "was missing") else WHITE
    caption(img, cur, 1180, 92 if cur != "₹8,400" else 130, col)
    if 2.1 <= t < 2.25:  # red flash
        ov = Image.new("RGB", (W, H), (200, 0, 0)); img.paste(Image.blend(img, ov, .35))

def flicker_bg(img, t, top):
    shades = [(225, 225, 225), (40, 34, 30), (245, 245, 245), (30, 30, 30), (160, 160, 160), (252, 248, 240)]
    c = shades[int(t * 6) % len(shades)]
    ImageDraw.Draw(img).rectangle([0, top, W, H], fill=c)

def scene_q(img, t):
    flicker_bg(img, t, 420)
    app_icon(img, W / 2, 1050, 120)
    top_bar(img, ["did you check today's galla bhai??"])

def rays(img, t):
    cx, cy = W / 2, 1060
    bg = Image.new("RGB", (W, H), (60, 32, 8)); d = ImageDraw.Draw(bg)
    for k in range(24):
        a = math.radians(k * 15 + t * 12)
        d.polygon([(cx, cy), (cx + math.cos(a - .07) * 1600, cy + math.sin(a - .07) * 1600),
                   (cx + math.cos(a + .07) * 1600, cy + math.sin(a + .07) * 1600)], fill=(150, 90, 25))
    bg = bg.filter(ImageFilter.GaussianBlur(18))
    glow = Image.new("L", (W, H), 0)
    pulse = 380 + 60 * math.sin(t * 5)
    ImageDraw.Draw(glow).ellipse([cx - pulse, cy - pulse, cx + pulse, cy + pulse], fill=255)
    bg = Image.composite(Image.new("RGB", (W, H), (255, 236, 180)), bg, glow.filter(ImageFilter.GaussianBlur(120)))
    img.paste(bg)

def scene_pitch(img, t):
    rays(img, t)
    d = ImageDraw.Draw(img)
    # dashboard card rising
    a = ease((t - 0.2) / 0.5); y = 1180 + int(80 * (1 - a))
    if t > 0.2:
        d.rounded_rectangle([200, y, W - 200, y + 300], 36, fill=WHITE)
        d.text((250, y + 40), "Today's sale", font=font(40, "Medium"), fill=(110, 110, 120))
        d.text((250, y + 95), "₹48,250", font=font(84, "Black"), fill=(20, 20, 25))
        d.text((250, y + 210), "✓ Cash matched · 0 missing bills", font=font(36, "SemiBold"), fill=(30, 160, 80))
    app_icon(img, W / 2, 900, 200, glow=True)
    top_bar(img, ["track every bill & every rupee", 'with "smart serve"', "(it's on the play store)"])
    if t > 0.6: caption(img, "type SAME if this happened to you", 1640, 52)

SCENES = [(scene_hook, 3.4), (scene_q, 2.6), (scene_pitch, 6.0)]
TOTAL = sum(d for _, d in SCENES)

# soundtrack: tense drone -> hit at the cut -> warm chord on the pitch
c1, c2 = SCENES[0][1], SCENES[0][1] + SCENES[1][1]
expr = (f"if(lt(t,{c1}), 0.25*sin(2*PI*55*t)*(0.6+0.4*sin(2*PI*4*t)) + 0.08*sin(2*PI*110*t),"
        f" if(lt(t,{c2}), 0.6*sin(2*PI*48*t)*exp(-4*(t-{c1})) + 0.12*sin(2*PI*220*t)*(0.5+0.5*sin(2*PI*6*t)),"
        f" 0.6*sin(2*PI*45*t)*exp(-4*(t-{c2})) + 0.12*(sin(2*PI*261.6*t)+sin(2*PI*329.6*t)+sin(2*PI*392*t))*min(1,(t-{c2})*2)))")
ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
    "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
    "-f", "lavfi", "-i", f"aevalsrc='{expr}':s=44100:d={TOTAL}",
    "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
    "-c:a", "aac", "-af", "afade=t=out:st=" + str(TOTAL - 0.6) + ":d=0.6", "-shortest", "-movflags", "+faststart", OUT],
    stdin=subprocess.PIPE)
for fn, dur in SCENES:
    for i in range(int(dur * FPS)):
        img = Image.new("RGB", (W, H)); fn(img, i / FPS); ff.stdin.write(img.tobytes())
ff.stdin.close(); ff.wait()
print("done", TOTAL, "s")
