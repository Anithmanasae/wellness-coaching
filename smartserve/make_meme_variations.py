# Smart Serve Reels #9-#12 - variations of the Reel #8 format:
# original two-panel food meme -> LOUD "WAIT." interrupt -> question bar -> standard Smart Serve CTA.
# Usage: python3 make_meme_variations.py [9 10 11 12]   (default: all)
import math, os, random, subprocess, sys
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import soundtrack as st
from make_reel_variations import W, H, FPS, font, caption, scene_question, scene_cta, shake, ease, pop, BLACK, WHITE
from make_reel_08_meme import meme_text, coin

PANEL = H // 2
BROWN = (60, 25, 10)

# ---------------- faces ----------------
def face(d, cx, cy, s, mood, t):
    def E(x0, y0, x1, y1, **k): d.ellipse([cx + x0 * s, cy + y0 * s, cx + x1 * s, cy + y1 * s], **k)
    lw = max(4, int(s * .05))
    if mood == "cool":
        d.rounded_rectangle([cx - .62 * s, cy - .2 * s, cx - .08 * s, cy + .04 * s], 10, fill=(15, 15, 20))
        d.rounded_rectangle([cx + .08 * s, cy - .2 * s, cx + .62 * s, cy + .04 * s], 10, fill=(15, 15, 20))
        d.line([cx - .1 * s, cy - .12 * s, cx + .1 * s, cy - .12 * s], fill=(15, 15, 20), width=lw)
        d.line([cx + .2 * s, cy - .15 * s, cx + .5 * s, cy - .18 * s], fill=WHITE, width=5)
        d.arc([cx - .3 * s, cy - .02 * s, cx + .35 * s, cy + .2 * s], 10, 170, fill=BROWN, width=lw)
    elif mood in ("sad", "panic", "fresh"):
        pr = .04 if mood == "panic" else .07
        for ex in (-.33, .33):
            E(ex - .16, -.22, ex + .16, .08, fill=WHITE, outline=BROWN, width=3)
            E(ex - pr, -.1 - pr, ex + pr, -.1 + pr, fill=BLACK)
            if mood == "fresh": E(ex - .02, -.16, ex + .03, -.11, fill=WHITE)
        if mood == "sad":
            for ex, sg in ((-.33, 1), (.33, -1)):
                d.line([cx + (ex - .2) * s, cy - .3 * s + 12 * sg, cx + (ex + .2) * s, cy - .3 * s - 12 * sg], fill=BROWN, width=8)
            d.arc([cx - .25 * s, cy + .08 * s, cx + .25 * s, cy + .34 * s], 200, 340, fill=BROWN, width=lw)
            for k in range(2):
                ty = (t * 380 + k * 140) % 260
                for ex in (-.33, .33):
                    x = cx + ex * s; y = cy + .1 * s + ty
                    d.ellipse([x - 12, y - 18, x + 12, y + 14], fill=(90, 170, 255))
        elif mood == "panic":
            E(-.13, .1, .13, .38, fill=BROWN)
            for k in range(3):  # flying sweat
                a = t * 9 + k * 2.1; x = cx + (.7 + .1 * math.sin(a)) * s * (1 if k % 2 else -1); y = cy - .45 * s + (t * 300 + k * 60) % 120
                d.ellipse([x - 13, y - 20, x + 13, y + 14], fill=(110, 190, 255))
        else:
            d.chord([cx - .28 * s, cy + .02 * s, cx + .28 * s, cy + .34 * s], 0, 180, fill=BROWN)
            d.ellipse([cx - .12 * s, cy + .16 * s, cx + .12 * s, cy + .3 * s], fill=(240, 110, 110))
    elif mood == "angel":
        for ex in (-.33, .33): d.arc([cx + (ex - .15) * s, cy - .18 * s, cx + (ex + .15) * s, cy + .02 * s], 200, 340, fill=BROWN, width=lw)
        d.arc([cx - .25 * s, cy, cx + .25 * s, cy + .26 * s], 20, 160, fill=BROWN, width=lw)
        for ex in (-.5, .5): E(ex - .1, .02, ex + .1, .12, fill=(255, 160, 170))
    elif mood == "sneaky":
        for ex in (-.33, .33):
            E(ex - .16, -.18, ex + .16, .06, fill=WHITE, outline=BROWN, width=3)
            d.rectangle([cx + (ex - .17) * s, cy - .19 * s, cx + (ex + .17) * s, cy - .07 * s], fill=BROWN)  # heavy lids
            E(ex + .04, -.06, ex + .14, .04, fill=BLACK)                                                       # side-eye
        d.arc([cx - .3 * s, cy - .05 * s, cx + .3 * s, cy + .25 * s], 15, 120, fill=BROWN, width=lw)            # sly grin
    elif mood == "moldy":
        for ex in (-.33, .33):
            x, y, r = cx + ex * s, cy - .08 * s, .1 * s
            d.line([x - r, y - r, x + r, y + r], fill=BROWN, width=lw); d.line([x - r, y + r, x + r, y - r], fill=BROWN, width=lw)
        pts = [(cx + (-.28 + k * .08) * s, cy + (.2 + .05 * (-1) ** k) * s) for k in range(8)]
        d.line(pts, fill=BROWN, width=lw)
        E(.02, .24, .14, .4, fill=(120, 200, 80))  # tongue out

# ---------------- bodies ----------------
def body_coffee(img, cx, cy, s, t, sad):
    d = ImageDraw.Draw(img)
    d.arc([cx + .6 * s, cy - .3 * s, cx + 1.15 * s, cy + .45 * s], 270, 90, fill=(240, 240, 240), width=int(.14 * s))
    d.polygon([(cx - .85 * s, cy - .6 * s), (cx + .85 * s, cy - .6 * s), (cx + .62 * s, cy + .85 * s), (cx - .62 * s, cy + .85 * s)], fill=(250, 250, 250))
    d.rectangle([cx - .8 * s, cy + .35 * s, cx + .8 * s, cy + .5 * s], fill=(24, 63, 191))
    d.ellipse([cx - .85 * s, cy - .75 * s, cx + .85 * s, cy - .45 * s], fill=(160, 100, 55))
    d.ellipse([cx - .3 * s, cy - .68 * s, cx + .3 * s, cy - .52 * s], fill=(245, 225, 200))  # latte art
    if sad:
        d.line([(cx - .5 * s, cy - .55 * s), (cx - .3 * s, cy - .2 * s), (cx - .45 * s, cy + .1 * s), (cx - .25 * s, cy + .4 * s)], fill=(90, 90, 90), width=6)
        for k in range(3):  # storm cloud instead of steam
            d.ellipse([cx - .7 * s + k * .45 * s, cy - 1.45 * s, cx - .1 * s + k * .45 * s, cy - .95 * s], fill=(90, 95, 110))
        if int(t * 5) % 4 == 0:
            d.line([(cx + .1 * s, cy - 1.0 * s), (cx - .05 * s, cy - .82 * s), (cx + .1 * s, cy - .8 * s)], fill=(255, 230, 80), width=8)
    else:
        for k in range(3):
            x = cx + (k - 1) * .35 * s
            d.line([(x + 15 * math.sin(t * 6 + j * .8 + k), cy - .85 * s - j * 30) for j in range(8)], fill=(255, 255, 255), width=8)
    face(d, cx, cy - .05 * s, s * .8, "sad" if sad else "cool", t)

def body_pizza(img, cx, cy, s, t, panic):
    d = ImageDraw.Draw(img)
    d.polygon([(cx - 1.0 * s, cy - .75 * s), (cx + 1.0 * s, cy - .75 * s), (cx, cy + 1.05 * s)], fill=(255, 200, 70))
    d.rounded_rectangle([cx - 1.08 * s, cy - .98 * s, cx + 1.08 * s, cy - .66 * s], int(.16 * s), fill=(214, 140, 60))
    for (x, y) in ((-.55, -.45), (.5, -.4), (0, .45), (-.2, -.5), (.25, .1)):
        d.ellipse([cx + (x - .13) * s, cy + (y - .13) * s, cx + (x + .13) * s, cy + (y + .13) * s], fill=(200, 50, 40))
    for x in (-.7, .1, .6): d.rounded_rectangle([cx + x * s, cy - .7 * s, cx + (x + .1) * s, cy - .45 * s], 12, fill=(255, 200, 70))
    face(d, cx, cy - .2 * s, s * .62, "panic" if panic else "cool", t)

def body_chai(img, cx, cy, s, t, sneaky):
    d = ImageDraw.Draw(img)
    if not sneaky:  # halo
        d.ellipse([cx - .5 * s, cy - 1.35 * s, cx + .5 * s, cy - 1.1 * s], outline=(255, 220, 90), width=14)
    d.polygon([(cx - .72 * s, cy - .9 * s), (cx + .72 * s, cy - .9 * s), (cx + .55 * s, cy + .9 * s), (cx - .55 * s, cy + .9 * s)], fill=(225, 240, 245))
    d.polygon([(cx - .66 * s, cy - .55 * s), (cx + .66 * s, cy - .55 * s), (cx + .53 * s, cy + .85 * s), (cx - .53 * s, cy + .85 * s)], fill=(196, 128, 60))
    for k in range(-3, 4): d.line([cx + k * .17 * s, cy - .85 * s, cx + k * .14 * s, cy + .85 * s], fill=(235, 245, 250), width=5)
    face(d, cx, cy + .05 * s, s * .62, "sneaky" if sneaky else "angel", t)
    if sneaky:  # arm stuffing cash in pocket
        d.line([cx + .55 * s, cy + .2 * s, cx + .95 * s, cy + .45 * s], fill=BROWN, width=12)
        lay = Image.new("RGBA", (190, 95), (0, 0, 0, 0)); ld = ImageDraw.Draw(lay)
        ld.rectangle([0, 0, 189, 94], fill=(170, 140, 190), outline=(90, 70, 110), width=4)
        ld.text((40, 18), "₹500", font=font(40, "Black"), fill=(70, 50, 90))
        lay = lay.rotate(25 + 8 * math.sin(t * 8), expand=True)
        img.paste(lay, (int(cx + .85 * s), int(cy + .25 * s)), lay)

def body_paneer(img, cx, cy, s, t, moldy):
    d = ImageDraw.Draw(img)
    top, side, front = ((236, 232, 205), (205, 200, 170), (250, 247, 230)) if not moldy else ((190, 200, 150), (150, 165, 110), (205, 212, 165))
    d.polygon([(cx - .8 * s, cy - .55 * s), (cx - .45 * s, cy - .9 * s), (cx + 1.0 * s, cy - .9 * s), (cx + .65 * s, cy - .55 * s)], fill=top)
    d.polygon([(cx + .65 * s, cy - .55 * s), (cx + 1.0 * s, cy - .9 * s), (cx + 1.0 * s, cy + .55 * s), (cx + .65 * s, cy + .9 * s)], fill=side)
    d.rectangle([cx - .8 * s, cy - .55 * s, cx + .65 * s, cy + .9 * s], fill=front)
    if moldy:
        rnd = random.Random(4)
        for _ in range(16):
            x, y, r = cx + rnd.uniform(-.75, .9) * s, cy + rnd.uniform(-.8, .85) * s, rnd.uniform(.05, .12) * s
            d.ellipse([x - r, y - r, x + r, y + r], fill=(95, 130, 60))
    face(d, cx - .07 * s, cy + .1 * s, s * .62, "moldy" if moldy else "fresh", t)

# ---------------- backgrounds / particles ----------------
def gradient(d, c0, c1, h=PANEL):
    for y in range(h):
        k = y / h; d.line([0, y, W, y], fill=tuple(int(c0[i] + (c1[i] - c0[i]) * k) for i in range(3)))

def particles(img, kind, t, seed):
    d = ImageDraw.Draw(img); rnd = random.Random(seed)
    if kind == "coins":
        for _ in range(14):
            x = rnd.randint(60, W - 60); y = (rnd.uniform(0, PANEL) + t * rnd.uniform(500, 800)) % (PANEL + 80) - 40; coin(d, x, y)
    elif kind == "sparkles":
        for _ in range(26):
            x, y = rnd.randint(30, W - 30), rnd.randint(260, PANEL - 30); r = 10 + 8 * abs(math.sin(t * 5 + rnd.random() * 6))
            d.polygon([(x, y - r), (x + r / 4, y), (x, y + r), (x - r / 4, y)], fill=WHITE); d.polygon([(x - r, y), (x, y + r / 4), (x + r, y), (x, y - r / 4)], fill=WHITE)
    elif kind == "rain":
        for _ in range(60):
            x = rnd.randint(0, W); y = (rnd.uniform(0, PANEL) + t * 1400) % PANEL; d.line([x, y, x - 8, y + 40], fill=(150, 165, 185), width=3)
    elif kind == "tickets":
        for _ in range(9):
            x = rnd.randint(40, W - 160); y = (rnd.uniform(0, PANEL) + t * rnd.uniform(300, 600)) % (PANEL + 200) - 150
            d.rectangle([x, y, x + 110, y + 160], fill=(255, 245, 215), outline=(150, 140, 120), width=3)
            d.text((x + 10, y + 10), "KOT", font=font(30, "Black"), fill=(200, 40, 40))
    elif kind == "alarm":
        if int(t * 6) % 2: d.rectangle([0, 0, W, PANEL], outline=(255, 40, 40), width=30)
    elif kind == "notes":
        for _ in range(10):
            x = rnd.randint(40, W - 200); y = (rnd.uniform(0, PANEL) - t * rnd.uniform(250, 450)) % (PANEL + 100) - 60
            d.rectangle([x, y, x + 150, y + 72], fill=(170, 140, 190), outline=(90, 70, 110), width=3)
            d.text((x + 28, y + 14), "₹500", font=font(32, "Black"), fill=(70, 50, 90))
    elif kind == "flies":
        for k in range(6):
            a = t * (4 + k) + k; x = W / 2 + math.cos(a) * (260 + 40 * k); y = 560 + math.sin(a * 1.3) * (200 + 20 * k)
            d.ellipse([x - 12, y - 9, x + 12, y + 9], fill=(20, 20, 20))
            d.ellipse([x - 16, y - 22, x - 2, y - 6], fill=(200, 220, 230)); d.ellipse([x + 2, y - 22, x + 16, y - 6], fill=(200, 220, 230))
        rnd2 = random.Random(9)
        for _ in range(5):  # stink lines
            x = rnd2.randint(250, 830); d.line([(x + 14 * math.sin(t * 5 + j), 300 - j * 22) for j in range(6)], fill=(140, 170, 90), width=6)

# ---------------- variations ----------------
MEMES = {
    9: dict(name="cafe", body=body_coffee,
            top=("me opening my\naesthetic café", (255, 190, 200), (250, 140, 170), "sparkles"),
            bottom=("me 6 months later\nchecking the numbers", (60, 65, 80), "rain"),
            tag="loss: ₹60,000/month", shout="café owners!!", sound="trombone",
            question="café owners, do you know your real numbers??"),
    10: dict(name="pizza_rush", body=body_pizza,
             top=("me when 40 tables\nare full on saturday", (255, 215, 80), (255, 150, 40), "coins"),
             bottom=("me when the kitchen\nloses 3 orders", (120, 20, 25), "tickets"),
             tag="table 7 walked out", shout="restaurant owners!!", sound="panic",
             question="how many orders did your kitchen lose this weekend??"),
    11: dict(name="cashier", body=body_chai,
             top=("the cashier when\nyou're at the counter", (170, 220, 255), (120, 180, 250), "sparkles"),
             bottom=("the cashier when\nyou leave early", (40, 30, 50), "notes"),
             tag="6 bills \"cancelled\"", shout="restaurant owners!!", sound="sneaky",
             question="when did you last check your cancelled bills??"),
    12: dict(name="paneer", body=body_paneer,
             top=("paneer on\nday 1", (190, 240, 200), (120, 210, 150), "sparkles"),
             bottom=("paneer on day 9\nbecause nobody checked", (60, 75, 45), "flies"),
             tag="₹12,000 in the bin", shout="restaurant owners!!", sound="trombone",
             question="do you know what's expiring in your kitchen right now??"),
}
T_LOSE = 2.4

def make_scenes(m):
    def scene_meme(img, t):
        txt, c0, c1, part = m["top"]
        top = Image.new("RGB", (W, PANEL)); gradient(ImageDraw.Draw(top), c0, c1); particles(top, part, t, 1)
        bob = abs(math.sin(t * math.pi * 4)) * 40
        m["body"](top, W / 2, 600 - bob, 230, t, False); meme_text(top, txt, 40)
        img.paste(top, (0, 0))
        ImageDraw.Draw(img).rectangle([0, PANEL, W, H], fill=(20, 20, 24))
        if t >= T_LOSE:
            txt, bg, part = m["bottom"]
            sub = Image.new("RGB", (W, PANEL), bg); particles(sub, part, t, 2)
            jit = (random.randint(-6, 6) if m["sound"] == "panic" else 0)
            m["body"](sub, W / 2 + jit, 600, 230, t, True); meme_text(sub, txt, 40, 60)
            if t - T_LOSE > 1.2:
                s_ = pop(t, T_LOSE + 1.2); d = ImageDraw.Draw(sub)
                f = font(int(70 * s_) or 1, "Black"); w = d.textlength(m["tag"], font=f)
                d.rounded_rectangle([(W - w) / 2 - 28, 830, (W + w) / 2 + 28, 925], 18, fill=(220, 30, 30))
                d.text(((W - w) / 2, 836), m["tag"], font=f, fill=WHITE)
            img.paste(sub, (0, PANEL + int(PANEL * (1 - ease((t - T_LOSE) / 0.18)))))
        ImageDraw.Draw(img).rectangle([0, PANEL - 6, W, PANEL + 6], fill=BLACK)

    def scene_interrupt(img, t):
        strobe = int(t * 14) % 2
        bg, fg = ((230, 20, 20), WHITE) if strobe else (WHITE, (230, 20, 20))
        ImageDraw.Draw(img).rectangle([0, 0, W, H], fill=bg)
        caption(img, "WAIT.", 900, 300, fg, scale=1.6 - 0.6 * ease(t / 0.15))
        caption(img, m["shout"], 1200, 90, fg)
        shake(img, 28)

    return [(scene_meme, 5.0), (scene_interrupt, 1.0), (scene_question(m["question"]), 2.0), (scene_cta, 6.0)]

def music_sneaky(dur):
    out = st.np.zeros(int(dur * st.SR)); seq = (40, 43, 45, 46, 45, 43, 40, 38)
    for k in range(int(dur / (st.BEAT / 2)) + 1):
        st.add(out, st.pluck(st.note(seq[k % 8]), 0.16, 4), k * st.BEAT / 2, .45)
        if k % 2 == 0: st.add(out, st.hat(), k * st.BEAT / 2, .08)
    return out

def music_panic(dur):
    out = st.np.zeros(int(dur * st.SR)); k = 0
    while k * 0.125 < dur:
        st.add(out, st.hat(), k * 0.125, .15)
        if k % 4 == 0: st.add(out, st.kick(), k * 0.125, .6); st.add(out, st.kick(), k * 0.125 + 0.14, .4)  # heartbeat
        k += 1
    st.add(out, st.sfx_siren(min(dur, 2.4)), 0.3, .12)
    return out

def build_audio(path, m, scenes):
    total = sum(d for _, d in scenes)
    c_int = scenes[0][1]; c_q = c_int + scenes[1][1]; c_cta = c_q + scenes[2][1]
    mix = st.np.zeros(int(total * st.SR) + st.SR)
    st.add(mix, st.music_happy(T_LOSE), 0)
    st.add(mix, st.sfx_scratch(), T_LOSE - 0.05, .5)
    if m["sound"] == "trombone":
        st.add(mix, st.sfx_sad_trombone(), T_LOSE + 0.15, .9)
        if m["bottom"][2] == "rain": st.add(mix, st.sfx_rain(c_int - T_LOSE), T_LOSE, .5)
        if m["bottom"][2] == "flies": st.add(mix, st.sfx_buzz(c_int - T_LOSE) * 0.25, T_LOSE, .5)
    elif m["sound"] == "sneaky": st.add(mix, music_sneaky(c_int - T_LOSE), T_LOSE + 0.1)
    else: st.add(mix, music_panic(c_int - T_LOSE), T_LOSE + 0.05)
    st.add(mix, st.sfx_impact(), T_LOSE + 1.2, .6)
    st.add(mix, st.sfx_impact(), c_int, 1.0)
    for k in range(3): st.add(mix, st.sfx_airhorn(), c_int + k * 0.33, 1.0)
    st.add(mix, st.sfx_siren(), c_int, .45)
    st.add(mix, st.music_glitch(scenes[2][1]), c_q)
    st.add(mix, st.sfx_whoosh(), c_cta - 0.25, .5)
    st.add(mix, st.music_uplift(total - c_cta), c_cta)
    for at, name in ((c_cta, "impact"), (c_cta + 0.2, "kaching"), (c_cta + 0.05, "sparkle"), (c_cta + 0.6, "pop")):
        fn, g = st.SFX[name]; st.add(mix, fn(), at, g)
    st.finish(mix, path, total)
    return total

def render(num):
    m = MEMES[num]; scenes = make_scenes(m)
    out = os.path.join(HERE, f"smartserve_reel_{num:02d}_meme_{m['name']}.mp4"); wav = out[:-4] + ".wav"
    build_audio(wav, m, scenes)
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
    for n in ([int(a) for a in sys.argv[1:]] or sorted(MEMES)): render(n)
