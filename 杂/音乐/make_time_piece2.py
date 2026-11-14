# -*- coding: utf-8 -*-
"""《时间的三种切分》90s — 与片头 BGM 完全不同的编制：无鼓组、3/4 与 4/4 交替、两个主题对位。
D 多利亚调式。全部合成器音色：正弦叠加 / 玻璃质感长音 / 低音拨弦脉冲。
"""
import math, os
import numpy as np
from scipy import signal as sg
from scipy.io import wavfile
from scipy.signal import fftconvolve

SR = 48000; DUR = 90.0; N = int(SR*DUR)
rng = np.random.RandomState(90210)
HERE = os.path.dirname(os.path.abspath(__file__))
DRY = np.zeros((2,N)); SND = np.zeros((2,N))

def m2f(m): return 440.0*2.0**((m-69)/12.0)

def put(buf, x, t0, pan=0.0):
    i0 = int(t0*SR)
    if i0 >= N: return
    if i0 < 0: x = x[-i0:]; i0 = 0
    ln = min(len(x), N-i0)
    if ln <= 0: return
    pan = max(-0.92, min(0.92, pan))
    gl = math.sqrt((1-pan)*0.5); gr = math.sqrt((1+pan)*0.5)
    buf[0,i0:i0+ln] += x[:ln]*gl; buf[1,i0:i0+ln] += x[:ln]*gr

def addi(f, n, nh=6, tilt=1.4):
    t = np.arange(n)/SR; x = np.zeros(n)
    kmax = int(min(nh, (SR*0.45)/max(f,1.0)))
    for k in range(1, kmax+1):
        x += np.sin(2*np.pi*f*k*t)/(k**tilt)
    return x

def glass(midi, t0, dur, amp, pan=0.0, a=0.06, r=0.9, bright=0.35, verb=0.45):
    f = m2f(midi); nb = int(dur*SR); nr = max(int(r*SR),128); n = nb+nr
    x = addi(f, n, 8, 1.15)
    t = np.arange(n)/SR
    x = x + bright*np.sin(2*np.pi*f*2.98*t)*np.exp(-t*3.2)
    env = np.ones(n)
    na = max(int(a*SR),8); env[:na] = np.linspace(0,1,na)
    env[:nb] *= np.linspace(1.0, 0.55, nb)
    env[nb:] = np.linspace(0.55, 0, nr)
    x = x*env*amp
    b,aa = sg.butter(2, 6200.0/(SR*0.5), btype='lowpass'); y = sg.lfilter(b,aa,x)
    put(DRY, y, t0, pan)
    if verb>0: put(SND, y*verb, t0, pan)

def pad(midis, t0, dur, amp, a=0.4, r=1.2, cut=1500.0, pan=0.0, verb=0.55):
    for i,m in enumerate(midis):
        f = m2f(m); nb = int(dur*SR); nr = max(int(r*SR),128); n = nb+nr
        x = addi(f, n, 6, 1.35)
        env = np.ones(n)
        na = max(int(a*SR),8); env[:na] = np.linspace(0,1,na)
        env[nb:] = np.linspace(1,0,nr)
        y = x*env*amp
        b,aa = sg.butter(2, min(cut/(SR*0.5),0.95), btype='lowpass'); y = sg.lfilter(b,aa,y)
        pp = pan + (i-(len(midis)-1)/2.0)*0.18
        put(DRY, y, t0, pp)
        if verb>0: put(SND, y*verb, t0, pp)

def pulse(midi, t0, amp=0.10, pan=0.0):
    f = m2f(midi); n = int(0.40*SR); t = np.arange(n)/SR
    x = (np.sin(2*np.pi*f*t) + 0.35*np.sin(2*np.pi*2*f*t))*np.exp(-t*9.0)
    na = int(0.004*SR); x[:na] *= np.linspace(0,1,na)
    put(DRY, x*amp, t0, pan); put(SND, x*amp*0.35, t0, pan)

BASS_TRIM = 0.55

def bass(midi, t0, dur, amp, pan=0.0):
    amp = amp*BASS_TRIM
    f = m2f(midi); nb = int(dur*SR); nr = int(0.25*SR); n = nb+nr
    x = addi(f, n, 3, 1.9)
    env = np.ones(n); na = int(0.02*SR); env[:na] = np.linspace(0,1,na)
    env[nb:] = np.linspace(1,0,nr)
    b,aa = sg.butter(2, 380.0/(SR*0.5), btype='lowpass')
    put(DRY, sg.lfilter(b,aa,x*env*amp), t0, pan)

# ---------------- 调式与和声（D 多利亚）----------------
CH = {'Dm':(50,53,57), 'Bb':(46,50,53), 'F':(53,57,60), 'C':(48,52,55), 'Gm':(43,46,50)}
R  = {'Dm':38, 'Bb':34, 'F':41, 'C':36, 'Gm':31}


def shimmer(t0, dur, amp=0.018, base=3136.0, pan=0.0, verb=0.75):
    n = int(dur*SR) + int(0.9*SR); t = np.arange(n)/SR
    x = np.zeros(n)
    for f, g in ((base, 1.0), (base*1.19, 0.65), (base*1.51, 0.45), (base*2.02, 0.3)):
        x += g*np.sin(2*np.pi*f*t)
    env = np.ones(n)
    na = int(1.1*SR); env[:na] = np.linspace(0, 1, na)
    nb = int(dur*SR)
    env[nb:] = np.linspace(1, 0, n-nb)
    put(DRY, x*env*amp, t0, pan)
    put(SND, x*env*amp*0.9, t0, pan)

# ================= 引子 0–12（3/4, 60）：三音动机 =================
pad(CH['Dm'], 0.6, 10.8, 0.050, a=4.0, r=2.5, cut=1100.0, verb=0.7)
bass(38, 0.6, 11.0, 0.070)
for tt, m in ((1.2, 74), (3.6, 69), (6.0, 65)):
    glass(m, tt, 1.9, 0.085, bright=0.30, verb=0.6)
for tt in (0.0, 3.0, 6.0, 9.0):
    pulse(38, tt, amp=0.055)
glass(74, 9.6, 2.2, 0.070, verb=0.6)   # 引出

# ================= A 段 12–32（3/4, 72）：主题 A =================
bA = 60.0/72.0; barA = bA*3
progA = ['Dm','Bb','F','C','Dm','Bb','Gm','Dm']
for k,ch in enumerate(progA):
    t0 = 12.0 + k*barA
    pad(CH[ch], t0, barA*1.02, 0.04, a=0.25, r=0.6, cut=1500.0, verb=0.5)
    bass(R[ch], t0, barA*0.95, 0.100)
    pulse(R[ch], t0, amp=0.075)
    if k % 2 == 1: pulse(R[ch]+7, t0+barA*0.66, amp=0.045)
# 主题 A（长音为主，3/4 摇摆感）
melA = [(0,0.0,74,2.0),(0,2.0,72,1.0),
        (1,0.0,69,3.0),
        (2,0.0,65,2.0),(2,2.0,67,1.0),
        (3,0.0,69,3.0),
        (4,0.0,72,2.0),(4,2.0,71,1.0),
        (5,0.0,69,2.0),(5,2.0,67,1.0),
        (6,0.0,65,2.0),(6,2.0,64,1.0),
        (7,0.0,62,3.0)]
for b_,beat,m,d in melA:
    glass(m, 12.0 + b_*barA + beat*bA, d*bA*0.95, 0.100, bright=0.32, verb=0.5)

# —— 过渡 1（接 B）：共同音 A 悬置 + 上行经过句 ——
pad((57,62,65), 30.6, 2.6, 0.048, a=0.5, r=0.6, cut=2000.0, verb=0.55)
run = [(69,30.9),(71,31.25),(72,31.6),(74,31.95),(76,32.3)]
for m,tt in run:
    glass(m, tt, 0.55, 0.070, a=0.02, bright=0.40, verb=0.45)

# ================= B 段 32.9–54（4/4, 88）：主题 B =================
bB = 60.0/88.0; barB = bB*4
progB = ['F','C','Dm','Bb','F','C','Gm','Dm']
for k,ch in enumerate(progB):
    t0 = 32.9 + k*barB
    pad(CH[ch], t0, barB*1.02, 0.042, a=0.18, r=0.6, cut=1900.0, verb=0.5)
    bass(R[ch], t0, barB*0.9, 0.110)
    for q in (0.0, 2.0):
        pulse(R[ch], t0+q*bB, amp=0.080)
    if k % 2 == 0:
        pulse(R[ch]+7, t0+3.0*bB, amp=0.050)
# 主题 B（大跳、4/4）
melB = [(0,0.0,69,1.0),(0,1.0,74,3.0),
        (1,0.0,72,1.0),(1,1.0,77,3.0),
        (2,0.0,76,2.0),(2,2.0,74,2.0),
        (3,0.0,72,4.0),
        (4,0.0,74,1.0),(4,1.0,79,3.0),
        (5,0.0,77,2.0),(5,2.0,76,2.0),
        (6,0.0,74,2.0),(6,2.0,72,1.0),(6,3.0,69,1.0),
        (7,0.0,74,4.0)]
for b_,beat,m,d in melB:
    glass(m, 32.9 + b_*barB + beat*bB, d*bB*0.95, 0.105, bright=0.34, verb=0.5)

# —— 过渡 2：下行经过句 + 0.45s 留白 ——
fall = [(79,52.4),(77,52.75),(76,53.1),(74,53.45),(72,53.8)]
for m,tt in fall:
    glass(m, tt, 0.55, 0.070, a=0.02, bright=0.36, verb=0.5)

# ================= 发展段 54.9–73（4/4, 92）：两主题对位 =================
bC = 60.0/92.0; barC = bC*4
progC = ['Dm','Bb','F','C','Dm','Bb','F','C']
for k,ch in enumerate(progC):
    t0 = 54.9 + k*barC
    pad(CH[ch], t0, barC*1.02, 0.044, a=0.12, r=0.5, cut=2100.0, verb=0.5)
    bass(R[ch], t0, barC*0.9, 0.115)
    for q in range(4):
        pulse(R[ch], t0+q*bB, amp=0.052 if q%2==0 else 0.034)
# 上层：主题 A 片段（3/4 的旋律压缩进 4/4）
fragA = [(0,0.0,74,2.0),(0,2.0,72,1.5),
         (1,0.0,69,3.0),
         (2,0.0,65,2.0),(2,2.0,67,2.0),
         (3,0.0,69,3.5),
         (4,0.0,72,2.0),(4,2.0,71,1.5),
         (5,0.0,69,3.0),
         (6,0.0,67,2.0),(6,2.0,65,2.0),
         (7,0.0,64,3.5)]
for b_,beat,m,d in fragA:
    glass(m, 54.9 + b_*barC + beat*bC, d*bC*0.92, 0.095, pan=-0.12, bright=0.30, verb=0.5)
# 下层：主题 B 片段做对位（低八度，错开一拍）
fragB = [(0,1.0,69,2.0),(0,3.0,74,1.0),
         (1,1.0,72,2.0),(1,3.0,77,1.0),
         (2,1.0,76,2.0),(2,3.0,74,1.0),
         (3,1.0,72,3.0),
         (4,1.0,74,2.0),(4,3.0,79,1.0),
         (5,1.0,77,2.0),(5,3.0,76,1.0),
         (6,1.0,74,2.0),(6,3.0,72,1.0),
         (7,1.0,69,3.0)]
for b_,beat,m,d in fragB:
    glass(m-12, 54.9 + b_*barC + beat*bC, d*bC*0.92, 0.048, pan=0.16, bright=0.22, verb=0.45)

# —— 过渡 3：涌起 + 留白，进高潮 ——
pad((62,65,69), 71.4, 2.0, 0.050, a=0.35, r=0.4, cut=2600.0, verb=0.6)
rise = [(69,71.6),(72,71.9),(74,72.2),(77,72.5)]
for m,tt in rise:
    glass(m, tt, 0.6, 0.075, a=0.02, bright=0.42, verb=0.5)

# ================= 再现 73.4–84：主题 A 回归（加厚）=================
progD = ['Dm','Bb','F','C']
for k,ch in enumerate(progD):
    t0 = 73.4 + k*barC
    pad(CH[ch], t0, barC*1.02, 0.046, a=0.10, r=0.5, cut=2400.0, verb=0.55)
    bass(R[ch], t0, barC*0.9, 0.120)
    for q in range(4):
        pulse(R[ch], t0+q*bB, amp=0.056 if q%2==0 else 0.036)
for b_,beat,m,d in melA[:8]:
    glass(m, 73.4 + b_*barC + beat*bC, d*bC*0.92, 0.108, pan=-0.06, bright=0.36, verb=0.5)

# ================= 尾声 84–90（3/4, 60）：回到三音动机 =================
bE = 60.0/60.0; barE = bE*3
pad(CH['Dm'], 84.0, 5.4, 0.055, a=0.8, r=2.2, cut=1300.0, verb=0.75)
bass(38, 84.0, 5.2, 0.080)
for tt,m,d in ((84.4,74,1.9),(86.8,69,1.9),(89.2,65,1.4)):
    glass(m, tt, d, 0.092, bright=0.30, verb=0.7)
for tt in (84.4, 87.4):
    pulse(38, tt, amp=0.060)


# ---- 高音微光：只保留第一段，且大幅减量（原先是蝉鸣的来源）----
shimmer(0.8, 11.0, amp=0.007, base=3136.0, pan=-0.45)

# ================= 混响 / 母带 =================
def make_ir(sec=2.6, damp=5200.0):
    n = int(sec*SR); tt = np.arange(n)/SR
    ir = rng.randn(2,n)*np.exp(-tt*3.8)
    b,a = sg.butter(2, damp/(SR*0.5)); ir = sg.lfilter(b,a,ir,axis=1)
    return ir/np.max(np.abs(ir))

IR = make_ir()
WET = np.zeros((2,N))
for ch in (0,1):
    WET[ch] = fftconvolve(SND[ch], IR[ch])[:N]
_d = np.sqrt((DRY**2).mean()); _w = np.sqrt((WET**2).mean())
if _w>1e-9 and _d>1e-9: WET *= (_d*10**(-12.0/20.0))/_w
mix = DRY + WET

# 存在感：玻璃音本来偏暗，给 1–6k 一点抬升
b,a = sg.butter(2, [1200.0/(SR*0.5), 6000.0/(SR*0.5)], btype='bandpass')
mix += sg.lfilter(b,a,mix,axis=1)*0.45
b,a = sg.butter(2, 3000.0/(SR*0.5), btype='lowpass')
low = sg.lfilter(b,a,mix,axis=1); mix = low + (mix-low)*1.30

b, a = sg.butter(2, 38.0/(SR*0.5), btype='highpass')
mix = sg.lfilter(b, a, mix, axis=1)

fade = np.ones(N)
ni, no = int(SR*0.02), int(SR*1.2)
fade[:ni] = np.linspace(0,1,ni); fade[-no:] = np.linspace(1,0,no)
mix *= fade
mix = mix/np.max(np.abs(mix))*0.90
mix = np.tanh(mix*1.02)/np.tanh(1.02)
mix = mix/np.max(np.abs(mix))*0.89

out = os.path.join(HERE,'TimePiece2_90s.wav')
wavfile.write(out, SR, (mix.T*32767).astype(np.int16))
print('wrote %s  peak %.3f  rms %.1f dB' % (out, np.max(np.abs(mix)), 20*math.log10(np.sqrt((mix**2).mean()))))
