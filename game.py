"""Undertale 風戰鬥場景 (含手勢切換靈魂顏色)。

模式：
  RED   食指                    自由 2D 移動 (預設)
  BLUE  食指+中指 (✌)           重力 + 跳躍；X 軸跟食指，Y 軸物理
  GREEN 整隻手張開 (🖐)          固定於中央，盾隨食指方向旋轉
"""
import math
import random

import pygame

import config
import bullets as bullets_mod
from utils import (clamp, draw_heart, heart_rect, draw_text_center,
                   draw_camera_preview, draw_shield_bar, shield_blocks,
                   draw_mode_indicator, draw_no_camera_banner)


class BattleScene:
    """單一關卡的戰鬥流程。"""

    def __init__(self, level, font_big, font_mid, font_small):
        self.level = level
        self.font_big = font_big
        self.font_mid = font_mid
        self.font_small = font_small

        self.hp = level["hp"]
        self.duration = level["duration"]
        self.elapsed = 0.0
        self.pattern = bullets_mod.make_pattern(level["id"])
        self.bullets = []

        # 心一開始放在戰鬥框中央 (紅心預設)
        self.heart_x = float(config.BOX_CENTER_X)
        self.heart_y = float(config.BOX_CENTER_Y)

        # 靈魂模式
        self.soul_mode = config.SOUL_RED
        self.mode_flash_t = 0.0  # 切換瞬間的閃光時間

        # 藍心物理
        self.vel_y = 0.0
        self.on_ground = False
        self.jump_cooldown = 0.0

        # 綠心盾
        self.shield_angle = 0.0  # 由 tracker.angle 更新

        self.invuln = 0
        self.shake_t = 0.0
        self.blocked_flash_t = 0.0  # 擋彈時的綠光提示
        self.result = None  # None / 'win' / 'lose'

    # ------------------------------------------------------------------
    @staticmethod
    def _floor_y():
        return config.BOX_BOTTOM - config.HEART_SIZE / 2 - 2

    def _enter_mode(self, mode):
        if mode == self.soul_mode:
            return
        self.soul_mode = mode
        self.mode_flash_t = 0.25
        if mode == config.SOUL_BLUE:
            self.heart_y = self._floor_y()
            self.vel_y = 0.0
            self.on_ground = True
        elif mode == config.SOUL_GREEN:
            self.heart_x = float(config.BOX_CENTER_X)
            self.heart_y = float(config.BOX_CENTER_Y)
            self.vel_y = 0.0

    # ------------------------------------------------------------------
    def update(self, dt, finger_norm, tracker):
        if self.result is not None:
            return self.result

        # 1) 模式切換 (HandTracker 已 debounce)
        self._enter_mode(tracker.gesture)
        self.shield_angle = tracker.angle

        # 2) 位置更新 (依模式)
        box_rect = (config.BOX_LEFT, config.BOX_TOP,
                    config.BOX_WIDTH, config.BOX_HEIGHT)
        mapped = tracker.map_to_rect(finger_norm, box_rect)

        if self.soul_mode == config.SOUL_RED:
            if mapped is not None:
                self.heart_x = clamp(mapped[0],
                                     config.BOX_LEFT + config.HEART_SIZE // 2,
                                     config.BOX_RIGHT - config.HEART_SIZE // 2)
                self.heart_y = clamp(mapped[1],
                                     config.BOX_TOP + config.HEART_SIZE // 2,
                                     config.BOX_BOTTOM - config.HEART_SIZE // 2)

        elif self.soul_mode == config.SOUL_BLUE:
            # X 跟手指；Y 由重力決定
            if mapped is not None:
                self.heart_x = clamp(mapped[0],
                                     config.BOX_LEFT + config.HEART_SIZE // 2,
                                     config.BOX_RIGHT - config.HEART_SIZE // 2)

            self.vel_y += config.GRAVITY * dt
            self.heart_y += self.vel_y * dt

            floor_y = self._floor_y()
            ceiling_y = config.BOX_TOP + config.HEART_SIZE / 2 + 2
            if self.heart_y >= floor_y:
                self.heart_y = floor_y
                self.vel_y = 0.0
                self.on_ground = True
            else:
                self.on_ground = False
            if self.heart_y < ceiling_y:
                self.heart_y = ceiling_y
                if self.vel_y < 0:
                    self.vel_y = 0.0

            # 跳躍：偵測食指快速向上揮
            if self.jump_cooldown > 0:
                self.jump_cooldown = max(0.0, self.jump_cooldown - dt)
            elif tracker.vy_norm < config.JUMP_VY_THRESHOLD and self.on_ground:
                self.vel_y = -config.JUMP_VELOCITY
                self.jump_cooldown = config.JUMP_COOLDOWN
                self.on_ground = False

        elif self.soul_mode == config.SOUL_GREEN:
            # 心釘在中央
            self.heart_x = float(config.BOX_CENTER_X)
            self.heart_y = float(config.BOX_CENTER_Y)

        # 3) 攻擊模式產生子彈
        self.pattern.update(dt, self.bullets)

        # 4) 更新子彈 + 碰撞
        hb = heart_rect(self.heart_x, self.heart_y)
        for b in self.bullets:
            b.update(dt)
            if not b.alive:
                continue

            # 綠心：先檢查盾 (對普通子彈與骨頭有效，雷射例外)
            if self.soul_mode == config.SOUL_GREEN and not isinstance(
                    b, bullets_mod.LaserBeam):
                if isinstance(b, bullets_mod.BoneBullet):
                    cx, cy = b.rect().center
                else:
                    cx, cy = b.x, b.y
                if shield_blocks(cx, cy, self.heart_x, self.heart_y,
                                 self.shield_angle):
                    b.alive = False
                    self.blocked_flash_t = 0.12
                    continue

            if self.invuln <= 0 and b.hits(hb):
                self.hp -= b.damage
                self.invuln = config.INVULN_FRAMES
                self.shake_t = 0.25
                if not isinstance(b, bullets_mod.LaserBeam):
                    b.alive = False

        self.bullets = [b for b in self.bullets if b.alive]

        if self.invuln > 0:
            self.invuln -= 1
        if self.shake_t > 0:
            self.shake_t -= dt
        if self.mode_flash_t > 0:
            self.mode_flash_t -= dt
        if self.blocked_flash_t > 0:
            self.blocked_flash_t -= dt

        # 5) 時間 / 勝負
        self.elapsed += dt
        if self.hp <= 0:
            self.hp = 0
            self.result = 'lose'
        elif self.elapsed >= self.duration:
            self.result = 'win'

        return self.result

    # ------------------------------------------------------------------
    def draw(self, surf, camera_frame=None, camera_error=None):
        shake = (0, 0)
        if self.shake_t > 0:
            shake = (random.randint(-4, 4), random.randint(-4, 4))

        surf.fill(config.BLACK)

        # 標題列
        draw_text_center(surf, self.font_mid, self.level["name"],
                         config.SCREEN_WIDTH // 2, 50, self.level["color"])
        remain = max(0.0, self.duration - self.elapsed)
        draw_text_center(surf, self.font_small,
                         f"撐過 {self.duration} 秒  |  剩餘 {remain:4.1f} s",
                         config.SCREEN_WIDTH // 2, 92, config.WHITE)

        # HP 條
        bar_w = 360
        bar_h = 22
        bar_x = (config.SCREEN_WIDTH - bar_w) // 2
        bar_y = 120
        pygame.draw.rect(surf, config.DARK_GREY,
                         (bar_x, bar_y, bar_w, bar_h), border_radius=6)
        ratio = self.hp / self.level["hp"]
        pygame.draw.rect(surf, config.YELLOW,
                         (bar_x, bar_y, int(bar_w * ratio), bar_h),
                         border_radius=6)
        pygame.draw.rect(surf, config.WHITE,
                         (bar_x, bar_y, bar_w, bar_h), 2, border_radius=6)
        draw_text_center(surf, self.font_small,
                         f"HP  {self.hp:>3} / {self.level['hp']}",
                         bar_x + bar_w // 2, bar_y + bar_h // 2, config.BLACK)

        # 戰鬥框 (套 shake)
        box = pygame.Rect(config.BOX_LEFT + shake[0],
                          config.BOX_TOP + shake[1],
                          config.BOX_WIDTH, config.BOX_HEIGHT)
        pygame.draw.rect(surf, config.WHITE, box, config.BOX_BORDER)

        # 藍心：畫地板提示線
        if self.soul_mode == config.SOUL_BLUE:
            floor_y = self._floor_y() + config.HEART_SIZE / 2 + 2
            pygame.draw.line(surf, (90, 90, 130),
                             (config.BOX_LEFT + shake[0], floor_y + shake[1]),
                             (config.BOX_RIGHT + shake[0], floor_y + shake[1]),
                             2)

        # 用 clip 將子彈限制在框內顯示
        prev_clip = surf.get_clip()
        surf.set_clip(box)
        for b in self.bullets:
            b.draw(surf)

        # 綠心盾
        if self.soul_mode == config.SOUL_GREEN:
            shield_color = (160, 255, 160) if self.blocked_flash_t > 0 \
                else config.SOUL_COLORS[config.SOUL_GREEN]
            draw_shield_bar(surf,
                            self.heart_x + shake[0],
                            self.heart_y + shake[1],
                            self.shield_angle,
                            shield_color)

        # 心 (依模式變色；無敵時閃爍；切換瞬間白色光暈)
        if self.invuln <= 0 or (self.invuln // 4) % 2 == 0:
            heart_color = config.SOUL_COLORS[self.soul_mode]
            heart_size = config.HEART_SIZE
            if self.mode_flash_t > 0:
                # 切換瞬間放大 + 白色外圈
                pygame.draw.circle(surf, config.WHITE,
                                   (int(self.heart_x + shake[0]),
                                    int(self.heart_y + shake[1])),
                                   int(heart_size * 1.3), 2)
                heart_size = int(heart_size * 1.15)
            draw_heart(surf,
                       self.heart_x + shake[0],
                       self.heart_y + shake[1],
                       size=heart_size, color=heart_color)
        surf.set_clip(prev_clip)

        # 模式指示器 (戰鬥框左側)
        mi_x = max(20, config.BOX_LEFT - 100)
        mi_y = config.BOX_TOP + 8
        draw_mode_indicator(surf, self.font_small, self.soul_mode, mi_x, mi_y)

        # 提示
        hint = self._mode_hint()
        draw_text_center(surf, self.font_small, hint,
                         config.SCREEN_WIDTH // 2,
                         config.SCREEN_HEIGHT - 24, config.GREY)

        # 攝影機預覽 (右上)
        draw_camera_preview(surf, camera_frame,
                            font=self.font_small, error_msg=camera_error)

        # 無鏡頭橫幅
        draw_no_camera_banner(surf, self.font_small, camera_error)

    def _mode_hint(self):
        if self.soul_mode == config.SOUL_RED:
            return "☝ 紅心：自由移動  /  ✌ 切藍心  /  🖐 切綠心"
        if self.soul_mode == config.SOUL_BLUE:
            return "✌ 藍心：手快速上揮 = 跳！  X 軸跟食指"
        return "🖐 綠心：心固定，盾隨食指方向旋轉擋彈"


class ResultScene:
    """勝利 / 失敗結束畫面 (用懸停按鈕回主選單)。"""

    BTN_W = 280
    BTN_H = 80

    def __init__(self, result, level, font_big, font_mid, font_small):
        self.result = result
        self.level = level
        self.font_big = font_big
        self.font_mid = font_mid
        self.font_small = font_small

        cx = config.SCREEN_WIDTH // 2
        cy = config.SCREEN_HEIGHT - 160
        self.btn_back = pygame.Rect(cx - self.BTN_W - 20, cy - self.BTN_H // 2,
                                    self.BTN_W, self.BTN_H)
        self.btn_retry = pygame.Rect(cx + 20, cy - self.BTN_H // 2,
                                     self.BTN_W, self.BTN_H)
        self.hover_back = 0.0
        self.hover_retry = 0.0
        self.cursor = (cx, cy)
        self.choice = None  # 'menu' / 'retry'

    def update(self, dt, finger_norm, tracker):
        screen_rect = (0, 0, config.SCREEN_WIDTH, config.SCREEN_HEIGHT)
        mapped = tracker.map_to_rect(finger_norm, screen_rect)
        if mapped is not None:
            self.cursor = (int(mapped[0]), int(mapped[1]))

        if self.btn_back.collidepoint(self.cursor):
            self.hover_back = min(config.HOVER_SELECT_SECONDS, self.hover_back + dt)
        else:
            self.hover_back = max(0.0, self.hover_back - dt * 1.5)

        if self.btn_retry.collidepoint(self.cursor):
            self.hover_retry = min(config.HOVER_SELECT_SECONDS, self.hover_retry + dt)
        else:
            self.hover_retry = max(0.0, self.hover_retry - dt * 1.5)

        if self.hover_back >= config.HOVER_SELECT_SECONDS:
            self.choice = 'menu'
        elif self.hover_retry >= config.HOVER_SELECT_SECONDS:
            self.choice = 'retry'

        return self.choice

    def _draw_button(self, surf, rect, label, hover, base_color):
        ratio = hover / config.HOVER_SELECT_SECONDS
        bg = tuple(min(255, int(c * (0.25 + 0.65 * ratio))) for c in base_color)
        pygame.draw.rect(surf, bg, rect, border_radius=10)
        pygame.draw.rect(surf, base_color, rect, 3, border_radius=10)
        draw_text_center(surf, self.font_mid, label,
                         rect.centerx, rect.centery - 6, config.WHITE)
        pygame.draw.rect(surf, config.DARK_GREY,
                         (rect.left + 14, rect.bottom - 14,
                          rect.width - 28, 6), border_radius=3)
        if ratio > 0:
            pygame.draw.rect(surf, config.WHITE,
                             (rect.left + 14, rect.bottom - 14,
                              int((rect.width - 28) * ratio), 6),
                             border_radius=3)

    def draw(self, surf, camera_frame=None, camera_error=None):
        surf.fill(config.BLACK)
        title = "VICTORY!" if self.result == 'win' else "GAME OVER"
        color = config.YELLOW if self.result == 'win' else config.RED
        draw_text_center(surf, self.font_big, title,
                         config.SCREEN_WIDTH // 2, 200, color)
        draw_text_center(surf, self.font_mid, self.level["name"],
                         config.SCREEN_WIDTH // 2, 280, config.WHITE)
        msg = ("* 你成功撐過了這一關。" if self.result == 'win'
               else "* 不要灰心！再試一次吧。")
        draw_text_center(surf, self.font_small, msg,
                         config.SCREEN_WIDTH // 2, 330, config.GREY)

        self._draw_button(surf, self.btn_back, "回主選單",
                          self.hover_back, config.BLUE)
        self._draw_button(surf, self.btn_retry, "重新挑戰",
                          self.hover_retry, config.GREEN)

        draw_camera_preview(surf, camera_frame,
                            font=self.font_small, error_msg=camera_error)

        draw_heart(surf, self.cursor[0], self.cursor[1], size=14)
        pygame.draw.circle(surf, config.WHITE, self.cursor, 22, 1)

        draw_no_camera_banner(surf, self.font_small, camera_error)
