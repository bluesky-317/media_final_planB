"""共用的繪圖輔助函式。"""
import math
import os

import cv2
import numpy as np
import pygame

import config


# ----------------------------------------------------------------------
# 怪物 GIF 動畫 (用 cv2.VideoCapture 抽幀 -> pygame Surface)
# ----------------------------------------------------------------------

_SPRITE_CACHE = {}


class EnemySprite:
    """循環播放的怪物 sprite。frames 為 pygame.Surface list。"""

    def __init__(self, frames, fps=6):
        self.frames = frames
        self.fps = fps
        self.t = 0.0

    def update(self, dt):
        self.t += dt

    def draw(self, surf, cx, cy, bob_amp=3.0):
        if not self.frames:
            return
        idx = int(self.t * self.fps) % len(self.frames)
        frame = self.frames[idx]
        # Undertale 風漂浮動效:整體上下輕微擺動
        oy = math.sin(self.t * 2.0) * bob_amp
        rect = frame.get_rect(center=(int(cx), int(cy + oy)))
        surf.blit(frame, rect)


def load_enemy_sprite(filename, target_height=140):
    """從 assets/images/enemies/<filename> 載入 GIF。

    用 cv2.VideoCapture 抽出每一幀,再轉成 pygame Surface。
    結果會快取,反覆呼叫同檔名只解碼一次。檔不存在/讀取失敗回 None。
    """
    if not filename:
        return None
    cache_key = (filename, target_height)
    if cache_key in _SPRITE_CACHE:
        return _SPRITE_CACHE[cache_key]

    path = os.path.join("assets", "images", "enemies", filename)
    if not os.path.exists(path):
        print(f"[警告] 找不到怪物圖檔: {path}")
        _SPRITE_CACHE[cache_key] = None
        return None

    cap = cv2.VideoCapture(path)
    frames = []
    while True:
        ok, frame_bgr = cap.read()
        if not ok or frame_bgr is None:
            break
        h, w = frame_bgr.shape[:2]
        scale = target_height / max(1, h)
        new_w = max(1, int(w * scale))
        # 像素風保留:INTER_NEAREST
        resized = cv2.resize(frame_bgr, (new_w, target_height),
                             interpolation=cv2.INTER_NEAREST)
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        # pygame.surfarray 要 (W,H,3)
        rgb_t = np.ascontiguousarray(rgb.transpose(1, 0, 2))
        surf = pygame.surfarray.make_surface(rgb_t).convert()
        # GIF 透明背景在 cv2 載入後變黑;對黑色背景的戰鬥畫面剛好相容,
        # 同時用 colorkey 讓陰影外部的黑色不會擋住其他東西。
        surf.set_colorkey((0, 0, 0))
        frames.append(surf)
    cap.release()

    if not frames:
        print(f"[警告] 怪物 GIF 沒抽到任何幀: {path}")
        _SPRITE_CACHE[cache_key] = None
        return None

    sprite = EnemySprite(frames)
    _SPRITE_CACHE[cache_key] = sprite
    return sprite


def draw_text_center(surf, font, text, cx, cy, color):
    s = font.render(text, True, color)
    r = s.get_rect(center=(cx, cy))
    surf.blit(s, r)


# 8x8 像素風心臟 (Undertale 風)
_HEART_BITMAP = (
    "01100110",
    "11111111",
    "11111111",
    "11111111",
    "01111110",
    "00111100",
    "00011000",
    "00000000",
)


def draw_heart(surf, cx, cy, size=18, color=config.HEART_RED, glow=False):
    """像素風心臟。size 約等於最終 sprite 邊長。glow 參數保留向後相容但忽略。"""
    scale = max(2, round(size / 6))
    w = 8 * scale
    h = 8 * scale
    ox = int(cx - w / 2)
    oy = int(cy - h / 2)
    for y, row in enumerate(_HEART_BITMAP):
        for x, ch in enumerate(row):
            if ch == "1":
                pygame.draw.rect(surf, color,
                                 (ox + x * scale, oy + y * scale, scale, scale))


def heart_rect(cx, cy, size=config.HEART_SIZE):
    """碰撞用矩形 (略大於繪製尺寸以利擊中判定)。"""
    s = int(size * 1.2)
    return pygame.Rect(int(cx - s // 2), int(cy - s // 2), s, s)


def cv_frame_to_surface(frame_bgr, target_w, target_h):
    """把 OpenCV BGR 影像轉成 pygame Surface 並縮放。"""
    resized = cv2.resize(frame_bgr, (target_w, target_h))
    rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
    # pygame surfarray 需要 (width, height, 3)
    rgb = np.transpose(rgb, (1, 0, 2))
    return pygame.surfarray.make_surface(rgb)


def draw_camera_preview(surf, frame_bgr, font=None, error_msg=None):
    """畫攝影機預覽到右上角；frame_bgr 為 None 時顯示「NO CAMERA」佔位符。"""
    x = config.SCREEN_WIDTH - config.PREVIEW_WIDTH - config.PREVIEW_MARGIN
    y = config.PREVIEW_MARGIN
    if frame_bgr is not None:
        cam_surf = cv_frame_to_surface(frame_bgr,
                                       config.PREVIEW_WIDTH, config.PREVIEW_HEIGHT)
        pygame.draw.rect(surf, config.WHITE,
                         (x - 2, y - 2, config.PREVIEW_WIDTH + 4,
                          config.PREVIEW_HEIGHT + 4), 2)
        surf.blit(cam_surf, (x, y))
        return

    # No camera placeholder
    pygame.draw.rect(surf, config.DARK_GREY,
                     (x, y, config.PREVIEW_WIDTH, config.PREVIEW_HEIGHT))
    pygame.draw.rect(surf, config.RED,
                     (x - 2, y - 2, config.PREVIEW_WIDTH + 4,
                      config.PREVIEW_HEIGHT + 4), 2)
    # 紅色 X
    pad = 24
    pygame.draw.line(surf, config.RED,
                     (x + pad, y + pad),
                     (x + config.PREVIEW_WIDTH - pad,
                      y + config.PREVIEW_HEIGHT - pad), 3)
    pygame.draw.line(surf, config.RED,
                     (x + config.PREVIEW_WIDTH - pad, y + pad),
                     (x + pad, y + config.PREVIEW_HEIGHT - pad), 3)
    if font is not None:
        ts = font.render("NO CAMERA", True, config.RED)
        surf.blit(ts, ts.get_rect(
            center=(x + config.PREVIEW_WIDTH // 2,
                    y + config.PREVIEW_HEIGHT - 22)))


def draw_no_camera_banner(surf, font, msg):
    """底部紅色橫幅，提示用戶目前處於無輸入模式。"""
    if not msg:
        return
    h = 34
    banner_y = config.SCREEN_HEIGHT - h - 50
    pygame.draw.rect(surf, (60, 0, 0),
                     (0, banner_y, config.SCREEN_WIDTH, h))
    pygame.draw.line(surf, config.RED,
                     (0, banner_y), (config.SCREEN_WIDTH, banner_y), 2)
    pygame.draw.line(surf, config.RED,
                     (0, banner_y + h), (config.SCREEN_WIDTH, banner_y + h), 2)
    text = (f"⚠ {msg}    ←↑↓→ 游標 / ENTER 確認 / SPACE 跳"
            "  (1 2 3 選關 / R 重玩)")
    ts = font.render(text, True, (255, 220, 220))
    surf.blit(ts, ts.get_rect(
        center=(config.SCREEN_WIDTH // 2, banner_y + h // 2)))


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def draw_shield_bar(surf, hx, hy, angle, color,
                    radius=config.SHIELD_RADIUS,
                    length=config.SHIELD_LENGTH,
                    thick=config.SHIELD_THICK):
    """以心為中心、在指定方向角放一個矩形盾 (Undertale 綠心風)。"""
    # 盾中心位於離心 radius 的點
    cx = hx + radius * math.cos(angle)
    cy = hy + radius * math.sin(angle)
    # 盾的長邊與 angle 垂直
    rot = angle + math.pi / 2
    cos_r, sin_r = math.cos(rot), math.sin(rot)
    hl, ht = length / 2.0, thick / 2.0
    locals_ = [(-hl, -ht), (hl, -ht), (hl, ht), (-hl, ht)]
    corners = []
    for lx, ly in locals_:
        rx = cx + cos_r * lx - sin_r * ly
        ry = cy + sin_r * lx + cos_r * ly
        corners.append((rx, ry))
    pygame.draw.polygon(surf, color, corners)
    pygame.draw.polygon(surf, config.WHITE, corners, 2)


def shield_blocks(bx, by, hx, hy, angle,
                  arc_deg=config.SHIELD_ARC_DEG,
                  max_dist=config.SHIELD_BLOCK_DIST):
    """判斷座標 (bx,by) 的子彈是否被盾擋下。"""
    dx, dy = bx - hx, by - hy
    d = math.hypot(dx, dy)
    if d > max_dist:
        return False
    a = math.atan2(dy, dx)
    arc = math.radians(arc_deg)
    diff = abs(((a - angle + math.pi) % (2 * math.pi)) - math.pi)
    return diff < arc / 2


class DialogBox:
    """打字機式對話框 (Undertale 風)。

    使用方式：建立時傳入 lines (list[str])、字體、矩形範圍。
    每幀呼叫 update(dt) + draw(surf)。所有行都顯示完 → self.done = True。
    每行顯示完成後等 post_line_delay 秒會自動進到下一行。
    """

    def __init__(self, lines, font, rect, chars_per_sec=30,
                 color=config.WHITE, blip_sfx=None,
                 post_line_delay=0.7, prefix="* "):
        self.lines = list(lines)
        self.font = font
        self.rect = pygame.Rect(rect)
        self.chars_per_sec = chars_per_sec
        self.color = color
        self.blip_sfx = blip_sfx        # callable() 或 None
        self.post_line_delay = post_line_delay
        self.prefix = prefix
        self.cur_line = 0
        self.cur_chars = 0.0
        self.post_delay_t = 0.0
        self._last_blip = -3

    @property
    def done(self):
        return self.cur_line >= len(self.lines)

    @property
    def line_full(self):
        if self.done:
            return True
        return int(self.cur_chars) >= len(self.lines[self.cur_line])

    def update(self, dt):
        if self.done:
            return
        if not self.line_full:
            prev = int(self.cur_chars)
            self.cur_chars += dt * self.chars_per_sec
            new = int(self.cur_chars)
            if (new > prev and self.blip_sfx is not None
                    and new - self._last_blip >= 3):
                self.blip_sfx()
                self._last_blip = new
        else:
            self.post_delay_t += dt
            if self.post_delay_t >= self.post_line_delay:
                self.cur_line += 1
                self.cur_chars = 0.0
                self.post_delay_t = 0.0
                self._last_blip = -3

    def draw(self, surf, bg=config.BLACK, border_color=config.WHITE,
             border_w=3, padding=20):
        pygame.draw.rect(surf, bg, self.rect)
        pygame.draw.rect(surf, border_color, self.rect, border_w)
        if self.done:
            return
        line = self.lines[self.cur_line]
        visible = line[:int(self.cur_chars)]
        sub_lines = visible.split("\n")
        if self.prefix:
            sub_lines[0] = self.prefix + sub_lines[0]
        line_h = self.font.get_linesize()
        for i, sub in enumerate(sub_lines):
            ts = self.font.render(sub, True, self.color)
            surf.blit(ts, (self.rect.left + padding,
                           self.rect.top + padding + i * line_h))
        # 行讀完時右下角小三角
        if self.line_full:
            tx = self.rect.right - padding - 14
            ty = self.rect.bottom - padding - 12
            pygame.draw.polygon(surf, self.color, [
                (tx, ty), (tx + 14, ty), (tx + 7, ty + 10),
            ])


def draw_mode_indicator(surf, font, current_mode, x, y):
    """戰鬥畫面右側的小型模式指示器。"""
    modes = [
        (config.SOUL_RED, "RED", "1F"),
        (config.SOUL_BLUE, "BLUE", "2F"),
        (config.SOUL_GREEN, "GREEN", "4F"),
    ]
    box_w, box_h = 78, 60
    gap = 10
    for i, (mode, label, hint) in enumerate(modes):
        rx = x
        ry = y + i * (box_h + gap)
        color = config.SOUL_COLORS[mode]
        active = (mode == current_mode)
        bg = tuple(min(255, int(c * (0.85 if active else 0.22))) for c in color)
        pygame.draw.rect(surf, bg, (rx, ry, box_w, box_h), border_radius=8)
        border_w = 3 if active else 1
        pygame.draw.rect(surf, color, (rx, ry, box_w, box_h),
                         border_w, border_radius=8)
        ts = font.render(label, True, config.WHITE)
        surf.blit(ts, ts.get_rect(center=(rx + box_w // 2, ry + 18)))
        hs = font.render(hint, True, (220, 220, 220))
        surf.blit(hs, hs.get_rect(center=(rx + box_w // 2, ry + 42)))
