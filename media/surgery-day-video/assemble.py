"""Build the surgery-day video from realistic footage clips (see shots.md).

Each scene's clips (clips/<scene>_1.mp4, <scene>_2.mp4, ...) are fitted to the scene's narration
length. Clips shorter than their share are slowed down slightly. If a scene has no clips, the
illustrated version is used. The voiceover, subtitles, step cards and music are layered on top.

Usage: python3 assemble.py <narration_dir> <clips_dir> <out_dir>
"""
import glob
import os
import subprocess
import sys

from PIL import Image

import render
from render import FPS, H, W


def clip_len(path):
    out = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                   "-of", "default=nw=1:nk=1", path])
    return float(out)


def fit_scene(clips, dur, path):
    """Concatenate clips into exactly `dur` seconds of 1920x1080 @ FPS footage."""
    share = dur / len(clips)
    inputs, filters = [], []
    for i, c in enumerate(clips):
        stretch = max(1.0, share / clip_len(c))
        inputs += ["-i", c]
        filters.append(f"[{i}:v]setpts={stretch:.4f}*(PTS-STARTPTS),fps={FPS},"
                       f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,"
                       f"trim=duration={share:.4f},setpts=PTS-STARTPTS,"
                       f"tpad=stop_mode=clone:stop_duration=1,trim=duration={share:.4f}[v{i}]")
    filters.append("".join(f"[v{i}]" for i in range(len(clips))) + f"concat=n={len(clips)}:v=1:a=0[out]")
    subprocess.check_call(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", ";".join(filters),
                           "-map", "[out]", "-an", "-c:v", "libx264", "-crf", "16", "-preset", "fast", path])


def main():
    vo_dir, clips_dir, out = sys.argv[1:4]
    os.makedirs(out, exist_ok=True)
    render.TIMELINE, render.VOICE, render.SUBS, render.TOTAL = render.build_timeline(vo_dir)
    tl = render.TIMELINE

    footage = {}
    for sid, start, dur, scene in tl:
        clips = sorted(glob.glob(os.path.join(clips_dir, f"{sid}_*.mp4")))
        if scene and clips:
            path = os.path.join(out, f"bg_{sid}.mp4")
            print(f"{sid}: fitting {len(clips)} clip(s) to {dur:.1f}s")
            fit_scene(clips, dur, path)
            footage[sid] = path
        elif scene:
            print(f"{sid}: no clips, using illustration")

    audio = os.path.join(out, "audio.wav")
    render.build_audio(render.VOICE, render.TOTAL, audio)
    render.write_srt(render.SUBS, os.path.join(out, "surgery-day.en.srt"))
    video = os.path.join(out, "surgery-day-realistic.mp4")
    enc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                            "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", audio,
                            "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
                            "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-shortest",
                            "-movflags", "+faststart", video], stdin=subprocess.PIPE)
    n = 0
    total = int(render.TOTAL * FPS)
    frame_bytes = W * H * 3
    for sid, start, dur, scene in tl:
        last = total if sid == "end" else int(round((start + dur) * FPS))
        dec = None
        if sid in footage:
            dec = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-i", footage[sid], "-f", "rawvideo",
                                    "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
        bg = None
        while n < last:
            if dec:
                buf = dec.stdout.read(frame_bytes)
                if len(buf) == frame_bytes:
                    bg = Image.frombytes("RGB", (W, H), buf)
            enc.stdin.write(render.render_frame(n, bg))
            n += 1
            if n % 300 == 0:
                print(f"frame {n}/{total}", flush=True)
        if dec:
            dec.stdout.close()
            dec.wait()
    enc.stdin.close()
    enc.wait()
    print("wrote", video)


if __name__ == "__main__":
    main()
