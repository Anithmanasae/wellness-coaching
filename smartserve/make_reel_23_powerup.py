# Smart Serve Reel #23 - "being a restaurant owner is not an easy job" -> cooking-game punchline,
# turned into a game: achievement toast -> pixelate -> arcade "POWER-UP UNLOCKED" end card.
# Usage: python3 make_reel_23_powerup.py <clip.mp4>
import math, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import soundtrack as st
from make_photo_memes import emoji_img

SRC = sys.argv[1]
OUT = os.path.join(HERE, "smartserve_reel_23_powerup.mp4")
W, H, FPS, SR = 1080, 1920, 30, 44100
F = "/usr/share/fonts/opentype/inter/"
def font(sz, w="Bold"): return ImageFont.truetype(F + f"Inter-{w}.otf", sz)
def arcade(sz): return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", sz)
WHITE, BLACK, GREEN, YEL = (255, 255, 255), (0, 0, 0), (60, 230, 120), (255, 214, 0)
LOGO = Image.open(os.path.join(HERE, "assets", "logo.png")).convert("RGBA")
def clamp(x): return max(0.0, min(1.0, x))
def ease(x): x = clamp(x); return 1 - (1 - x) ** 3

CUT = 9.6                 # setup (0-5s) + ~4.6s of the game
TOAST_T = 7.4             # achievement pops over the game
PIX = 0.5                 # pixelate-out length at the end of the clip
END = 6.4

def pixelate(img, k):
    if k <= 0: return img
    s = max(1, int(1 + k * 60))
    return img.resize((W // s, H // s), Image.NEAREST).resize((W, H), Image.NEAREST)

def achievement(img, t):
    if t < 0: return
    a = ease(t / 0.3) if t < 1.7 else 1 - ease((t - 1.7) / 0.3)
    if a <= 0: return
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    y = 1380 + int(140 * (1 - a)); x0, x1 = 90, W - 90
    d.rounded_rectangle([x0, y, x1, y + 170], 85, fill=(20, 22, 26, int(235 * a)), outline=(60, 230, 120, int(255 * a)), width=5)
    d.ellipse([x0 + 22, y + 22, x0 + 148, y + 148], fill=(60, 230, 120, int(255 * a)))
    tro = emoji_img("🏆", 76); lay.paste(tro, (x0 + 43, y + 46), tro)
    d.text((x0 + 175, y + 32), "ACHIEVEMENT UNLOCKED", font=font(30, "Bold"), fill=(170, 175, 185, int(255 * a)))
    d.text((x0 + 175, y + 76), "Found Smart Serve", font=font(56, "Black"), fill=(255, 255, 255, int(255 * a)))
    img.paste(lay, (0, 0), lay)

STATS = [("ORDER SPEED", "▲", 0.92, GREEN), ("MISSED ORDERS", "▼", 0.08, GREEN), ("STRESS", "▼", 0.1, GREEN), ("PROFIT", "▲", 0.95, GREEN)]
def end_card(img, t):
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, H], fill=(22, 10, 48))
    for k in range(0, W, 40): d.line([k, 0, k, H], fill=(34, 18, 70))
    for k in range(0, H, 40): d.line([0, k, W, k], fill=(34, 18, 70))
    cx, cy = W / 2, 560
    rays = Image.new("RGBA", (W, H), (0, 0, 0, 0)); rd = ImageDraw.Draw(rays)
    for k in range(16):
        a = math.radians(k * 22.5 + t * 40)
        rd.polygon([(cx, cy), (cx + math.cos(a - .08) * 900, cy + math.sin(a - .08) * 900),
                    (cx + math.cos(a + .08) * 900, cy + math.sin(a + .08) * 900)], fill=(120, 60, 255, 70))
    img.paste(rays, (0, 0), rays); d = ImageDraw.Draw(img)
    f = arcade(78); txt = "POWER-UP"; w = d.textlength(txt, font=f)
    blink = YEL if int(t * 6) % 2 or t > 1.2 else WHITE
    d.text(((W - w) / 2, 150), txt, font=f, fill=blink, stroke_width=6, stroke_fill=(120, 40, 0))
    txt = "UNLOCKED!"; w = d.textlength(txt, font=f); d.text(((W - w) / 2, 245), txt, font=f, fill=blink, stroke_width=6, stroke_fill=(120, 40, 0))
    # power-up box with the icon, bobbing
    sc = 0.3 + 0.7 * ease(t / 0.4) + 0.08 * math.sin(clamp(t / 0.4) * math.pi); bob = 12 * math.sin(t * 4)
    s = int(300 * sc)
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse([cx - 230, cy - 230 + bob, cx + 230, cy + 230 + bob], fill=(255, 220, 90, 120))
    glow = glow.filter(ImageFilter.GaussianBlur(50)); img.paste(glow, (0, 0), glow); d = ImageDraw.Draw(img)
    d.rectangle([cx - s / 2 - 22, cy - s / 2 - 22 + bob, cx + s / 2 + 22, cy + s / 2 + 22 + bob], fill=(255, 214, 0))
    d.rectangle([cx - s / 2 - 10, cy - s / 2 - 10 + bob, cx + s / 2 + 10, cy + s / 2 + 10 + bob], fill=(150, 80, 0))
    l = LOGO.resize((max(1, s), max(1, s)), Image.LANCZOS); img.paste(l, (int(cx - s / 2), int(cy - s / 2 + bob)), l)
    d = ImageDraw.Draw(img)
    # stat bars
    for i, (name, arrow, val, col) in enumerate(STATS):
        st0 = 0.8 + i * 0.35
        if t < st0: continue
        y = 840 + i * 105; fv = ease((t - st0) / 0.5) * val
        d.text((120, y), name, font=arcade(40), fill=WHITE)
        d.text((W - 160, y - 6), arrow, font=font(52, "Black"), fill=col)
        bx0, bx1 = 120, W - 200
        d.rectangle([bx0, y + 52, bx1, y + 80], fill=(50, 30, 90))
        for c in range(int((bx1 - bx0) * fv / 30)):
            d.rectangle([bx0 + c * 30 + 3, y + 55, bx0 + c * 30 + 27, y + 77], fill=col)
    if t > 2.6:
        a = ease((t - 2.6) / 0.3); f4 = font(50, "Black"); txt = 'Comment "APP" for the app\'s name'; w = d.textlength(txt, font=f4)
        on = int(t * 2.5) % 2 == 0 or t < 3.2
        d.rounded_rectangle([(W - w) / 2 - 30, 1310, (W + w) / 2 + 30, 1400], 18, fill=GREEN if on else (40, 170, 90))
        d.text(((W - w) / 2, 1322), txt, font=f4, fill=(5, 30, 15))
        f5 = arcade(34); txt = "FREE ON PLAY STORE · LINK IN BIO"; w = d.textlength(txt, font=f5)
        d.text(((W - w) / 2, 1430), txt, font=f5, fill=(200, 190, 255))
    if t < 0.3:  # pixel-in from the transition
        img.paste(pixelate(img.copy(), 1 - t / 0.3))

def sq(freq, dur, duty=0.5, vol=1.0):
    tt = np.arange(int(dur * SR)) / SR
    return (((tt * freq) % 1) < duty).astype(float) * 2 - 1, tt

def soundtrack(path, total):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-t", str(CUT), "-i", SRC, "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"],
                         capture_output=True).stdout
    src = np.frombuffer(raw, np.int16).astype(np.float64) / 32768
    mix = np.zeros(int(total * SR) + SR); n = int(PIX * SR); src = src.copy(); src[-n:] *= np.linspace(1, 0, n)
    st.add(mix, src, 0)
    for j, m in enumerate((76, 79, 84, 88)):                      # achievement chime
        x, tt = sq(st.note(m), 0.16, 0.25); st.add(mix, x * np.exp(-tt / 0.12) * 0.18, TOAST_T + j * 0.07)
    tt = np.arange(int(PIX * SR)) / SR                            # pixelate whoosh down
    x = np.sign(np.sin(2 * np.pi * np.cumsum(1200 * np.exp(-tt * 4)) / SR)); st.add(mix, x * 0.12, CUT - PIX)
    t0 = CUT
    for j, m in enumerate(range(60, 85, 3)):                       # power-up arpeggio
        x, tt = sq(st.note(m), 0.07, 0.5); st.add(mix, x * 0.16, t0 + j * 0.045)
    # chiptune loop for the end card
    mel = (72, 76, 79, 76, 74, 77, 81, 77, 72, 76, 79, 84, 83, 79, 76, 74)
    bass = (48, 48, 53, 53, 55, 55, 48, 48)
    for k in range(int((total - t0 - 0.4) / 0.15)):
        at = t0 + 0.4 + k * 0.15
        x, tt = sq(st.note(mel[k % 16]), 0.13, 0.25); st.add(mix, x * np.exp(-tt / 0.1) * 0.10, at)
        if k % 2 == 0: x, tt = sq(st.note(bass[(k // 2) % 8]), 0.28, 0.5); st.add(mix, x * np.exp(-tt / 0.25) * 0.08, at)
        if k % 4 == 0: st.add(mix, st.kick() * 0.3, at)
        if k % 4 == 2: st.add(mix, st.band(st.noise(0.05), 3000, 9000) * np.exp(-np.arange(int(0.05 * SR)) / SR / 0.015) * 0.2, at)
    for i in range(len(STATS)):                                   # stat bar fills
        for c in range(6): x, tt = sq(st.note(84 + c), 0.03); st.add(mix, x * 0.06, t0 + 0.8 + i * 0.35 + c * 0.06)
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
        achievement(fr, t - TOAST_T)
        if t > CUT - PIX: fr = pixelate(fr, (t - (CUT - PIX)) / PIX)
        ff.stdin.write(fr.tobytes()); i += 1
    p.wait()
    for k in range(int(END * FPS)):
        img = Image.new("RGB", (W, H)); end_card(img, k / FPS); ff.stdin.write(img.tobytes())
    ff.stdin.close(); ff.wait(); os.remove(wav)
    # match the other reels' loudness
    tmp = OUT[:-4] + "_tmp.mp4"; os.replace(OUT, tmp)
    out = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", tmp, "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True).stderr
    gain = -13.5 - float(out.split("Summary:")[1].split("I:")[1].split("LUFS")[0])
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", tmp, "-c:v", "copy", "-af", f"volume={gain:.2f}dB,alimiter=limit=0.9",
                    "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", OUT], check=True); os.remove(tmp)
    print("done", OUT, total)
