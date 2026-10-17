# Smart Serve Reel #24 - "Restaurant owners: before / after opening restaurant" (phone scene),
# with the calls he's getting shown as bubbles, a PLOT TWIST freeze, the happy scene relabelled
# "after opening + Smart Serve", and an incoming-call end card ("Smart Serve is calling…").
# Usage: python3 make_reel_24_calls.py <clip.mp4>
import math, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import soundtrack as st
from make_photo_memes import emoji_img
from make_reel_variations import scene_cta_comment

SRC = sys.argv[1]
OUT = os.path.join(HERE, "smartserve_reel_24_calls.mp4")
W, H, FPS, SR = 1080, 1920, 30, 44100
F = "/usr/share/fonts/opentype/inter/"
def font(sz, w="Bold"): return ImageFont.truetype(F + f"Inter-{w}.otf", sz)
WHITE, BLACK, GREEN, RED, YEL = (255, 255, 255), (0, 0, 0), (52, 199, 89), (255, 59, 48), (255, 214, 0)
LOGO = Image.open(os.path.join(HERE, "assets", "logo.png")).convert("RGBA")
def clamp(x): return max(0.0, min(1.0, x))
def ease(x): x = clamp(x); return 1 - (1 - x) ** 3

SEG1 = (0.0, 3.8)        # before opening (original caption)
SEG2 = (7.3, 12.8)       # after opening - crying on the phone (original caption)
TWIST = 1.3              # freeze + plot twist
SEG4 = (0.2, 3.8)        # happy planning again, relabelled
END = 6.4
VIDEO_BOTTOM = 1250      # source video area ends here (black bar below)
CALLS = ["Sir, Swiggy order cancelled again", "Sir, cash is ₹3,000 short today",
         "Sir, paneer is over… nobody told us", "Sir, the chef didn't come today"]
CALL_T = [0.3, 1.5, 2.7, 3.9]

def frames(a, b):
    p = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-ss", str(a), "-t", str(b - a), "-i", SRC,
        "-vf", f"fps={FPS},scale={W}:{H}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    n = W * H * 3
    while True:
        buf = p.stdout.read(n)
        if len(buf) < n: break
        yield Image.frombytes("RGB", (W, H), buf)
    p.wait()

def bubble(img, txt, y, t):
    a = ease(t / 0.25); d = ImageDraw.Draw(img)
    f = font(42, "SemiBold"); w = d.textlength(txt, font=f)
    x0 = 70; yy = y + int(30 * (1 - a))
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ld = ImageDraw.Draw(lay)
    ld.rounded_rectangle([x0, yy, x0 + w + 70, yy + 120], 36, fill=(44, 44, 48, int(255 * a)))
    ld.text((x0 + 35, yy + 14), "MANAGER · on call", font=font(26, "Bold"), fill=(255, 120, 110, int(255 * a)))
    ld.text((x0 + 35, yy + 52), txt, font=f, fill=(255, 255, 255, int(255 * a)))
    img.paste(lay, (0, 0), lay)

def new_caption(img):
    d = ImageDraw.Draw(img); d.rectangle([0, 270, W, 640], fill=BLACK)
    f = font(66, "Medium")
    for y, txt in ((290, "Restaurant Owners:"), (395, "After Opening Restaurant")):
        w = d.textlength(txt, font=f); d.text(((W - w) / 2, y), txt, font=f, fill=WHITE)
    f2 = font(72, "Black"); txt = "+ Smart Serve"; e = emoji_img("😎", 74); w = d.textlength(txt, font=f2) + e.width + 16
    x = (W - w) / 2; d.text((x, 500), txt, font=f2, fill=YEL); img.paste(e, (int(x + w - e.width), 506), e)

def calm_lines(img, t):
    d = ImageDraw.Draw(img)
    for i, txt in enumerate(["✓ every order reached the kitchen", "✓ cash matched to the rupee", "✓ low stock flagged in time"]):
        st0 = 0.4 + i * 0.7
        if t < st0: continue
        a = ease((t - st0) / 0.25); y = 1330 + i * 105 + int(20 * (1 - a))
        f = font(44, "Bold"); w = d.textlength(txt, font=f)
        d.rounded_rectangle([70, y, 70 + w + 60, y + 84], 30, fill=(20, 70, 40))
        d.text((100, y + 16), txt, font=f, fill=(140, 255, 170))

def twist(img, last, t):
    g = ImageOps.grayscale(last).convert("RGB")
    z = 1 + 0.08 * ease(t / TWIST); cw, ch = W / z, H / z
    g = g.crop((int((W - cw) / 2), int((H - ch) / 2), int((W + cw) / 2), int((H + ch) / 2))).resize((W, H))
    img.paste(g); d = ImageDraw.Draw(img)
    if t > 0.15:
        s = 1 + 0.4 * (1 - ease((t - 0.15) / 0.2))
        f = font(int(120 * s), "Black"); txt = "PLOT TWIST"; w = d.textlength(txt, font=f)
        d.text(((W - w) / 2, 820 - 60 * s), txt, font=f, fill=YEL, stroke_width=10, stroke_fill=BLACK)
    if t > 0.55:
        f = font(66, "Black"); txt = "he got Smart Serve"; w = d.textlength(txt, font=f)
        d.rounded_rectangle([(W - w) / 2 - 30, 980, (W + w) / 2 + 30, 1080], 26, fill=WHITE)
        d.text(((W - w) / 2, 994), txt, font=f, fill=BLACK)

def end_card(img, t):
    """incoming-call screen from Smart Serve."""
    bg = Image.new("RGB", (W, H)); d = ImageDraw.Draw(bg)
    for y in range(H):
        k = y / H; d.line([0, y, W, y], fill=(int(20 + 15 * k), int(40 + 20 * k), int(110 - 50 * k)))
    img.paste(bg); d = ImageDraw.Draw(img)
    f = font(40, "Medium"); txt = "incoming call…"; w = d.textlength(txt, font=f); d.text(((W - w) / 2, 250), txt, font=f, fill=(200, 210, 240))
    f = font(84, "Black"); txt = "Smart Serve"; w = d.textlength(txt, font=f); d.text(((W - w) / 2, 310), txt, font=f, fill=WHITE)
    f = font(38, "Medium"); txt = "your restaurant's new manager"; w = d.textlength(txt, font=f); d.text(((W - w) / 2, 420), txt, font=f, fill=(200, 210, 240))
    cx, cy = W / 2, 760
    for k in range(3):  # pulsing rings
        ph = ((t * 0.9) + k / 3) % 1
        r = 170 + ph * 230; a = int(120 * (1 - ph))
        ring = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(ring).ellipse([cx - r, cy - r, cx + r, cy + r], outline=(255, 255, 255, a), width=6)
        img.paste(ring, (0, 0), ring)
    d = ImageDraw.Draw(img)
    d.ellipse([cx - 175, cy - 175, cx + 175, cy + 175], fill=WHITE)
    wob = 6 * math.sin(t * 40) if (t % 1.2) < 0.5 else 0
    l = LOGO.resize((300, 300), Image.LANCZOS).rotate(wob, resample=Image.BICUBIC)
    img.paste(l, (int(cx - 150), int(cy - 150)), l); d = ImageDraw.Draw(img)
    # decline / accept
    for x, col, lab in ((W / 2 - 240, RED, "Decline"), (W / 2 + 240, GREEN, "Accept")):
        y = 1170 + (int(10 * math.sin(t * 8)) if lab == "Accept" else 0)
        d.ellipse([x - 85, y - 85, x + 85, y + 85], fill=col)
        d.rounded_rectangle([x - 40, y - 14, x + 40, y + 14], 14, fill=WHITE)
        f = font(34, "SemiBold"); w = d.textlength(lab, font=f); d.text((x - w / 2, y + 100), lab, font=f, fill=WHITE)
    if t > 1.6:
        a = ease((t - 1.6) / 0.3)
        f4 = font(50, "Black"); txt = 'Comment "APP" for the app\'s name'; w = d.textlength(txt, font=f4)
        d.rounded_rectangle([(W - w) / 2 - 30, 1410 + int(20 * (1 - a)), (W + w) / 2 + 30, 1500 + int(20 * (1 - a))], 24, fill=GREEN)
        d.text(((W - w) / 2, 1422 + int(20 * (1 - a))), txt, font=f4, fill=(5, 30, 15))
        f5 = font(36, "SemiBold"); txt = "free on Play Store · link in bio"; w = d.textlength(txt, font=f5)
        d.text(((W - w) / 2, 1530), txt, font=f5, fill=(200, 215, 255))

def soundtrack(path, marks, total):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", SRC, "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"], capture_output=True).stdout
    src = np.frombuffer(raw, np.int16).astype(np.float64) / 32768
    mix = np.zeros(int(total * SR) + SR)
    def put(a, b, at, g=1.0):
        seg = src[int(a * SR):int(b * SR)].copy(); n = int(0.05 * SR)
        seg[:n] *= np.linspace(0, 1, n); seg[-n:] *= np.linspace(1, 0, n); st.add(mix, seg * g, at)
    t1, t2, t3, t4 = marks
    put(*SEG1, 0); put(*SEG2, t1)
    for c in CALL_T:                                   # phone buzz for each bad call
        tt = np.arange(int(0.22 * SR)) / SR
        st.add(mix, np.sin(2 * np.pi * 180 * tt) * (np.sin(2 * np.pi * 30 * tt) > 0) * 0.25, t1 + c)
    st.add(mix, st.sfx_scratch() * 0.6, t2); st.add(mix, st.sfx_impact() * 0.8, t2 + 0.15)
    put(*SEG4, t3, 0.9)
    for i in range(3):
        for j, m in enumerate((84, 91)): st.add(mix, st.pluck(st.note(m), 0.3, 2) * 0.3, t3 + 0.4 + i * 0.7 + j * 0.07)
    # standard CTA audio: transition sound effect, then ka-ching + music
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", os.path.join(HERE, "assets", "cta_transition_sfx.wav"),
                          "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"], capture_output=True).stdout
    fx = np.frombuffer(raw, np.int16).astype(np.float64) / 32768; st.add(mix, fx, t4)
    m0 = t4 + len(fx) / SR - 0.1
    st.add(mix, st.music_uplift(total - m0), m0)
    for at, name in ((0.2, "kaching"), (0.05, "sparkle"), (0.6, "pop")):
        fn, g = st.SFX[name]; st.add(mix, fn(), m0 + at, g)
    st.finish(mix, path, total)

if __name__ == "__main__":
    l1, l2, l4 = SEG1[1] - SEG1[0], SEG2[1] - SEG2[0], SEG4[1] - SEG4[0]
    t1 = l1; t2 = t1 + l2; t3 = t2 + TWIST; t4 = t3 + l4; total = t4 + END
    wav = OUT[:-4] + ".wav"; soundtrack(wav, (t1, t2, t3, t4), total)
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
        "-r", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", OUT], stdin=subprocess.PIPE)
    emit = lambda im: ff.stdin.write(im.tobytes())
    for fr in frames(*SEG1): emit(fr)
    last = None
    for i, fr in enumerate(frames(*SEG2)):
        t = i / FPS; shown = [k for k, c in enumerate(CALL_T) if t >= c]
        for slot, k in enumerate(shown[-3:]):   # newest at the bottom, max 3 on screen
            bubble(fr, CALLS[k], VIDEO_BOTTOM + 30 + slot * 130, t - CALL_T[k] if k == shown[-1] else 1)
        emit(fr); last = fr
    for i in range(int(TWIST * FPS)):
        img = Image.new("RGB", (W, H)); twist(img, last, i / FPS); emit(img)
    for i, fr in enumerate(frames(*SEG4)):
        new_caption(fr); calm_lines(fr, i / FPS); emit(fr)
    for i in range(int(END * FPS)):
        img = Image.new("RGB", (W, H)); scene_cta_comment(img, i / FPS); emit(img)
    ff.stdin.close(); ff.wait(); os.remove(wav)
    tmp = OUT[:-4] + "_tmp.mp4"; os.replace(OUT, tmp)
    out = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", tmp, "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True).stderr
    gain = -13.5 - float(out.split("Summary:")[1].split("I:")[1].split("LUFS")[0])
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", tmp, "-c:v", "copy", "-af", f"volume={gain:.2f}dB,alimiter=limit=0.9",
                    "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", OUT], check=True); os.remove(tmp)
    print("done", OUT, round(total, 2))
