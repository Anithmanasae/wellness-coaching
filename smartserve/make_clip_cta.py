# Any meme clip -> dissolve -> scannable Smart Serve "Comment APP" CTA.
# The clip plays untouched (its own audio). As the CTA opens, the transition sound effect from
# Reel #15 (assets/cta_transition_sfx.wav) plays, then our CTA music takes over.
# Non-vertical clips are centred on a blurred copy of themselves to fill 9:16.
# Usage: python3 make_clip_cta.py <clip.mp4> <name> [reel_number] [cut_seconds]
import os, random, subprocess, sys
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import soundtrack as st
from make_reel_variations import W, H, FPS, scene_cta_comment

SRC, NAME = sys.argv[1], sys.argv[2]
NUM = int(sys.argv[3]) if len(sys.argv) > 3 else 16
DUR = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", SRC]))
CUT = float(sys.argv[4]) if len(sys.argv) > 4 else DUR   # where the clip hands over to the CTA
OUT = os.path.join(HERE, f"smartserve_reel_{NUM:02d}_clip_{NAME}.mp4")
SFX = os.path.join(HERE, "assets", "cta_transition_sfx.wav")
SFX_LEN = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", SFX]))
XFADE = 0.8

def gain_to(target=-14.0):
    """dB gain that brings the clip's integrated loudness to the target (fixed gain, no lookahead)."""
    out = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-t", str(CUT), "-i", SRC, "-af", "ebur128", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    i = float(out.split("Summary:")[1].split("I:")[1].split("LUFS")[0])
    return target - i

CTA_LEN = 6.8

def cta_audio(path):
    mix = st.np.zeros(int(CTA_LEN * st.SR) + st.SR)
    t0 = SFX_LEN - 0.1                       # our sound starts once the transition effect has played
    st.add(mix, st.music_uplift(CTA_LEN - t0), t0)
    for at, name in ((0.2, "kaching"), (0.05, "sparkle"), (0.6, "pop")):
        fn, g = st.SFX[name]; st.add(mix, fn(), t0 + at, g)
    st.finish(mix, path, CTA_LEN)

if __name__ == "__main__":
    base = OUT[:-4]; cta_wav, cta_mp4 = base + "_cta.wav", base + "_cta.mp4"
    cta_audio(cta_wav)
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", cta_wav,
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-ar", "44100", "-ac", "2", "-shortest", cta_mp4], stdin=subprocess.PIPE)
    random.seed(NUM)
    for i in range(int(CTA_LEN * FPS)):
        img = Image.new("RGB", (W, H)); scene_cta_comment(img, i / FPS); ff.stdin.write(img.tobytes())
    ff.stdin.close(); ff.wait()
    off = CUT - XFADE
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-t", str(CUT), "-i", SRC, "-i", cta_mp4, "-i", SFX, "-filter_complex",
        # clip on a blurred 9:16 fill of itself
        f"[0:v]fps={FPS},split[c1][c2];"
        f"[c1]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},gblur=sigma=40,eq=brightness=-0.08[bg];"
        f"[c2]scale={W}:-2[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1[v0];"
        f"[1:v]setsar=1,fps={FPS}[v1];"
        f"[v0][v1]xfade=transition=fade:duration={XFADE}:offset={off}[v];"
        f"[0:a]aresample=44100,aformat=channel_layouts=stereo,volume={gain_to():.2f}dB,alimiter=limit=0.89,afade=t=out:st={off}:d={XFADE}[a0];"
        f"[2:a]aformat=channel_layouts=stereo:sample_rates=44100,adelay={int(off * 1000)}:all=1[fx];"
        f"[1:a]aformat=channel_layouts=stereo:sample_rates=44100,adelay={int(off * 1000)}:all=1[a1];"
        "[a0][fx][a1]amix=inputs=3:duration=longest:normalize=0[a]",
        "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-t", str(off + CTA_LEN), "-movflags", "+faststart", OUT], check=True)
    for f in (cta_wav, cta_mp4): os.remove(f)
    print("done", OUT)
