"""Replace garbled AI text on a sign that the camera moves past.

The sign is tracked from a reference frame with ORB features + a homography, and a corrected
patch (drawn once in reference-frame coordinates) is warped onto every frame where it is visible.

Usage (from Python): fix_sign(src, dst, ref_t, sign_box, patch_box, lines, until_t)
  sign_box  - (x0, y0, x1, y1) of the whole sign in the reference frame (1920x1080 pixels)
  patch_box - (x0, y0, x1, y1) of the area to repaint, inside the sign
  lines     - [(text, font_path, colour)] drawn top to bottom inside patch_box
"""
import subprocess

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H = 1920, 1080


def read_frames(src):
    cap = cv2.VideoCapture(src)
    fps = cap.get(cv2.CAP_PROP_FPS) or 24
    frames = []
    while True:
        ok, f = cap.read()
        if not ok:
            break
        frames.append(cv2.resize(f, (W, H), interpolation=cv2.INTER_CUBIC))
    return frames, fps


def make_patch(ref, patch_box, lines):
    x0, y0, x1, y1 = patch_box
    region = ref[y0:y1, x0:x1]
    light = region[cv2.cvtColor(region, cv2.COLOR_BGR2GRAY) > 170]
    bg = tuple(int(v) for v in np.median(light, axis=0)[::-1]) if len(light) else (240, 240, 240)
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle([x0, y0, x1, y1], fill=bg + (255,))
    lh = (y1 - y0) / len(lines)
    for i, (text, face, col) in enumerate(lines):
        size = int(lh * 0.82)
        f = ImageFont.truetype(face, size, layout_engine=ImageFont.Layout.RAQM)
        while f.getlength(text) > (x1 - x0) * 0.97 and size > 10:
            size -= 1
            f = ImageFont.truetype(face, size, layout_engine=ImageFont.Layout.RAQM)
        d.text((x0 + 4, y0 + lh * (i + 0.5)), text, font=f, fill=col, anchor="lm")
    rgba = np.array(im)
    return rgba[:, :, [2, 1, 0, 3]]  # BGRA


def fix_sign(src, dst, ref_t, sign_box, patch_box, lines, until_t):
    frames, fps = read_frames(src)
    ref_i = int(round(ref_t * fps))
    ref = frames[ref_i]
    patch = make_patch(ref, patch_box, lines)
    orb = cv2.ORB_create(4000)
    mask = np.zeros((H, W), np.uint8)
    sx0, sy0, sx1, sy1 = sign_box
    mask[sy0:sy1, sx0:sx1] = 255
    kp0, des0 = orb.detectAndCompute(cv2.cvtColor(ref, cv2.COLOR_BGR2GRAY), mask)
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    prev = np.eye(3)
    for n in range(min(len(frames), int(until_t * fps) + 1)):
        g = cv2.cvtColor(frames[n], cv2.COLOR_BGR2GRAY)
        kp, des = orb.detectAndCompute(g, None)
        M = None
        if des is not None:
            m = sorted(bf.match(des0, des), key=lambda a: a.distance)[:400]
            if len(m) >= 12:
                p0 = np.float32([kp0[a.queryIdx].pt for a in m])
                p1 = np.float32([kp[a.trainIdx].pt for a in m])
                M, inl = cv2.findHomography(p0, p1, cv2.RANSAC, 4.0)
                if M is None or inl.sum() < 10:
                    M = None
        M = prev if M is None else M
        prev = M
        warped = cv2.warpPerspective(patch, M, (W, H), flags=cv2.INTER_LINEAR)
        a = warped[:, :, 3:4].astype(np.float32) / 255
        frames[n] = (frames[n] * (1 - a) + warped[:, :, :3] * a).astype(np.uint8)
    enc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgr24",
                            "-s", f"{W}x{H}", "-r", f"{fps}", "-i", "-", "-i", src, "-map", "0:v", "-map", "1:a?",
                            "-c:v", "libx264", "-crf", "14", "-preset", "fast", "-pix_fmt", "yuv420p",
                            "-c:a", "copy", "-shortest", dst], stdin=subprocess.PIPE)
    for f in frames:
        enc.stdin.write(f.tobytes())
    enc.stdin.close()
    enc.wait()
