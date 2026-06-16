"""共用的繪圖輔助函式。"""
import math

import cv2
import numpy as np
import pygame

import config


def draw_text_center(surf, font, text, cx, cy, color):
    s = font.render(text, True, color)
    r = s.get_rect(center=(cx, cy))
    surf.blit(s, r)


def draw_heart(surf, cx, cy, size=18, color=config.HEART_RED, glow=True):
    """畫 Undertale 風的紅心。"""
    # 用兩個圓 + 一個三角形組成
    r = max(2, size // 2)
    left = (int(cx - r // 1.1), int(cy - r // 2.5))
    right = (int(cx + r // 1.1), int(cy - r // 2.5))
    bottom = (int(cx), int(cy + size // 1.3))

    if glow:
        glow_surf = pygame.Surface((size * 3, size * 3), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (*color, 60),
                           (size * 3 // 2, size * 3 // 2), int(size * 1.4))
        surf.blit(glow_surf, (cx - size * 3 // 2, cy - size * 3 // 2))

    pygame.draw.circle(surf, color, left, r)
    pygame.draw.circle(surf, color, right, r)
    pygame.draw.polygon(surf, color, [
        (left[0] - r, left[1]),
        (right[0] + r, right[1]),
        bottom,
    ])


def heart_rect(cx, cy, size=config.HEART_SIZE):
    """碰撞用矩形 (略小於繪製尺寸以利玩家)。"""
    s = int(size * 0.9)
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
    text = f"⚠  {msg}    無輸入模式：鍵盤 1/2/3 選關、R 重玩、ENTER 回選單"
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
