import os
import threading
import time
import sys
import numpy as np
from lib import tlog
from engine.file import resource_path

# Try to import audio backends
BACKEND = None

try:
    import pygame
    pygame.mixer.init()
    BACKEND = "pygame"
    tlog.info("SoundManager: Using pygame backend.")
except ImportError:
    try:
        import miniaudio
        BACKEND = "miniaudio"
        tlog.info("SoundManager: Using miniaudio backend.")
    except ImportError:
        tlog.warn("SoundManager: No audio backend found (pygame or miniaudio). Sound will be disabled.")
        BACKEND = None

class Voice:
    def __init__(self, sound_data, volume, loop, low_pass):
        self.sound_data = sound_data
        self.volume = volume
        self.loop = loop
        self.lp_amount = max(0.0, min(1.0, low_pass)) # CLAMP TO PREVENT OVERFLOW
        self.playing = True
        
        try:
            self.samples = np.array(sound_data.samples, dtype=np.int16)
        except:
            self.samples = np.frombuffer(sound_data.samples, dtype=np.int16)
            
        self.offset = 0
        self.nchannels = sound_data.nchannels
        self.last_y = np.zeros(self.nchannels, dtype=np.float32)
        # Filter alpha: 1.0 (no filter) to 0.05 (heavy filter)
        self.alpha = 1.0 - (self.lp_amount * 0.95)

    def stop(self):
        self.playing = False

class SoundHandle:
    def __init__(self, voice):
        self.voice = voice
    
    def stop(self):
        if self.voice:
            self.voice.stop()

    def set_volume(self, volume):
        if self.voice:
            self.voice.volume = volume

class SoundManager:
    _instance = None
    
    def __init__(self):
        self.sounds = {} 
        self.volume = 1.0
        self.active_voices = []
        self._lock = threading.Lock()
        self._device = None
        self._gen = None
        print(f"[AUDIO] SoundManager initialized at {id(self)}")

    @classmethod
    def get(cls):
        if cls._instance is None:
            cls._instance = SoundManager()
        return cls._instance

    def _ensure_device(self, sample_rate, nchannels):
        if self._device is not None:
            return
            
        if BACKEND == "miniaudio":
            import miniaudio
            try:
                self._device = miniaudio.PlaybackDevice(
                    sample_rate=sample_rate,
                    nchannels=nchannels
                )
                
                def mixer_gen(manager):
                    required_frames = yield b""
                    while True:
                        if required_frames is None or required_frames <= 0:
                            required_frames = yield b""
                            continue
                            
                        num_samples = required_frames * nchannels
                        mix_buffer = np.zeros(num_samples, dtype=np.float32)
                        
                        with manager._lock:
                            for v in manager.active_voices[:]:
                                if not v.playing:
                                    manager.active_voices.remove(v)
                                    continue
                                
                                end_idx = v.offset + num_samples
                                chunk = None
                                
                                if end_idx > len(v.samples):
                                    if v.loop:
                                        part1 = v.samples[v.offset:]
                                        wrap = num_samples - len(part1)
                                        v.offset = wrap % len(v.samples)
                                        part2 = v.samples[:v.offset]
                                        chunk = np.concatenate([part1, part2])
                                    else:
                                        chunk = v.samples[v.offset:]
                                        v.playing = False 
                                else:
                                    chunk = v.samples[v.offset:end_idx]
                                    v.offset = end_idx
                                
                                if chunk is not None and len(chunk) > 0:
                                    if len(chunk) < num_samples:
                                        chunk = np.pad(chunk, (0, num_samples - len(chunk)))
                                        
                                    chunk_f = chunk.astype(np.float32) * v.volume * manager.volume
                                    
                                    if v.lp_amount > 0.01:
                                        chunk_f = chunk_f.reshape(-1, nchannels)
                                        for n in range(chunk_f.shape[0]):
                                            # Using the pre-clamped alpha
                                            v.last_y = v.alpha * chunk_f[n] + (1.0 - v.alpha) * v.last_y
                                            chunk_f[n] = v.last_y
                                        chunk_f = chunk_f.flatten()
                                        
                                    mix_buffer += chunk_f

                        out_bytes = np.clip(mix_buffer, -32768, 32767).astype(np.int16).tobytes()
                        required_frames = yield out_bytes

                self._gen = mixer_gen(self)
                next(self._gen)
                self._device.start(self._gen)
                print("[AUDIO] Global mixer started.")
            except Exception as e:
                print(f"[AUDIO] Critical Error: {e}", file=sys.stderr)

    def load(self, path: str, name: str = None):
        if not BACKEND: return
        key = name or path
        if key in self.sounds: return
        full_path = resource_path(path)
        try:
            if BACKEND == "pygame":
                self.sounds[key] = pygame.mixer.Sound(full_path)
                print(f"[AUDIO] Loaded (pygame): {key} from {full_path}")
            elif BACKEND == "miniaudio":
                import miniaudio
                decoded = miniaudio.decode_file(full_path)
                self.sounds[key] = decoded
                print(f"[AUDIO] Loaded (miniaudio): {key} from {full_path} (keys now: {list(self.sounds.keys())})")
                self._ensure_device(decoded.sample_rate, decoded.nchannels)
        except Exception as e:
            print(f"[AUDIO] Load error {full_path}: {e}")

    def play(self, name: str, volume: float = 1.0, loop: bool = False, low_pass: float = 0.0) -> SoundHandle:
        if not BACKEND: return SoundHandle(None)
        s = self.sounds.get(name)
        if not s:
            print(f"[AUDIO] Warning: Sound '{name}' not found.")
            return SoundHandle(None)

        if BACKEND == "pygame":
            s.set_volume(volume * self.volume)
            s.play(loops=-1 if loop else 0)
            return SoundHandle(None) 
        else:
            voice = Voice(s, volume, loop, low_pass)
            with self._lock:
                self.active_voices.append(voice)
            return SoundHandle(voice)

    def set_global_volume(self, v: float):
        self.volume = max(0.0, min(1.0, v))
