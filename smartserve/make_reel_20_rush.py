# Smart Serve Reel #20 - "before / during the rush" skit, flipped with a VHS rewind:
#   Us before the rush -> restaurants WITHOUT Smart Serve during the rush (chaos)
#   -> REWIND -> us during the rush WITH Smart Serve (chill + live app notifications)
#   -> printed-receipt end card.  All new visuals and sound for this format.
# Usage: python3 make_reel_20_rush.py <skit.mp4>
import io, math, os, random, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import soundtrack as st
from make_photo_memes import emoji_img

SRC = sys.argv[1]
OUT = os.path.join(HERE, "smartserve_reel_20_rush.mp4")
W, H, FPS, SR = 1080, 1920, 30, 44100
F = "/usr/share/fonts/opentype/inter/"
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
def font(sz, w="Bold"): return ImageFont.truetype(F + f"Inter-{w}.otf", sz)
def mono(sz): return ImageFont.truetype(MONO, sz)
WHITE, BLACK = (255, 255, 255), (0, 0, 0)
BLUE, NAVY, SKY = (24, 63, 191), (8, 18, 58), (84, 175, 247)
LOGO = Image.open(os.path.join(HERE, "assets", "logo.png")).convert("RGBA")
def clamp(x): return max(0.0, min(1.0, x))
def ease(x): x = clamp(x); return 1 - (1 - x) ** 3

# source caption bands (output px) to erase: chill scenes / chaos scene
BAND_CHILL = (240, 1095, 840, 1190)
BAND_CHAOS = (290, 1052, 790, 1132)

# ---------------- source access ----------------
def src_frames(a, b, step=1):
    p = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-ss", str(a), "-t", str(b - a), "-i", SRC,
        "-vf", f"fps={FPS},scale={W}:{H}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    n = W * H * 3; i = 0
    while True:
        buf = p.stdout.read(n)
        if len(buf) < n: break
        if i % step == 0: yield Image.frombytes("RGB", (W, H), buf)
        i += 1
    p.wait()

def src_audio():
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", SRC, "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"],
                         capture_output=True).stdout
    return np.frombuffer(raw, np.int16).astype(np.float64) / 32768

def erase(img, band):
    x0, y0, x1, y1 = band
    b = img.crop(band); mask = b.convert("L").point(lambda v: 255 if v > 170 else 0).filter(ImageFilter.MaxFilter(13))
    fill = b.copy()
    for _ in range(12): fill = Image.composite(fill.filter(ImageFilter.GaussianBlur(7)), b, mask)
    img.paste(fill, (x0, y0))

# ---------------- overlays ----------------
def label(img, text, emoji, yc, t, bg=WHITE, fg=BLACK):
    """bold rounded label chip centred on yc (sits over the old caption), slides up into place."""
    a = 0.6 + 0.4 * ease(t / 0.3); d = ImageDraw.Draw(img)   # never fully transparent: it hides the old caption
    lines = text.split("\n"); f = font(54, "ExtraBold"); lh = 66
    e = emoji_img(emoji, 58) if emoji else None
    wmax = max(d.textlength(l, font=f) for l in lines) + (e.width + 14 if e else 0)
    h = lh * len(lines) + 34; yy = int(yc - h / 2) + int(40 * (1 - a))
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ld = ImageDraw.Draw(lay)
    ld.rounded_rectangle([(W - wmax) / 2 - 34, yy, (W + wmax) / 2 + 34, yy + h], 30, fill=bg + (int(240 * a),))
    for i, l in enumerate(lines):
        w = ld.textlength(l, font=f) + (e.width + 14 if (e and i == 0) else 0)
        x = (W - w) / 2; ld.text((x, yy + 14 + i * lh), l, font=f, fill=fg + (int(255 * a),))
        if e and i == 0: lay.paste(e, (int(x + ld.textlength(l, font=f) + 14), int(yy + 18)), e)
    img.paste(lay, (0, 0), lay)

def toast(img, y, title, body, t):
    """phone-style push notification from Smart Serve."""
    a = ease(t / 0.28); yy = y - int(160 * (1 - a))
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    d.rounded_rectangle([60, yy + 6, W - 60, yy + 156], 36, fill=(0, 0, 0, int(70 * a)))
    d.rounded_rectangle([60, yy, W - 60, yy + 150], 36, fill=(250, 250, 252, int(245 * a)))
    l = LOGO.resize((96, 96), Image.LANCZOS); lay.paste(l, (88, yy + 27), l)
    d.text((206, yy + 24), "SMART SERVE", font=font(28, "Bold"), fill=(120, 120, 130, int(255 * a)))
    d.text((W - 160, yy + 24), "now", font=font(28, "Medium"), fill=(140, 140, 150, int(255 * a)))
    d.text((206, yy + 66), title, font=font(40, "ExtraBold"), fill=(15, 15, 20, int(255 * a)))
    d.text((206, yy + 112), body, font=font(30, "Medium"), fill=(70, 70, 80, int(255 * a)))
    img.paste(lay, (0, 0), lay)

def vhs(img, t, k):
    """rewind look: chroma split, wobbling rows, scanlines, OSD text."""
    r, g, b = img.split()
    img.paste(Image.merge("RGB", (ImageChops.offset(r, 9, 0), g, ImageChops.offset(b, -9, 0))))
    rnd = random.Random(k)
    for _ in range(14):
        y = rnd.randint(0, H - 40); h = rnd.randint(8, 40)
        strip = img.crop((0, y, W, y + h)); img.paste(ImageChops.offset(strip, rnd.randint(-60, 60), 0), (0, y))
    d = ImageDraw.Draw(img)
    for y in range(0, H, 4): d.line([0, y, W, y], fill=(0, 0, 0), width=1)
    nb = (k * 37) % H; d.rectangle([0, nb, W, nb + 26], fill=(200, 200, 200))
    f = mono(84); d.text((70, 120), "<< REWIND", font=f, fill=WHITE, stroke_width=3, stroke_fill=BLACK)
    d.text((70, 230), f"00:0{3 - int(t * 3)}:{59 - int(t * 50):02d}", font=mono(56), fill=WHITE, stroke_width=3, stroke_fill=BLACK)
    f2 = font(74, "Black"); txt = "WAIT… let's try that again"
    w = d.textlength(txt, font=f2); d.text(((W - w) / 2, 1380), txt, font=f2, fill=(255, 220, 60), stroke_width=7, stroke_fill=BLACK)

# ---------------- end card: printed receipt ----------------
RECEIPT = [("SMART SERVE", "c"), ("------------------------", "c"), ("SATURDAY RUSH HOUR", "c"), ("", ""),
           ("Orders taken", "142"), ("Sent to kitchen", "142 ✓"), ("Missed orders", "0"), ("Bills settled", "142 ✓"),
           ("Cash matched", "✓"), ("Staff stress", "0"), ("------------------------", "c"), ("TOTAL", "CHILL")]
LINE_T = 0.17
def end_card(img, t):
    d = ImageDraw.Draw(img)
    for y in range(H):  # navy -> blue gradient
        k = y / H; d.line([0, y, W, y], fill=tuple(int(NAVY[i] + (BLUE[i] - NAVY[i]) * k * 0.7) for i in range(3)))
    for x in range(0, W, 60): d.line([x, 0, x, H], fill=(20, 40, 100), width=1)
    # printer
    d.rounded_rectangle([140, 150, W - 140, 300], 28, fill=(30, 32, 40)); d.rectangle([200, 262, W - 200, 278], fill=(5, 5, 8))
    d.ellipse([W - 230, 190, W - 200, 220], fill=(60, 220, 120) if int(t * 4) % 2 else (20, 90, 50))
    n = min(len(RECEIPT), int(t / LINE_T) + 1)
    lh = 58; paper_h = 90 + n * lh + (40 if n == len(RECEIPT) else 0)
    x0, x1, top = 230, W - 230, 270
    d.rectangle([x0, top, x1, top + paper_h], fill=(252, 251, 246))
    for zx in range(x0, x1, 30): d.polygon([(zx, top + paper_h), (zx + 15, top + paper_h + 18), (zx + 30, top + paper_h)], fill=(252, 251, 246))
    f = mono(38)
    for i, (l, r) in enumerate(RECEIPT[:n]):
        y = top + 50 + i * lh
        if r == "c":
            w = d.textlength(l, font=f); d.text(((W - w) / 2, y), l, font=f, fill=(25, 25, 30))
        elif l:
            big = l == "TOTAL"; ff = mono(50) if big else f; col = BLUE if big else (25, 25, 30)
            d.text((x0 + 36, y), l, font=ff, fill=col)
            w = d.textlength(r, font=ff); d.text((x1 - 36 - w, y), r, font=ff, fill=(20, 150, 70) if r != "CHILL" else BLUE)
    done = len(RECEIPT) * LINE_T + 0.3
    if t > done:  # app icon pops in under the receipt
        a = ease((t - done) / 0.35); sz = int(180 * (0.6 + 0.4 * a) + 18 * math.sin(clamp((t - done) / 0.35) * math.pi))
        glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(glow).ellipse([W / 2 - 200, 1020, W / 2 + 200, 1420], fill=(120, 190, 255, int(110 * a)))
        glow = glow.filter(ImageFilter.GaussianBlur(50)); img.paste(glow, (0, 0), glow)
        l = LOGO.resize((sz, sz), Image.LANCZOS); img.paste(l, (int(W / 2 - sz / 2), int(1220 - sz / 2)), l)
        d = ImageDraw.Draw(img)
        f2 = font(54, "Black"); txt = "Run every rush like this"; w = d.textlength(txt, font=f2)
        d.text(((W - w) / 2, 1330 + int(30 * (1 - a))), txt, font=f2, fill=WHITE)
    if t > done + 0.5:
        f4 = font(50, "Black"); txt = 'Comment "APP" for the app\'s name'; w = d.textlength(txt, font=f4)
        d.rounded_rectangle([(W - w) / 2 - 30, 1420, (W + w) / 2 + 30, 1510], 24, fill=(60, 220, 120))
        d.text(((W - w) / 2, 1432), txt, font=f4, fill=(5, 30, 15))
        f5 = font(38, "SemiBold"); txt = "free on Play Store · link in bio"; w = d.textlength(txt, font=f5)
        d.text(((W - w) / 2, 1532), txt, font=f5, fill=(200, 220, 255))

# ---------------- timeline ----------------
S1 = (0.0, 3.4)        # us before the rush
S2 = (6.0, 8.9)        # chaos
REW = 1.0              # rewind
S4 = [(3.47, 6.0), (0.3, 1.8)]   # chill again, with notifications
END = 5.6
TOASTS = [("Order #142 → kitchen ✓", "Sent the second it was taken"), ("Table 7 paid ₹1,240", "Bill closed · cash matched"),
          ("Paneer running low", "Tap to reorder before tonight"), ("Today's sales ₹48,250", "Up 18% vs last Saturday")]
TOAST_T = [0.25, 1.05, 1.85, 2.65]

def soundtrack(path, t_s2, t_rew, t_s4, t_end, total):
    src = src_audio(); mix = np.zeros(int(total * SR) + SR)
    def put(a, b, at, g=1.0, fade=0.06):
        seg = src[int(a * SR):int(b * SR)].copy(); n = int(fade * SR)
        seg[:n] *= np.linspace(0, 1, n); seg[-n:] *= np.linspace(1, 0, n); st.add(mix, seg, at, g)
    put(*S1, 0); put(*S2, t_s2)
    # tape rewind: rising warbly squeal + hiss, then a clunk
    tt = np.arange(int(REW * SR)) / SR; f = 400 + 2600 * tt / REW + 120 * np.sin(2 * np.pi * 9 * tt)
    squeal = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.35 + st.band(st.noise(REW), 2000, 9000) * 0.25
    st.add(mix, squeal * np.minimum(1, tt / 0.05), t_rew); st.add(mix, st.kick() * 0.8, t_s4 - 0.02)
    at = t_s4
    for a, b in S4: put(a, b, at, 0.8); at += b - a
    for k, tt0 in enumerate(TOAST_T):   # two-tone notification ping
        for j, m in enumerate((88, 95)): st.add(mix, st.pluck(st.note(m), 0.35, 2) * 0.5, t_s4 + tt0 + j * 0.09)
    # end card: lo-fi Rhodes chords + soft beat + printer chatter + bell
    dur = total - t_end; chords = [(53, 57, 60, 64), (52, 55, 59, 62), (50, 53, 57, 60), (48, 52, 55, 59)]
    for i in range(int(dur / 1.4) + 1):
        for m in chords[i % 4]:
            tt = np.arange(int(1.4 * SR)) / SR
            x = np.sin(2 * np.pi * st.note(m) * tt) * (1 + 0.3 * np.sin(2 * np.pi * 5 * tt)) * np.exp(-tt / 1.2)
            st.add(mix, x * 0.07, t_end + i * 1.4)
        st.add(mix, st.kick() * 0.35, t_end + i * 1.4); st.add(mix, st.clap() * 0.12, t_end + i * 1.4 + 0.7)
    st.add(mix, st.band(st.noise(dur), 3000, 10000) * 0.02, t_end)       # vinyl hiss
    for i in range(len(RECEIPT)):
        for c in range(6): st.add(mix, st.band(st.noise(0.012), 1500, 6000) * 0.25, t_end + i * LINE_T + c * 0.022)
    bell_t = t_end + len(RECEIPT) * LINE_T + 0.3
    st.add(mix, st.pluck(st.note(96), 1.0, 3) * 0.5, bell_t); st.add(mix, st.pluck(st.note(103), 1.0, 3) * 0.35, bell_t + 0.05)
    st.finish(mix, path, total)

if __name__ == "__main__":
    t_s2 = S1[1] - S1[0]; t_rew = t_s2 + (S2[1] - S2[0]); t_s4 = t_rew + REW
    s4_len = sum(b - a for a, b in S4); t_end = t_s4 + s4_len; total = t_end + END
    wav = OUT[:-4] + ".wav"; soundtrack(wav, t_s2, t_rew, t_s4, t_end, total)
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
        "-r", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", OUT], stdin=subprocess.PIPE)
    def emit(img): ff.stdin.write(img.tobytes())
    # 1) us before the rush
    for i, fr in enumerate(src_frames(*S1)):
        erase(fr, BAND_CHILL); label(fr, "Us before the rush", "😌", 1142, i / FPS); emit(fr)
    # 2) chaos, relabelled
    chaos_keep = []
    for i, fr in enumerate(src_frames(*S2)):
        erase(fr, BAND_CHAOS)
        if i % 3 == 0: chaos_keep.append(fr.copy())
        label(fr, "Restaurants WITHOUT Smart Serve\nduring the rush", "😵", 1092, i / FPS, bg=(230, 40, 40), fg=WHITE); emit(fr)
    # 3) rewind: chaos backwards, fast
    n = int(REW * FPS)
    for k in range(n):
        fr = chaos_keep[max(0, len(chaos_keep) - 1 - int(k * len(chaos_keep) / n))].copy(); vhs(fr, k / n, k); emit(fr)
    # 4) us during the rush, with Smart Serve
    t = 0.0
    for a, b in S4:
        for fr in src_frames(a, b):
            erase(fr, BAND_CHILL)
            shown = [i for i, tt in enumerate(TOAST_T) if t >= tt][-2:]   # newest two stay on screen
            for slot, i in enumerate(reversed(shown)):
                toast(fr, 170 + slot * 175, *TOASTS[i], t - TOAST_T[i] if slot == 0 else 1.0)
            label(fr, "Us during the rush\nwith Smart Serve", "😎", 1142, t, bg=BLUE, fg=WHITE); emit(fr)
            t += 1 / FPS
    # 5) receipt end card
    for i in range(int(END * FPS)):
        img = Image.new("RGB", (W, H)); end_card(img, i / FPS); emit(img)
    ff.stdin.close(); ff.wait(); os.remove(wav)
    print("done", OUT, round(total, 2))
