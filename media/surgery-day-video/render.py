"""Render the surgery-day patient video: illustrated animated scenes, on-screen text,
narration, subtitles and a soft music bed.

Usage: python3 render.py <narration_dir> <out_dir> [--preview]
"""
import json
import math
import os
import subprocess
import sys
import textwrap
from multiprocessing import Pool

import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from script import SCENES, SUBTITLE, TITLE, WARD

W, H, S, FPS = 1920, 1080, 2, 30
FONTS = "/usr/share/fonts/opentype/inter/"

TEAL = (42, 157, 143)
TEAL_L = (200, 232, 228)
NAVY = (31, 61, 77)
CORAL = (231, 111, 81)
SAND = (244, 182, 120)
SCRUB = (64, 168, 176)
SCRUB_D = (46, 128, 138)
THEATRE = (92, 150, 120)
GOWN = (160, 200, 222)
WHITE = (255, 255, 255)
HAIR = (38, 28, 24)
SKINS = [(198, 134, 86), (160, 102, 62), (224, 172, 120), (128, 80, 48)]
INK = (52, 44, 44)


def font(name, size):
    return ImageFont.truetype(FONTS + name, size)


def ease(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


# ---------------------------------------------------------------- drawing ---

class Canvas:
    """2x supersampled drawing surface addressed in 1x coordinates."""

    def __init__(self, im):
        self.im = im
        self.d = ImageDraw.Draw(im)

    def _b(self, b):
        x0, y0, x1, y1 = b
        return [min(x0, x1) * S, min(y0, y1) * S, max(x0, x1) * S, max(y0, y1) * S]

    def rect(self, b, fill, r=0, outline=None, w=0):
        self.d.rounded_rectangle(self._b(b), radius=r * S, fill=fill, outline=outline, width=int(w * S))

    def ell(self, b, fill, outline=None, w=0):
        self.d.ellipse(self._b(b), fill=fill, outline=outline, width=int(w * S))

    def circ(self, x, y, r, fill, **k):
        self.ell((x - r, y - r, x + r, y + r), fill, **k)

    def line(self, pts, fill, w, cap=True):
        self.d.line([(x * S, y * S) for x, y in pts], fill=fill, width=max(1, int(w * S)), joint="curve")
        if cap:
            for x, y in (pts[0], pts[-1]):
                self.circ(x, y, w / 2, fill)

    def poly(self, pts, fill):
        self.d.polygon([(x * S, y * S) for x, y in pts], fill=fill)

    def arc(self, b, a0, a1, fill, w):
        self.d.arc(self._b(b), a0, a1, fill=fill, width=max(1, int(w * S)))

    def pie(self, b, a0, a1, fill):
        self.d.pieslice(self._b(b), a0, a1, fill=fill)

    def text(self, xy, s, size, fill, name="Inter-Bold.otf", anchor="mm"):
        self.d.text((xy[0] * S, xy[1] * S), s, font=font(name, int(size * S)), fill=fill, anchor=anchor)


def gradient(top, bottom, h0=0, h1=H):
    """Full-canvas (2x) vertical gradient image between rows h0..h1."""
    ys = np.clip((np.arange(H * S) / S - h0) / max(1, h1 - h0), 0, 1)[:, None]
    top, bottom = np.array(top, float), np.array(bottom, float)
    col = top[None, :] * (1 - ys) + bottom[None, :] * ys
    arr = np.repeat(col[:, None, :], W * S, axis=1)
    return Image.fromarray(arr.astype(np.uint8), "RGB")


def shade(c, k):
    return tuple(int(max(0, min(255, v * k))) for v in c)


def limb(c, start, a1, l1, a2, l2, side, sleeve, skin, w1, w2):
    """Two-segment limb; angles in degrees from straight down, outward positive."""
    x0, y0 = start
    x1 = x0 + side * math.sin(math.radians(a1)) * l1
    y1 = y0 + math.cos(math.radians(a1)) * l1
    x2 = x1 + side * math.sin(math.radians(a2)) * l2
    y2 = y1 + math.cos(math.radians(a2)) * l2
    c.line([(x0, y0), (x1, y1)], sleeve, w1)
    c.line([(x1, y1), (x2, y2)], skin, w2)
    c.circ(x2, y2, w2 * 0.62, skin)
    return (x2, y2)


def head(c, x, y, r, skin, hair, style="short", cap=None, eyes=1.0, mouth=0.0, mask=False, facing=0):
    u = r / 11
    if style == "long":
        c.rect((x - 13 * u, y - 6 * u, x + 13 * u, y + 15 * u), hair, r=6 * u)
    c.circ(x, y, r, skin)
    # ears
    c.circ(x - r, y + 1 * u, 2.3 * u, shade(skin, 0.92))
    c.circ(x + r, y + 1 * u, 2.3 * u, shade(skin, 0.92))
    if cap:
        c.pie((x - 12.5 * u, y - 13 * u, x + 12.5 * u, y + 8 * u), 180, 360, cap)
        c.rect((x - 12.5 * u, y - 4 * u, x + 12.5 * u, y - 1.5 * u), shade(cap, 0.85), r=1 * u)
    else:
        c.pie((x - 12 * u, y - 12.5 * u, x + 12 * u, y + 6 * u), 180, 360, hair)
        c.pie((x - 12 * u, y - 12.5 * u, x + 4 * u, y + 2 * u), 180, 300, hair)
        if style == "bun":
            c.circ(x, y - 12 * u, 5 * u, hair)
    ex = 4 * u
    fx = facing * 2 * u
    for sx in (-1, 1):
        if eyes > 0.5:
            c.ell((x + fx + sx * ex - 1.4 * u, y - (1.6 * eyes) * u, x + fx + sx * ex + 1.4 * u, y + (1.6 * eyes) * u), INK)
        else:
            c.arc((x + fx + sx * ex - 1.8 * u, y - 1.5 * u, x + fx + sx * ex + 1.8 * u, y + 1.2 * u), 20, 160, INK, 0.8 * u)
    c.ell((x + fx - 7.5 * u, y + 2.5 * u, x + fx - 4 * u, y + 4.5 * u), shade(skin, 1.08))
    c.ell((x + fx + 4 * u, y + 2.5 * u, x + fx + 7.5 * u, y + 4.5 * u), shade(skin, 1.08))
    if mouth > 0.15:
        c.ell((x + fx - 2.3 * u, y + 4 * u, x + fx + 2.3 * u, y + (4.5 + 3.2 * mouth) * u), (120, 50, 50))
    else:
        c.arc((x + fx - 3.6 * u, y + 1.6 * u, x + fx + 3.6 * u, y + 6.6 * u), 20, 160, INK, 0.9 * u)
    if mask:
        c.rect((x - 8 * u, y + 8 * u, x + 8 * u, y + 13 * u), (170, 210, 235), r=2 * u)


def person(c, x, y, h, skin, top, bottom=None, hair=HAIR, style="short", cap=None,
           arms=(("down", 0), ("down", 0)), eyes=1.0, mouth=0.0, steth=False, mask=False,
           walk=None, coat=False, badge=True, pattern=False, facing=0):
    """Standing figure with feet at (x, y). Returns hand positions."""
    u = h / 100
    bottom = bottom or top
    hip = y - 44 * u
    for i, sx in enumerate((-1, 1)):
        ang = 0 if walk is None else math.sin(walk + i * math.pi) * 16
        fx = x + sx * 5 * u + math.sin(math.radians(ang)) * 42 * u
        fy = hip + math.cos(math.radians(ang)) * 42 * u
        c.line([(x + sx * 5 * u, hip), (fx, fy)], bottom, 10 * u)
        c.ell((fx - 6 * u, fy - 2.5 * u, fx + 7 * u, fy + 2.5 * u), (58, 58, 70))
    torso_top = y - 77 * u
    c.rect((x - 16 * u, torso_top, x + 16 * u, hip + 6 * u), top, r=9 * u)
    if pattern:
        for py in range(int(torso_top + 8 * u), int(hip), int(8 * u)):
            for px in range(int(x - 12 * u), int(x + 12 * u), int(8 * u)):
                c.circ(px + 3 * u, py, 1.3 * u, shade(top, 0.85))
    if coat:
        c.rect((x - 17 * u, torso_top, x + 17 * u, hip + 14 * u), (246, 248, 250), r=9 * u)
        c.rect((x - 6 * u, torso_top, x + 6 * u, hip + 4 * u), SCRUB, r=3 * u)
        c.line([(x - 6 * u, torso_top), (x - 3 * u, hip + 14 * u)], (215, 220, 226), 1.2 * u)
    c.rect((x - 4 * u, y - 85 * u, x + 4 * u, torso_top + 3 * u), shade(skin, 0.9))
    c.poly([(x - 6 * u, torso_top), (x + 6 * u, torso_top), (x, torso_top + 9 * u)], shade(skin, 0.9))
    if badge and not pattern:
        c.rect((x + 6 * u, torso_top + 12 * u, x + 13 * u, torso_top + 17 * u), WHITE, r=1 * u)
    if steth:
        c.arc((x - 9 * u, torso_top - 4 * u, x + 9 * u, torso_top + 22 * u), 0, 180, (70, 80, 90), 1.4 * u)
        c.circ(x + 5 * u, torso_top + 24 * u, 2.6 * u, (150, 160, 170))
    hands = []
    for side, (pose, k) in zip((-1, 1), arms):
        sh = (x + side * 13 * u, torso_top + 6 * u)
        if pose == "down":
            a1, a2 = 10, 4
        elif pose == "wave":
            a1, a2 = 130, 165 + 18 * math.sin(k)
        elif pose == "reach":
            a1, a2 = 40 + k, 75 + k
        elif pose == "push":
            a1, a2 = 35, 80
        elif pose == "sip":
            a1, a2 = 20, 160 - 30 * k
        else:
            a1, a2 = pose
        hands.append(limb(c, sh, a1, 20 * u, a2, 19 * u, side,
                          (246, 248, 250) if coat else top, skin, 9 * u, 7 * u))
    head(c, x, y - 96 * u, 12 * u, skin, hair, style, cap, eyes, mouth, mask, facing)
    return hands


def bed(c, x, y, w, frame=(180, 190, 198), mattress=(250, 250, 252), legs=170, rails=True, wheels=True):
    """Hospital bed side view; (x, y) = mattress top-left."""
    c.rect((x - 18, y - 120, x + 4, y + 40), shade(frame, 0.92), r=8)  # headboard
    c.rect((x + w - 4, y - 50, x + w + 16, y + 40), shade(frame, 0.92), r=8)
    c.rect((x, y + 28, x + w, y + 48), frame, r=6)
    for lx in (x + 30, x + w - 40):
        c.rect((lx, y + 48, lx + 14, y + legs), shade(frame, 0.8))
        if wheels:
            c.circ(lx + 7, y + legs + 4, 13, (70, 75, 84))
            c.circ(lx + 7, y + legs + 4, 5, (150, 155, 160))
    c.rect((x, y, x + w, y + 34), mattress, r=12)
    if rails:
        c.rect((x + w * 0.45, y - 24, x + w * 0.8, y - 14), shade(frame, 0.85), r=5)
        for rx in (x + w * 0.47, x + w * 0.78):
            c.rect((rx, y - 24, rx + 6, y + 30), shade(frame, 0.85))


def lying(c, x, y, length, skin, hair=HAIR, eyes=1.0, blanket=(120, 180, 200), style="short",
          head_left=True, arm_out=False, cap=None):
    """Patient lying on a mattress whose top surface is at y."""
    hx = x + 62 if head_left else x + length - 62
    c.ell((hx - 80, y - 44, hx + 80, y + 10), (236, 240, 244))  # pillow
    head(c, hx, y - 56, 52, skin, hair, style, cap, eyes)
    bx0, bx1 = (x + 100, x + length) if head_left else (x, x + length - 100)
    c.rect((bx0, y - 80, bx1, y + 12), blanket, r=40)
    fx = bx1 - 60 if head_left else bx0 + 60
    c.ell((fx - 48, y - 116, fx + 48, y - 20), blanket)
    c.line([(bx0 + 14, y - 70), (bx1 - 14, y - 70)], shade(blanket, 1.12), 8)
    hand = None
    if arm_out:
        sx = bx0 + 30 if head_left else bx1 - 30
        d = 1 if head_left else -1
        c.line([(sx, y - 76), (sx + d * 120, y - 60)], GOWN, 30)
        c.line([(sx + d * 120, y - 60), (sx + d * 200, y - 48)], skin, 22)
        hand = (sx + d * 216, y - 46)
        c.circ(hand[0], hand[1], 15, skin)
    return hand


def monitor(c, x, y, w, h, t, pole=True, hr=72):
    if pole:
        c.rect((x + w / 2 - 6, y + h, x + w / 2 + 6, y + h + 330), (150, 158, 166))
        c.rect((x + w / 2 - 70, y + h + 322, x + w / 2 + 70, y + h + 338), (120, 126, 134), r=6)
    c.rect((x - 12, y - 12, x + w + 12, y + h + 12), (60, 66, 74), r=18)
    c.rect((x, y, x + w, y + h), (14, 22, 28), r=8)
    trace(c, x + 14, y + h * 0.18, w * 0.62, h * 0.26, t, ecg, (80, 230, 120), hr)
    trace(c, x + 14, y + h * 0.6, w * 0.62, h * 0.2, t, pleth, (90, 200, 240), hr)
    tx = x + w * 0.83
    c.text((tx, y + h * 0.2), "HR", h * 0.07, (80, 230, 120), "Inter-SemiBold.otf")
    c.text((tx, y + h * 0.36), str(hr + int(2 * math.sin(t * 0.7))), h * 0.17, (80, 230, 120))
    c.text((tx, y + h * 0.58), "SpO₂", h * 0.07, (90, 200, 240), "Inter-SemiBold.otf")
    c.text((tx, y + h * 0.72), "98%", h * 0.14, (90, 200, 240))
    c.text((tx, y + h * 0.9), "120/78", h * 0.08, (240, 220, 120), "Inter-SemiBold.otf")
    if (t * hr / 60) % 1 < 0.15:
        c.circ(x + w * 0.93, y + h * 0.12, h * 0.025, (240, 80, 80))


def ecg(p):
    g = lambda m, s, a: a * math.exp(-((p - m) / s) ** 2)
    return g(0.12, 0.03, 0.12) - g(0.28, 0.008, 0.12) + g(0.3, 0.01, 1.0) - g(0.32, 0.01, 0.28) + g(0.55, 0.05, 0.25)


def pleth(p):
    return 0.85 * math.exp(-((p - 0.35) / 0.12) ** 2) + 0.3 * math.exp(-((p - 0.62) / 0.08) ** 2)


def trace(c, x, y, w, h, t, fn, col, hr):
    beat = 60 / hr
    span = 3.0  # seconds across the screen
    cursor = (t % span) / span * w
    pts = []
    for i in range(0, int(w), 3):
        tt = t - ((cursor - i) % w) / w * span
        pts.append((x + i, y + h * 0.75 - fn((tt / beat) % 1) * h * 0.8))
    gap = int(cursor // 3)
    if gap > 2:
        c.line(pts[: gap - 1], col, 3, cap=False)
    if gap + 6 < len(pts) - 1:
        c.line(pts[gap + 6:], shade(col, 0.55), 3, cap=False)


def window(c, x, y, w, h, t=0):
    c.rect((x - 14, y - 14, x + w + 14, y + h + 14), (250, 250, 250), r=10)
    sky = gradient((150, 205, 235), (215, 236, 246), y, y + h).crop((x * S, y * S, (x + w) * S, (y + h) * S))
    mask = Image.new("L", sky.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, sky.size[0] - 1, sky.size[1] - 1], radius=6 * S, fill=255)
    c.im.paste(sky, (x * S, y * S), mask)
    c.circ(x + w * 0.75, y + h * 0.3, h * 0.12, (255, 236, 170))
    for cx, cy, k in ((0.25, 0.35, 1), (0.55, 0.62, 0.8)):
        px, py = x + w * cx, y + h * cy
        for dx, dy, r in ((-30, 4, 26), (0, -10, 34), (34, 4, 26)):
            c.circ(px + dx * k, py + dy * k, r * k, (250, 252, 255))
    c.rect((x - 14, y - 14, x + w + 14, y + h + 14), None, r=10, outline=(235, 238, 240), w=10)
    c.rect((x + w / 2 - 5, y, x + w / 2 + 5, y + h), (250, 250, 250))
    c.rect((x - 24, y + h + 8, x + w + 24, y + h + 26), (240, 242, 244), r=4)


def curtain(c, x, y, w, h, col):
    c.rect((x - 20, y - 16, x + w + 20, y - 6), (170, 176, 184), r=4)
    n = max(3, int(w / 46))
    for i in range(n):
        px = x + i * w / n
        c.rect((px, y, px + w / n + 2, y + h), col if i % 2 else shade(col, 0.93))
    c.rect((x, y + h - 10, x + w, y + h), shade(col, 0.85))


def room(wall=(236, 243, 245), wall2=(222, 235, 239), floor=(208, 214, 218), stripe=TEAL_L, fy=840):
    im = gradient(wall, wall2, 0, fy)
    c = Canvas(im)
    c.rect((0, fy - 150, W, fy - 128), stripe)
    c.rect((0, fy, W, H), floor)
    for i in range(-20, 30):
        x = 960 + i * 150
        c.line([(x, fy), (960 + (x - 960) * 2.6, H)], shade(floor, 0.95), 2, cap=False)
    for yy in (fy + 40, fy + 110, fy + 200):
        c.line([(0, yy), (W, yy)], shade(floor, 0.95), 2, cap=False)
    c.rect((0, fy - 10, W, fy + 4), shade(floor, 0.85))
    return im, c


def logo(c, x, y, r, col=TEAL, bg=WHITE):
    c.circ(x, y, r, bg)
    c.circ(x, y, r * 0.86, col)
    k = r * 0.5
    c.circ(x - k * 0.42, y - k * 0.3, k * 0.5, bg)
    c.circ(x + k * 0.42, y - k * 0.3, k * 0.5, bg)
    c.poly([(x - k * 0.9, y - k * 0.12), (x + k * 0.9, y - k * 0.12), (x, y + k * 0.85)], bg)
    c.rect((x - k * 0.1, y - k * 0.55, x + k * 0.1, y + k * 0.2), col)
    c.rect((x - k * 0.33, y - k * 0.28, x + k * 0.33, y - k * 0.08), col)


# ---------------------------------------------------------------- scenes ---
# Each scene: static() -> 2x Image (cached), dynamic(canvas, t, dur), focus (x, y) for the slow zoom.

def welcome_static():
    im, c = room()
    window(c, 1300, 150, 340, 300)
    curtain(c, 1760, 90, 160, 740, (190, 222, 214))
    c.rect((1660, 600, 1760, 840), (226, 214, 196), r=6)  # bedside cabinet
    c.rect((1675, 640, 1745, 660), (200, 186, 166), r=4)
    bed(c, 1150, 640, 520)
    return im


def welcome_dynamic(c, t, d):
    blink = 0.0 if (t % 4.3) < 0.15 else 1.0
    # patient sitting up in bed
    px = 1230
    c.rect((1170, 400, 1320, 650), (236, 240, 244), r=40)  # raised pillow
    head(c, px, 420, 58, SKINS[2], HAIR, "long", eyes=blink)
    c.rect((px - 66, 480, px + 66, 650), GOWN, r=36)
    c.rect((px + 10, 580, 1640, 662), (122, 176, 196), r=34)
    c.ell((1540, 540, 1640, 640), (122, 176, 196))
    c.line([(px + 44, 510), (px + 110, 580)], GOWN, 30)
    c.line([(px + 110, 580), (px + 200, 580)], SKINS[2], 22)
    c.circ(px + 210, 580, 15, SKINS[2])
    # nurse greeting
    wave = ("wave", t * 5) if t < 4 else ("reach", 8 * math.sin(t))
    person(c, 980, 930, 600, SKINS[0], SCRUB, style="bun", arms=(("down", 0), wave), steth=True, facing=1,
           mouth=abs(math.sin(t * 9)) if 1.0 < t < 3.5 else 0)


def prep_static():
    im, c = room(wall=(240, 240, 236), wall2=(228, 232, 228), stripe=(226, 214, 196))
    curtain(c, 860, 90, 1060, 700, (206, 226, 236))
    bed(c, 1300, 650, 560, rails=False)
    # over-bed tray table
    c.rect((1540, 610, 1820, 628), (210, 196, 176), r=6)
    c.rect((1670, 628, 1684, 830), (150, 158, 166))
    c.rect((1620, 826, 1740, 840), (120, 126, 134), r=4)
    return im


def prep_dynamic(c, t, d):
    items_t = [d * 0.55 + i * 0.7 for i in range(4)]
    # items on tray: glasses, watch, ring, denture pot
    def pop(i):
        return ease((t - items_t[i]) / 0.35)
    k = pop(0)
    if k:
        for gx in (1572, 1612):
            c.circ(gx, 596, 15 * k, None, outline=NAVY, w=4)
        c.line([(1587, 596), (1597, 596)], NAVY, 4)
    k = pop(1)
    if k:
        c.rect((1650 - 6 * k, 572, 1650 + 6 * k, 608), (110, 90, 70), r=3)
        c.circ(1650, 590, 13 * k, (230, 200, 120))
        c.circ(1650, 590, 9 * k, WHITE)
    k = pop(2)
    if k:
        c.circ(1700, 598, 10 * k, None, outline=(225, 185, 60), w=4)
    k = pop(3)
    if k:
        c.rect((1740, 610 - 46 * k, 1790, 610), (230, 240, 250), r=8)
        c.rect((1740, 610 - 46 * k, 1790, 610 - 40 * k), (120, 170, 200), r=4)
    # patient in gown holding wrist out for ID check
    blink = 0.0 if (t % 3.7) < 0.15 else 1.0
    hands = person(c, 1440, 900, 560, SKINS[1], GOWN, bottom=GOWN, pattern=True, eyes=blink,
                   arms=(("reach", 4 * math.sin(t)), ("down", 0)), facing=-1)
    hx, hy = hands[0]
    c.rect((hx + 4, hy - 9, hx + 22, hy + 9), WHITE, r=3)
    c.rect((hx + 8, hy - 5, hx + 18, hy + 5), (245, 170, 60), r=2)
    # nurse scanning the ID band
    nh = person(c, 1080, 900, 580, SKINS[3], SCRUB, style="short", steth=True, facing=1,
                arms=(("down", 0), ("reach", -6)), mouth=abs(math.sin(t * 8)) if 1 < t < 4 else 0)
    sx, sy = nh[1]
    c.rect((sx - 6, sy - 26, sx + 22, sy + 14), (60, 66, 74), r=6)
    if (t % 1.6) < 0.8:
        r = 26 + (t % 0.8) * 50
        c.circ(hx + 13, hy, r, None, outline=(245, 170, 60), w=3)


def transfer_static():
    im = gradient((228, 236, 240), (214, 226, 232), 0, H)
    c = Canvas(im)
    vx, vy = 1350, 470
    c.poly([(0, 0), (W, 0), (W, 150), (vx + 170, vy - 120), (vx - 170, vy - 120), (0, 150)], (240, 244, 246))
    c.poly([(0, 150), (vx - 170, vy - 120), (vx - 170, vy + 110), (0, 900)], (226, 234, 238))
    c.poly([(W, 150), (vx + 170, vy - 120), (vx + 170, vy + 110), (W, 900)], (218, 228, 233))
    c.poly([(0, 900), (vx - 170, vy + 110), (vx + 170, vy + 110), (W, 900), (W, H), (0, H)], (200, 208, 212))
    c.poly([(0, 780), (vx - 170, vy + 80), (vx - 170, vy + 92), (0, 810)], TEAL_L)
    c.poly([(W, 780), (vx + 170, vy + 80), (vx + 170, vy + 92), (W, 810)], TEAL_L)
    for f in (0.15, 0.35, 0.55, 0.72):
        lx0 = vx - 170 * (1 - f) - (1 - f) * 0  # light panels along ceiling
        yy = (vy - 120) * (1 - f) + 0 * f
        hw = 170 + (W / 2) * (1 - f) * 0.6
        c.poly([(vx - hw * 0.3, (vy - 120) + (150 - (vy - 120)) * (1 - f) * 0.5 - 6),
                (vx + hw * 0.3, (vy - 120) + (150 - (vy - 120)) * (1 - f) * 0.5 - 6),
                (vx + hw * 0.26, (vy - 120) + (150 - (vy - 120)) * (1 - f) * 0.5 + 10),
                (vx - hw * 0.26, (vy - 120) + (150 - (vy - 120)) * (1 - f) * 0.5 + 10)], (255, 255, 240))
    # theatre doors at the end
    c.rect((vx - 150, vy - 100, vx + 150, vy + 110), (120, 170, 190))
    c.rect((vx - 140, vy - 80, vx - 4, vy + 110), (150, 196, 214))
    c.rect((vx + 4, vy - 80, vx + 140, vy + 110), (150, 196, 214))
    c.rect((vx - 110, vy - 50, vx - 40, vy), (210, 232, 240), r=6)
    c.rect((vx + 40, vy - 50, vx + 110, vy), (210, 232, 240), r=6)
    c.rect((vx - 110, vy - 150, vx + 110, vy - 108), TEAL, r=8)
    c.text((vx, vy - 129), "OPERATING THEATRES", 18, WHITE)
    # side doors in perspective
    c.poly([(240, 290), (420, 340), (420, 760), (240, 820)], (186, 206, 214))
    c.poly([(1680, 340), (1820, 300), (1820, 830), (1680, 760)], (186, 206, 214))
    return im


def transfer_dynamic(c, t, d):
    vx, vy = 1350, 470
    # staff waiting at the doors
    wave = ("wave", t * 5) if t > d * 0.45 else ("down", 0)
    person(c, vx - 60, vy + 118, 190, SKINS[0], THEATRE, cap=(90, 120, 200), arms=(("down", 0), wave), badge=False)
    person(c, vx + 60, vy + 118, 190, SKINS[2], THEATRE, cap=(220, 120, 160), style="bun", badge=False,
           arms=(("down", 0), ("down", 0)))
    # trolley moving towards the theatre
    p = ease(t / (d * 0.95))
    tx = 1220 - p * 440
    ty = 760
    c.rect((tx - 10, ty + 34, tx + 560, ty + 52), (176, 186, 194), r=6)
    for lx in (tx + 40, tx + 480):
        c.rect((lx, ty + 52, lx + 12, ty + 140), (150, 158, 166))
        c.circ(lx + 6, ty + 146, 13, (70, 75, 84))
    c.rect((tx, ty, tx + 560, ty + 36), (250, 250, 252), r=12)
    c.rect((tx + 380, ty - 26, tx + 540, ty - 16), (176, 186, 194), r=4)
    # IV pole travelling with the trolley
    c.rect((tx + 18, ty - 300, tx + 26, ty + 40), (160, 168, 176))
    c.rect((tx, ty - 300, tx + 44, ty - 230), (220, 236, 246), r=10)
    lying(c, tx, ty, 560, SKINS[2], eyes=1.0, blanket=(130, 186, 206), style="long", head_left=False)
    # porter/nurse pushing at the head end
    person(c, tx + 640, ty + 150, 520, SKINS[1], SCRUB, walk=t * 4.0, badge=True, facing=-1,
           arms=(("push", 0), ("push", 0)), mouth=abs(math.sin(t * 8)) if 3 < t < 5 else 0)


def anaes_static():
    im, c = room(wall=(226, 238, 236), wall2=(208, 226, 222), floor=(188, 202, 200), stripe=(180, 210, 200))
    c.rect((900, 170, 1250, 380), (238, 244, 244), r=10)  # wall cabinets
    c.rect((910, 180, 1070, 370), (220, 232, 232), r=6)
    c.rect((1080, 180, 1240, 370), (220, 232, 232), r=6)
    c.rect((1300, 110, 1460, 160), (255, 255, 240), r=6)  # ceiling light
    # IV pole + bag
    c.rect((1795, 230, 1805, 830), (160, 168, 176))
    c.rect((1760, 820, 1840, 834), (120, 126, 134), r=4)
    c.rect((1770, 240, 1830, 330), (220, 236, 246), r=12)
    c.rect((1776, 270, 1824, 324), (200, 226, 242), r=8)
    return im


def anaes_dynamic(c, t, d):
    sleep = ease((t - (d - 4.0)) / 2.5)
    eyes = 1.0 - sleep if (t % 3.9) > 0.15 else 0.0
    # anaesthetist behind trolley
    person(c, 1260, 820, 560, SKINS[3], THEATRE, cap=(70, 120, 190), mask=True, badge=False,
           arms=(("reach", 0), ("reach", 6 * math.sin(t * 1.3))), mouth=abs(math.sin(t * 8)) if sleep < 0.3 else 0,
           facing=1)
    # trolley
    tx, ty = 980, 700
    c.rect((tx - 10, ty + 34, tx + 640, ty + 52), (176, 186, 194), r=6)
    for lx in (tx + 50, tx + 560):
        c.rect((lx, ty + 52, lx + 12, ty + 136), (150, 158, 166))
        c.circ(lx + 6, ty + 142, 13, (70, 75, 84))
    c.rect((tx, ty, tx + 640, ty + 36), (250, 250, 252), r=12)
    hand = lying(c, tx, ty, 640, SKINS[1], eyes=eyes, blanket=(150, 196, 214), head_left=False, arm_out=True)
    hx, hy = hand
    # BP cuff on the arm, finger clip, IV line
    c.rect((hx + 120, hy - 32, hx + 172, hy + 14), (70, 90, 120), r=8)
    glow = 0.5 + 0.5 * math.sin(t * 4)
    c.circ(hx - 14, hy, 16 + 4 * glow, (255, int(120 + 60 * glow), int(120 + 60 * glow)))
    c.rect((hx - 26, hy - 10, hx - 2, hy + 10), (60, 70, 80), r=5)
    c.line([(hx + 30, hy - 6), (1800, 330)], (200, 220, 230), 3, cap=False)
    # ECG stickers
    for sx in (tx + 640 - 190, tx + 640 - 150):
        c.circ(sx, ty - 84, 8, WHITE, outline=(200, 200, 200), w=2)
    monitor(c, 1540, 240, 220, 160, t)
    # dim the lights as the patient drifts off
    if sleep > 0:
        ov = Image.new("RGB", c.im.size, (20, 30, 50))
        c.im.paste(Image.blend(c.im, ov, 0.35 * sleep))


def recovery_static():
    im, c = room(wall=(242, 236, 228), wall2=(232, 224, 214), floor=(206, 200, 194), stripe=(230, 206, 180))
    window(c, 950, 160, 300, 280)
    c.circ(1450, 240, 52, WHITE, outline=(120, 120, 130), w=6)  # clock
    c.line([(1450, 240), (1450, 206)], NAVY, 5)
    c.line([(1450, 240), (1474, 252)], NAVY, 5)
    bed(c, 1060, 640, 600)
    return im


def recovery_dynamic(c, t, d):
    open_k = ease((t - 2.0) / 1.5)
    eyes = open_k if (t % 4.1) > 0.15 or open_k < 1 else 0.0
    lying(c, 1060, 640, 600, SKINS[2], eyes=eyes, blanket=(240, 180, 130), style="long")
    monitor(c, 1700, 170, 180, 130, t, pole=False, hr=68)
    c.rect((1784, 300, 1796, 380), (120, 126, 134))
    # nurse tucking the warm blanket
    person(c, 1640, 900, 560, SKINS[0], SCRUB, style="bun", steth=True, facing=-1,
           arms=(("reach", 10 + 8 * math.sin(t * 1.4)), ("down", 0)), mouth=abs(math.sin(t * 8)) if 4 < t < 6 else 0)


def ward_static():
    im, c = room()
    window(c, 1450, 150, 360, 300)
    c.rect((1700, 600, 1800, 840), (226, 214, 196), r=6)
    c.rect((1725, 520, 1765, 600), (200, 226, 236), r=10)  # vase + flowers
    for fx, fy, col in ((1730, 490, CORAL), (1760, 480, SAND), (1745, 460, (230, 120, 160))):
        c.line([(1745, 520), (fx, fy)], (90, 150, 90), 4)
        c.circ(fx, fy, 15, col)
    bed(c, 1060, 640, 600)
    return im


def ward_dynamic(c, t, d):
    blink = 0.0 if (t % 4.6) < 0.15 else 1.0
    px = 1140
    c.rect((1070, 400, 1220, 650), (236, 240, 244), r=40)
    head(c, px, 420, 58, SKINS[1], HAIR, "short", eyes=blink)
    c.rect((px - 66, 480, px + 66, 650), GOWN, r=36)
    c.rect((px + 10, 580, 1640, 662), (122, 176, 196), r=34)
    c.ell((1540, 540, 1640, 640), (122, 176, 196))
    # sipping water periodically
    k = ease(math.sin(max(0, (t % 6) - 3) / 3 * math.pi))
    hand = limb(c, (px + 48, 500), 40 - 10 * k, 80, 150 - 70 * (1 - k), 70, 1, GOWN, SKINS[1], 30, 22)
    gx, gy = hand
    c.rect((gx - 16, gy - 54, gx + 18, gy + 8), (220, 238, 248), r=5)
    c.rect((gx - 13, gy - 30, gx + 15, gy + 5), (170, 210, 236), r=4)
    # family member visiting
    person(c, 900, 920, 540, SKINS[3], (200, 120, 150), bottom=(70, 80, 110), style="long", badge=False, facing=1,
           arms=(("down", 0), ("reach", 2 * math.sin(t))), mouth=abs(math.sin(t * 7)) if 6 < t < 8 else 0)
    # call bell on the rail
    c.line([(1400, 616), (1420, 680), (1460, 700)], (90, 96, 104), 4, cap=False)
    c.rect((1440, 690, 1490, 760), (238, 240, 244), r=12)
    pulse = 0.5 + 0.5 * math.sin(t * 5)
    c.circ(1465, 715, 14 + 2 * pulse, (220, 60 + int(40 * pulse), 60))
    if t > d * 0.62:
        a = ease((t - d * 0.62) / 0.5)
        c.circ(1465, 715, 30 + 26 * ((t * 1.2) % 1), None, outline=CORAL, w=4 * a)
        c.rect((1500, 760, 1500 + 200 * a, 810), NAVY, r=22)
        if a > 0.9:
            c.text((1600, 785), "Call bell", 24, WHITE)


def outro_static():
    im, c = room()
    window(c, 1500, 150, 300, 260)
    return im


def outro_dynamic(c, t, d):
    person(c, 1050, 920, 560, SKINS[0], SCRUB, style="bun", steth=True, arms=(("down", 0), ("wave", t * 5)))
    person(c, 1340, 920, 600, SKINS[3], (60, 90, 140), coat=True, steth=True,
           arms=(("wave", t * 5 + 1), ("down", 0)))
    person(c, 1630, 920, 560, SKINS[2], (130, 110, 190), style="long", arms=(("down", 0), ("wave", t * 5 + 2)))


SCENE_ART = {
    "welcome": (welcome_static, welcome_dynamic, (1300, 600)),
    "prep": (prep_static, prep_dynamic, (1450, 600)),
    "transfer": (transfer_static, transfer_dynamic, (1300, 600)),
    "anaesthesia": (anaes_static, anaes_dynamic, (1400, 560)),
    "recovery": (recovery_static, recovery_dynamic, (1350, 620)),
    "ward": (ward_static, ward_dynamic, (1350, 600)),
    "outro": (outro_static, outro_dynamic, (1340, 600)),
}


# --------------------------------------------------------------- overlays ---

def rgba_text_block(text, size, name, fill, width):
    f = font(name, size)
    lines, cur = [], ""
    for word in text.split():
        trial = (cur + " " + word).strip()
        if f.getlength(trial) > width and cur:
            lines.append(cur)
            cur = word
        else:
            cur = trial
    lines.append(cur)
    lh = int(size * 1.22)
    im = Image.new("RGBA", (int(width), lh * len(lines) + 6), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for i, ln in enumerate(lines):
        d.text((0, i * lh), ln, font=f, fill=fill)
    return im


def build_card(scene):
    """Pre-render the left text card as separately animated layers."""
    x0, y0, cw, pad = 80, 150, 680, 48
    layers = []
    y = y0 + pad
    badge_f = font("Inter-Bold.otf", 26)
    bw = int(badge_f.getlength(scene["badge"])) + 44
    b = Image.new("RGBA", (bw, 50), (0, 0, 0, 0))
    bd = ImageDraw.Draw(b)
    bd.rounded_rectangle([0, 0, bw - 1, 49], radius=25, fill=TEAL + (255,))
    bd.text((bw / 2, 25), scene["badge"], font=badge_f, fill=WHITE, anchor="mm")
    layers.append((b, x0 + pad, y))
    y += 76
    hd = rgba_text_block(scene["heading"], 56, "InterDisplay-Bold.otf", NAVY + (255,), cw - 2 * pad)
    layers.append((hd, x0 + pad, y))
    y += hd.size[1] + 26
    for bullet in scene["bullets"]:
        tb = rgba_text_block(bullet, 36, "Inter-Medium.otf", (60, 80, 92, 255), cw - 2 * pad - 64)
        item = Image.new("RGBA", (cw - 2 * pad, max(tb.size[1], 48)), (0, 0, 0, 0))
        idr = ImageDraw.Draw(item, "RGBA")
        idr.ellipse([0, 2, 40, 42], fill=TEAL_L + (255,))
        idr.line([(11, 22), (18, 30), (30, 14)], fill=TEAL + (255,), width=5, joint="curve")
        item.alpha_composite(tb, (64, 0))
        layers.append((item, x0 + pad, y))
        y += item.size[1] + 22
    card_h = y - y0 + pad - 22
    card = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([x0 + 6, y0 + 14, x0 + cw + 6, y0 + card_h + 14], radius=36,
                                         fill=(20, 50, 60, 70))
    card.alpha_composite(sh.filter(ImageFilter.GaussianBlur(18)))
    ImageDraw.Draw(card).rounded_rectangle([x0, y0, x0 + cw, y0 + card_h], radius=36, fill=(255, 255, 255, 236))
    ImageDraw.Draw(card).rectangle([x0 + 36, y0, x0 + cw - 36, y0 + 8], fill=TEAL + (255,))
    return card, layers


def with_alpha(im, a):
    if a >= 0.999:
        return im
    out = im.copy()
    out.putalpha(im.getchannel("A").point(lambda v: int(v * a)))
    return out


def subtitle_img(text):
    f = font("Inter-SemiBold.otf", 40)
    lines = textwrap.wrap(text, 58)
    lh = 52
    w = int(max(f.getlength(l) for l in lines)) + 64
    h = lh * len(lines) + 30
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=18, fill=(10, 24, 30, 175))
    for i, l in enumerate(lines):
        d.text((w / 2, 15 + i * lh + lh / 2), l, font=f, fill=WHITE, anchor="mm")
    return im


def progress_img(step):
    im = Image.new("RGBA", (360, 60), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, 359, 59], radius=30, fill=(255, 255, 255, 220))
    for i in range(5):
        cx = 52 + i * 64
        if i + 1 < step:
            d.ellipse([cx - 14, 16, cx + 14, 44], fill=TEAL)
        elif i + 1 == step:
            d.ellipse([cx - 18, 12, cx + 18, 48], fill=CORAL)
        else:
            d.ellipse([cx - 14, 16, cx + 14, 44], fill=(210, 220, 224))
        d.text((cx, 30), str(i + 1), font=font("Inter-Bold.otf", 18), fill=WHITE, anchor="mm")
    return im


# --------------------------------------------------------------- timeline ---

LEAD, GAP, TAIL = 1.4, 0.75, 2.2
TITLE_DUR, END_DUR = 5.0, 5.0
FADE = 0.45


def split_sub(sentence):
    """Break long sentences into subtitle chunks at commas, roughly <= 75 chars."""
    parts, cur = [], ""
    for piece in sentence.replace(", ", ", \u0000").split("\u0000"):
        if cur and len(cur) + len(piece) > 75:
            parts.append(cur.strip())
            cur = piece
        else:
            cur += piece
    parts.append(cur.strip())
    return [p for p in parts if p]


def build_timeline(vo_dir):
    manifest = json.load(open(os.path.join(vo_dir, "manifest.json")))
    timeline, voice, subs = [], [], []
    t = TITLE_DUR
    timeline.append(("title", 0.0, TITLE_DUR, None))
    for scene in SCENES:
        start = t
        cur = t + LEAD
        for i, sentence in enumerate(scene["narration"]):
            path = os.path.join(vo_dir, f"{scene['id']}_{i}.wav")
            dur = manifest[path]
            voice.append((cur, path))
            chunks = split_sub(sentence)
            total = sum(len(ch) for ch in chunks)
            ct = cur
            for ch in chunks:
                cd = dur * len(ch) / total
                subs.append((ct, ct + cd, ch))
                ct += cd
            cur += dur + GAP
        end = cur - GAP + TAIL
        timeline.append((scene["id"], start, end - start, scene))
        t = end
    timeline.append(("end", t, END_DUR, None))
    return timeline, voice, subs, t + END_DUR


# ---------------------------------------------------------------- frames ---

_cache = {}


def static_for(sid):
    if sid not in _cache:
        _cache[sid] = SCENE_ART[sid][0]()
    return _cache[sid]


def overlay_for(scene):
    key = "card_" + scene["id"]
    if key not in _cache:
        _cache[key] = build_card(scene)
    return _cache[key]


def sub_for(text):
    key = "sub_" + text
    if key not in _cache:
        _cache[key] = subtitle_img(text)
    return _cache[key]


def title_frame(t, dur, end=False):
    im = gradient((44, 160, 150), (28, 70, 96), 0, H)
    c = Canvas(im)
    k = ease(t / 0.9)
    c.circ(960, 330, 150 + 20 * math.sin(t * 1.3), shade((44, 160, 150), 1.1))
    logo(c, 960, 330, 110 * (0.6 + 0.4 * k))
    frame = im.resize((W, H), Image.BILINEAR, reducing_gap=2.0).convert("RGBA")
    d = ImageDraw.Draw(frame)
    a1 = int(255 * ease((t - 0.5) / 0.8))
    a2 = int(255 * ease((t - 1.1) / 0.8))
    a3 = int(255 * ease((t - 1.7) / 0.8))
    if end:
        lines = [("Wishing you a smooth recovery", 84, "InterDisplay-Bold.otf", a1),
                 ("Have questions? Ask your doctor or nurse.", 44, "Inter-Medium.otf", a2),
                 (WARD, 32, "Inter-SemiBold.otf", a3)]
    else:
        lines = [(TITLE, 104, "InterDisplay-Bold.otf", a1), (SUBTITLE, 56, "InterDisplay-Medium.otf", a2),
                 (WARD + "  ·  Patient Guide", 32, "Inter-SemiBold.otf", a3)]
    y = 580
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(lay)
    for text, size, name, a in lines:
        ld.text((W / 2, y + (1 - a / 255) * 20), text, font=font(name, size), fill=(255, 255, 255, a), anchor="mm")
        y += size * 1.45
    frame.alpha_composite(lay)
    return frame


def scene_frame(sid, scene, t, dur):
    static, dynamic, focus = SCENE_ART[sid]
    im = static_for(sid).copy()
    dynamic(Canvas(im), t, dur)
    z = 1.0 + 0.045 * (t / dur)
    cw, ch = W * S / z, H * S / z
    fx, fy = focus[0] * S, focus[1] * S
    x0 = min(max(fx - cw * (fx / (W * S)), 0), W * S - cw)
    y0 = min(max(fy - ch * (fy / (H * S)), 0), H * S - ch)
    frame = im.resize((W, H), Image.BILINEAR, box=(x0, y0, x0 + cw, y0 + ch), reducing_gap=2.0).convert("RGBA")
    card, layers = overlay_for(scene)
    ca = ease((t - 0.2) / 0.6)
    frame.alpha_composite(with_alpha(card, ca))
    for i, (lay, lx, ly) in enumerate(layers):
        a = ease((t - (0.4 + i * (0.35 if i < 2 else 1.4))) / 0.5)
        if a > 0:
            frame.alpha_composite(with_alpha(lay, a), (lx - int((1 - a) * 24), ly))
    step = scene["badge"].startswith("STEP") and int(scene["badge"].split()[1])
    if step:
        frame.alpha_composite(with_alpha(progress_img(step), ca), (W - 420, 56))
    return frame


def render_frame(n):
    t = n / FPS
    for sid, start, dur, scene in TIMELINE:
        if start <= t < start + dur or sid == "end":
            lt = t - start
            break
    if sid in ("title", "end"):
        frame = title_frame(lt, dur, end=(sid == "end"))
    else:
        frame = scene_frame(sid, scene, lt, dur)
    for s0, s1, text in SUBS:
        if s0 - 0.1 <= t < s1 + 0.15:
            a = min(ease((t - s0 + 0.1) / 0.15), ease((s1 + 0.15 - t) / 0.15))
            sub = sub_for(text)
            frame.alpha_composite(with_alpha(sub, a), ((W - sub.size[0]) // 2, H - sub.size[1] - 56))
            break
    fade = min(ease(lt / FADE), ease((dur - lt) / FADE)) if sid != "title" or lt > 0.5 else ease(lt / 0.5)
    if sid == "end":
        fade = min(ease(lt / FADE), ease((dur - lt) / 1.2))
    rgb = frame.convert("RGB")
    if fade < 0.999:
        bg = (255, 255, 255) if sid not in ("end",) or lt < dur / 2 else (0, 0, 0)
        rgb = Image.blend(Image.new("RGB", (W, H), bg), rgb, fade)
    return rgb.tobytes()


# ------------------------------------------------------------------ audio ---

def music(total, sr=24000):
    """Soft, slow ambient pad (Cmaj7 - Am7 - Fmaj7 - G6)."""
    t = np.arange(int(total * sr)) / sr
    out = np.zeros_like(t)
    chords = [[261.6, 329.6, 392.0, 493.9], [220.0, 261.6, 329.6, 392.0],
              [174.6, 220.0, 261.6, 329.6], [196.0, 246.9, 293.7, 329.6]]
    seg = 6.0
    for i in range(int(total / seg) + 2):
        notes = chords[i % 4]
        s0 = i * seg - 1.5
        env = np.clip((t - s0) / 2.0, 0, 1) * np.clip((s0 + seg + 3.0 - t) / 2.0, 0, 1)
        if not env.any():
            continue
        for j, f in enumerate(notes):
            out += env * (np.sin(2 * np.pi * f / 2 * t + j) * 0.5 + np.sin(2 * np.pi * f * t) * 0.25
                          + np.sin(2 * np.pi * f * 1.003 * t) * 0.15)
        bell = notes[(i * 3) % 4] * 2
        bt = t - (i * seg + 0.5)
        m = (bt > 0) & (bt < 4)
        out[m] += np.sin(2 * np.pi * bell * bt[m]) * np.exp(-bt[m] * 1.4) * 0.6
    out /= np.abs(out).max()
    fade = np.clip(t / 3, 0, 1) * np.clip((total - t) / 4, 0, 1)
    return out * fade * 0.11


def build_audio(voice, total, path, sr=24000):
    mix = music(total, sr)
    duck = np.ones_like(mix)
    for start, wav in voice:
        data, wsr = sf.read(wav)
        assert wsr == sr
        i = int(start * sr)
        mix[i:i + len(data)] += data * 0.95
        duck[max(0, i - sr // 4):i + len(data) + sr // 4] = 0.6
    sf.write(path, np.clip(mix, -1, 1).astype(np.float32), sr)


def write_srt(subs, path):
    def ts(x):
        ms = int(round(x * 1000))
        return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"
    with open(path, "w") as f:
        for i, (s0, s1, text) in enumerate(subs, 1):
            f.write(f"{i}\n{ts(s0)} --> {ts(s1)}\n{text}\n\n")


TIMELINE, VOICE, SUBS, TOTAL = None, None, None, None


def main():
    global TIMELINE, VOICE, SUBS, TOTAL
    vo_dir, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    TIMELINE, VOICE, SUBS, TOTAL = build_timeline(vo_dir)
    if "--preview" in sys.argv:
        for sid, start, dur, _ in TIMELINE:
            for frac in (0.15, 0.7):
                n = int((start + dur * frac) * FPS)
                Image.frombytes("RGB", (W, H), render_frame(n)).save(os.path.join(out, f"preview_{sid}_{frac}.jpg"),
                                                                    quality=85)
        print("total", TOTAL)
        return
    audio = os.path.join(out, "audio.wav")
    build_audio(VOICE, TOTAL, audio)
    write_srt(SUBS, os.path.join(out, "surgery-day.en.srt"))
    nframes = int(TOTAL * FPS)
    video = os.path.join(out, "surgery-day.mp4")
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", audio,
                           "-c:v", "libx264", "-preset", "medium", "-crf", "21", "-pix_fmt", "yuv420p",
                           "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-shortest",
                           "-movflags", "+faststart", video], stdin=subprocess.PIPE)
    with Pool(os.cpu_count()) as pool:
        for i, buf in enumerate(pool.imap(render_frame, range(nframes), chunksize=4)):
            ff.stdin.write(buf)
            if i % 300 == 0:
                print(f"frame {i}/{nframes}", flush=True)
    ff.stdin.close()
    ff.wait()
    print("wrote", video, f"{TOTAL:.1f}s")


if __name__ == "__main__":
    main()
