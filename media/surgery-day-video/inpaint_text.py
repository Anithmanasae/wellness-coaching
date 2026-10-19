"""Remove burned-in AI text from a clip by inpainting only the letter pixels.

Each region is (x, y, w, h, t0, t1, kind) in 1920x1080 pixels; kind picks the letter colour:
  "yellow" - yellow letters with a dark outline (e.g. "Pause")
  "navy"   - dark blue letters on a light sign
The output is a 1920x1080 clip with the original audio.
"""
import subprocess

import cv2
import numpy as np

W, H = 1920, 1080


def letter_mask(roi, kind):
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    if kind == "yellow":
        core = cv2.inRange(hsv, (12, 90, 120), (40, 255, 255))
        return cv2.dilate(core, np.ones((3, 3), np.uint8), iterations=6)  # take in the dark outline
    if kind == "navy":
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        bg = cv2.medianBlur(gray, 31)
        dark = ((bg.astype(int) - gray.astype(int)) > 28).astype(np.uint8) * 255  # darker than the sign face
        return cv2.dilate(dark, np.ones((3, 3), np.uint8), iterations=4)  # take in the letter shadows
    raise ValueError(kind)


def clean_frame(frame, t, regions):
    for x, y, w, h, t0, t1, kind in regions:
        if not (t0 <= t <= (t1 if t1 is not None else 1e9)):
            continue
        roi = frame[y:y + h, x:x + w]
        mask = letter_mask(roi, kind)
        frame[y:y + h, x:x + w] = cv2.inpaint(roi, mask, 9, cv2.INPAINT_TELEA)
    return frame


def clean_clip(src, dst, regions):
    cap = cv2.VideoCapture(src)
    fps = cap.get(cv2.CAP_PROP_FPS) or 24
    enc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgr24",
                            "-s", f"{W}x{H}", "-r", f"{fps}", "-i", "-", "-i", src, "-map", "0:v", "-map", "1:a?",
                            "-c:v", "libx264", "-crf", "14", "-preset", "fast", "-pix_fmt", "yuv420p",
                            "-c:a", "copy", "-shortest", dst], stdin=subprocess.PIPE)
    n = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        frame = cv2.resize(frame, (W, H), interpolation=cv2.INTER_CUBIC)
        enc.stdin.write(clean_frame(frame, n / fps, regions).tobytes())
        n += 1
    enc.stdin.close()
    enc.wait()
