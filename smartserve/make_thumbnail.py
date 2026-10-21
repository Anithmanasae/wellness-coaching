# One cover/thumbnail for every Smart Serve reel (1080x1920; key content sits inside the 3:4 grid crop).
import math, os, sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from make_photo_memes import emoji_img
W, H = 1080, 1920
F = "/usr/share/fonts/opentype/inter/"
def font(s, w="Black"): return ImageFont.truetype(F + f"Inter-{w}.otf", s)
BLUE, NAVY, YEL, WHITE = (24, 63, 191), (8, 18, 58), (255, 214, 0), (255, 255, 255)

img = Image.new("RGB", (W, H)); d = ImageDraw.Draw(img)
for y in range(H):
    k = y / H; d.line([0, y, W, y], fill=tuple(int(NAVY[i] + (BLUE[i] - NAVY[i]) * (1 - abs(k - 0.5) * 2) * 0.9) for i in range(3)))
cx, cy = W / 2, 1000
rays = Image.new("RGBA", (W, H), (0, 0, 0, 0)); rd = ImageDraw.Draw(rays)
for k in range(20):
    a = math.radians(k * 18)
    rd.polygon([(cx, cy), (cx + math.cos(a - .08) * 1500, cy + math.sin(a - .08) * 1500),
                (cx + math.cos(a + .08) * 1500, cy + math.sin(a + .08) * 1500)], fill=(90, 140, 255, 40))
img.paste(rays, (0, 0), rays); d = ImageDraw.Draw(img)

def centre(txt, y, f, col, stroke=0):
    w = d.textlength(txt, font=f); d.text(((W - w) / 2, y), txt, font=f, fill=col, stroke_width=stroke, stroke_fill=(0, 0, 0))

f = font(46, "Bold"); tag = "POV: you own a restaurant"; w = d.textlength(tag, font=f)
d.rounded_rectangle([(W - w) / 2 - 34, 330, (W + w) / 2 + 34, 410], 40, fill=WHITE); d.text(((W - w) / 2, 343), tag, font=f, fill=NAVY)
centre("RESTAURANT", 480, font(134), YEL, 8)
centre("OWNERS", 640, font(160), YEL, 8)
f = font(96); txt = "watch this"; e = emoji_img("👀", 100); w = d.textlength(txt, font=f) + e.width + 20
x = (W - w) / 2; d.text((x, 830), txt, font=f, fill=WHITE, stroke_width=6, stroke_fill=(0, 0, 0)); img.paste(e, (int(x + w - e.width), 838), e)
glow = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ImageDraw.Draw(glow).ellipse([cx - 230, 1010, cx + 230, 1470], fill=(140, 200, 255, 150))
glow = glow.filter(ImageFilter.GaussianBlur(60)); img.paste(glow, (0, 0), glow)
logo = Image.open(os.path.join(HERE, "assets", "logo.png")).convert("RGBA").resize((340, 340), Image.LANCZOS)
img.paste(logo, (int(cx - 170), 1070), logo); d = ImageDraw.Draw(img)
f = font(54); txt = 'Comment "APP"'; w = d.textlength(txt, font=f)
d.rounded_rectangle([(W - w) / 2 - 40, 1500, (W + w) / 2 + 40, 1600], 30, fill=(52, 199, 89)); d.text(((W - w) / 2, 1514), txt, font=f, fill=(5, 30, 15))
img.save(os.path.join(HERE, "assets", "thumbnail_all_reels.png"))
print("done")
