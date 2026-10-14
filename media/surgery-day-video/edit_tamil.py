"""Edit the Sri Lankan Tamil Veo clips (see flow-guide.html) into the final patient video.

Adds an opening title card, the hospital/ward lower third, step labels, Tamil + English
subtitles timed to the speech in each clip, short fades, loudness levelling and an end card.

Usage: python3 edit_tamil.py <clips_dir with clipNN.mp4> <out_dir>
"""
import os
import re
import subprocess
import sys

import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1920, 1080, 24
TA_BOLD = "/usr/share/fonts/truetype/noto/NotoSansTamil-Bold.ttf"
TA_REG = "/usr/share/fonts/truetype/noto/NotoSansTamil-Regular.ttf"
EN_BOLD = "/usr/share/fonts/opentype/inter/Inter-Bold.otf"
EN_MED = "/usr/share/fonts/opentype/inter/Inter-Medium.otf"
TEAL = (13, 117, 99)
NAVY = (20, 48, 43)

HOSPITAL_TA = "கிளிநொச்சி மாவட்ட பொது வைத்தியசாலை"
HOSPITAL_EN = "District General Hospital Kilinochchi"
WARD_TA = "எலும்பியல் சத்திரசிகிச்சை விடுதி 16"
WARD_EN = "Orthopaedic Surgery Ward 16"

STEPS = {
    "welcome": ("வரவேற்பு", "Welcome"),
    "1": ("படி 1 - காலைத் தயாரிப்பு", "Step 1 · Morning Prep"),
    "2": ("படி 2 - சத்திரசிகிச்சைக் கூடத்துக்கு", "Step 2 · To Theatre"),
    "3": ("படி 3 - மயக்க மருந்து வைத்தியர்", "Step 3 · Your Anaesthetist"),
    "4": ("படி 4 - மீட்பு அறை", "Step 4 · Recovery Room"),
    "5": ("படி 5 - மீண்டும் விடுதிக்கு", "Step 5 · Back to the Ward"),
    "end": ("கேள்விகள்?", "Questions?"),
}

# Same lines as flow-guide.html.
CLIPS = {
    0: (None, "கிளிநொச்சி மாவட்ட பொது வைத்தியசாலை, எலும்பியல் சத்திரசிகிச்சை விடுதி 16க்கு உங்களை அன்புடன் வரவேற்கிறோம்.",
        "Welcome to District General Hospital Kilinochchi, Orthopaedic Surgery Ward 16."),
    1: ("welcome", "வணக்கம்! சத்திரசிகிச்சைக்கு முன் கொஞ்சம் பயமாக இருப்பது முற்றிலும் சாதாரணம்தான்.",
        "Hello! Feeling a little nervous before surgery is completely normal."),
    2: ("welcome", "உங்கள் சத்திரசிகிச்சை நாள் தொடக்கம் முதல் முடிவு வரை எப்படி இருக்கும் என்று பார்ப்போம்.",
        "Let's see what your surgery day will look like, from start to finish."),
    3: ("1", "உங்கள் நாள் இங்கே விடுதியில்தான் தொடங்குகிறது. இந்த சுத்தமான உடையை மாற்றிக்கொள்ளுங்கள்.",
        "Your day begins right here in the ward. Please change into this clean gown."),
    4: ("1", "நகைகள், பொய்ப்பல், கண்ணாடியைக் கழற்றி வையுங்கள். உங்கள் அடையாளப் பட்டியைச் சரிபார்க்கிறேன்.",
        "Please take off your jewellery, dentures and glasses. I'll check your identification band."),
    5: ("2", "நேரம் வந்ததும் உங்களைச் சத்திரசிகிச்சைக் கூடத்துக்குக் கவனமாகக் கொண்டு செல்வோம். பயப்பட வேண்டாம்.",
        "When it's time, we'll take you carefully to the operating theatre. Don't worry."),
    6: ("2", "வணக்கம், நான் உங்கள் மயக்க மருந்து வைத்தியர். உங்கள் விவரங்களை ஒருமுறை சரிபார்க்கிறோம்.",
        "Hello, I'm your anaesthetist. We'll just check your details once more."),
    7: ("3", "நெஞ்சில் ஸ்டிக்கர்கள், கையில் இரத்த அழுத்தப் பட்டி, விரலில் ஒரு சிறிய கிளிப் போடுகிறோம்.",
        "We'll put stickers on your chest, a blood pressure cuff on your arm and a small clip on your finger."),
    8: ("3", "கையில் ஒரு சிறிய கனுலா போடுவேன். கொஞ்ச நேரத்தில் நீங்கள் பாதுகாப்பாக நன்றாகத் தூங்கிவிடுவீர்கள்.",
        "I'll put a small cannula in your hand. In a little while you'll fall into a safe, deep sleep."),
    9: ("4", "சத்திரசிகிச்சை முடிந்துவிட்டது. நீங்கள் இப்போது மீட்பு அறையில் இருக்கிறீர்கள். கொஞ்சம் தூக்கக் கலக்கமாக இருக்கலாம்.",
        "Your surgery is finished. You're in the recovery room now. You may feel a little drowsy."),
    10: ("4", "நான் உங்கள் பக்கத்திலேயே இருப்பேன். குளிராமல் பார்த்துக்கொள்வோம். வலி இருந்தால் சொல்லுங்கள்.",
         "I'll be right beside you. We'll keep you warm. Tell us if you have any pain."),
    11: ("5", "அம்மா, நீங்கள் மீண்டும் விடுதிக்கு வந்துவிட்டீர்கள். இப்போது நன்றாக ஓய்வெடுங்கள்.",
         "Amma, you're back on the ward. Rest well now."),
    12: ("5", "அனுமதித்த பின் தண்ணீர் குடிக்கலாம். ஏதாவது தேவையென்றால் இந்த அழைப்பு மணியை அழுத்துங்கள்.",
         "You can drink water once we allow it. If you need anything, press this call bell."),
    13: ("end", "சத்திரசிகிச்சை பற்றி ஏதாவது சந்தேகமா? உங்கள் வைத்தியரிடமோ தாதியிடமோ தயங்காமல் கேளுங்கள்.",
         "Any questions about your surgery? Don't hesitate to ask your doctor or nurse."),
    14: ("end", "நீங்கள் விரைவில் குணமடைய வாழ்த்துகிறோம்!", "We wish you a speedy recovery!"),
}


def font(path, size):
    return ImageFont.truetype(path, size, layout_engine=ImageFont.Layout.RAQM)


def wrap(text, f, width):
    lines, cur = [], ""
    for word in text.split():
        trial = (cur + " " + word).strip()
        if f.getlength(trial) > width and cur:
            lines.append(cur)
            cur = word
        else:
            cur = trial
    return lines + [cur]


def subtitle_png(ta, en, path):
    """Bottom subtitle: Tamil (large) over English (small) on a soft dark box."""
    fta, fen = font(TA_BOLD, 44), font(EN_MED, 30)
    ta_lines, en_lines = wrap(ta, fta, 1500), wrap(en, fen, 1500)
    lh_ta, lh_en = 66, 42
    bw = int(max([fta.getlength(l) for l in ta_lines] + [fen.getlength(l) for l in en_lines])) + 80
    bh = lh_ta * len(ta_lines) + lh_en * len(en_lines) + 40
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x0, y0 = (W - bw) // 2, H - bh - 48
    d.rounded_rectangle([x0, y0, x0 + bw, y0 + bh], radius=20, fill=(8, 20, 18, 185))
    y = y0 + 18
    for l in ta_lines:
        d.text((W / 2, y + lh_ta / 2), l, font=fta, fill="white", anchor="mm")
        y += lh_ta
    for l in en_lines:
        d.text((W / 2, y + lh_en / 2), l, font=fen, fill=(205, 228, 222), anchor="mm")
        y += lh_en
    im.save(path)


def chip_png(step, path):
    ta, en = STEPS[step]
    fta, fen = font(TA_BOLD, 30), font(EN_BOLD, 22)
    w = int(max(fta.getlength(ta), fen.getlength(en))) + 56
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([48, 44, 48 + w, 44 + 104], radius=18, fill=(255, 255, 255, 228))
    d.rectangle([48, 62, 56, 130], fill=TEAL)
    d.text((76, 58), ta, font=fta, fill=NAVY)
    d.text((76, 104), en, font=fen, fill=TEAL)
    im.save(path)


def lower_third_png(path):
    fta, fen = font(TA_BOLD, 48), font(EN_BOLD, 30)
    fta2, fen2 = font(TA_REG, 36), font(EN_MED, 26)
    rows = [(HOSPITAL_TA, fta, "white", 64), (HOSPITAL_EN, fen, (205, 236, 228), 44),
            (WARD_TA, fta2, "white", 54), (WARD_EN, fen2, (205, 236, 228), 38)]
    w = int(max(f.getlength(t) for t, f, _, _ in rows)) + 90
    h = sum(r[3] for r in rows) + 50
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x0, y0 = 64, 120
    d.rounded_rectangle([x0, y0, x0 + w, y0 + h], radius=22, fill=(13, 86, 74, 225))
    d.rectangle([x0, y0 + 24, x0 + 10, y0 + h - 24], fill=(255, 214, 140))
    y = y0 + 24
    for t, f, col, lh in rows:
        d.text((x0 + 44, y), t, font=f, fill=col)
        y += lh
    im.save(path)


def card_png(path, lines):
    """Full-screen title/end card on a teal gradient."""
    ys = np.linspace(0, 1, H)[:, None, None]
    top, bot = np.array([18, 128, 110]), np.array([14, 52, 60])
    arr = (top * (1 - ys) + bot * ys).repeat(W, axis=1).astype(np.uint8)
    im = Image.fromarray(arr, "RGB")
    d = ImageDraw.Draw(im)
    cx, cy, r = W // 2, 250, 92
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill="white")
    d.ellipse([cx - r + 12, cy - r + 12, cx + r - 12, cy + r - 12], fill=TEAL)
    d.rectangle([cx - 12, cy - 50, cx + 12, cy + 50], fill="white")
    d.rectangle([cx - 50, cy - 12, cx + 50, cy + 12], fill="white")
    y = 430
    for text, fpath, size, col, gap in lines:
        f = font(fpath, size)
        for l in wrap(text, f, 1600):
            d.text((W / 2, y), l, font=f, fill=col, anchor="mm")
            y += int(size * 1.45)
        y += gap
    im.save(path)


def speech_span(path, dur):
    """First and last moments of speech, from ffmpeg silence detection."""
    out = subprocess.run(["ffmpeg", "-i", path, "-af", "silencedetect=n=-35dB:d=0.35", "-vn", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    starts = [float(x) for x in re.findall(r"silence_start: ([0-9.]+)", out)]
    ends = [float(x) for x in re.findall(r"silence_end: ([0-9.]+)", out)]
    begin = ends[0] if starts and starts[0] < 0.05 and ends else 0.2
    end = dur
    if starts and starts[-1] > begin + 1 and (len(ends) < len(starts) or ends[-1] >= dur - 0.1):
        end = starts[-1]
    return max(0.0, begin - 0.15), min(dur, end + 0.35)


def duration(path):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                          "-of", "default=nw=1:nk=1", path]))


def pad_wav(path, seconds, sr=48000):
    t = np.arange(int(seconds * sr)) / sr
    tone = sum(np.sin(2 * np.pi * f * t) for f in (220.0, 277.2, 329.6, 440.0)) / 4
    env = np.clip(t / 1.2, 0, 1) * np.clip((seconds - t) / 1.5, 0, 1)
    sf.write(path, np.stack([tone * env * 0.06] * 2, axis=1).astype(np.float32), sr)


ENC = ["-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-r", str(FPS),
       "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2"]


def make_card(png, seconds, out, tmp):
    wav = os.path.join(tmp, os.path.basename(out) + ".wav")
    pad_wav(wav, seconds)
    subprocess.check_call(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-t", str(seconds), "-i", png,
                           "-i", wav, "-vf", f"fps={FPS},format=yuv420p,fade=t=in:st=0:d=0.6,"
                           f"fade=t=out:st={seconds - 0.8}:d=0.8", "-shortest", *ENC, out])


def make_clip(n, src, out, tmp):
    step, ta, en = CLIPS[n]
    dur = duration(src)
    s0, s1 = speech_span(src, dur)
    sub = os.path.join(tmp, f"sub{n:02d}.png")
    subtitle_png(ta, en, sub)
    inputs = ["-i", src, "-loop", "1", "-i", sub]
    chain = (f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,fps={FPS}[v0];"
             f"[v0][1:v]overlay=enable='between(t,{s0:.2f},{s1:.2f})'[v1]")
    top = os.path.join(tmp, f"top{n:02d}.png")
    if step is None:
        lower_third_png(top)
        chain += f";[v1][2:v]overlay=enable='between(t,0.6,{dur - 0.4:.2f})'[v2]"
    else:
        chip_png(step, top)
        chain += ";[v1][2:v]overlay[v2]"
    inputs += ["-loop", "1", "-i", top]
    chain += f";[v2]fade=t=in:st=0:d=0.3,fade=t=out:st={dur - 0.3:.2f}:d=0.3,format=yuv420p[v]"
    achain = (f"[0:a]loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000,"
              f"afade=t=in:st=0:d=0.2,afade=t=out:st={dur - 0.3:.2f}:d=0.3[a]")
    subprocess.check_call(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", chain + ";" + achain,
                           "-map", "[v]", "-map", "[a]", "-t", f"{dur:.3f}", *ENC, out])
    return dur, s0, s1


def main():
    clips_dir, out = sys.argv[1:3]
    tmp = os.path.join(out, "parts")
    os.makedirs(tmp, exist_ok=True)
    parts = []
    t = 0.0
    srt = []

    title = os.path.join(tmp, "title.png")
    card_png(title, [("சத்திரசிகிச்சை நாளில் என்ன நடக்கும்?", TA_BOLD, 76, (255, 255, 255), 0),
                     ("What to Expect on Surgery Day", EN_BOLD, 48, (205, 236, 228), 36),
                     (HOSPITAL_TA + " - " + WARD_TA, TA_REG, 32, (255, 255, 255), 0),
                     (HOSPITAL_EN + " · " + WARD_EN, EN_MED, 26, (205, 236, 228), 0)])
    parts.append(os.path.join(tmp, "p_title.mp4"))
    make_card(title, 5.0, parts[-1], tmp)
    t += 5.0

    present = sorted(int(m.group(1)) for f in os.listdir(clips_dir) if (m := re.match(r"clip(\d\d)\.mp4$", f)))
    for n in present:
        part = os.path.join(tmp, f"p_clip{n:02d}.mp4")
        dur, s0, s1 = make_clip(n, os.path.join(clips_dir, f"clip{n:02d}.mp4"), part, tmp)
        parts.append(part)
        srt.append((t + s0, t + s1, CLIPS[n][1], CLIPS[n][2]))
        print(f"clip{n:02d}: {dur:.1f}s, subtitle {s0:.1f}-{s1:.1f}s", flush=True)
        t += dur

    end = os.path.join(tmp, "end.png")
    lines = [("நீங்கள் விரைவில் குணமடைய வாழ்த்துகிறோம்!", TA_BOLD, 66, (255, 255, 255), 0),
             ("We wish you a speedy recovery!", EN_BOLD, 42, (205, 236, 228), 36)]
    if 13 not in present:
        lines += [("கேள்விகள் இருந்தால் உங்கள் வைத்தியரிடமோ தாதியிடமோ தயங்காமல் கேளுங்கள்.", TA_REG, 34,
                   (255, 255, 255), 0),
                  ("Any questions? Please ask your doctor or nurse.", EN_MED, 28, (205, 236, 228), 30)]
    lines += [(HOSPITAL_TA + " - " + WARD_TA, TA_REG, 30, (255, 255, 255), 0),
              (HOSPITAL_EN + " · " + WARD_EN, EN_MED, 24, (205, 236, 228), 0)]
    card_png(end, lines)
    parts.append(os.path.join(tmp, "p_end.mp4"))
    make_card(end, 6.0, parts[-1], tmp)

    listing = os.path.join(tmp, "list.txt")
    with open(listing, "w") as f:
        f.writelines(f"file '{p}'\n" for p in parts)
    final = os.path.join(out, "surgery-day-tamil.mp4")
    subprocess.check_call(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", listing,
                           "-c", "copy", "-movflags", "+faststart", final])

    def ts(x):
        ms = int(round(x * 1000))
        return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"
    with open(os.path.join(out, "surgery-day-tamil.srt"), "w") as f:
        for i, (a, b, ta, en) in enumerate(srt, 1):
            f.write(f"{i}\n{ts(a)} --> {ts(b)}\n{ta}\n{en}\n\n")
    print("wrote", final, f"{t + 6.0:.1f}s")


if __name__ == "__main__":
    main()
