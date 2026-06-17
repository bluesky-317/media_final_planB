"""遊戲畫面後製特效 (純 OpenCV)。

直接吃 / 吐 BGR ndarray;不再經過 pygame Surface round-trip。
所有效果都用計時器觸發;沒有效果活躍時 ``apply`` 直接 bypass,不付 cv2 成本。

效果一覽:
    damage_flash      受傷紅色 + Gaussian 模糊 (重傷時加 cv2.blur 馬賽克)
    sans_wave         Sans 階段 sin 波 cv2.remap
    glitch_burst      色差 split/warpAffine/merge + Laplacian 鬼影
    pixelate          進關 / 結算的 cv2.resize 像素化
    victory_shockwave 勝利瞬間 cv2.warpPolar 環狀錯動
    defeat_edges      GAME OVER 持續 Sobel 邊緣強化 + 冷藍色調
"""
import math
import random

import cv2
import numpy as np

import config


_DAMAGE_DUR = 0.30
_VICTORY_DUR = 1.0
_TRANSITION_DUR = 0.45
_GLITCH_DUR = 0.08


class PostFX:
    def __init__(self):
        self.t = 0.0
        self.damage_t = 0.0
        self.heavy_damage = False
        self.victory_t = 0.0
        self.defeat_active = False
        self.transition_t = 0.0
        self.sans_wave_active = False
        self.glitch_t = 0.0
        self._next_glitch_t = 0.0

        h, w = config.SCREEN_HEIGHT, config.SCREEN_WIDTH
        xs = np.arange(w, dtype=np.float32)
        ys = np.arange(h, dtype=np.float32)
        self._map_x_base, self._map_y_base = np.meshgrid(xs, ys)

    # ------------------------------------------------------------------
    def trigger_damage(self, severe=False):
        self.damage_t = _DAMAGE_DUR
        self.heavy_damage = severe

    def trigger_victory(self):
        self.victory_t = _VICTORY_DUR

    def set_defeat(self, on):
        self.defeat_active = bool(on)

    def trigger_transition(self):
        self.transition_t = _TRANSITION_DUR

    def trigger_glitch(self):
        self.glitch_t = _GLITCH_DUR

    def set_sans_wave(self, on):
        on = bool(on)
        if on and not self.sans_wave_active:
            self.glitch_t = _GLITCH_DUR
            self._next_glitch_t = self.t + random.uniform(2.0, 4.0)
        self.sans_wave_active = on

    # ------------------------------------------------------------------
    def update(self, dt):
        self.t += dt
        if self.damage_t > 0:
            self.damage_t = max(0.0, self.damage_t - dt)
        if self.victory_t > 0:
            self.victory_t = max(0.0, self.victory_t - dt)
        if self.transition_t > 0:
            self.transition_t = max(0.0, self.transition_t - dt)
        if self.glitch_t > 0:
            self.glitch_t = max(0.0, self.glitch_t - dt)
        if self.sans_wave_active and self.t >= self._next_glitch_t:
            self.trigger_glitch()
            self._next_glitch_t = self.t + random.uniform(2.5, 5.0)

    def _has_active(self):
        return (self.damage_t > 0
                or self.victory_t > 0
                or self.defeat_active
                or self.transition_t > 0
                or self.sans_wave_active
                or self.glitch_t > 0)

    # ------------------------------------------------------------------
    def apply(self, bgr):
        """無效果時直接回傳同一張影像;有效果時逐層套用後回傳新的 BGR 陣列。"""
        if not self._has_active():
            return bgr

        img = bgr  # 已經是 BGR ndarray
        if self.sans_wave_active:
            img = self._fx_sans_wave(img)
        if self.damage_t > 0:
            img = self._fx_damage(img)
        if self.glitch_t > 0:
            img = self._fx_glitch(img)
        if self.defeat_active:
            img = self._fx_defeat(img)
        if self.victory_t > 0:
            img = self._fx_victory(img)
        if self.transition_t > 0:
            img = self._fx_pixelate(img)
        return img

    # ------------------------------------------------------------------
    def _fx_damage(self, img):
        s = self.damage_t / _DAMAGE_DUR
        blurred = cv2.GaussianBlur(img, (0, 0), 3.5 * s + 0.1)
        red = np.zeros_like(img)
        red[:, :, 2] = 255
        out = cv2.addWeighted(blurred, 1.0 - 0.30 * s, red, 0.30 * s, 0.0)
        if self.heavy_damage:
            block = max(3, int(14 * s))
            mosaic = cv2.blur(out, (block, block))
            out = cv2.addWeighted(out, 1.0 - 0.55 * s, mosaic, 0.55 * s, 0.0)
        return out

    def _fx_sans_wave(self, img):
        amp = 5.5
        freq = 2 * math.pi / 90
        t = self.t * 3.0
        dx = (amp * np.sin(self._map_y_base * freq + t)).astype(np.float32)
        dy = (amp * 0.5 * np.cos(self._map_x_base * freq + t * 1.3)).astype(np.float32)
        map_x = self._map_x_base + dx
        map_y = self._map_y_base + dy
        return cv2.remap(img, map_x, map_y,
                         cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)

    def _fx_glitch(self, img):
        h, w = img.shape[:2]
        b, g, r = cv2.split(img)
        shift_r = random.randint(-14, 14)
        shift_b = random.randint(-14, 14)
        M_r = np.float32([[1, 0, shift_r], [0, 1, random.randint(-2, 2)]])
        M_b = np.float32([[1, 0, shift_b], [0, 1, random.randint(-2, 2)]])
        r = cv2.warpAffine(r, M_r, (w, h), borderMode=cv2.BORDER_REPLICATE)
        b = cv2.warpAffine(b, M_b, (w, h), borderMode=cv2.BORDER_REPLICATE)
        out = cv2.merge([b, g, r])
        lap = cv2.Laplacian(img, cv2.CV_8U, ksize=3)
        out = cv2.addWeighted(out, 0.85, lap, 0.35, 0.0)
        return out

    def _fx_defeat(self, img):
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        sx = cv2.Sobel(gray, cv2.CV_16S, 1, 0, ksize=3)
        sy = cv2.Sobel(gray, cv2.CV_16S, 0, 1, ksize=3)
        edges = cv2.convertScaleAbs(cv2.add(sx, sy))
        edges_bgr = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
        cold = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        cb, cg, cr = cv2.split(cold)
        cb = cv2.add(cb, 45)
        cr = cv2.subtract(cr, 25)
        cold = cv2.merge([cb, cg, cr])
        return cv2.addWeighted(cold, 0.80, edges_bgr, 0.55, 0.0)

    def _fx_victory(self, img):
        s = self.victory_t / _VICTORY_DUR
        if s < 0.05:
            return img
        h, w = img.shape[:2]
        cx, cy = w / 2.0, h / 2.0
        radius = math.hypot(cx, cy)
        polar = cv2.warpPolar(img, (w, h), (cx, cy), radius,
                              cv2.INTER_LINEAR + cv2.WARP_FILL_OUTLIERS)
        offset = int(24 * s)
        M = np.float32([[1, 0, offset], [0, 1, 0]])
        polar = cv2.warpAffine(polar, M, (w, h), borderMode=cv2.BORDER_WRAP)
        unpolar = cv2.warpPolar(polar, (w, h), (cx, cy), radius,
                                cv2.INTER_LINEAR + cv2.WARP_INVERSE_MAP)
        return cv2.addWeighted(img, 1.0 - 0.55 * s, unpolar, 0.55 * s, 0.0)

    def _fx_pixelate(self, img):
        ratio = self.transition_t / _TRANSITION_DUR
        peak = 1.0 - abs(ratio - 0.5) * 2.0
        if peak <= 0.02:
            return img
        h, w = img.shape[:2]
        block = max(2, int(3 + 55 * peak))
        small = cv2.resize(img, (max(2, w // block), max(2, h // block)),
                           interpolation=cv2.INTER_AREA)
        return cv2.resize(small, (w, h), interpolation=cv2.INTER_NEAREST)
