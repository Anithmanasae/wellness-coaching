# Smart Serve Reel #15 - existing meme clip with its caption swapped for our line,
# black ending trimmed, then the standard Smart Serve CTA.
# Usage: python3 make_reel_15_reels_meme.py <source_video.mp4>
import os, random, subprocess, sys
from PIL import Image, ImageDraw, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import soundtrack as st
from make_reel_variations import W, H, FPS, font, scene_cta, WHITE, BLACK

SRC = sys.argv[1]
OUT = os.path.join(HERE, "smartserve_reel_15_reelsmeme_get_to_work.mp4")
CUT = 7.8                         # source turns black here
CAP_ON = 4.3                      # source caption appears here
BAND = (210, 1230, 870, 1400)     # source caption area, in 1080x1920 output pixels (x0, y0, x1, y1)
NEW_CAPTION = ["DON'T WASTE YOUR TIME ON REELS", "INSTEAD GET TO WORK ON", "YOUR RESTAURANT BUSINESS"]
CTA_LEN = 6.8                     # includes the dissolve overlap
XFADE = 0.8                       # dissolve length, matched to the source's own transition
SFX_SRC = (7.9, 8.98)             # the source's end sound effect, replayed as the CTA opens
SFX_LEN = SFX_SRC[1] - SFX_SRC[0]

def erase_caption(img):
    """remove the burnt-in white caption: mask its bright pixels and diffuse the surroundings into the holes."""
    x0, y0, x1, y1 = BAND
    band = img.crop(BAND)
    g = band.convert("L").point(lambda v: 255 if v > 200 else 0)
    mask = g.filter(ImageFilter.MaxFilter(9))
    fill = band.copy()
    for _ in range(10):
        fill = Image.composite(fill.filter(ImageFilter.GaussianBlur(6)), band, mask)
    img.paste(fill, (x0, y0))

def draw_caption(img, lines):
    d = ImageDraw.Draw(img); f = font(54, "ExtraBold"); lh = 64
    yc = (BAND[1] + BAND[3]) / 2 - 10
    y0 = yc - lh * len(lines) / 2
    for i, ln in enumerate(lines):
        w = d.textlength(ln, font=f)
        d.text(((W - w) / 2, y0 + i * lh), ln, font=f, fill=WHITE, stroke_width=4, stroke_fill=BLACK)

def source_frames():
    p = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-t", str(CUT), "-i", SRC,
        "-vf", f"fps={FPS},scale={W}:{H}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    n = W * H * 3
    while True:
        buf = p.stdout.read(n)
        if len(buf) < n: break
        yield Image.frombytes("RGB", (W, H), buf)
    p.wait()

def cta_audio(path):
    """our CTA sound starts once the source's end sound effect has played."""
    mix = st.np.zeros(int(CTA_LEN * st.SR) + st.SR)
    t0 = SFX_LEN - 0.1
    st.add(mix, st.music_uplift(CTA_LEN - t0), t0)
    for at, name in ((0.2, "kaching"), (0.05, "sparkle"), (0.6, "pop")):
        fn, g = st.SFX[name]; st.add(mix, fn(), t0 + at, g)
    st.finish(mix, path, CTA_LEN)

if __name__ == "__main__":
    base = OUT[:-4]; hook_mp4, cta_wav, cta_mp4 = base + "_hook.mp4", base + "_cta.wav", base + "_cta.mp4"
    # 1) hook: source video with our caption, original audio kept
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-t", str(CUT), "-i", SRC, "-map", "0:v", "-map", "1:a",
        "-af", "aresample=44100,aformat=channel_layouts=stereo,loudnorm=I=-14:TP=-1.5",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", hook_mp4],
        stdin=subprocess.PIPE)
    for i, fr in enumerate(source_frames()):
        if i / FPS >= CAP_ON - 0.02:
            erase_caption(fr); draw_caption(fr, NEW_CAPTION)
        ff.stdin.write(fr.tobytes())
    ff.stdin.close(); ff.wait()
    # 2) Smart Serve CTA
    cta_audio(cta_wav)
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", cta_wav,
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-ar", "44100", "-ac", "2", "-shortest", cta_mp4], stdin=subprocess.PIPE)
    random.seed(15)
    for i in range(int(CTA_LEN * FPS)):
        img = Image.new("RGB", (W, H)); scene_cta(img, i / FPS); ff.stdin.write(img.tobytes())
    ff.stdin.close(); ff.wait()
    # 3) join
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", hook_mp4, "-i", cta_mp4, "-i", SRC, "-filter_complex",
        "[0:v]setsar=1,fps=30[v0];[1:v]setsar=1,fps=30[v1];[0:a]aformat=channel_layouts=stereo:sample_rates=44100[a0];"
        "[1:a]aformat=channel_layouts=stereo:sample_rates=44100[a1];"
        # same soft dissolve the source uses between its dance clip and the photo
        f"[v0][v1]xfade=transition=fade:duration={XFADE}:offset={CUT - XFADE}[v];"
        # source audio fades under the dissolve; its end sound effect plays as the CTA opens, then our CTA audio
        f"[a0]afade=t=out:st={CUT - XFADE}:d={XFADE}[a0f];"
        f"[2:a]atrim={SFX_SRC[0]}:{SFX_SRC[1]},asetpts=PTS-STARTPTS,aresample=44100,aformat=channel_layouts=stereo,"
        f"loudnorm=I=-14:TP=-1.5,adelay={int((CUT - XFADE) * 1000)}:all=1[fx];"
        f"[a1]adelay={int((CUT - XFADE) * 1000)}:all=1[a1d];"
        "[a0f][fx][a1d]amix=inputs=3:duration=longest:normalize=0[a]",
        "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-t", str(CUT - XFADE + CTA_LEN), "-movflags", "+faststart", OUT], check=True)
    for f in (hook_mp4, cta_wav, cta_mp4): os.remove(f)
    print("done", OUT)
