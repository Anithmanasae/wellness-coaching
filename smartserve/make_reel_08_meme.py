# Smart Serve Reel #8 - food meme -> LOUD pattern interrupt -> standard Smart Serve CTA.
# Original two-panel meme: a cartoon burger "after 300 orders" vs "after paying everyone".
import math, os, random, subprocess, sys
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import soundtrack as st
from make_reel_variations import (W, H, FPS, font, caption, scene_question, scene_cta, shake, ease, pop, BLACK, WHITE)

OUT = os.path.join(HERE, "smartserve_reel_08_meme.mp4")
PANEL = H // 2

def meme_text(img, txt, y, sz=66):
    d = ImageDraw.Draw(img); f = font(sz, "Black")
    for i, ln in enumerate(txt.split("\n")):
        w = d.textlength(ln, font=f)
        d.text(((W - w) / 2, y + i * sz * 1.12), ln, font=f, fill=WHITE, stroke_width=7, stroke_fill=BLACK)

def burger(img, cx, cy, s, mood, t):
    """cartoon burger character. mood: 'cool' or 'sad'."""
    d = ImageDraw.Draw(img)
    sx, sy = (1.12, 0.78) if mood == "sad" else (1.0, 1.0)
    def R(x0, y0, x1, y1): return [cx + x0 * s * sx, cy + y0 * s * sy, cx + x1 * s * sx, cy + y1 * s * sy]
    d.rounded_rectangle(R(-1.0, .55, 1.0, .9), int(18 * s / 100), fill=(214, 140, 60))           # bottom bun
    d.rounded_rectangle(R(-1.05, .3, 1.05, .6), int(30 * s / 100), fill=(110, 58, 30))           # patty
    d.polygon([(cx - 1.05 * s * sx, cy + .28 * s * sy), (cx + 1.05 * s * sx, cy + .28 * s * sy),
               (cx + .6 * s * sx, cy + .5 * s * sy), (cx + .3 * s * sx, cy + .38 * s * sy),
               (cx - .2 * s * sx, cy + .55 * s * sy), (cx - .6 * s * sx, cy + .38 * s * sy)], fill=(255, 200, 40))  # cheese
    for k in range(8):                                                                           # lettuce
        x = -1.08 + k * .27; d.ellipse(R(x, .14, x + .3, .34), fill=(90, 190, 70))
    d.chord(R(-1.05, -.85, 1.05, .45), 180, 360, fill=(232, 160, 70))                            # top bun
    d.rectangle(R(-1.05, -.21, 1.05, .2), fill=(232, 160, 70))
    for (x, y) in ((-.6, -.55), (-.2, -.7), (.25, -.62), (.6, -.45), (0, -.4), (-.45, -.3)):
        d.ellipse(R(x - .06, y - .03, x + .06, y + .03), fill=(255, 245, 220))                   # sesame
    if mood == "cool":
        d.rounded_rectangle(R(-.62, -.22, -.08, .02), 10, fill=(15, 15, 20))
        d.rounded_rectangle(R(.08, -.22, .62, .02), 10, fill=(15, 15, 20))
        d.line([cx - .1 * s, cy - .14 * s, cx + .1 * s, cy - .14 * s], fill=(15, 15, 20), width=int(s * .06))
        d.line([cx + .2 * s * sx, cy - .17 * s, cx + .5 * s * sx, cy - .2 * s], fill=(255, 255, 255), width=5)  # glint
        d.arc(R(-.3, -.05, .35, .16), 10, 170, fill=(60, 25, 10), width=int(s * .05))             # smirk
    else:
        for ex in (-.35, .35):
            d.ellipse(R(ex - .16, -.2, ex + .16, .06), fill=WHITE)
            d.ellipse(R(ex - .07, -.08, ex + .07, .05), fill=BLACK)
            d.line([cx + (ex - .2) * s * sx, cy - .28 * s * sy + (12 if ex < 0 else -12), cx + (ex + .2) * s * sx,
                    cy - .28 * s * sy + (-12 if ex < 0 else 12)], fill=(60, 25, 10), width=8)       # worried brows
        d.arc(R(-.25, .02, .25, .3), 200, 340, fill=(60, 25, 10), width=int(s * .05))               # frown
        # sunglasses slid down and cracked
        gx, gy = cx + .1 * s, cy + .62 * s * sy
        d.rounded_rectangle([gx - .55 * s, gy, gx - .05 * s, gy + .2 * s], 10, fill=(15, 15, 20))
        d.rounded_rectangle([gx + .05 * s, gy + .04 * s, gx + .55 * s, gy + .24 * s], 10, fill=(15, 15, 20))
        d.line([gx - .45 * s, gy + .03 * s, gx - .25 * s, gy + .15 * s, gx - .15 * s, gy + .05 * s], fill=WHITE, width=4)
        for k in range(2):  # tears
            ty = (t * 380 + k * 140) % 300
            for ex in (-.35, .35):
                x = cx + ex * s * sx; y = cy + .05 * s + ty
                d.ellipse([x - 12, y - 18, x + 12, y + 14], fill=(90, 170, 255))

def coin(d, x, y, r=34):
    d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 205, 40), outline=(200, 140, 0), width=5)
    f = font(int(r * 1.1), "Black"); w = d.textlength("₹", font=f); d.text((x - w / 2, y - r * .72), "₹", font=f, fill=(170, 110, 0))

def panel_win(img, t):
    d = ImageDraw.Draw(img)
    for y in range(PANEL):  # gold gradient
        k = y / PANEL; d.line([0, y, W, y], fill=(255, int(215 - 60 * k), int(80 - 50 * k)))
    rnd = random.Random(3)
    for i in range(14):
        x = rnd.randint(60, W - 60); sp = rnd.uniform(500, 800)
        y = (rnd.uniform(0, PANEL) + t * sp) % (PANEL + 80) - 40
        coin(d, x, y)
    bob = abs(math.sin(t * math.pi * 4)) * 40
    burger(img, W / 2, 560 - bob, 230, "cool", t)
    meme_text(img, "me after 300 orders\non saturday", 40)

def panel_lose(img, t, t_in):
    sub = Image.new("RGB", (W, PANEL), (70, 80, 95)); d = ImageDraw.Draw(sub)
    rnd = random.Random(5)
    for i in range(60):  # rain
        x = rnd.randint(0, W); y = (rnd.uniform(0, PANEL) + t * 1400) % PANEL
        d.line([x, y, x - 8, y + 40], fill=(150, 165, 185), width=3)
    burger(sub, W / 2, 560, 230, "sad", t)
    meme_text(sub, "me after paying zomato,\nstaff, rent & the gas guy", 40, 60)
    if t - t_in > 1.2:
        s_ = pop(t, t_in + 1.2)
        f = font(int(78 * s_) or 1, "Black"); txt = "profit: ₹312"; w = d.textlength(txt, font=f)
        d.rounded_rectangle([(W - w) / 2 - 28, 800, (W + w) / 2 + 28, 900], 18, fill=(220, 30, 30))
        d.text(((W - w) / 2, 805), txt, font=f, fill=WHITE)
    slide = int(PANEL * (1 - ease((t - t_in) / 0.18)))
    img.paste(sub, (0, PANEL + slide))

T_LOSE = 2.4
def scene_meme(img, t):
    panel_win(img, t)
    ImageDraw.Draw(img).rectangle([0, PANEL, W, H], fill=(20, 20, 24))
    if t >= T_LOSE: panel_lose(img, t, T_LOSE)
    ImageDraw.Draw(img).rectangle([0, PANEL - 6, W, PANEL + 6], fill=BLACK)

def scene_interrupt(img, t):
    strobe = int(t * 14) % 2
    bg, fg = ((230, 20, 20), WHITE) if strobe else (WHITE, (230, 20, 20))
    ImageDraw.Draw(img).rectangle([0, 0, W, H], fill=bg)
    s = 1.6 - 0.6 * ease(t / 0.15)
    caption(img, "WAIT.", 900, 300, fg, scale=s)
    caption(img, "restaurant owners!!", 1200, 90, fg)
    shake(img, 28)

SCENES = [(scene_meme, 5.0), (scene_interrupt, 1.0),
          (scene_question("so where did all the money go??"), 1.8), (scene_cta, 6.0)]
TOTAL = sum(d for _, d in SCENES)

def soundtrack(path):
    c_int = SCENES[0][1]; c_q = c_int + SCENES[1][1]; c_cta = c_q + SCENES[2][1]
    mix = st.np.zeros(int(TOTAL * st.SR) + st.SR)
    st.add(mix, st.music_happy(T_LOSE), 0)
    st.add(mix, st.sfx_scratch(), T_LOSE - 0.05, .5)          # record stop
    st.add(mix, st.sfx_sad_trombone(), T_LOSE + 0.15, .9)
    st.add(mix, st.sfx_rain(c_int - T_LOSE), T_LOSE, .5)
    st.add(mix, st.sfx_impact(), T_LOSE + 1.2, .6)            # "profit: ₹312"
    # the loud interrupt: impact + triple air horn + siren
    st.add(mix, st.sfx_impact(), c_int, 1.0)
    for k in range(3): st.add(mix, st.sfx_airhorn(), c_int + k * 0.33, 1.0)
    st.add(mix, st.sfx_siren(), c_int, .45)
    st.add(mix, st.music_glitch(SCENES[2][1]), c_q)
    st.add(mix, st.sfx_whoosh(), c_cta - 0.25, .5)
    st.add(mix, st.music_uplift(TOTAL - c_cta), c_cta)
    for at, name in ((c_cta, "impact"), (c_cta + 0.2, "kaching"), (c_cta + 0.05, "sparkle"), (c_cta + 0.6, "pop")):
        fn, g = st.SFX[name]; st.add(mix, fn(), at, g)
    st.finish(mix, path, TOTAL)

if __name__ == "__main__":
    wav = OUT[:-4] + ".wav"; soundtrack(wav)
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", wav,
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
        "-shortest", "-movflags", "+faststart", OUT], stdin=subprocess.PIPE)
    random.seed(8)
    for fn, dur in SCENES:
        for i in range(int(dur * FPS)):
            img = Image.new("RGB", (W, H)); fn(img, i / FPS); ff.stdin.write(img.tobytes())
    ff.stdin.close(); ff.wait(); os.remove(wav)
    print("done", OUT, TOTAL)
