"""Generate one narration WAV per sentence with Kokoro TTS.

Usage: python3 narrate.py <kokoro.onnx> <voices.bin> <out_dir>
"""
import json
import os
import sys

import soundfile as sf
from kokoro_onnx import Kokoro

from script import SCENES

VOICE = "bf_emma"  # calm British English female voice
SPEED = 0.9

model, voices, out = sys.argv[1:4]
os.makedirs(out, exist_ok=True)
k = Kokoro(model, voices)
manifest = {}
for scene in SCENES:
    for i, sentence in enumerate(scene["narration"]):
        path = os.path.join(out, f"{scene['id']}_{i}.wav")
        if not os.path.exists(path):
            samples, sr = k.create(sentence, voice=VOICE, speed=SPEED, lang="en-gb")
            sf.write(path, samples, sr)
        info = sf.info(path)
        manifest[path] = info.frames / info.samplerate
        print(f"{path}: {manifest[path]:.2f}s")
json.dump(manifest, open(os.path.join(out, "manifest.json"), "w"), indent=1)
