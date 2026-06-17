"""共用的繪圖輔助函式 (OpenCV / numpy 版)。

所有「畫畫」函式都吃 ``canvas.Canvas`` 而非 pygame Surface;
所有「字型」參數則收 ``Font`` 物件 (帶 size + bold)。
"""
import math
import os

import cv2
import numpy as np

import config
from canvas import Rect, measure_text


# ----------------------------------------------------------------------
# Font:輕量包裝,讓呼叫端能像 pygame.font.Font 那樣量字 / 拿高度,
# 實際繪製走 Canvas.text(...)。
# ----------------------------------------------------------------------

class Font:
    __slots__ = ("size_pt", "bold")

    def __init__(self, size_pt, bold=False):
        self.size_pt = int(size_pt)
        self.bold = bool(bold)

    def size(self, text):
        return measure_text(text, self.size_pt, self.bold)

    def get_height(self):
        _, h = measure_text("Mg中p", self.size_pt, self.bold)
        return h

    def get_linesize(self):
        # 行距:約 1.3 倍字高
        return int(self.size_pt * 1.35)


# ----------------------------------------------------------------------
# 怪物 GIF 動畫 (cv2.VideoCapture 抽幀 -> BGR ndarray frames)
# ----------------------------------------------------------------------

_SPRITE_CACHE = {}


class EnemySprite:
    """循環播放的怪物 sprite (BGR ndarray frames + 透明遮罩)。"""

    def __init__(self, frames_bgr, masks, fps=6):
        self.frames = frames_bgr   # list of (H, W, 3) BGR
        self.masks = masks         # list of (H, W, 1) float 0/1
        self.fps = fps
        self.t = 0.0

    def update(self, dt):
        self.t += dt

    def draw(self, canvas, cx, cy, bob_amp=3.0):
        if not self.frames:
            return
        idx = int(self.t * self.fps) % len(self.frames)
        frame = self.frames[idx]
        mask = self.masks[idx]
        oy = math.sin(self.t * 2.0) * bob_amp
        h, w = frame.shape[:2]
        x = int(cx - w / 2)
        y = int(cy + oy - h / 2)
        canvas.blit(frame, x, y, alpha_mask=mask)


def load_enemy_sprite(filename, target_height=140):
    """從 assets/images/enemies/<filename> 載入 GIF (BGR 多幀 + 透明 mask)。

    用 cv2.VideoCapture 抽幀,黑底當作透明 (用作 mask)。結果以檔名快取。
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
    masks = []
    while True:
        ok, frame_bgr = cap.read()
        if not ok or frame_bgr is None:
            break
        h, w = frame_bgr.shape[:2]
        scale = target_height / max(1, h)
        new_w = max(1, int(w * scale))
        resized = cv2.resize(frame_bgr, (new_w, target_height),
                             interpolation=cv2.INTER_NEAREST)
        # 黑色背景視為透明 (= 0);其餘像素不透明
        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
        mask = (gray > 6).astype(np.float32)[..., None]
        frames.append(resized)
        masks.append(mask)
    cap.release()

    if not frames:
        print(f"[警告] 怪物 GIF 沒抽到任何幀: {path}")
        _SPRITE_CACHE[cache_key] = None
        return None

    sprite = EnemySprite(frames, masks)
    _SPRITE_CACHE[cache_key] = sprite
    return sprite


# ----------------------------------------------------------------------
# 基本繪圖小工具
# ----------------------------------------------------------------------

def draw_text_center(canvas, font, text, cx, cy, color, max_width=None):
    canvas.text(text, cx, cy, color, font.size_pt,
                bold=font.bold, anchor="center", max_width=max_width)


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


# ----------------------------------------------------------------------
# 8×8 像素風心臟 (Undertale 風)
# ----------------------------------------------------------------------

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


def draw_heart(canvas, cx, cy, size=18, color=config.HEART_RED, glow=False):
    """像素風心臟。size ≈ 最終 sprite 邊長。glow 參數保留向後相容但忽略。"""
    scale = max(2, round(size / 6))
    w = 8 * scale
    h = 8 * scale
    ox = int(cx - w / 2)
    oy = int(cy - h / 2)
    for y, row in enumerate(_HEART_BITMAP):
        for x, ch in enumerate(row):
            if ch == "1":
                canvas.rect((ox + x * scale, oy + y * scale, scale, scale),
                            color, thickness=-1)


def heart_rect(cx, cy, size=config.HEART_SIZE):
    """碰撞用矩形 (略大於繪製尺寸以利擊中判定)。"""
    s = int(size * 1.2)
    return Rect(int(cx - s // 2), int(cy - s // 2), s, s)


# ----------------------------------------------------------------------
# 右上角攝影機預覽 / 無鏡頭橫幅
# ----------------------------------------------------------------------

def draw_camera_preview(canvas, frame_bgr, font=None, error_msg=None):
    """畫攝影機預覽到右上角;frame_bgr 為 None 時顯示「NO CAMERA」佔位符。"""
    x = config.SCREEN_WIDTH - config.PREVIEW_WIDTH - config.PREVIEW_MARGIN
    y = config.PREVIEW_MARGIN
    if frame_bgr is not None:
        resized = cv2.resize(frame_bgr,
                             (config.PREVIEW_WIDTH, config.PREVIEW_HEIGHT))
        canvas.blit(resized, x, y)
        canvas.rect((x - 2, y - 2,
                     config.PREVIEW_WIDTH + 4, config.PREVIEW_HEIGHT + 4),
                    config.WHITE, thickness=2)
        return

    # No camera placeholder
    canvas.rect((x, y, config.PREVIEW_WIDTH, config.PREVIEW_HEIGHT),
                config.DARK_GREY, thickness=-1)
    canvas.rect((x - 2, y - 2,
                 config.PREVIEW_WIDTH + 4, config.PREVIEW_HEIGHT + 4),
                config.RED, thickness=2)
    pad = 24
    canvas.line((x + pad, y + pad),
                (x + config.PREVIEW_WIDTH - pad,
                 y + config.PREVIEW_HEIGHT - pad),
                config.RED, thickness=3)
    canvas.line((x + config.PREVIEW_WIDTH - pad, y + pad),
                (x + pad, y + config.PREVIEW_HEIGHT - pad),
                config.RED, thickness=3)
    if font is not None:
        canvas.text("NO CAMERA",
                    x + config.PREVIEW_WIDTH // 2,
                    y + config.PREVIEW_HEIGHT - 22,
                    config.RED, font.size_pt,
                    bold=font.bold, anchor="center")


def draw_no_camera_banner(canvas, font, msg):
    """頂部紅色細橫幅,提示用戶目前處於無輸入模式。"""
    if not msg:
        return
    h = 24
    banner_y = 0
    banner_w = (config.SCREEN_WIDTH
                - config.PREVIEW_WIDTH - 2 * config.PREVIEW_MARGIN)
    canvas.rect((0, banner_y, banner_w, h), (60, 0, 0), thickness=-1)
    canvas.line((0, banner_y + h), (banner_w, banner_y + h),
                config.RED, thickness=2)
    canvas.line((banner_w, banner_y), (banner_w, banner_y + h),
                config.RED, thickness=2)
    text = (f"[!] {msg}    ←↑↓→ 游標 / ENTER 確認 / SPACE 跳"
            "  (1 2 3 選關 / R 重玩)")
    canvas.text(text, banner_w // 2, banner_y + h // 2,
                (255, 220, 220), font.size_pt, bold=font.bold,
                anchor="center", max_width=banner_w - 20)


# ----------------------------------------------------------------------
# 綠心盾
# ----------------------------------------------------------------------

def draw_shield_bar(canvas, hx, hy, angle, color,
                    radius=config.SHIELD_RADIUS,
                    length=config.SHIELD_LENGTH,
                    thick=config.SHIELD_THICK):
    """以心為中心、在指定方向角放一個矩形盾 (Undertale 綠心風)。"""
    cx = hx + radius * math.cos(angle)
    cy = hy + radius * math.sin(angle)
    rot = angle + math.pi / 2
    cos_r, sin_r = math.cos(rot), math.sin(rot)
    hl, ht = length / 2.0, thick / 2.0
    locals_ = [(-hl, -ht), (hl, -ht), (hl, ht), (-hl, ht)]
    corners = []
    for lx, ly in locals_:
        rx = cx + cos_r * lx - sin_r * ly
        ry = cy + sin_r * lx + cos_r * ly
        corners.append((rx, ry))
    canvas.polygon(corners, color, thickness=-1)
    canvas.polygon(corners, config.WHITE, thickness=2)


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


# ----------------------------------------------------------------------
# DialogBox:打字機對話框
# ----------------------------------------------------------------------

class DialogBox:
    """逐字 reveal 的對話框 (Undertale 風)。

    使用方式:建立時傳入 lines (list[str])、font (utils.Font)、rect (canvas.Rect 或 4 元組)。
    每幀呼叫 update(dt) + draw(canvas)。所有行顯示完 → self.done = True。
    """

    def __init__(self, lines, font, rect, chars_per_sec=30,
                 color=config.WHITE, blip_sfx=None,
                 post_line_delay=0.7, prefix="* "):
        self.lines = list(lines)
        self.font = font
        if isinstance(rect, Rect):
            self.rect = rect.copy()
        else:
            x, y, w, h = rect
            self.rect = Rect(x, y, w, h)
        self.chars_per_sec = chars_per_sec
        self.color = color
        self.blip_sfx = blip_sfx
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

    def draw(self, canvas, bg=config.BLACK, border_color=config.WHITE,
             border_w=3, padding=20):
        canvas.rect(self.rect, bg, thickness=-1)
        canvas.rect(self.rect, border_color, thickness=int(border_w))
        if self.done:
            return
        line = self.lines[self.cur_line]
        visible = line[:int(self.cur_chars)]
        sub_lines = visible.split("\n")
        if self.prefix:
            sub_lines[0] = self.prefix + sub_lines[0]
        line_h = self.font.get_linesize()
        max_w = self.rect.w - padding * 2 - 16
        for i, sub in enumerate(sub_lines):
            canvas.text(sub,
                        self.rect.left + padding,
                        self.rect.top + padding + i * line_h,
                        self.color, self.font.size_pt,
                        bold=self.font.bold,
                        anchor="topleft",
                        max_width=max_w)
        if self.line_full:
            tx = self.rect.right - padding - 14
            ty = self.rect.bottom - padding - 12
            canvas.polygon([
                (tx, ty), (tx + 14, ty), (tx + 7, ty + 10),
            ], self.color, thickness=-1)


# ----------------------------------------------------------------------
# 戰鬥畫面左側的模式指示器
# ----------------------------------------------------------------------

def draw_mode_indicator(canvas, font, current_mode, x, y):
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
        canvas.rect((rx, ry, box_w, box_h), bg, thickness=-1)
        border_w = 3 if active else 1
        canvas.rect((rx, ry, box_w, box_h), color, thickness=border_w)
        canvas.text(label, rx + box_w // 2, ry + 18,
                    config.WHITE, font.size_pt,
                    bold=font.bold, anchor="center")
        canvas.text(hint, rx + box_w // 2, ry + 42,
                    (220, 220, 220), font.size_pt,
                    bold=font.bold, anchor="center")
