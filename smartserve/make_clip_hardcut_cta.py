# Clip -> HARD CUT on a punchline frame (white flash + bonk + transition SFX) -> scannable "Comment APP" CTA.
# The clip keeps its own audio up to the cut.
# Usage: python3 make_clip_hardcut_cta.py <clip.mp4> <name> <reel_number> <cut_seconds>
import os, random, subprocess, sys
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import soundtrack as st
from make_reel_variations import W, H, FPS, scene_cta_comment

SRC, NAME, NUM, CUT = sys.argv[1], sys.argv[2], int(sys.argv[3]), float(sys.argv[4])
OUT = os.path.join(HERE, f"smartserve_reel_{NUM:02d}_clip_{NAME}.mp4")
SFX = os.path.join(HERE, "assets", "cta_transition_sfx.wav")
SFX_LEN = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", SFX]))
CTA_LEN = 6.0

def gain_to(target=-14.0):
    out = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-t", str(CUT), "-i", SRC, "-af", "ebur128", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    return target - float(out.split("Summary:")[1].split("I:")[1].split("LUFS")[0])

def cta_audio(path):
    mix = st.np.zeros(int(CTA_LEN * st.SR) + st.SR)
    st.add(mix, st.sfx_impact() * 0.9, 0)                  # the bonk on the cut
    t0 = SFX_LEN - 0.1
    st.add(mix, st.music_uplift(CTA_LEN - t0), t0)
    for at, name in ((0.2, "kaching"), (0.05, "sparkle"), (0.6, "pop")):
        fn, g = st.SFX[name]; st.add(mix, fn(), t0 + at, g)
    st.finish(mix, path, CTA_LEN)

if __name__ == "__main__":
    base = OUT[:-4]; cta_wav, cta_mp4 = base + "_cta.wav", base + "_cta.mp4"
    cta_audio(cta_wav)
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", cta_wav, "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-ar", "44100", "-ac", "2", "-shortest", cta_mp4], stdin=subprocess.PIPE)
    random.seed(NUM)
    for i in range(int(CTA_LEN * FPS)):
        img = Image.new("RGB", (W, H)); scene_cta_comment(img, i / FPS)
        if i < 3: img = Image.blend(img, Image.new("RGB", (W, H), (255, 255, 255)), 0.85 - i * 0.3)  # impact flash
        ff.stdin.write(img.tobytes())
    ff.stdin.close(); ff.wait()
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-t", str(CUT), "-i", SRC, "-i", cta_mp4, "-i", SFX, "-filter_complex",
        f"[0:v]fps={FPS},scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2,setsar=1[v0];"
        f"[1:v]setsar=1,fps={FPS}[v1];[v0][v1]concat=n=2:v=1:a=0[v];"
        f"[0:a]aresample=44100,aformat=channel_layouts=stereo,volume={gain_to():.2f}dB,alimiter=limit=0.89,apad=whole_dur={CUT}[a0];"
        f"[1:a]aformat=channel_layouts=stereo:sample_rates=44100,adelay={int(CUT * 1000)}:all=1[a1];"
        f"[2:a]aformat=channel_layouts=stereo:sample_rates=44100,adelay={int(CUT * 1000)}:all=1[fx];"
        "[a0][a1][fx]amix=inputs=3:duration=longest:normalize=0[a]",
        "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-t", str(CUT + CTA_LEN), "-movflags", "+faststart", OUT], check=True)
    for f in (cta_wav, cta_mp4): os.remove(f)
    print("done", OUT)
