# Smart Serve photo-meme reels: classic meme (caption bar + photo + pop-in labels + dramatic zoom)
# -> LOUD "WAIT." interrupt -> question bar -> standard Smart Serve CTA.
# Add a new meme by dropping its photo in assets/memes/ and adding an entry to PHOTO_MEMES.
# Usage: python3 make_photo_memes.py [13 ...]   (default: all)
import math, os, random, subprocess, sys
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import soundtrack as st
from make_reel_variations import W, H, FPS, font, caption, scene_question, scene_cta, shake, ease, pop, BLACK, WHITE
from make_meme_variations import music_sneaky

EMOJI_FONT = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"
CAP_Y, CAP_H = 230, 430          # caption bar
PHOTO_Y = CAP_Y + CAP_H          # photo starts right under it

PHOTO_MEMES = {
    13: dict(name="cat_stretch", photo="cat_stretch.png",
             caption="When you're running the kitchen AND the cash counter on a Saturday night",
             emoji="😐😑",
             # labels: (text, x, y) in source-photo pixels, shown one after another
             labels=[("THE\nKITCHEN", 130, 250), ("THE CASH\nCOUNTER", 575, 545), ("ME, THE\nOWNER", 390, 335)],
             zoom_to=(440, 210),  # dramatic zoom target (source-photo pixels)
             shout="restaurant owners!!",
             question="who's watching the cash while you're in the kitchen??"),
}

LABEL_T0, LABEL_GAP = 0.9, 0.7

def emoji_img(chars, size):
    f = ImageFont.truetype(EMOJI_FONT, 109)
    tiles = []
    for ch in chars:
        im = Image.new("RGBA", (136, 128), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((0, 0), ch, font=f, embedded_color=True)
        tiles.append(im.resize((int(size * 136 / 128), size), Image.LANCZOS))
    out = Image.new("RGBA", (sum(t.width for t in tiles) + 6 * len(tiles), size), (0, 0, 0, 0))
    x = 0
    for t in tiles: out.paste(t, (x, 0), t); x += t.width + 6
    return out

def caption_bar(img, text, emoji):
    d = ImageDraw.Draw(img); d.rectangle([0, CAP_Y, W, PHOTO_Y], fill=WHITE)
    f = font(70, "SemiBold"); lines = []; maxw = W - 100
    for word in text.split():
        if lines and d.textlength(lines[-1] + " " + word, font=f) <= maxw: lines[-1] += " " + word
        else: lines.append(word)
    lh = 90; y0 = CAP_Y + (CAP_H - lh * len(lines)) / 2 - 10
    for i, ln in enumerate(lines): d.text((55, y0 + i * lh), ln, font=f, fill=(25, 25, 25))
    if emoji:
        e = emoji_img(emoji, 70); last = lines[-1]
        x = 55 + d.textlength(last, font=f) + 16
        if x + e.width > W - 40: x, y = 55, y0 + len(lines) * lh
        else: y = y0 + (len(lines) - 1) * lh + 8
        img.paste(e, (int(x), int(y)), e)

def meme_label(img, txt, x, y, s):
    if s <= 0: return
    f = font(int(72 * s), "Black"); d = ImageDraw.Draw(img)
    lines = txt.split("\n"); lh = int(72 * s * 1.08)
    half = max(d.textlength(ln, font=f) for ln in lines) / 2 + 20
    x = min(max(x, half), W - half)  # keep labels inside the frame
    for i, ln in enumerate(lines):
        w = d.textlength(ln, font=f)
        d.text((x - w / 2, y - lh * len(lines) / 2 + i * lh), ln, font=f, fill=WHITE, stroke_width=8, stroke_fill=BLACK)

def make_scenes(m):
    photo = Image.open(os.path.join(HERE, "assets", "memes", m["photo"])).convert("RGB")
    k = W / photo.width; ph = int(photo.height * k)
    base = photo.resize((W, ph), Image.LANCZOS)
    t_zoom = LABEL_T0 + LABEL_GAP * len(m["labels"]) - 0.2
    zx, zy = m["zoom_to"][0] * k, m["zoom_to"][1] * k

    def scene_meme(img, t):
        ImageDraw.Draw(img).rectangle([0, 0, W, H], fill=BLACK)
        # slow push-in, then a snap zoom onto the face
        z = 1 + 0.04 * t / t_zoom
        if t >= t_zoom: z = 1.04 + 1.1 * ease((t - t_zoom) / 0.12)
        cx = W / 2 + (zx - W / 2) * min(1, max(0, (t - t_zoom) / 0.12)) if t >= t_zoom else W / 2
        cy = ph / 2 + (zy - ph / 2) * min(1, max(0, (t - t_zoom) / 0.12)) if t >= t_zoom else ph / 2
        cw, ch = W / z, ph / z
        x0 = min(max(cx - cw / 2, 0), W - cw); y0 = min(max(cy - ch / 2, 0), ph - ch)
        frame = base.crop((int(x0), int(y0), int(x0 + cw), int(y0 + ch))).resize((W, ph), Image.LANCZOS)
        img.paste(frame, (0, PHOTO_Y))
        if t < t_zoom:
            for i, (txt, lx, ly) in enumerate(m["labels"]):
                meme_label(img, txt, lx * k, PHOTO_Y + ly * k, pop(t, LABEL_T0 + i * LABEL_GAP))
        else:
            shake(img, 10 if t - t_zoom < 0.3 else 0)
            meme_label(img, m["labels"][-1][0], W / 2, PHOTO_Y + ph - 160, 1.2)
        caption_bar(img, m["caption"], m["emoji"])

    def scene_interrupt(img, t):
        strobe = int(t * 14) % 2
        bg, fg = ((230, 20, 20), WHITE) if strobe else (WHITE, (230, 20, 20))
        ImageDraw.Draw(img).rectangle([0, 0, W, H], fill=bg)
        caption(img, "WAIT.", 900, 300, fg, scale=1.6 - 0.6 * ease(t / 0.15))
        caption(img, m["shout"], 1200, 90, fg)
        shake(img, 28)

    meme_len = t_zoom + 1.4
    return [(scene_meme, meme_len), (scene_interrupt, 1.0), (scene_question(m["question"]), 2.0), (scene_cta, 6.0)], t_zoom

def build_audio(path, m, scenes, t_zoom):
    total = sum(d for _, d in scenes)
    c_int = scenes[0][1]; c_q = c_int + scenes[1][1]; c_cta = c_q + scenes[2][1]
    mix = st.np.zeros(int(total * st.SR) + st.SR)
    st.add(mix, music_sneaky(t_zoom), 0, .8)                       # comedic tiptoe bed
    for i in range(len(m["labels"])): st.add(mix, st.sfx_pop(), LABEL_T0 + i * LABEL_GAP, .6)
    st.add(mix, st.sfx_whoosh(0.2), t_zoom - 0.1, .5)
    st.add(mix, st.sfx_impact(), t_zoom, 1.0)                      # dramatic zoom "boom"
    st.add(mix, st.sfx_impact(), c_int, 1.0)
    for k in range(3): st.add(mix, st.sfx_airhorn(), c_int + k * 0.33, 1.0)
    st.add(mix, st.sfx_siren(), c_int, .45)
    st.add(mix, st.music_glitch(scenes[2][1]), c_q)
    st.add(mix, st.sfx_whoosh(), c_cta - 0.25, .5)
    st.add(mix, st.music_uplift(total - c_cta), c_cta)
    for at, name in ((c_cta, "impact"), (c_cta + 0.2, "kaching"), (c_cta + 0.05, "sparkle"), (c_cta + 0.6, "pop")):
        fn, g = st.SFX[name]; st.add(mix, fn(), at, g)
    st.finish(mix, path, total)

def render(num):
    m = PHOTO_MEMES[num]; scenes, t_zoom = make_scenes(m)
    out = os.path.join(HERE, f"smartserve_reel_{num:02d}_photomeme_{m['name']}.mp4"); wav = out[:-4] + ".wav"
    build_audio(wav, m, scenes, t_zoom)
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
    for n in ([int(a) for a in sys.argv[1:]] or sorted(PHOTO_MEMES)): render(n)
