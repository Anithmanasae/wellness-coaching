# Original music + sound effects for the Smart Serve reels, synthesized from scratch with numpy.
# Nothing here is sampled from existing recordings, so there is no third-party copyright to claim.
import wave
import numpy as np

SR = 44100
BPM = 120
BEAT = 60 / BPM
rng = np.random.default_rng(11)

def t_(dur): return np.arange(int(dur * SR)) / SR
def env(n, a=0.005, d=0.2):
    t = np.arange(n) / SR
    return np.minimum(1, t / a) * np.exp(-t / d)
def noise(dur): return rng.uniform(-1, 1, int(dur * SR))
def note(midi): return 440 * 2 ** ((midi - 69) / 12)

def band(x, lo, hi):
    """FFT band-pass (fine for short one-shot buffers)."""
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR)
    X[(f < lo) | (f > hi)] = 0
    return np.fft.irfft(X, len(x))

def sweep_noise(dur, f0, f1, width=0.6):
    """noise whose band centre glides f0 -> f1, done in 25 ms chunks."""
    n = int(dur * SR); out = np.zeros(n); step = int(0.025 * SR)
    src = noise(dur + 0.1)
    for i in range(0, n, step):
        c = f0 + (f1 - f0) * i / n
        seg = band(src[i:i + step * 2], c * (1 - width), c * (1 + width))[:min(step, n - i)]
        out[i:i + len(seg)] = seg
    return out / (np.abs(out).max() + 1e-9)

def add(buf, x, at, gain=1.0):
    i = int(at * SR)
    if i >= len(buf): return
    x = x[:len(buf) - i]; buf[i:i + len(x)] += gain * x

# ---------------- instruments ----------------
def kick(): t = t_(0.35); return np.sin(2 * np.pi * (50 * t + 90 * (1 - np.exp(-t * 30)) / 30)) * env(len(t), .002, .12)
def clap():
    x = band(noise(0.25), 900, 5000) * env(int(0.25 * SR), .001, .06)
    return x / np.abs(x).max()
def hat(open_=False):
    d = 0.18 if open_ else 0.05; x = band(noise(d), 7000, 16000) * env(int(d * SR), .001, d / 3)
    return x / np.abs(x).max()
def pluck(freq, dur=0.6, bright=3):
    t = t_(dur); x = sum(np.sin(2 * np.pi * freq * k * t) / k ** 1.4 for k in range(1, bright + 1))
    return x * env(len(t), .004, dur / 3)
def pad(freqs, dur):
    t = t_(dur); x = np.zeros(len(t))
    for f in freqs:
        for det in (-0.25, 0.25):  # soft detuned saw-ish via 6 harmonics
            x += sum(np.sin(2 * np.pi * (f + det) * k * t) / k for k in range(1, 7))
    a = np.minimum(1, t / 0.08) * np.minimum(1, (dur - t) / 0.1)
    return x * a / (len(freqs) * 6)
def sub(freq, dur):
    t = t_(dur); return np.sin(2 * np.pi * freq * t) * np.minimum(1, t / .02) * np.minimum(1, (dur - t) / .05)

# ---------------- sound effects ----------------
def sfx_impact():
    t = t_(1.2); boom = np.sin(2 * np.pi * (40 * t + 60 * (1 - np.exp(-t * 8)) / 8)) * env(len(t), .002, .45)
    crack = band(noise(1.2), 200, 4000) * env(len(t), .001, .08)
    return 0.9 * boom + 0.5 * crack
def sfx_whoosh(dur=0.45): return sweep_noise(dur, 400, 4000) * np.sin(np.pi * np.linspace(0, 1, int(dur * SR))) ** 2
def sfx_riser(dur=0.9): return sweep_noise(dur, 300, 6000, 0.4) * np.linspace(0, 1, int(dur * SR)) ** 2
def sfx_pop():
    t = t_(0.12); return np.sin(2 * np.pi * (900 * t - 2500 * t * t)) * env(len(t), .001, .03)
def sfx_stamp():
    t = t_(0.3); thud = np.sin(2 * np.pi * 70 * t) * env(len(t), .001, .07)
    return thud + 0.6 * band(noise(0.3), 300, 3000) * env(len(t), .001, .025)
def sfx_paper(): x = band(noise(0.18), 2000, 9000) * env(int(0.18 * SR), .01, .05); return x / np.abs(x).max()
def sfx_clink():
    t = t_(0.6); return sum(np.sin(2 * np.pi * f * t) * a for f, a in ((2100, 1), (3350, .6), (5200, .3))) * env(len(t), .001, .12)
def sfx_shutter(dur=0.9):
    t = t_(dur); x = band(noise(dur), 300, 5000) * (0.5 + 0.5 * np.sign(np.sin(2 * np.pi * 28 * t)))
    return x / np.abs(x).max() * np.minimum(1, (dur - t) / .05)
def sfx_buzz(dur=0.25):
    t = t_(dur); return np.sign(np.sin(2 * np.pi * 100 * t)) * 0.4 * (rng.uniform(0, 1, len(t)) > 0.3)
def sfx_scratch():
    t = t_(0.4); f = 300 + 1200 * np.abs(np.sin(2 * np.pi * 3.5 * t))
    x = band(noise(0.4), 500, 5000) * 0.6 + 0.6 * np.sign(np.sin(2 * np.pi * np.cumsum(f) / SR))
    return x * np.minimum(1, (0.4 - t) / 0.05)
def sfx_glitch():
    t = t_(0.06); return np.sign(np.sin(2 * np.pi * rng.choice([180, 360, 720, 1440]) * t)) * env(len(t), .001, .02)
def sfx_kaching():
    t = t_(1.2)
    bell = sum(np.sin(2 * np.pi * f * t) * a for f, a in ((2637, 1), (3520, .7), (4186, .5), (5274, .3))) * env(len(t), .001, .35)
    coins = np.zeros(len(t))
    for k in range(8): add(coins, sfx_clink() * 0.4, 0.05 + k * 0.035)
    drawer = band(noise(0.15), 100, 1200) * env(int(0.15 * SR), .001, .05)
    out = 0.6 * bell + coins; out[:len(drawer)] += drawer
    return out
def sfx_sparkle():
    out = np.zeros(int(1.0 * SR))
    for k, m in enumerate((84, 88, 91, 96)): add(out, pluck(note(m), 0.5, 2), k * 0.07, 0.5)
    return out

def sfx_airhorn(dur=0.32):
    t = t_(dur); x = np.zeros(len(t))
    for f in (466.2, 587.3, 698.5):
        for det in (-1.5, 1.5): x += np.sign(np.sin(2 * np.pi * (f + det) * t)) * 0.5 + np.sin(2 * np.pi * 2 * (f + det) * t) * 0.3
    return x / 6 * np.minimum(1, t / .01) * np.minimum(1, (dur - t) / .03)
def sfx_siren(dur=0.9):
    t = t_(dur); f = 700 + 500 * np.sin(2 * np.pi * 3 * t)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.minimum(1, (dur - t) / .05)
def sfx_sad_trombone():
    out = np.zeros(int(2.4 * SR))
    for i, (m, d) in enumerate(((62, .38), (61, .38), (60, .38), (59, 1.2))):
        t = t_(d); f = note(m - 12) * (1 + 0.012 * np.sin(2 * np.pi * 6 * t) * (t > .15))
        ph = 2 * np.pi * np.cumsum(f) / SR
        x = sum(np.sin(k * ph) / k for k in range(1, 9)) * np.minimum(1, t / .03) * np.minimum(1, (d - t) / .06)
        add(out, x * 0.5, sum(dd for _, dd in ((62, .38), (61, .38), (60, .38))[:i]))
    return out
def sfx_rain(dur): return band(noise(dur), 3000, 12000) * 0.25

SFX = {"impact": (sfx_impact, .8), "whoosh": (sfx_whoosh, .5), "pop": (sfx_pop, .35), "stamp": (sfx_stamp, .8),
       "paper": (sfx_paper, .35), "clink": (sfx_clink, .45), "shutter": (sfx_shutter, .5), "buzz": (sfx_buzz, .18),
       "riser": (sfx_riser, .45), "scratch": (sfx_scratch, .6), "kaching": (sfx_kaching, .7), "sparkle": (sfx_sparkle, .5),
       "airhorn": (sfx_airhorn, .7), "siren": (sfx_siren, .35)}

# ---------------- music sections ----------------
def music_tense(dur):
    """A-minor suspense: sub drone, ticking hats, sparse low stabs."""
    out = np.zeros(int(dur * SR))
    add(out, sub(55, dur) * (0.75 + 0.25 * np.sin(2 * np.pi * 2 * t_(dur))), 0, .35)
    k = 0
    while k * BEAT / 2 < dur:
        add(out, hat(), k * BEAT / 2, .12 if k % 2 else .2); k += 1
    for i, m in enumerate((45, 48, 52, 51)):  # A2 C3 E3 Eb3 - uneasy
        if i * BEAT * 1.5 < dur: add(out, pluck(note(m), 1.2, 5), i * BEAT * 1.5, .32)
    for b in range(int(dur / BEAT) + 1): add(out, kick(), b * BEAT * 2, .5)
    return out

def music_glitch(dur, flicker_hz=6):
    out = np.zeros(int(dur * SR))
    k = 0
    while k / flicker_hz < dur: add(out, sfx_glitch(), k / flicker_hz, .25); k += 1
    add(out, sub(41.2, dur), 0, .2)
    return out

def music_uplift(dur):
    """C - G - Am - F, four-on-the-floor, claps on 2 & 4."""
    out = np.zeros(int(dur * SR))
    chords = [(60, 64, 67), (55, 59, 62), (57, 60, 64), (53, 57, 60)]
    bar = BEAT * 4 / 2  # half-bar chords keep it moving in a short clip
    i = 0
    while i * bar < dur:
        ch = chords[i % 4]; seg = min(bar, dur - i * bar)
        add(out, pad([note(m) for m in ch], seg), i * bar, .22)
        add(out, sub(note(ch[0] - 24), seg), i * bar, .3)
        for s in range(4): add(out, pluck(note(ch[s % 3] + 12), 0.3, 3), i * bar + s * BEAT / 2, .12)
        i += 1
    b = 0
    while b * BEAT < dur:
        add(out, kick(), b * BEAT, .55)
        if b % 2: add(out, clap(), b * BEAT, .25)
        add(out, hat(), b * BEAT + BEAT / 2, .12); b += 1
    return out

def music_happy(dur):
    """bouncy C-major bop for the 'winning' meme panel."""
    out = np.zeros(int(dur * SR)); b16 = BEAT / 4; arp = (60, 64, 67, 72, 67, 64)
    k = 0
    while k * b16 < dur:
        add(out, pluck(note(arp[k % 6] + 12), 0.18, 2), k * b16, .18)
        if k % 4 == 0: add(out, kick(), k * b16, .55); add(out, sub(note(36 if (k // 8) % 2 == 0 else 43), b16 * 3), k * b16, .3)
        if k % 8 == 4: add(out, clap(), k * b16, .3)
        if k % 2: add(out, hat(), k * b16, .1)
        k += 1
    return out

def build(path, total, c1, c2, events=()):
    """total length, hook->question cut at c1, question->CTA cut at c2, events = [(time, sfx_name)]."""
    mix = np.zeros(int(total * SR) + SR)
    add(mix, music_tense(c1), 0)
    add(mix, music_glitch(c2 - c1), c1)
    add(mix, music_uplift(total - c2), c2)
    # transitions shared by every reel
    std = [(c1 - 0.9, "riser"), (c1, "impact"), (c1, "scratch"), (c2 - 0.25, "whoosh"), (c2, "impact"),
           (c2 + 0.2, "kaching"), (c2 + 0.05, "sparkle"), (c2 + 0.6, "pop")]
    for at, name in list(events) + std:
        fn, g = SFX[name]; add(mix, fn(), at, g)
    finish(mix, path, total)

def finish(mix, path, total):
    """trim, fade, limit, normalise and write a mono 16-bit WAV."""
    mix = mix[:int(total * SR)]
    fade = int(0.6 * SR); mix[-fade:] *= np.linspace(1, 0, fade)
    mix = np.tanh(mix * 1.2)                        # gentle limiter
    mix = mix / (np.abs(mix).max() + 1e-9) * 0.89   # peak about -1 dBFS
    pcm = (mix * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
