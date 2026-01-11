import os, threading, time, sys
import numpy as np
from lib import tlog
from engine.file import resource_path

BACKEND = None
try:
    import pygame; pygame.mixer.init(); BACKEND = "pygame"
except:
    try: import miniaudio; BACKEND = "miniaudio"
    except: BACKEND = None

class Voice:
    def __init__(self, data, volume, loop, low_pass):
        self.data, self.volume, self.loop, self.lp_amount = data, volume, loop, max(0.0, min(1.0, low_pass))
        self.playing, self.offset = True, 0
        try: self.samples = np.array(data.samples, dtype=np.int16)
        except: self.samples = np.frombuffer(data.samples, dtype=np.int16)
        self.last_y = np.zeros(data.nchannels, dtype=np.float32)
        self.alpha = 1.0 - (self.lp_amount * 0.95)
    def stop(self): self.playing = False

class SoundHandle:
    def __init__(self, voice): self.voice = voice
    def stop(self):
        if self.voice: self.voice.stop()
    def set_volume(self, v):
        if self.voice: self.voice.volume = v

class SoundManager:
    _instance = None
    def __init__(self):
        self.sounds, self.volume, self.active_voices = {}, 1.0, []
        self._lock, self._device, self._gen = threading.Lock(), None, None

    @classmethod
    def get(cls):
        if cls._instance is None: cls._instance = SoundManager()
        return cls._instance

    def _ensure_device(self, sr, nch):
        if self._device or BACKEND != "miniaudio": return
        import miniaudio
        try:
            self._device = miniaudio.PlaybackDevice(sample_rate=sr, nchannels=nch)
            def mixer_gen(mgr):
                req = yield b""
                while True:
                    if not req or req <= 0: req = yield b""; continue
                    buf = np.zeros(req * nch, dtype=np.float32)
                    with mgr._lock:
                        for v in mgr.active_voices[:]:
                            if not v.playing: mgr.active_voices.remove(v); continue
                            end = v.offset + req * nch; chunk = None
                            if end > len(v.samples):
                                if v.loop:
                                    p1 = v.samples[v.offset:]; v.offset = (req * nch - len(p1)) % len(v.samples)
                                    chunk = np.concatenate([p1, v.samples[:v.offset]])
                                else: chunk = v.samples[v.offset:]; v.playing = False
                            else: chunk = v.samples[v.offset:end]; v.offset = end
                            if chunk is not None and len(chunk) > 0:
                                if len(chunk) < req * nch: chunk = np.pad(chunk, (0, req * nch - len(chunk)))
                                c_f = chunk.astype(np.float32) * v.volume * mgr.volume
                                if v.lp_amount > 0.01:
                                    c_f = c_f.reshape(-1, nch)
                                    for n in range(c_f.shape[0]): v.last_y = v.alpha * c_f[n] + (1.0 - v.alpha) * v.last_y; c_f[n] = v.last_y
                                    c_f = c_f.flatten()
                                buf += c_f
                    req = yield np.clip(buf, -32768, 32767).astype(np.int16).tobytes()
            self._gen = mixer_gen(self); next(self._gen); self._device.start(self._gen)
        except Exception as e: print(f"[AUDIO] Error: {e}", file=sys.stderr)

    def load(self, path, name=None):
        if not BACKEND: return
        k = name or path
        if k in self.sounds: return
        fp = resource_path(path)
        try:
            if BACKEND == "pygame": self.sounds[k] = pygame.mixer.Sound(fp)
            else:
                import miniaudio; d = miniaudio.decode_file(fp); self.sounds[k] = d
                self._ensure_device(d.sample_rate, d.nchannels)
        except Exception as e: print(f"[AUDIO] Load error {fp}: {e}")

    def play(self, name, volume=1.0, loop=False, low_pass=0.0):
        if not BACKEND: return SoundHandle(None)
        s = self.sounds.get(name)
        if not s: return SoundHandle(None)
        if BACKEND == "pygame": s.set_volume(volume * self.volume); s.play(loops=-1 if loop else 0); return SoundHandle(None)
        v = Voice(s, volume, loop, low_pass)
        with self._lock: self.active_voices.append(v)
        return SoundHandle(v)

    def set_global_volume(self, v): self.volume = max(0.0, min(1.0, v))