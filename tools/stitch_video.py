#!/usr/bin/env python3
"""Stitch a folder of screenshots into a short portrait video.

Tall images (phone screenshots) get a slow vertical pan so the whole screen is
seen; images that fit the canvas get a gentle push-in. Segments are joined with
crossfades, and the reel fades in from and out to black.

Usage:
    python3 tools/stitch_video.py media/screens media/app-tour.mp4
    python3 tools/stitch_video.py media/screens out.mp4 --seconds 3 --fps 30

Frames are generated with Pillow and piped as raw RGB into ffmpeg, so nothing
larger than the crossfade buffer is ever held in memory.
"""

import argparse
import os
import shutil
import subprocess
import sys
from collections import deque

from PIL import Image, ImageFilter

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


def find_ffmpeg():
    """Prefer a system ffmpeg, fall back to the imageio-ffmpeg static build."""
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        sys.exit("ffmpeg not found. Install it, or: pip install imageio-ffmpeg")


def smoothstep(t):
    return t * t * (3.0 - 2.0 * t)


def load_images(src):
    if os.path.isdir(src):
        names = sorted(
            n for n in os.listdir(src) if os.path.splitext(n)[1].lower() in IMAGE_EXTS
        )
        paths = [os.path.join(src, n) for n in names]
    else:
        paths = [src]
    if not paths:
        sys.exit(f"No images found in {src}")
    return paths


def build_background(img, size):
    """A blurred, over-scaled copy of the image, used to fill any empty canvas."""
    w, h = size
    scale = max(w / img.width, h / img.height) * 1.15
    bg = img.resize((int(img.width * scale), int(img.height * scale)), Image.LANCZOS)
    bg = bg.filter(ImageFilter.GaussianBlur(28))
    left = (bg.width - w) // 2
    top = (bg.height - h) // 2
    return bg.crop((left, top, left + w, top + h))


def segment_frames(path, size, n_frames):
    """Yield n_frames RGB frames for one image: pan if tall, push-in if not."""
    w, h = size
    img = Image.open(path).convert("RGB")

    fit_h = round(img.height * w / img.width)
    scaled = img.resize((w, fit_h), Image.LANCZOS)

    if fit_h > h:
        # Taller than the canvas: scroll down through it.
        travel = fit_h - h
        for i in range(n_frames):
            t = smoothstep(i / max(n_frames - 1, 1))
            top = round(travel * t)
            yield scaled.crop((0, top, w, top + h))
    else:
        # Fits inside the canvas: gentle push-in over a blurred backdrop.
        bg = build_background(img, size)
        for i in range(n_frames):
            t = smoothstep(i / max(n_frames - 1, 1))
            zoom = 1.0 + 0.06 * t
            zw, zh = round(w * zoom), round(fit_h * zoom)
            frame = bg.copy()
            frame.paste(scaled.resize((zw, zh), Image.LANCZOS), ((w - zw) // 2, (h - zh) // 2))
            yield frame


def blend(a, b, alpha):
    return Image.blend(a, b, alpha)


def fade_to_black(frame, alpha):
    """alpha 0 = fully black, 1 = untouched."""
    if alpha >= 1.0:
        return frame
    return Image.blend(Image.new("RGB", frame.size, (0, 0, 0)), frame, alpha)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src", help="directory of images (sorted by filename) or a single image")
    ap.add_argument("out", help="output .mp4 path")
    ap.add_argument("--seconds", type=float, default=3.0, help="hold per image (default 3)")
    ap.add_argument("--fade", type=float, default=0.6, help="crossfade length in seconds")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--width", type=int, default=1080)
    ap.add_argument("--height", type=int, default=1920)
    args = ap.parse_args()

    paths = load_images(args.src)
    size = (args.width, args.height)
    fps = args.fps
    seg_n = max(int(args.seconds * fps), 2)
    xf = min(int(args.fade * fps), seg_n - 1)
    ffmpeg = find_ffmpeg()

    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    cmd = [
        ffmpeg, "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{args.width}x{args.height}", "-r", str(fps),
        "-i", "-",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        args.out,
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    # Total visible frames, after crossfade overlap is accounted for.
    total = len(paths) * seg_n - xf * (len(paths) - 1)
    fade_edge = int(0.4 * fps)
    written = 0
    tail = deque()  # last `xf` frames of the previous segment

    def emit(frame):
        nonlocal written
        # Fade in at the very start, out at the very end.
        if written < fade_edge:
            frame = fade_to_black(frame, (written + 1) / fade_edge)
        elif written >= total - fade_edge:
            frame = fade_to_black(frame, max(total - written, 1) / fade_edge)
        proc.stdin.write(frame.tobytes())
        written += 1

    for idx, path in enumerate(paths):
        print(f"  [{idx + 1}/{len(paths)}] {os.path.basename(path)}", flush=True)
        pending = deque()
        for i, frame in enumerate(segment_frames(path, size, seg_n)):
            if idx > 0 and i < xf:
                frame = blend(tail[i], frame, (i + 1) / (xf + 1))
            pending.append(frame)
            # Hold back the last `xf` frames — the next segment blends into them.
            if len(pending) > xf:
                emit(pending.popleft())
        tail = pending

    for frame in tail:  # flush the final segment
        emit(frame)

    proc.stdin.close()
    if proc.wait() != 0:
        sys.exit("ffmpeg failed")
    print(f"\nWrote {args.out}  ({written} frames, {written / fps:.1f}s)")


if __name__ == "__main__":
    main()
