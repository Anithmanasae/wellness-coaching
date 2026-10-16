# One-off: cut the "guys with books" photo section out of the Reel #15 source, with our
# "get to work on your restaurant business" caption burnt in, as a reusable clip
# (assets/getwork_photo.mp4, with the source's audio under it).
# Usage: python3 make_getwork_asset.py <reel15_source.mp4>
import os, subprocess, sys
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from make_reel_15_reels_meme import erase_caption, draw_caption, NEW_CAPTION
from make_reel_variations import W, H, FPS

SRC = sys.argv[1]
START, END = 5.2, 7.8            # photo fully on screen, before the source goes black
A_START = 4.3                    # take the song from where the caption first appears
HOLD = START - A_START           # hold the first photo frame this long so video matches the audio
OUT = os.path.join(HERE, "assets", "getwork_photo.mp4")

p = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-ss", str(START), "-t", str(END - START), "-i", SRC,
    "-vf", f"fps={FPS},scale={W}:{H}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
    "-r", str(FPS), "-i", "-", "-ss", str(A_START), "-t", str(END - A_START), "-i", SRC, "-map", "0:v", "-map", "1:a",
    "-vf", f"tpad=start_duration={HOLD}:start_mode=clone",
    "-af", "aresample=44100,aformat=channel_layouts=stereo",
    "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
    "-shortest", OUT], stdin=subprocess.PIPE)
n = W * H * 3
while True:
    buf = p.stdout.read(n)
    if len(buf) < n: break
    fr = Image.frombytes("RGB", (W, H), buf); erase_caption(fr); draw_caption(fr, NEW_CAPTION)
    ff.stdin.write(fr.tobytes())
ff.stdin.close(); ff.wait(); p.wait()
print("done", OUT)
