"""音樂與音效管理。

設計重點：
- SFX：assets/audio/<name>.wav (或 .ogg) 存在則用；不存在則用 numpy 合成嗶聲。
- BGM：assets/audio/bgm_<name>.{ogg,wav,mp3} 存在則播；不存在則靜音。
- 整個模組失敗不會 crash，呼叫端用 try/except 包起來即可。

放音樂方式：把檔案丟到 assets/audio/，命名為
  bgm_menu.ogg / bgm_level1.ogg / bgm_level2.ogg / bgm_level3.ogg
即可自動播放（也支援 .wav / .mp3）。
"""
import math
import os

import pygame

try:
    import numpy as np
except ImportError:
    np = None


_AUDIO_DIR = os.path.join(os.path.dirname(__file__), "assets", "audio")
_sfx = {}
_current_bgm = None
_enabled = False


def init():
    """在 pygame.init() 之後呼叫。失敗會 print 警告但不丟例外。"""
    global _enabled
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        _enabled = True
    except pygame.error as e:
        print(f"[警告] 音訊初始化失敗：{e}（將靜音執行）")
        return
    if not os.path.isdir(_AUDIO_DIR):
        print(f"[提示] 找不到 {_AUDIO_DIR}；BGM 將為靜音。"
              "\n        把 .ogg/.wav 放進去並命名為 bgm_menu / bgm_level1..3 可啟用音樂。")
    _load_sfx()


def _synth(freq, duration, decay, square=False, vol=0.3):
    """用 numpy 合成單聲帶嗶聲；無 numpy 時回傳 None。"""
    if np is None:
        return None
    sr = 44100
    n = max(1, int(sr * duration))
    t = np.linspace(0, duration, n, endpoint=False)
    if square:
        wave = np.sign(np.sin(2 * math.pi * freq * t))
    else:
        wave = np.sin(2 * math.pi * freq * t)
    env = np.exp(-t * decay)
    audio = (wave * env * vol * 32767).astype(np.int16)
    stereo = np.column_stack([audio, audio])
    try:
        return pygame.sndarray.make_sound(stereo)
    except Exception as e:
        print(f"[警告] sndarray 失敗：{e}")
        return None


def _load_sfx():
    # (檔名, 合成 fallback)
    defaults = {
        "blip":   ("blip.wav",   lambda: _synth(600, 0.03, 80, square=True, vol=0.18)),
        "select": ("select.wav", lambda: _synth(1200, 0.08, 25, vol=0.35)),
        "menu":   ("menu.wav",   lambda: _synth(900, 0.05, 40, vol=0.28)),
        "hit":    ("hit.wav",    lambda: _synth(180, 0.20, 12, square=True, vol=0.45)),
        "heal":   ("heal.wav",   lambda: _synth(1500, 0.18, 8, vol=0.35)),
        "spare":  ("spare.wav",  lambda: _synth(1800, 0.30, 5, vol=0.4)),
    }
    for name, (fname, fallback) in defaults.items():
        path = os.path.join(_AUDIO_DIR, fname)
        snd = None
        if os.path.exists(path):
            try:
                snd = pygame.mixer.Sound(path)
            except pygame.error:
                snd = None
        if snd is None:
            snd = fallback()
        if snd is not None:
            _sfx[name] = snd


def play_sfx(name, volume=None):
    if not _enabled:
        return
    s = _sfx.get(name)
    if s is None:
        return
    if volume is not None:
        s.set_volume(volume)
    s.play()


def play_bgm(name, loop=True, volume=0.4):
    """name 例如 'menu' / 'level1' / 'level2' / 'level3'。同名重複呼叫不會中斷。"""
    global _current_bgm
    if not _enabled:
        return
    if _current_bgm == name:
        return
    for ext in (".ogg", ".wav", ".mp3"):
        path = os.path.join(_AUDIO_DIR, f"bgm_{name}{ext}")
        if os.path.exists(path):
            try:
                pygame.mixer.music.load(path)
                pygame.mixer.music.set_volume(volume)
                pygame.mixer.music.play(-1 if loop else 0)
                _current_bgm = name
                return
            except pygame.error as e:
                print(f"[警告] BGM 載入失敗 {path}：{e}")
                return
    # 找不到檔 → 靜音
    pygame.mixer.music.stop()
    _current_bgm = None


def stop_bgm():
    global _current_bgm
    if not _enabled:
        return
    pygame.mixer.music.stop()
    _current_bgm = None
