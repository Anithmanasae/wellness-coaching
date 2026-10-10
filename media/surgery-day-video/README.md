# Patient video: What to Expect on Surgery Day

`surgery-day.mp4`: a 1080p video, about 2.5 minutes long, for the orthopaedic ward. It has an animated
illustrated walkthrough, on-screen step cards, a calm British-English voiceover, burned-in subtitles and a
soft music bed. `surgery-day.en.srt` contains the same subtitles as a separate file, ready to translate into Tamil or Sinhala.

## Regenerate

```bash
pip install kokoro-onnx soundfile pillow numpy   # ffmpeg must be on PATH
# Kokoro model files: https://github.com/thewh1teagle/kokoro-onnx/releases (model-files-v1.0)
python3 narrate.py kokoro-v1.0.int8.onnx voices-v1.0.bin vo/   # one WAV per sentence
python3 render.py vo/ out/            # add --preview to save stills only
```

Edit the narration and on-screen text in `script.py`. The voice and speed are set in `narrate.py`.
