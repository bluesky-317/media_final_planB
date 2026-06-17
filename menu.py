"""用手選擇關卡的選單場景 (OpenCV 版)。

食指當游標,懸停在按鈕上超過 HOVER_SELECT_SECONDS 秒即確認。
"""
import config
from canvas import Rect
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
            rect = Rect(start_x + i * (self.BTN_W + self.BTN_GAP),
                        y, self.BTN_W, self.BTN_H)
            self.buttons.append({"rect": rect, "level": lv, "hover": 0.0})

        self.cursor = (config.SCREEN_WIDTH // 2, 90)
        self.selected_level = None

    def update(self, dt, finger_norm, tracker):
        screen_rect = (0, 0, config.SCREEN_WIDTH, config.SCREEN_HEIGHT)
        mapped = tracker.map_to_rect(finger_norm, screen_rect)
        if mapped is not None:
            self.cursor = (int(mapped[0]), int(mapped[1]))

        for b in self.buttons:
            if b["rect"].collidepoint(self.cursor):
                b["hover"] = min(config.HOVER_SELECT_SECONDS, b["hover"] + dt)
                if (b["hover"] >= config.HOVER_SELECT_SECONDS
                        and self.selected_level is None):
                    self.selected_level = b["level"]
            else:
                b["hover"] = max(0.0, b["hover"] - dt * 1.5)

        return self.selected_level

    def reset(self):
        self.selected_level = None
        self.cursor = (config.SCREEN_WIDTH // 2, 90)
        for b in self.buttons:
            b["hover"] = 0.0

    def draw(self, canvas, camera_frame=None, camera_error=None):
        canvas.fill(config.BLACK)

        # 標題:HandTale → 副標 → 懸停提示。
        draw_text_center(canvas, self.font_big, "HandTale",
                         config.SCREEN_WIDTH // 2, 90, config.WHITE)
        draw_text_center(canvas, self.font_mid, "用『右手食指』選擇關卡",
                         config.SCREEN_WIDTH // 2, 170, config.YELLOW)
        draw_text_center(canvas, self.font_small, "懸停 1.5 秒以確認",
                         config.SCREEN_WIDTH // 2, 210, config.GREY)

        # 按鈕
        for b in self.buttons:
            r = b["rect"]
            lv = b["level"]
            hover_ratio = b["hover"] / config.HOVER_SELECT_SECONDS

            bg_color = tuple(min(255, int(c * (0.25 + 0.55 * hover_ratio)))
                             for c in lv["color"])
            canvas.rect(r, bg_color, thickness=-1)
            border_color = lv["color"] if hover_ratio > 0 else config.WHITE
            canvas.rect(r, border_color, thickness=4)

            # 關卡編號
            draw_text_center(canvas, self.font_big, str(lv["id"]),
                             r.centerx, r.top + 50, config.WHITE)

            # 名稱 / 副標 — 帶 max_width 防止中文超出框
            inner_w = r.width - 20
            draw_text_center(canvas, self.font_small, lv["name"],
                             r.centerx, r.centery + 18, config.WHITE,
                             max_width=inner_w)
            draw_text_center(canvas, self.font_small, lv["subtitle"],
                             r.centerx, r.centery + 44, (220, 220, 220),
                             max_width=inner_w)

            # 懸停進度條
            bar_x = r.left + 16
            bar_y = r.bottom - 18
            bar_w = r.width - 32
            canvas.rect((bar_x, bar_y, bar_w, 8),
                        config.DARK_GREY, thickness=-1)
            if hover_ratio > 0:
                canvas.rect((bar_x, bar_y, int(bar_w * hover_ratio), 8),
                            config.WHITE, thickness=-1)

        # 攝影機預覽 (右上)
        draw_camera_preview(canvas, camera_frame,
                            font=self.font_small, error_msg=camera_error)

        # 游標 (心)
        draw_heart(canvas, self.cursor[0], self.cursor[1], size=14)
        canvas.circle(self.cursor[0], self.cursor[1], 22,
                      config.WHITE, thickness=1)

        # 無鏡頭橫幅 (若有)
        draw_no_camera_banner(canvas, self.font_tiny, camera_error)

        # 底部說明
        draw_text_center(canvas, self.font_tiny,
                         "ESC 結束 / 沒有偵測到手請靠近鏡頭並抬起『右手食指』",
                         config.SCREEN_WIDTH // 2,
                         config.SCREEN_HEIGHT - 22, config.GREY,
                         max_width=config.SCREEN_WIDTH - 80)
