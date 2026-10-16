# Smart Serve Reel #14 - video meme: the original clip played as-is (its own Tamil captions + audio)
# -> LOUD "WAIT." interrupt -> question bar -> standard Smart Serve CTA.
# Usage: python3 make_reel_14_video_meme.py <source_video.mp4> [output_name]
import os, random, subprocess, sys
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import soundtrack as st
from make_reel_variations import W, H, FPS, caption, scene_question, scene_cta, shake, ease, WHITE

SRC = sys.argv[1]
NAME = sys.argv[2] if len(sys.argv) > 2 else "biryani"
OUT = os.path.join(HERE, f"smartserve_reel_14_videomeme_{NAME}.mp4")

def interrupt(img, t):
    strobe = int(t * 14) % 2
    bg, fg = ((230, 20, 20), WHITE) if strobe else (WHITE, (230, 20, 20))
    ImageDraw.Draw(img).rectangle([0, 0, W, H], fill=bg)
    caption(img, "WAIT.", 900, 300, fg, scale=1.6 - 0.6 * ease(t / 0.15))
    caption(img, "restaurant owners!!", 1200, 90, fg)
    shake(img, 28)

TAIL = [(interrupt, 1.0), (scene_question("restaurant owners, do you know where your money went today??"), 2.0), (scene_cta, 6.0)]
TAIL_LEN = sum(d for _, d in TAIL)

def tail_audio(path):
    mix = st.np.zeros(int(TAIL_LEN * st.SR) + st.SR)
    st.add(mix, st.sfx_impact(), 0, 1.0)
    for k in range(3): st.add(mix, st.sfx_airhorn(), k * 0.33, 1.0)
    st.add(mix, st.sfx_siren(), 0, .45)
    st.add(mix, st.music_glitch(2.0), 1.0)
    st.add(mix, st.sfx_whoosh(), 2.75, .5)
    st.add(mix, st.music_uplift(TAIL_LEN - 3.0), 3.0)
    for at, name in ((3.0, "impact"), (3.2, "kaching"), (3.05, "sparkle"), (3.6, "pop")):
        fn, g = st.SFX[name]; st.add(mix, fn(), at, g)
    st.finish(mix, path, TAIL_LEN)

if __name__ == "__main__":
    base = OUT[:-4]; tail_wav, tail_mp4 = base + "_tail.wav", base + "_tail.mp4"
    tail_audio(tail_wav)
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", tail_wav,
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-ar", "44100", "-ac", "2", "-shortest", tail_mp4], stdin=subprocess.PIPE)
    random.seed(14)
    for fn, dur in TAIL:
        for i in range(int(dur * FPS)):
            img = Image.new("RGB", (W, H)); fn(img, i / FPS); ff.stdin.write(img.tobytes())
    ff.stdin.close(); ff.wait()
    # original clip untouched (scaled to 1080x1920, its own audio loudness-matched) + our tail
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", SRC, "-i", tail_mp4, "-filter_complex",
        f"[0:v]scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2,fps={FPS},setsar=1[v0];"
        "[0:a]aresample=44100,aformat=channel_layouts=stereo,loudnorm=I=-14:TP=-1.5[a0];"
        "[1:v]setsar=1[v1];[1:a]aformat=channel_layouts=stereo[a1];"
        "[v0][a0][v1][a1]concat=n=2:v=1:a=1[v][a]",
        "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", OUT], check=True)
    os.remove(tail_wav); os.remove(tail_mp4)
    print("done", OUT)
