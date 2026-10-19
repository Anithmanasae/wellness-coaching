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
# blur: (x, y, w, h, t0, t1) in 1920x1080 output pixels; t1 None = to the end.
SCENES = [
    {"ta": "அறுவை சிகிச்சைக்கு பின் விரைவாக குணமடைய ஒரு எளிய வழி உண்டு!",
     "en": "There is a simple way to recover quickly after surgery!",
     "blur": [(270, 90, 1500, 330, 0, 1.25)]},   # misspelled hospital sign in the first second
    {"ta": None, "en": None,
     "blur": [(560, 880, 800, 200, 0, None)]},  # garbled Veo captions at the bottom
]


def make_scene(i, sc, src, out, tmp):
    dur = duration(src)
    chain = f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,fps={FPS}[b0]"
    last = "b0"
    for k, (x, y, w, h, t0, t1) in enumerate(sc.get("blur", [])):
        t1 = dur if t1 is None else t1
        chain += (f";[{last}]split[m{k}][c{k}];[c{k}]crop={w}:{h}:{x}:{y},boxblur=28:3[bl{k}];"
                  f"[m{k}][bl{k}]overlay={x}:{y}:enable='between(t,{t0},{t1})'[b{k + 1}]")
        last = f"b{k + 1}"
    inputs = ["-i", src]
    if sc["ta"]:
        s0, s1 = speech_span(src, dur)
        sub = os.path.join(tmp, f"r_sub{i:02d}.png")
        subtitle_png(sc["ta"], sc["en"], sub)
        inputs += ["-loop", "1", "-i", sub]
        chain += f";[{last}][1:v]overlay=enable='between(t,{s0:.2f},{s1:.2f})'[s]"
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
    parts += [os.path.join(prev_parts, "p_end.mp4"), os.path.join(prev_parts, "p_credits.mp4")]
    listing = os.path.join(tmp, "r_list.txt")
    with open(listing, "w") as f:
        f.writelines(f"file '{p}'\n" for p in parts)
    final = os.path.join(out, "recovery-tamil.mp4")
    subprocess.check_call(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", listing,
                           "-c", "copy", "-movflags", "+faststart", final])
    print("wrote", final)


if __name__ == "__main__":
    main()
