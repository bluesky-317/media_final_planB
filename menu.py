"""用手選擇關卡的選單場景。

食指當游標，懸停在按鈕上超過 HOVER_SELECT_SECONDS 秒即確認。
"""
import pygame

import config
from utils import (draw_heart, draw_text_center, draw_camera_preview,
                   draw_no_camera_banner)


class LevelMenu:
    BTN_W = 240
    BTN_H = 160
    BTN_GAP = 30

    def __init__(self, font_big, font_mid, font_small,
                 font_btn=None, font_tiny=None):
        self.font_big = font_big
        self.font_mid = font_mid
        self.font_small = font_small
        self.font_btn = font_btn or font_mid
        self.font_tiny = font_tiny or font_small

        total_w = self.BTN_W * 3 + self.BTN_GAP * 2
        start_x = (config.SCREEN_WIDTH - total_w) // 2
        y = config.SCREEN_HEIGHT // 2 - self.BTN_H // 2 + 20

        self.buttons = []
        for i, lv in enumerate(config.LEVELS):
            rect = pygame.Rect(start_x + i * (self.BTN_W + self.BTN_GAP),
                               y, self.BTN_W, self.BTN_H)
            self.buttons.append({"rect": rect, "level": lv, "hover": 0.0})

        # 初始游標放在標題下方、按鈕上方，避免一進選單就壓到關卡按鈕
        self.cursor = (config.SCREEN_WIDTH // 2, 90)
        self.selected_level = None

    def update(self, dt, finger_norm, tracker):
        # 食指 → 全螢幕游標位置
        screen_rect = (0, 0, config.SCREEN_WIDTH, config.SCREEN_HEIGHT)
        mapped = tracker.map_to_rect(finger_norm, screen_rect)
        if mapped is not None:
            self.cursor = (int(mapped[0]), int(mapped[1]))

        hovered_any = False
        for b in self.buttons:
            if b["rect"].collidepoint(self.cursor):
                b["hover"] = min(config.HOVER_SELECT_SECONDS, b["hover"] + dt)
                hovered_any = True
                if b["hover"] >= config.HOVER_SELECT_SECONDS and self.selected_level is None:
                    self.selected_level = b["level"]
            else:
                b["hover"] = max(0.0, b["hover"] - dt * 1.5)

        return self.selected_level

    def reset(self):
        self.selected_level = None
        self.cursor = (config.SCREEN_WIDTH // 2, 90)
        for b in self.buttons:
            b["hover"] = 0.0

    def draw(self, surf, camera_frame=None, camera_error=None):
        surf.fill(config.BLACK)

        # 標題:HandTale → 副標 → 懸停提示。
        # 三層垂直分開,避免大字 (font_big 64) 與粗體 CJK 字型上下衝撞。
        draw_text_center(surf, self.font_big, "HandTale",
                         config.SCREEN_WIDTH // 2, 90, config.WHITE)
        draw_text_center(surf, self.font_mid, "用『右手食指』選擇關卡",
                         config.SCREEN_WIDTH // 2, 170, config.YELLOW)
        draw_text_center(surf, self.font_small, "懸停 1.5 秒以確認",
                         config.SCREEN_WIDTH // 2, 210, config.GREY)

        # 按鈕
        for b in self.buttons:
            r = b["rect"]
            lv = b["level"]
            hover_ratio = b["hover"] / config.HOVER_SELECT_SECONDS

            # 外框與底色
            bg_color = tuple(min(255, int(c * (0.25 + 0.55 * hover_ratio))) for c in lv["color"])
            pygame.draw.rect(surf, bg_color, r, border_radius=12)
            border_color = lv["color"] if hover_ratio > 0 else config.WHITE
            pygame.draw.rect(surf, border_color, r, 4, border_radius=12)

            # 關卡編號
            num_surf = self.font_big.render(str(lv["id"]), True, config.WHITE)
            num_rect = num_surf.get_rect(center=(r.centerx, r.top + 50))
            surf.blit(num_surf, num_rect)

            # 名稱 / 副標 — 名稱用 font_small,副標長字串改 font_tiny 並做超寬截斷
            draw_text_center(surf, self.font_small, lv["name"],
                             r.centerx, r.centery + 18, config.WHITE)
            sub = lv["subtitle"]
            sub_font = self.font_small
            # 若副標仍寬於按鈕內側,改用更小的 font_tiny,避免溢到隔壁按鈕
            if sub_font.size(sub)[0] > r.width - 24:
                sub_font = self.font_tiny
            draw_text_center(surf, sub_font, sub,
                             r.centerx, r.centery + 44, (220, 220, 220))

            # 懸停進度條
            bar_x = r.left + 16
            bar_y = r.bottom - 18
            bar_w = r.width - 32
            pygame.draw.rect(surf, config.DARK_GREY,
                             (bar_x, bar_y, bar_w, 8), border_radius=4)
            if hover_ratio > 0:
                pygame.draw.rect(surf, config.WHITE,
                                 (bar_x, bar_y, int(bar_w * hover_ratio), 8),
                                 border_radius=4)

        # 攝影機預覽 (右上)
        draw_camera_preview(surf, camera_frame,
                            font=self.font_small, error_msg=camera_error)

        # 游標 (心)
        draw_heart(surf, self.cursor[0], self.cursor[1], size=14)
        pygame.draw.circle(surf, config.WHITE, self.cursor, 22, 1)

        # 無鏡頭橫幅 (若有)
        draw_no_camera_banner(surf, self.font_tiny, camera_error)

        # 底部說明
        draw_text_center(surf, self.font_tiny,
                         "ESC 結束 / 沒有偵測到手請靠近鏡頭並抬起『右手食指』",
                         config.SCREEN_WIDTH // 2,
                         config.SCREEN_HEIGHT - 22, config.GREY)
