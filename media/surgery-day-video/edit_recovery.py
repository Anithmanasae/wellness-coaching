"""Second patient video (quick recovery after surgery), built from Veo clips.

Reuses the opening hospital clip, end card and credits rendered by edit_tamil.py, and adds
the new scenes with Tamil + English subtitles. Garbled AI-generated signs and burned-in
captions are blurred out.

Usage: python3 edit_recovery.py <edit_tamil parts dir> <out_dir> <scene1.mp4> <scene2.mp4> ...
"""
import os
import subprocess
import sys

from edit_tamil import ENC, FPS, H, W, duration, speech_span, subtitle_png

# One entry per scene, in order. ta/en None = no subtitle yet.
# blur / erase boxes: (x, y, w, h, t0, t1) in 1920x1080 output pixels; t1 None = to the end.
# "erase" fills the box from its surroundings (ffmpeg delogo); "blur" softens it.
# "fix": replacement labels drawn over misspelled AI text: (x, y, w, h, text, size).
SCENES = [
    {"ta": "அறுவை சிகிச்சைக்கு பின் விரைவாக குணமடைய ஒரு எளிய வழி உண்டு!",
     "en": "There is a simple way to recover quickly after surgery!",
     "erase": [(560, 880, 800, 195, 0, None)]},  # garbled Veo captions
    {"ta": "புகையிலை, வெற்றிலை, பாக்கு நிறுத்தினால் சிகிச்சை இருமடங்கு வேகமாகும்!",
     "en": "Stopping tobacco, betel and areca nut makes treatment twice as fast!",
     "erase": [(110, 890, 1700, 186, 0, None)]},  # garbled Veo captions
    {"ta": "புகையிலையை நிறுத்துவதால் ஆக்சிஜன் அதிகரித்து காயம் விரைவில் ஆறும்",
     "en": "Stopping tobacco raises oxygen levels, so wounds heal faster."},
    {"ta": "நுரையீரல் ஆரோக்கியமாக இருந்தால் அறுவை சிகிச்சைக்கு பின் மூச்சுத்திணறல் இருக்காது.",
     "en": "With healthy lungs, there is no breathlessness after surgery.",
     "erase": [(115, 140, 730, 80, 0, None), (1065, 140, 725, 80, 0, None),   # misspelled headings
               (1000, 312, 265, 100, 0, None), (1565, 305, 290, 100, 0, None),  # garbled labels
               (1300, 842, 260, 66, 0, None), (410, 895, 1100, 150, 0, None)],  # label + caption
     "fix": [(110, 140, 735, 82, "ஆரோக்கியமான நுரையீரல்", 46),
             (1060, 140, 730, 82, "அழற்சி அடைந்த நுரையீரல்", 46)]},
    {"ta": "வெற்றிலை பாக்கு தவிர்த்தால் வாய் தொற்றுகள் தடுத்து சதை விரைவில் கூடும்.",
     "en": "Avoiding betel and areca nut prevents mouth infections and helps tissue heal quickly.",
     "erase": [(80, 830, 1400, 180, 0, None)]},  # garbled caption
    {"ta": "நிகோடின் தவிர்ப்பதால் தையல் போட்ட இடத்திற்கு சீரான ரத்த ஓட்டம் கிடைக்கும்.",
     "en": "Avoiding nicotine gives the stitched area a steady blood supply.",
     "erase": [(8, 8, 235, 80, 0, None), (985, 8, 510, 80, 0, None),          # "LEFtrol", "Nocotine Effect"
               (8, 950, 180, 95, 0, None), (990, 950, 515, 95, 0, None)],    # "LEFT", "Nicotine Effect"
     "fix": [(40, 24, 560, 92, "நிகோடின் இல்லாமல் · Without nicotine", 34, "badge"),
             (1000, 24, 560, 92, "நிகோடின் விளைவு · Nicotine effect", 34, "badge")]},
    {"ta": "காயம் சீழ் பிடிப்பதும், தையல் பிரிவதும் தவிர்க்கப்படும்.",
     "en": "Wound infection and stitches coming apart are avoided."},
    {"ta": "வலியும் அசௌகரியமும் குறைந்து இயல்பு நிலைக்கு விரைவாக திரும்புவீர்கள்.",
     "en": "With less pain and discomfort, you return to normal life sooner.",
     "erase": [(350, 925, 1150, 140, 0, None)]},  # garbled caption
    {"ta": "மருத்துவமனை நாட்கள் குறைந்து விரைவில் வீடு திரும்பலாம்!",
     "en": "Fewer days in hospital, so you can go home sooner!",
     "erase": [(230, 20, 1100, 170, 0, 2.4)]},   # garbled calendar month names
    {"ta": "நிறுத்த சிரமமாக இருந்தால் நம் மருத்துவக் குழுவின் உதவியை நாடுங்கள்!",
     "en": "If stopping is hard, ask our medical team for help!",
     "erase": [(540, 960, 850, 115, 0, None)]},  # garbled Veo caption
    {"ta": "உங்கள் அறுவை சிகிச்சை வெற்றிபெற இன்றே இந்த நல்ல முடிவை எடுங்கள்.",
     "en": "Make this good decision today for a successful surgery.",
     "erase": [(380, 830, 1150, 175, 0, None)]},  # garbled caption
    # Closing card: the message is written on the card itself, so no bottom subtitle.
    {"ta": None, "en": None,
     # Starts after the zoom-in (which shows the misspelled name) and ends before the flare.
     "trim": (1.0, 6.5),
     "fix_t": (0, 5.5),
     "fix": [(120, 530, 1480, 410, "", 0, "plate"),  # card with the old lettering removed
             (160, 540, 1240, 80, "DISTRICT GENERAL HOSPITAL KILINOCHCHI", 40, (22, 78, 132)),
             (160, 660, 1240, 76, "ஒரு சிறிய இடைவெளி... பெரிய ஆரோக்கியம்!", 46, (16, 124, 117)),
             (160, 740, 1240, 76, "விரைவாக குணமடைய வாழ்த்துகிறோம்!", 46, (16, 124, 117)),
             (160, 830, 1240, 60, "A small break... big health! Wishing you a speedy recovery!", 30, (60, 96, 110))]},
]
WATERMARK = (1830, 1040, 85, 34)  # Veo logo, bottom right


def fix_png(fixes, path, sample):
    """Correct Tamil labels, drawn over areas already erased with delogo."""
    from PIL import Image, ImageDraw
    from edit_tamil import EN_BOLD, TA_BOLD, font
    EN_BLACK = "/usr/share/fonts/opentype/inter/Inter-Black.otf"
    bg = Image.open(sample).convert("RGB")
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for x, y, w, h, text, size, *style in fixes:
        if style and style[0] == "face":  # rebuild a plain sign face, row by row, from its light pixels
            px = bg.load()
            for r in range(y, y + h):
                row = [px[c, r] for c in range(x, x + w, 3)]
                light = [p for p in row if sum(p) > 3 * 185] or row
                col = tuple(sorted(v[i] for v in light)[len(light) // 2] for i in range(3))
                d.line([(x, r), (x + w, r)], fill=col + (255,))
            continue
        if style and style[0] == "plate":
            import cv2
            import numpy as np
            frame = np.array(bg)[y:y + h, x:x + w, ::-1].copy()
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            dark = (gray < 228).astype(np.uint8)  # letters and their soft edges
            n, lab, stats, _ = cv2.connectedComponentsWithStats(dark, connectivity=8)
            mask = np.zeros_like(dark)
            for k in range(1, n):  # keep shapes touching the top edge (the title), remove the rest
                if stats[k, cv2.CC_STAT_TOP] > 0:
                    mask[lab == k] = 255
            mask = cv2.dilate(mask, np.ones((3, 3), np.uint8), iterations=7)
            clean = cv2.inpaint(frame, mask, 7, cv2.INPAINT_TELEA)[:, :, ::-1]
            im.paste(Image.fromarray(clean).convert("RGBA"), (x, y))
            continue
        if style and style[0] == "stop":
            d.rounded_rectangle([x + 6, y + 10, x + w + 6, y + h + 10], radius=36, fill=(0, 0, 0, 70))
            d.rounded_rectangle([x, y, x + w, y + h], radius=36, fill=(206, 38, 38, 255), outline="white", width=8)
            f = font(TA_BOLD, size)
            while f.getlength(text) > w - 70:
                size -= 2
                f = font(TA_BOLD, size)
            d.text((x + w / 2, y + h / 2 - 16), text, font=f, fill="white", anchor="mm")
            d.text((x + w / 2, y + h - 34), "STOP", font=font(EN_BOLD, 30), fill=(255, 225, 225), anchor="mm")
            continue
        if style and style[0] == "title":  # bold outlined title text, e.g. "DO NOT RUIN YOUR CAST!"
            f = font(EN_BLACK, size)
            d.text((x + w / 2 + 6, y + h / 2 + 8), text, font=f, fill=(20, 24, 60, 160), anchor="mm",
                   stroke_width=12, stroke_fill=(20, 24, 60, 160))
            d.text((x + w / 2, y + h / 2), text, font=f, fill=style[1], anchor="mm",
                   stroke_width=10, stroke_fill=(24, 30, 72))
            continue
        if style and style[0] == "badge":
            ta, en = (t.strip() for t in text.split("·"))
            fta, fen = font(TA_BOLD, size), font(EN_BOLD, int(size * 0.8))
            bw = int(max(fta.getlength(ta), fen.getlength(en))) + 48
            d.rounded_rectangle([x, y, x + bw, y + h], radius=16, fill=(10, 24, 22, 200))
            d.text((x + 24, y + 10), ta, font=fta, fill="white")
            d.text((x + 24, y + 12 + size * 1.25), en, font=fen, fill=(205, 236, 228))
            continue
        face = EN_BOLD if text.isascii() else TA_BOLD
        f = font(face, size)
        while f.getlength(text) > w and size > 12:  # shrink to fit
            size -= 2
            f = font(face, size)
        if style and style[0] == "sign":  # raised navy letters on a white facade sign
            d.text((x + w / 2 + 3, y + h / 2 + 4), text, font=f, fill=(150, 150, 160), anchor="mm")
            d.text((x + w / 2, y + h / 2), text, font=f, fill=(32, 48, 98), anchor="mm")
            continue
        col = style[0] if style else (38, 38, 38)
        d.text((x + w / 2, y + h / 2), text, font=f, fill=col, anchor="mm")
    im.save(path)


def make_scene(i, sc, src, out, tmp):
    trim = sc.get("trim")
    dur = trim[1] - trim[0] if trim else duration(src)
    chain = f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,fps={FPS}[b0]"
    last = "b0"
    for k, (x, y, w, h, t0, t1) in enumerate(sc.get("erase", []) + [WATERMARK + (0, None)]):
        t1 = dur if t1 is None else t1
        chain += f";[{last}]delogo=x={x}:y={y}:w={w}:h={h}:enable='between(t,{t0},{t1})'[e{k}]"
        last = f"e{k}"
    for k, (x, y, w, h, t0, t1) in enumerate(sc.get("blur", [])):
        t1 = dur if t1 is None else t1
        chain += (f";[{last}]split[m{k}][c{k}];[c{k}]crop={w}:{h}:{x}:{y},boxblur={min(28, min(w, h) // 4)}:3[bl{k}];"
                  f"[m{k}][bl{k}]overlay={x}:{y}:enable='between(t,{t0},{t1})'[b{k + 1}]")
        last = f"b{k + 1}"
    inputs = (["-ss", str(trim[0]), "-to", str(trim[1])] if trim else []) + ["-i", src]
    if sc.get("fix"):
        sample = os.path.join(tmp, f"r_bg{i:02d}.png")
        at = str(trim[0] + 2.5) if trim else "1"
        subprocess.check_call(["ffmpeg", "-y", "-loglevel", "error", "-ss", at, "-i", src,
                               "-vf", f"scale={W}:{H}", "-frames:v", "1", sample])
        fx = os.path.join(tmp, f"r_fix{i:02d}.png")
        fix_png(sc["fix"], fx, sample)
        inputs += ["-loop", "1", "-i", fx]
        t0, t1 = sc.get("fix_t", (0, dur))
        chain += f";[{last}][{inputs.count('-i') - 1}:v]overlay=enable='between(t,{t0},{t1})'[f]"
        last = "f"
    if sc["ta"]:
        s0, s1 = sc["sub_t"] if "sub_t" in sc else speech_span(src, dur)
        sub = os.path.join(tmp, f"r_sub{i:02d}.png")
        subtitle_png(sc["ta"], sc["en"], sub)
        inputs += ["-loop", "1", "-i", sub]
        chain += f";[{last}][{inputs.count('-i') - 1}:v]overlay=enable='between(t,{s0:.2f},{s1:.2f})'[s]"
        last = "s"
    chain += f";[{last}]fade=t=in:st=0:d=0.3,fade=t=out:st={dur - 0.3:.2f}:d=0.3,format=yuv420p[v]"
    achain = (f"[0:a]loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000,"
              f"afade=t=in:st=0:d=0.2,afade=t=out:st={dur - 0.3:.2f}:d=0.3[a]")
    subprocess.check_call(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", chain + ";" + achain,
                           "-map", "[v]", "-map", "[a]", "-t", f"{dur:.3f}", *ENC, out])
    return dur


def main():
    prev_parts, out, *sources = sys.argv[1:]
    tmp = os.path.join(out, "parts")
    os.makedirs(tmp, exist_ok=True)
    parts = [os.path.join(prev_parts, "p_clip00.mp4")]
    for i, (sc, src) in enumerate(zip(SCENES, sources), 1):
        part = os.path.join(tmp, f"r_scene{i:02d}.mp4")
        print(f"scene {i}: {make_scene(i, sc, src, part, tmp):.1f}s", flush=True)
        parts.append(part)
    if os.environ.get("WITH_CREDITS") == "1":
        parts.append(os.path.join(prev_parts, "p_credits.mp4"))
    listing = os.path.join(tmp, "r_list.txt")
    with open(listing, "w") as f:
        f.writelines(f"file '{p}'\n" for p in parts)
    final = os.path.join(out, "recovery-tamil.mp4")
    subprocess.check_call(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", listing,
                           "-c", "copy", "-movflags", "+faststart", final])
    print("wrote", final)


if __name__ == "__main__":
    main()
