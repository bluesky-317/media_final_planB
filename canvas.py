"""繪圖層 (取代 pygame)。

提供:
- ``Rect``:幾何盒子 (碰撞 / 對齊),API 仿 pygame.Rect 子集。
- ``Canvas``:把所有「畫到畫面」的動作包成 numpy BGR 陣列上的 cv2 操作,
  並用 Pillow 解 CJK 文字 (cv2.putText 不支援中文)。
- ``measure_text`` / ``fit_font_size``:量字寬,讓中文不會超出框 (auto-shrink-to-fit)。

設計重點:
- 所有顏色輸入皆為 RGB (跟 config.py 沿用 pygame 慣例);內部轉 BGR。
- 文字渲染做 LRU 快取 (相同字串 + 大小 + 顏色直接複用,別每幀重畫)。
- 文字「不溢出邊框」用 max_width 參數:量過寬度後逐級縮字,直到塞得進去。

未實作 (用不到 / 用替代寫法):
- 圓角矩形 (改畫一般矩形,視覺差異小)。
- alpha surface 與 set_clip (改在呼叫端手動裁剪 / 在 blit 處傳 alpha mask)。
"""
import os
from functools import lru_cache

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


# ----------------------------------------------------------------------
# 顏色:config.py 仍以 RGB 慣例存,我們在最後一刻轉 BGR 給 cv2 用。
# ----------------------------------------------------------------------

def to_bgr(color):
    """(R, G, B) → (B, G, R);長度 4 (含 alpha) 也接受。"""
    if len(color) == 3:
        r, g, b = color
        return (int(b), int(g), int(r))
    r, g, b, a = color
    return (int(b), int(g), int(r), int(a))


# ----------------------------------------------------------------------
# Rect:pygame.Rect 用到的子集
# ----------------------------------------------------------------------

class Rect:
    """簡化的矩形,提供 pygame.Rect 的常用屬性與方法。"""

    __slots__ = ("x", "y", "w", "h")

    def __init__(self, x, y, w, h):
        self.x = int(x)
        self.y = int(y)
        self.w = int(w)
        self.h = int(h)

    # 別名
    @property
    def left(self): return self.x
    @left.setter
    def left(self, v): self.x = int(v)

    @property
    def top(self): return self.y
    @top.setter
    def top(self, v): self.y = int(v)

    @property
    def width(self): return self.w
    @width.setter
    def width(self, v): self.w = int(v)

    @property
    def height(self): return self.h
    @height.setter
    def height(self, v): self.h = int(v)

    @property
    def right(self): return self.x + self.w
    @right.setter
    def right(self, v): self.x = int(v) - self.w

    @property
    def bottom(self): return self.y + self.h
    @bottom.setter
    def bottom(self, v): self.y = int(v) - self.h

    @property
    def centerx(self): return self.x + self.w // 2
    @centerx.setter
    def centerx(self, v): self.x = int(v) - self.w // 2

    @property
    def centery(self): return self.y + self.h // 2
    @centery.setter
    def centery(self, v): self.y = int(v) - self.h // 2

    @property
    def center(self): return (self.centerx, self.centery)
    @center.setter
    def center(self, v):
        cx, cy = v
        self.x = int(cx) - self.w // 2
        self.y = int(cy) - self.h // 2

    @property
    def topleft(self): return (self.x, self.y)
    @topleft.setter
    def topleft(self, v):
        self.x = int(v[0])
        self.y = int(v[1])

    # 操作
    def collidepoint(self, x, y=None):
        if y is None:
            x, y = x
        return self.x <= x < self.x + self.w and self.y <= y < self.y + self.h

    def colliderect(self, other):
        return (self.x < other.x + other.w
                and self.x + self.w > other.x
                and self.y < other.y + other.h
                and self.y + self.h > other.y)

    def inflate(self, dx, dy):
        return Rect(self.x - dx // 2, self.y - dy // 2,
                    self.w + dx, self.h + dy)

    def copy(self):
        return Rect(self.x, self.y, self.w, self.h)

    def __iter__(self):
        return iter((self.x, self.y, self.w, self.h))

    def __repr__(self):
        return f"Rect({self.x}, {self.y}, {self.w}, {self.h})"


def make_rect(rect_like):
    """接受 Rect / 4 元 tuple,皆轉成 Rect。"""
    if isinstance(rect_like, Rect):
        return rect_like
    x, y, w, h = rect_like
    return Rect(x, y, w, h)


# ----------------------------------------------------------------------
# 字型:Windows 用 Microsoft JhengHei (繁中) / YaHei (簡中);其他平台找 noto / arial。
# ----------------------------------------------------------------------

_FONT_PATH_CACHE = {}     # bold -> path 或 None


def _candidate_font_paths(bold):
    """回傳依優先序的可能字型路徑。"""
    out = []
    win_dir = os.environ.get("WINDIR", r"C:\Windows")
    fonts_dir = os.path.join(win_dir, "Fonts")
    if bold:
        out += [
            os.path.join(fonts_dir, "msjhbd.ttc"),
            os.path.join(fonts_dir, "msyhbd.ttc"),
            os.path.join(fonts_dir, "msjh.ttc"),     # 退而求其次
            os.path.join(fonts_dir, "msyh.ttc"),
        ]
    else:
        out += [
            os.path.join(fonts_dir, "msjh.ttc"),
            os.path.join(fonts_dir, "msyh.ttc"),
            os.path.join(fonts_dir, "msjhbd.ttc"),
            os.path.join(fonts_dir, "msyhbd.ttc"),
        ]
    out += [
        "/System/Library/Fonts/PingFang.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        os.path.join(fonts_dir, "arial.ttf"),
    ]
    return out


def _find_font_path(bold):
    if bold in _FONT_PATH_CACHE:
        return _FONT_PATH_CACHE[bold]
    for p in _candidate_font_paths(bold):
        if os.path.exists(p):
            _FONT_PATH_CACHE[bold] = p
            return p
    _FONT_PATH_CACHE[bold] = None
    return None


@lru_cache(maxsize=128)
def get_font(size, bold=False):
    """取得 PIL ImageFont (帶快取);找不到 CJK 字型時退回 PIL 內建。"""
    path = _find_font_path(bold)
    if path is None:
        return ImageFont.load_default()
    try:
        return ImageFont.truetype(path, max(6, int(size)))
    except OSError:
        return ImageFont.load_default()


def measure_text(text, size, bold=False):
    """回傳 (width, height) — 用 PIL 量字。"""
    if not text:
        return 0, 0
    font = get_font(size, bold)
    bbox = font.getbbox(text)
    return (bbox[2] - bbox[0], bbox[3] - bbox[1])


def fit_font_size(text, max_width, base_size, bold=False, min_size=10):
    """從 base_size 開始往下找,回傳能塞進 max_width 的最大字體大小。"""
    if max_width is None or max_width <= 0:
        return base_size
    s = int(base_size)
    while s > min_size:
        w, _ = measure_text(text, s, bold)
        if w <= max_width:
            return s
        s -= 1
    return min_size


# ----------------------------------------------------------------------
# 文字渲染:渲染到一張 RGBA PIL Image,再轉成 (BGR ndarray, alpha mask)。
# 一次性算好,以 LRU 快取下次同字串直接複用。
# ----------------------------------------------------------------------

_TEXT_CACHE = {}                # (text, size, bold, color) -> (bgr, alpha)
_TEXT_CACHE_MAX = 512


def render_text(text, size, color_rgb, bold=False):
    """渲染文字成 (bgr ndarray, alpha float ndarray)。空字串回 (None, None)。"""
    if not text:
        return None, None
    color_rgb = tuple(int(c) for c in color_rgb[:3])
    key = (text, int(size), bool(bold), color_rgb)
    cached = _TEXT_CACHE.get(key)
    if cached is not None:
        return cached

    font = get_font(size, bold)
    # 用 textbbox 量實際渲染框 (含偏移),確保畫布夠裝。
    dummy = Image.new("RGBA", (1, 1))
    d = ImageDraw.Draw(dummy)
    try:
        bbox = d.textbbox((0, 0), text, font=font)
    except AttributeError:
        # 老版 Pillow 沒 textbbox,退回 textsize
        w, h = d.textsize(text, font=font)
        bbox = (0, 0, w, h)
    pad = 2
    canvas_w = max(1, bbox[2] - bbox[0] + pad * 2)
    canvas_h = max(1, bbox[3] - bbox[1] + pad * 2)
    img = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # 畫在 (-bbox[0]+pad, -bbox[1]+pad),這樣 bbox 起點剛好落到 (pad, pad)
    draw.text((-bbox[0] + pad, -bbox[1] + pad), text,
              font=font, fill=color_rgb + (255,))

    arr = np.asarray(img)              # H, W, 4 (RGBA)
    rgb = arr[..., :3]
    alpha = arr[..., 3:4].astype(np.float32) / 255.0
    bgr = np.ascontiguousarray(rgb[..., ::-1])   # RGB → BGR

    if len(_TEXT_CACHE) >= _TEXT_CACHE_MAX:
        # 簡易 FIFO:Python dict 保留插入順序,踢掉最舊的
        _TEXT_CACHE.pop(next(iter(_TEXT_CACHE)))
    _TEXT_CACHE[key] = (bgr, alpha)
    return bgr, alpha


# ----------------------------------------------------------------------
# Canvas:numpy BGR 陣列 + 所有畫畫方法
# ----------------------------------------------------------------------

class Canvas:
    """960×720 邏輯畫布。內部存 BGR uint8 ndarray (給 cv2.imshow 直接用)。"""

    def __init__(self, width, height):
        self.w = int(width)
        self.h = int(height)
        self.arr = np.zeros((self.h, self.w, 3), dtype=np.uint8)

    # --- 全圖 ---
    def fill(self, color):
        self.arr[:] = to_bgr(color)

    def clear(self):
        self.arr.fill(0)

    # --- 基本圖形 ---
    def rect(self, rect_like, color, thickness=-1):
        """thickness < 0 = 實心填滿;>0 = 邊框寬度。"""
        r = make_rect(rect_like)
        cv2.rectangle(self.arr,
                      (r.x, r.y), (r.x + r.w, r.y + r.h),
                      to_bgr(color), int(thickness))

    def circle(self, cx, cy, radius, color, thickness=-1):
        cv2.circle(self.arr, (int(cx), int(cy)), int(radius),
                   to_bgr(color), int(thickness))

    def line(self, p1, p2, color, thickness=1):
        cv2.line(self.arr,
                 (int(p1[0]), int(p1[1])),
                 (int(p2[0]), int(p2[1])),
                 to_bgr(color), int(thickness))

    def polygon(self, pts, color, thickness=-1):
        arr_pts = np.array([[int(p[0]), int(p[1])] for p in pts],
                           dtype=np.int32)
        if thickness < 0:
            cv2.fillPoly(self.arr, [arr_pts], to_bgr(color))
        else:
            cv2.polylines(self.arr, [arr_pts], True,
                          to_bgr(color), int(thickness))

    # --- alpha 覆蓋全螢幕邊框 (取代 pygame.SRCALPHA + draw.rect border) ---
    def overlay_color(self, color_rgb, alpha):
        """整張畫面塗上 alpha 比例的 color (像玩家受傷紅閃)。"""
        if alpha <= 0:
            return
        overlay = np.empty_like(self.arr)
        overlay[:] = to_bgr(color_rgb)
        cv2.addWeighted(self.arr, 1.0 - alpha, overlay, alpha, 0.0,
                        dst=self.arr)

    def overlay_border(self, color_rgb, alpha, thickness):
        """畫面四邊內側 thickness 像素塗紅光 (取代受傷時的紅色內邊框)。"""
        if alpha <= 0 or thickness <= 0:
            return
        mask = np.zeros((self.h, self.w), dtype=np.uint8)
        cv2.rectangle(mask, (0, 0), (self.w - 1, self.h - 1),
                      255, int(thickness))
        overlay = np.empty_like(self.arr)
        overlay[:] = to_bgr(color_rgb)
        a3 = (mask.astype(np.float32) / 255.0 * alpha)[..., None]
        self.arr[:] = (self.arr.astype(np.float32) * (1.0 - a3)
                       + overlay.astype(np.float32) * a3).astype(np.uint8)

    # --- 文字 ---
    def text(self, text, x, y, color, size, bold=False,
             anchor="topleft", max_width=None, alpha=1.0):
        """畫 CJK 文字到 (x, y);anchor: topleft / center / midtop / midbottom。

        max_width 不為 None 時,文字過寬會自動縮小字體 (保證不溢出框)。
        """
        if not text:
            return
        if max_width is not None and max_width > 0:
            size = fit_font_size(text, int(max_width), int(size), bold)
        bgr, a = render_text(text, int(size), color, bold)
        if bgr is None:
            return
        th, tw = bgr.shape[:2]
        if anchor == "topleft":
            tx, ty = int(x), int(y)
        elif anchor == "center":
            tx, ty = int(x) - tw // 2, int(y) - th // 2
        elif anchor == "midtop":
            tx, ty = int(x) - tw // 2, int(y)
        elif anchor == "midbottom":
            tx, ty = int(x) - tw // 2, int(y) - th
        elif anchor == "topright":
            tx, ty = int(x) - tw, int(y)
        else:
            tx, ty = int(x), int(y)
        self.blit(bgr, tx, ty, alpha_mask=a, opacity=alpha)

    # --- 貼圖 (numpy / Canvas / Surface 樣式) ---
    def blit(self, src_bgr, x, y, alpha_mask=None, opacity=1.0,
             src_rect=None):
        """把 src_bgr (H,W,3) 貼到 (x, y);可選 alpha_mask (H,W,1 float 0~1)。

        src_rect = (sx, sy, sw, sh) 只貼 src 的子區。
        """
        if src_rect is not None:
            sx, sy, sw, sh = src_rect
            src_bgr = src_bgr[sy:sy + sh, sx:sx + sw]
            if alpha_mask is not None:
                alpha_mask = alpha_mask[sy:sy + sh, sx:sx + sw]
        sh, sw = src_bgr.shape[:2]
        x, y = int(x), int(y)

        # 對 canvas 邊界做剪裁
        x1, y1 = max(0, x), max(0, y)
        x2 = min(self.w, x + sw)
        y2 = min(self.h, y + sh)
        if x1 >= x2 or y1 >= y2:
            return
        sx1 = x1 - x
        sy1 = y1 - y
        sx2 = sx1 + (x2 - x1)
        sy2 = sy1 + (y2 - y1)

        roi = self.arr[y1:y2, x1:x2]
        src = src_bgr[sy1:sy2, sx1:sx2]
        if alpha_mask is None and opacity >= 1.0:
            roi[:] = src
            return

        if alpha_mask is not None:
            a = alpha_mask[sy1:sy2, sx1:sx2] * float(opacity)
        else:
            a = np.full((y2 - y1, x2 - x1, 1), float(opacity),
                        dtype=np.float32)
        blended = src.astype(np.float32) * a + roi.astype(np.float32) * (1.0 - a)
        roi[:] = blended.astype(np.uint8)


def make_canvas(width, height):
    return Canvas(width, height)
