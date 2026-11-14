# -*- coding: utf-8 -*-
"""以“时间”为主题的 90 秒纯音乐。与片头/宣发片无关，独立作品。
全部音色为合成器：正弦叠加 / 2 算子 FM / 短门限噪声打击。
"""
import math, os
import numpy as np
from scipy import signal as sg
from scipy.io import wavfile
from scipy.signal import fftconvolve

SR = 48000
DUR = 90.0
N = int(SR * DUR)
rng = np.random.RandomState(31415)
HERE = os.path.dirname(os.path.abspath(__file__))
DRY = np.zeros((2, N)); SND = np.zeros((2, N))

def m2f(m): return 440.0 * 2.0 ** ((m - 69) / 12.0)

def put(buf, x, t0, pan=0.0):
    i0 = int(t0 * SR)
    if i0 >= N: return
    if i0 < 0: x = x[-i0:]; i0 = 0
    ln = min(len(x), N - i0)
    if ln <= 0: return
    pan = max(-0.92, min(0.92, pan))
    gl = math.sqrt((1.0 - pan) * 0.5); gr = math.sqrt((1.0 + pan) * 0.5)
    buf[0, i0:i0 + ln] += x[:ln] * gl
    buf[1, i0:i0 + ln] += x[:ln] * gr

def additive(f, n, nharm=6, tilt=1.35):
    t = np.arange(n) / SR
    x = np.zeros(n)
    kmax = int(min(nharm, (SR * 0.45) / max(f, 1.0)))
    for k in range(1, kmax + 1):
        x += np.sin(2 * np.pi * f * k * t) / (k ** tilt)
    return x

def pad(midis, t0, dur, amp, a=0.30, r=1.0, cut=1600.0, pan=0.0, verb=0.5, nh=6):
    for i, m in enumerate(midis):
        f = m2f(m); nb = int(dur * SR); nr = max(int(r * SR), 128); n = nb + nr
        x = additive(f, n, nh)
        env = np.ones(n)
        na = max(int(a * SR), 8); env[:na] = np.linspace(0, 1, na)
        env[nb:] = np.linspace(1, 0, nr)
        x = x * env * amp
        b, aa = sg.butter(2, min(cut / (SR * 0.5), 0.95), btype='lowpass')
        y = sg.lfilter(b, aa, x)
        pp = pan + (i - (len(midis) - 1) / 2.0) * 0.16
        put(DRY, y, t0, pp)
        if verb > 0: put(SND, y * verb, t0, pp)

def lead(midi, t0, dur, amp, pan=0.0, verb=0.45, r=0.70, bright=1.0):
    f = m2f(midi); nb = int(dur * SR); nr = max(int(r * SR), 128); n = nb + nr
    t = np.arange(n) / SR
    idx = 1.15 * np.exp(-t * 5.5) * bright
    x = np.sin(2 * np.pi * f * t + idx * np.sin(2 * np.pi * f * t))
    x += 0.22 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t * 9.0)
    env = np.ones(n)
    na = max(int(0.028 * SR), 8); env[:na] = np.linspace(0, 1, na)
    env[:nb] *= np.linspace(1.0, 0.62, nb)
    env[nb:] = np.linspace(0.62, 0, nr)
    x = x * env * amp
    put(DRY, x, t0, pan)
    if verb > 0: put(SND, x * verb, t0, pan)

def bass(midi, t0, dur, amp, pan=0.0):
    f = m2f(midi)
    nb = int(dur * SR); nr = int(0.20 * SR); n = nb + nr
    x = additive(f, n, 3, 1.8)
    env = np.ones(n)
    na = int(0.012 * SR); env[:na] = np.linspace(0, 1, na)
    env[nb:] = np.linspace(1, 0, nr)
    b, aa = sg.butter(2, 420.0 / (SR * 0.5), btype='lowpass')
    y = sg.lfilter(b, aa, x * env * amp)
    put(DRY, y, t0, pan)

def tock(t0, amp=0.10, pan=0.0, hi=False):
    f = 1290.0 if hi else 470.0
    n = int(0.030 * SR); t = np.arange(n) / SR
    x = (np.sin(2 * np.pi * f * t) + 0.30 * np.sin(2 * np.pi * f * 2.0 * t)) * np.exp(-t * 130.0)
    na = int(0.0015 * SR); x[:na] *= np.linspace(0, 1, na)
    put(DRY, x * amp, t0, pan)
    put(SND, x * amp * 0.25, t0, pan)

def kick(t0, amp=0.55):
    n = int(0.36 * SR); t = np.arange(n) / SR
    fr = 46.0 + 92.0 * np.exp(-t * 26.0)
    ph = np.cumsum(2 * np.pi * fr / SR)
    x = np.sin(ph) * np.exp(-t * 7.5)
    put(DRY, x * amp * 0.70, t0, 0.0)

def hat(t0, amp=0.045, pan=0.0, dur=0.045, hp=7200.0):
    n = int(dur * SR); t = np.arange(n) / SR
    x = rng.randn(n) * np.exp(-t * 110.0)
    b, a = sg.butter(2, hp / (SR * 0.5), btype='highpass'); x = sg.lfilter(b, a, x)
    b, a = sg.butter(2, 15000.0 / (SR * 0.5), btype='lowpass'); x = sg.lfilter(b, a, x)
    put(DRY, x * amp, t0, pan)

def clap(t0, amp=0.10, pan=0.05):
    n = int(0.16 * SR); t = np.arange(n) / SR
    x = rng.randn(n)
    b, a = sg.butter(2, [900.0 / (SR * 0.5), 4200.0 / (SR * 0.5)], btype='bandpass')
    x = sg.lfilter(b, a, x)
    e = np.zeros(n)
    for d in (0.0, 0.010, 0.022):
        i0 = int(d * SR); seg = np.exp(-np.arange(n - i0) / SR * 70.0); e[i0:] += seg[:n - i0]
    x = x * e * amp
    put(DRY, x, t0, pan); put(SND, x * 0.5, t0, pan)

CH = {'Am': (45, 48, 52), 'F': (41, 45, 48), 'C': (48, 52, 55), 'G': (43, 47, 50), 'Em': (40, 43, 47)}
ROOT = {'Am': 33, 'F': 29, 'C': 36, 'G': 31, 'Em': 28}

# ================= A 段 0–16：钟摆与呼吸（58 BPM）=================
bpmA = 58.0; ba = 60.0 / bpmA
t = 0.5
i = 0
while t < 15.5:
    tock(t, amp=0.115 if i % 2 == 0 else 0.070, pan=0.0)
    t += ba * 2.0; i += 1
pad((45, 48, 52), 1.0, 14.0, 0.052, a=4.0, r=2.0, cut=1200.0, verb=0.65)
bass(33, 0.5, 15.0, 0.075)
lead(76, 6.20, 3.2, 0.075, verb=0.55)      # 第一个“意识”
lead(81, 11.40, 3.0, 0.070, verb=0.55)

# ================= B 段 16–40：主题 A（72 BPM）=================
bpmB = 72.0; bb = 60.0 / bpmB; barB = bb * 4
progB = ['Am', 'F', 'C', 'G', 'Am', 'F', 'C', 'G', 'Am']
for k, ch in enumerate(progB):
    t0 = 16.0 + k * barB
    if t0 > 39.0: break
    pad(CH[ch], t0, barB * 0.98, 0.055, a=0.18, r=0.7, cut=1500.0, verb=0.5)
    bass(ROOT[ch], t0, barB * 0.9, 0.105)
    if k % 2 == 0:
        bass(ROOT[ch] + 7, t0 + barB * 0.5, barB * 0.4, 0.070)
    for bt2 in (0.0, 2.0):
        kick(t0 + bt2 * bb, amp=0.42)
    for bt2 in (1.0, 3.0):
        clap(t0 + bt2 * bb, amp=0.070)
    st = 0.0
    while st < 4.0:
        hat(t0 + st * bb, amp=0.036 if abs(st - 2.0) < 0.01 else 0.022, pan=(-0.2 if int(st) % 2 else 0.2))
        st += 1.0
    tock(t0 + 0.0, amp=0.040, hi=True)

# 主题 A：4 小节一句，两句
def phraseA(t0, step):
    seq = [(0, 0.0, 69, 2.0), (0, 2.0, 72, 1.0), (0, 3.0, 76, 1.0),
           (1, 0.0, 74, 2.0), (1, 2.0, 72, 1.0), (1, 3.0, 71, 1.0),
           (2, 0.0, 69, 1.5), (2, 1.5, 67, 0.5), (2, 2.0, 69, 2.0),
           (3, 0.0, 76, 4.0)]
    for b_, beat, m, d in seq:
        lead(m, t0 + b_ * barB + beat * bb, d * bb * 0.95, 0.115, verb=0.5)
phraseA(16.0 + 2 * barB, 0)
phraseA(16.0 + 6 * barB, 0)

# ================= C 段 40–56：加速（84→96）=================
t = 40.0; bcur = 60.0 / 84.0
progC = ['Am', 'F', 'C', 'G'] * 3
ki = 0
while t < 55.4 and ki < len(progC):
    ch = progC[ki]
    bar = bcur * 4
    pad(CH[ch], t, bar * 0.95, 0.058, a=0.10, r=0.5, cut=1800.0, verb=0.45)
    bass(ROOT[ch], t, bar * 0.9, 0.115)
    for q in range(4):
        kick(t + q * bcur, amp=0.46 + 0.02 * ki)
    for q in (1, 3):
        clap(t + q * bcur, amp=0.082)
    st = 0.0
    while st < 4.0:
        hat(t + st * bcur, amp=0.040 if abs(st - 2.0) < 0.01 else 0.026, pan=(-0.24 if int(st * 2) % 2 else 0.24))
        st += 0.5
    t += bar; ki += 1
    bcur = max(60.0 / 96.0, bcur * 0.985)          # 逐渐加快
# 上升的旋律线
riseT = 40.5
for m in (72, 74, 76, 77, 79, 81, 84):
    lead(m, riseT, 1.1, 0.100, verb=0.45)
    riseT += 2.05

# ================= D 段 56–68：高潮，主题 B（96 BPM）=================
bpmD = 96.0; bd = 60.0 / bpmD; barD = bd * 4
progD = ['F', 'G', 'Am', 'Am', 'F', 'G', 'Am']
for k, ch in enumerate(progD):
    t0 = 56.0 + k * barD
    if t0 > 67.4: break
    pad(CH[ch], t0, barD * 0.98, 0.062, a=0.09, r=0.5, cut=2200.0, verb=0.5)
    bass(ROOT[ch], t0, barD * 0.9, 0.125)
    for q in range(4):
        kick(t0 + q * bd, amp=0.50)
    for q in (1, 3):
        clap(t0 + q * bd, amp=0.090)
    st = 0.0
    while st < 4.0:
        hat(t0 + st * bd, amp=0.042 if abs(st - 2.0) < 0.01 else 0.028, pan=(-0.26 if int(st * 2) % 2 else 0.26))
        st += 0.5
seqB = [(0, 0.0, 76, 2.0), (0, 2.0, 79, 1.0), (0, 3.0, 81, 1.0),
        (1, 0.0, 79, 2.0), (1, 2.0, 76, 2.0),
        (2, 0.0, 77, 2.0), (2, 2.0, 76, 1.0), (2, 3.0, 74, 1.0),
        (3, 0.0, 72, 4.0)]
for k in (0, 4):
    for b_, beat, m, d in seqB:
        lead(m, 56.0 + (k + b_) * barD + beat * bd, d * bd * 0.95, 0.125, verb=0.5)

# ================= E 段 68–76：时间慢下来 =================
t = 68.0; beat = bd
slow = []
while t < 76.2:
    slow.append(t)
    beat = beat * 1.085                     # 每拍越来越长
    t += beat
score = 1.0
for idx, tt in enumerate(slow):
    kick(tt, amp=0.46 * (1.0 - idx / (len(slow) + 2)))
    tock(tt + beat * 0.5, amp=0.05, hi=True)
pad((45, 48, 52), 68.0, 7.6, 0.058, a=0.4, r=2.0, cut=1400.0, verb=0.65)
bass(33, 68.0, 7.6, 0.090)
lead(76, 69.4, 2.6, 0.100, verb=0.6)
lead(72, 72.6, 2.4, 0.095, verb=0.6)
lead(74, 75.0, 2.6, 0.090, verb=0.65)

# ================= F 段 76–90：只剩钟摆 =================
bpmF = 44.0; bf = 60.0 / bpmF
t = 76.6; i = 0
while t < 89.0:
    tock(t, amp=0.105 if i % 2 == 0 else 0.062)
    t += bf; i += 1
pad((45, 48, 52, 57), 76.8, 12.4, 0.050, a=1.2, r=3.0, cut=1100.0, verb=0.75)
bass(33, 76.8, 12.0, 0.070)
for m, tt, d in ((69, 78.4, 2.6), (72, 81.8, 2.6), (76, 85.2, 2.8), (69, 87.6, 3.0)):
    lead(m, tt, d, 0.098, verb=0.65)
tock(89.6, amp=0.11)

# ================= 混响 / 母带 =================
def make_ir(sec=2.4, damp=5000.0):
    n = int(sec * SR); tt = np.arange(n) / SR
    ir = rng.randn(2, n) * np.exp(-tt * 4.0)
    b, a = sg.butter(2, damp / (SR * 0.5)); ir = sg.lfilter(b, a, ir, axis=1)
    return ir / np.max(np.abs(ir))

IR = make_ir()
WET = np.zeros((2, N))
for ch in (0, 1):
    WET[ch] = fftconvolve(SND[ch], IR[ch])[:N]
_d = np.sqrt((DRY ** 2).mean()); _w = np.sqrt((WET ** 2).mean())
if _w > 1e-9 and _d > 1e-9:
    WET *= (_d * 10 ** (-13.0 / 20.0)) / _w
mix = DRY + WET

# 存在感均衡（与参考 BGM 的倾斜一致）
b, a = sg.butter(2, [900.0 / (SR * 0.5), 3000.0 / (SR * 0.5)], btype='bandpass')
mix += sg.lfilter(b, a, mix, axis=1) * 0.30
b, a = sg.butter(2, 2600.0 / (SR * 0.5), btype='lowpass')
low = sg.lfilter(b, a, mix, axis=1)
mix = low + (mix - low) * 1.25

fade = np.ones(N)
ni, no = int(SR * 0.02), int(SR * 0.8)
fade[:ni] = np.linspace(0, 1, ni); fade[-no:] = np.linspace(1, 0, no)
mix *= fade
mix = mix / np.max(np.abs(mix)) * 0.90
mix = np.tanh(mix * 1.03) / np.tanh(1.03)
mix = mix / np.max(np.abs(mix)) * 0.89

out = os.path.join(HERE, 'TimePiece_90s.wav')
wavfile.write(out, SR, (mix.T * 32767).astype(np.int16))
print('wrote %s  peak %.3f  rms %.1f dB  dur %.2fs' % (out, np.max(np.abs(mix)), 20*math.log10(np.sqrt((mix**2).mean())), N/SR))
