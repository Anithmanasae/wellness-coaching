# Smart Serve Reel #25 - "before vs during the rush" turned into a LIVE SPORTS BROADCAST ("RUSH TV"):
#   pre-match (calm crew) -> BREAKING: rush hits the kitchen (chaos, scoreboard, ticker, crowd)
#   -> INSTANT REPLAY in slow-mo -> full-time whistle -> PLAYER OF THE RUSH card + Comment APP.
# Usage: python3 make_reel_25_broadcast.py <clip.mp4>
import math, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import soundtrack as st

SRC = sys.argv[1]
OUT = os.path.join(HERE, "smartserve_reel_25_broadcast.mp4")
W, H, FPS, SR = 1080, 1920, 30, 44100
F = "/usr/share/fonts/opentype/inter/"
def font(sz, w="Bold"): return ImageFont.truetype(F + f"Inter-{w}.otf", sz)
WHITE, BLACK, RED, GOLD, NAVY = (255, 255, 255), (0, 0, 0), (220, 20, 40), (255, 196, 40), (10, 22, 60)
LOGO = Image.open(os.path.join(HERE, "assets", "logo.png")).convert("RGBA")
def clamp(x): return max(0.0, min(1.0, x))
def ease(x): x = clamp(x); return 1 - (1 - x) ** 3

SEG1 = (0.0, 3.6)            # pre-match
SEG2 = (5.63, 10.1)          # the rush
REPLAY = (8.9, 10.1)         # replayed at half speed
END = 6.2
TICK1 = "PRE-MATCH  •  Team warming up with coffee…  •  calm before the storm  •  "
TICK2 = "UNBELIEVABLE SCENES IN THE KITCHEN!!  •  orders flying in from every table  •  is that a WATERMELON?!  •  "

def frames(a, b):
    p = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-ss", str(a), "-t", str(b - a), "-i", SRC,
        "-vf", f"fps={FPS},scale={W}:{H}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    n = W * H * 3
    while True:
        buf = p.stdout.read(n)
        if len(buf) < n: break
        yield Image.frombytes("RGB", (W, H), buf)
    p.wait()

# ---------------- broadcast graphics ----------------
def live_bug(d, t):
    d.rounded_rectangle([40, 60, 205, 120], 12, fill=RED)
    if int(t * 2) % 2 == 0: d.ellipse([58, 78, 82, 102], fill=WHITE)
    d.text((92, 70), "LIVE", font=font(38, "Black"), fill=WHITE)
    d.rounded_rectangle([215, 60, 420, 120], 12, fill=(15, 15, 20))
    d.text((235, 70), "RUSH TV", font=font(36, "Black"), fill=GOLD)

def scoreboard(d, pending, over):
    x0, y0 = 440, 60
    d.rounded_rectangle([x0, y0, W - 40, y0 + 120], 14, fill=(15, 15, 20))
    d.rectangle([x0, y0, x0 + 12, y0 + 120], fill=GOLD)
    d.text((x0 + 30, y0 + 12), "KITCHEN v CUSTOMERS", font=font(28, "Black"), fill=WHITE)
    d.text((x0 + 30, y0 + 56), "orders pending", font=font(28, "SemiBold"), fill=(170, 170, 185))
    col = RED if pending > 8 else WHITE
    txt = f"{pending}"; f = font(52, "Black"); w = d.textlength(txt, font=f)
    d.text((W - 70 - w, y0 + 50), txt, font=f, fill=col)
    f2 = font(28, "Bold"); txt = f"OVER {over}"; w = d.textlength(txt, font=f2)
    d.text((W - 70 - w, y0 + 14), txt, font=f2, fill=GOLD)

def ticker(img, text, t, col=(15, 15, 20)):
    d = ImageDraw.Draw(img); y = 1440
    d.rectangle([0, y, W, y + 74], fill=col); d.rectangle([0, y, 160, y + 74], fill=GOLD)
    d.text((22, y + 18), "LIVE", font=font(36, "Black"), fill=BLACK)
    f = font(40, "Bold"); full = text * 4; tw = d.textlength(text, font=f)
    x = 180 - (t * 420) % tw
    strip = Image.new("RGB", (W - 160, 74), col); sd = ImageDraw.Draw(strip)
    sd.text((x - 160, 16), full, font=f, fill=WHITE); img.paste(strip, (160, y))

def breaking(img, t):
    if t < 0.2: return
    a = ease((t - 0.2) / 0.25); d = ImageDraw.Draw(img)
    x = int(-W * (1 - a)); y = 1250
    d.rectangle([x, y, x + W, y + 170], fill=RED)
    d.rectangle([x, y, x + 300, y + 70], fill=WHITE)
    d.text((x + 24, y + 10), "BREAKING", font=font(48, "Black"), fill=RED)
    d.text((x + 24, y + 82), "SATURDAY RUSH HITS THE KITCHEN", font=font(54, "Black"), fill=WHITE)

def replay_overlay(img, t):
    img2 = ImageEnhance.Color(img).enhance(0.55); img.paste(img2)
    d = ImageDraw.Draw(img)
    for k in range(0, H, 6): d.line([0, k, W, k], fill=(0, 0, 0), width=1)
    r = 70; cx, cy = 140, 250; ang = t * 360
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=GOLD)
    d.arc([cx - 45, cy - 45, cx + 45, cy + 45], ang, ang + 280, fill=BLACK, width=12)
    d.text((230, 205), "INSTANT REPLAY", font=font(66, "Black"), fill=WHITE, stroke_width=6, stroke_fill=BLACK)
    d.text((230, 285), "slow-mo", font=font(40, "Bold"), fill=GOLD, stroke_width=4, stroke_fill=BLACK)

def player_card(img, t):
    d = ImageDraw.Draw(img)
    for y in range(H):
        k = y / H; d.line([0, y, W, y], fill=(int(8 + 20 * k), int(14 + 30 * k), int(40 + 60 * k)))
    if t < 0.9:  # FULL TIME flash
        f = font(130, "Black"); txt = "FULL TIME"; w = d.textlength(txt, font=f)
        d.text(((W - w) / 2, 820), txt, font=f, fill=GOLD, stroke_width=8, stroke_fill=BLACK)
        return
    tt = t - 0.9; a = ease(tt / 0.4)
    f = font(48, "Black"); txt = "PLAYER OF THE RUSH"; w = d.textlength(txt, font=f)
    d.text(((W - w) / 2, 150), txt, font=f, fill=GOLD)
    # gold player card
    cw, ch = 560, 820; cx = W / 2; y0 = 250 + int(120 * (1 - a))
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0)); sd = ImageDraw.Draw(sh)
    sd.rounded_rectangle([cx - cw / 2, y0, cx + cw / 2, y0 + ch], 40, fill=(255, 220, 110, 255))
    sd.rounded_rectangle([cx - cw / 2 + 18, y0 + 18, cx + cw / 2 - 18, y0 + ch - 18], 30, fill=(214, 160, 40, 255))
    glow = sh.filter(ImageFilter.GaussianBlur(30)); img.paste(glow, (0, 0), glow); img.paste(sh, (0, 0), sh)
    d = ImageDraw.Draw(img)
    d.text((cx - cw / 2 + 50, y0 + 40), "99", font=font(90, "Black"), fill=(70, 40, 0))
    d.text((cx - cw / 2 + 56, y0 + 140), "MGR", font=font(40, "Black"), fill=(70, 40, 0))
    l = LOGO.resize((300, 300), Image.LANCZOS); img.paste(l, (int(cx - 150 + 40), y0 + 70), l)
    d = ImageDraw.Draw(img)
    f = font(60, "Black"); txt = "SMART SERVE"; w = d.textlength(txt, font=f); d.text((cx - w / 2, y0 + 400), txt, font=f, fill=(50, 25, 0))
    d.line([cx - cw / 2 + 50, y0 + 490, cx + cw / 2 - 50, y0 + 490], fill=(120, 80, 10), width=4)
    stats = [("ORD", "142"), ("MISS", "0"), ("CASH", "✓"), ("KOT", "142"), ("STRS", "0"), ("RUSH", "W")]
    for i, (k, v) in enumerate(stats):
        if tt < 0.4 + i * 0.12: continue
        col, row = i % 2, i // 2
        x = cx - cw / 2 + 70 + col * 250; y = y0 + 520 + row * 90
        d.text((x, y), v, font=font(52, "Black"), fill=(50, 25, 0)); d.text((x + 110, y + 12), k, font=font(36, "Bold"), fill=(90, 55, 5))
    if tt > 1.5:
        b = ease((tt - 1.5) / 0.3); f4 = font(50, "Black"); txt = 'Comment "APP" for the app\'s name'; w = d.textlength(txt, font=f4)
        yb = 1140 + 20 + int(20 * (1 - b))
        d.rounded_rectangle([(W - w) / 2 - 30, yb, (W + w) / 2 + 30, yb + 90], 24, fill=(52, 199, 89))
        d.text(((W - w) / 2, yb + 12), txt, font=f4, fill=(5, 30, 15))
        f5 = font(36, "SemiBold"); txt = "free on Play Store · link in bio"; w = d.textlength(txt, font=f5)
        d.text(((W - w) / 2, yb + 115), txt, font=f5, fill=(200, 215, 255))

# ---------------- audio ----------------
def crowd(dur, swell=True):
    x = st.band(st.noise(dur), 300, 3500) * 0.5 + st.band(st.noise(dur), 3500, 7000) * 0.15
    tt = np.arange(len(x)) / SR
    env = np.minimum(1, tt / 0.8) if swell else np.ones(len(x))
    return x * env * (0.8 + 0.2 * np.sin(2 * np.pi * 0.7 * tt))

def whistle(dur=0.9):
    tt = np.arange(int(dur * SR)) / SR
    f = 2900 + 120 * np.sign(np.sin(2 * np.pi * 22 * tt))
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.minimum(1, (dur - tt) / 0.05) * np.minimum(1, tt / 0.02)

def soundtrack(path, t2, t3, t4, total):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", SRC, "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"], capture_output=True).stdout
    src = np.frombuffer(raw, np.int16).astype(np.float64) / 32768
    mix = np.zeros(int(total * SR) + SR)
    def seg(a, b):
        s = src[int(a * SR):int(b * SR)].copy(); n = int(0.05 * SR); s[:n] *= np.linspace(0, 1, n); s[-n:] *= np.linspace(1, 0, n); return s
    st.add(mix, seg(*SEG1), 0); st.add(mix, crowd(SEG1[1] - SEG1[0], False) * 0.08, 0)     # stadium murmur
    st.add(mix, seg(*SEG2), t2); st.add(mix, crowd(SEG2[1] - SEG2[0]) * 0.35, t2)          # crowd goes wild
    tt = np.arange(int(0.6 * SR)) / SR; horn = (np.sign(np.sin(2 * np.pi * 233 * tt)) + np.sign(np.sin(2 * np.pi * 294 * tt))) * 0.15
    st.add(mix, horn * np.minimum(1, (0.6 - tt) / 0.05), t2 + 0.2); st.add(mix, st.sfx_impact() * 0.6, t2 + 0.2)
    r = seg(*REPLAY); slow = np.interp(np.arange(0, len(r), 0.5), np.arange(len(r)), r)          # half-speed, lower pitch
    st.add(mix, st.sfx_whoosh() * 0.6, t3 - 0.1); st.add(mix, slow * 0.8, t3)
    st.add(mix, whistle() * 0.35, t4); st.add(mix, crowd(2.0) * 0.3, t4)
    t5 = t4 + 0.9
    for j, m in enumerate((72, 76, 79, 84, 88)): st.add(mix, st.pluck(st.note(m), 0.8, 3) * 0.3, t5 + j * 0.09)   # fanfare
    st.add(mix, st.music_uplift(total - t5 - 0.4), t5 + 0.4)
    st.finish(mix, path, total)

if __name__ == "__main__":
    l1, l2, lr = SEG1[1] - SEG1[0], SEG2[1] - SEG2[0], (REPLAY[1] - REPLAY[0]) * 2
    t2 = l1; t3 = t2 + l2; t4 = t3 + lr; total = t4 + END
    wav = OUT[:-4] + ".wav"; soundtrack(wav, t2, t3, t4, total)
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
        "-r", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", OUT], stdin=subprocess.PIPE)
    emit = lambda im: ff.stdin.write(im.tobytes())
    for i, fr in enumerate(frames(*SEG1)):
        t = i / FPS; d = ImageDraw.Draw(fr); live_bug(d, t); scoreboard(d, 0, "0.0"); ticker(fr, TICK1, t); emit(fr)
    for i, fr in enumerate(frames(*SEG2)):
        t = i / FPS; d = ImageDraw.Draw(fr); live_bug(d, t)
        pend = int(23 * clamp((t - 0.3) / (l2 - 0.8))); over = f"18.{min(5, int(t * 1.4))}"
        scoreboard(d, pend, over); breaking(fr, t); ticker(fr, TICK2, t, col=(120, 10, 20)); emit(fr)
    rep = list(frames(*REPLAY))
    for k in range(len(rep) * 2):
        fr = rep[k // 2].copy(); replay_overlay(fr, k / FPS); emit(fr)
    for i in range(int(END * FPS)):
        img = Image.new("RGB", (W, H)); player_card(img, i / FPS); emit(img)
    ff.stdin.close(); ff.wait(); os.remove(wav)
    tmp = OUT[:-4] + "_tmp.mp4"; os.replace(OUT, tmp)
    out = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", tmp, "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True).stderr
    gain = -13.5 - float(out.split("Summary:")[1].split("I:")[1].split("LUFS")[0])
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", tmp, "-c:v", "copy", "-af", f"volume={gain:.2f}dB,alimiter=limit=0.9",
                    "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", OUT], check=True); os.remove(tmp)
    print("done", OUT, round(total, 2))
