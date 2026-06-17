"""Undertale 風戰鬥場景 (回合制 + 手勢切換靈魂顏色) — OpenCV 版。

階段:
  DIALOG   → 對話 (打字機)
  PLAYER   → 玩家回合,選 FIGHT / ACT / ITEM / MERCY
  ACT_MENU → ACT 子選單
  ENEMY    → 敵人回合,閃彈幕 (沿用 RED/BLUE/GREEN 手勢)

靈魂模式 (僅 ENEMY 階段):
  RED   食指                自由 2D 移動 (預設)
  BLUE  食指+中指 (✌)        重力 + 跳躍
  GREEN 整隻手張開 (🖐)       固定中央 + 盾
"""
import math
import random

import config
import bullets as bullets_mod
from canvas import Rect
from utils import (clamp, draw_heart, heart_rect, draw_text_center,
                   draw_camera_preview, draw_shield_bar, shield_blocks,
                   draw_mode_indicator, draw_no_camera_banner, DialogBox,
                   load_enemy_sprite)

try:
    import audio
    _AUDIO = True
except Exception:
    _AUDIO = False


def _sfx(name):
    if _AUDIO:
        try:
            audio.play_sfx(name)
        except Exception:
            pass


class BattleScene:
    """回合制戰鬥。"""

    PHASE_DIALOG = "DIALOG"
    PHASE_PLAYER = "PLAYER"
    PHASE_ACT_MENU = "ACT_MENU"
    PHASE_ENEMY = "ENEMY"

    def __init__(self, level, font_big, font_mid, font_small,
                 font_btn=None, font_tiny=None):
        self.level = level
        self.font_big = font_big
        self.font_mid = font_mid
        self.font_small = font_small
        self.font_btn = font_btn or font_mid
        self.font_tiny = font_tiny or font_small

        # 玩家
        self.hp = level["hp"]
        self.hp_max = level["hp"]
        self.items = 3
        self.heal_amount = 10

        # 敵人
        self.enemy_name = level["enemy_name"]
        self.enemy_hp = level["enemy_hp"]
        self.enemy_hp_max = level["enemy_hp"]
        self.mercy = 0
        self.mercy_threshold = level["mercy_threshold"]

        # 階段 + 對話
        self.phase = self.PHASE_DIALOG
        self.dialog = None
        self.dialog_next_phase = self.PHASE_PLAYER
        self.dialog_done_action = None
        self._start_dialog(level["intro"], next_phase=self.PHASE_PLAYER)

        # 行動按鈕 (PLAYER 階段)
        self._build_action_buttons()
        self.act_buttons = []

        # 戰鬥彈幕
        self.pattern_id = level["pattern_id"]
        self.pattern = None
        self.bullets = []
        self.turn_duration = level["turn_duration"]
        self.turn_elapsed = 0.0

        # 心與游標
        self.heart_x = float(config.BOX_CENTER_X)
        self.heart_y = float(config.BOX_CENTER_Y)
        self.cursor = (config.BOX_CENTER_X, config.BOX_CENTER_Y)

        # 視覺反饋
        self.damage_numbers = []
        self.red_flash_t = 0.0
        self.shake_t = 0.0
        self.mode_flash_t = 0.0
        self.blocked_flash_t = 0.0

        # 動畫計時 (給 MERCY 鈕脈動用,取代 pygame.time.get_ticks)
        self._anim_t = 0.0

        # 既有 soul 模式 (僅 ENEMY 使用)
        self.soul_mode = config.SOUL_RED
        self.vel_y = 0.0
        self.on_ground = False
        self.jump_cooldown = 0.0
        self.shield_angle = 0.0
        self.invuln = 0

        # 怪物 GIF sprite
        self.sprite = load_enemy_sprite(level.get("sprite"))

        self.result = None

        # BGM
        if _AUDIO:
            try:
                audio.play_bgm(f"level{level['id']}", volume=0.4)
            except Exception:
                pass

    # ------------------------------------------------------------------
    def _build_action_buttons(self):
        labels_colors = [
            ("FIGHT",  (220, 60, 60)),
            ("ACT",    (220, 180, 60)),
            ("ITEM",   (80, 170, 230)),
            ("MERCY",  (60, 220, 120)),
        ]
        n = len(labels_colors)
        gap = 16
        bw = (config.BOX_WIDTH - (n - 1) * gap) // n
        bh = 48
        by = config.BOX_BOTTOM + 22
        self.action_buttons = []
        for i, (label, color) in enumerate(labels_colors):
            r = Rect(config.BOX_LEFT + i * (bw + gap), by, bw, bh)
            self.action_buttons.append({
                "rect": r, "label": label, "hover": 0.0, "color": color,
            })

    def _start_dialog(self, lines, next_phase=None, after=None):
        rect = Rect(config.BOX_LEFT, config.BOX_TOP,
                    config.BOX_WIDTH, config.BOX_HEIGHT)
        self.dialog = DialogBox(
            lines, self.font_small, rect,
            chars_per_sec=30,
            blip_sfx=(lambda: _sfx("blip")),
            post_line_delay=0.7,
        )
        self.dialog_next_phase = next_phase
        self.dialog_done_action = after
        self.phase = self.PHASE_DIALOG

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

        self._anim_t += dt
        if self.shake_t > 0: self.shake_t -= dt
        if self.mode_flash_t > 0: self.mode_flash_t -= dt
        if self.blocked_flash_t > 0: self.blocked_flash_t -= dt
        if self.red_flash_t > 0: self.red_flash_t -= dt
        if self.sprite is not None:
            self.sprite.update(dt)
        for d in self.damage_numbers:
            d["t"] += dt
            d["y"] += d["vy"] * dt
        self.damage_numbers = [d for d in self.damage_numbers if d["t"] < 0.8]

        # 游標 (全螢幕)
        screen_rect = (0, 0, config.SCREEN_WIDTH, config.SCREEN_HEIGHT)
        mapped = tracker.map_to_rect(finger_norm, screen_rect)
        if mapped is not None:
            self.cursor = (int(mapped[0]), int(mapped[1]))

        if self.phase == self.PHASE_DIALOG:
            self.dialog.update(dt)
            if self.dialog.done:
                action = self.dialog_done_action
                next_phase = self.dialog_next_phase
                self.dialog_done_action = None
                self.dialog_next_phase = None
                if action is not None:
                    action()
                elif next_phase is not None:
                    self.phase = next_phase
        elif self.phase == self.PHASE_PLAYER:
            self._update_button_hover(dt, self.action_buttons, self._on_action)
        elif self.phase == self.PHASE_ACT_MENU:
            self._update_button_hover(dt, self.act_buttons, self._on_act)
        elif self.phase == self.PHASE_ENEMY:
            self._update_enemy_turn(dt, finger_norm, tracker)

        return self.result

    def _update_button_hover(self, dt, buttons, on_pick):
        chosen = None
        for b in buttons:
            if b["rect"].collidepoint(self.cursor):
                b["hover"] = min(config.TURN_HOVER_SECONDS, b["hover"] + dt)
                if b["hover"] >= config.TURN_HOVER_SECONDS:
                    chosen = b["label"]
            else:
                b["hover"] = max(0.0, b["hover"] - dt * 1.5)
        if chosen is not None:
            for b in buttons: b["hover"] = 0.0
            on_pick(chosen)

    # ------------------------------------------------------------------
    def _on_action(self, label):
        if label == "FIGHT":
            self._do_fight()
        elif label == "ACT":
            self._open_act_menu()
        elif label == "ITEM":
            self._do_item()
        elif label == "MERCY":
            self._do_mercy()

    def _do_fight(self):
        _sfx("select")
        # 若該關卡設定了 dodge_chance,先擲骰判斷是否被閃開 (Sans 50%)
        dodge_chance = self.level.get("dodge_chance", 0.0)
        if dodge_chance > 0 and random.random() < dodge_chance:
            self.damage_numbers.append({
                "x": config.SCREEN_WIDTH // 2 + random.randint(-30, 30),
                "y": 140, "vy": -55, "t": 0,
                "val": "MISS", "color": config.GREY,
            })
            _sfx("menu")
            dodge_lines = self.level.get(
                "dodge_lines", ["你揮拳!", "...但是沒打中。"])
            self._start_dialog(dodge_lines, after=self._begin_enemy_turn)
            return

        dmg = random.randint(7, 13)
        self.enemy_hp = max(0, self.enemy_hp - dmg)
        self.damage_numbers.append({
            "x": config.SCREEN_WIDTH // 2 + random.randint(-30, 30),
            "y": 140, "vy": -55, "t": 0,
            "val": dmg, "color": config.YELLOW,
        })
        _sfx("hit")
        if self.enemy_hp <= 0:
            self._start_dialog(self.level["kill_lines"], after=self._end_victory)
        else:
            self._start_dialog(self.level["fight_lines"], after=self._begin_enemy_turn)

    def _do_item(self):
        _sfx("select")
        if self.items <= 0:
            self._start_dialog(["道具袋裡什麼都沒了。"], after=self._begin_enemy_turn)
            return
        self.items -= 1
        heal = min(self.heal_amount, self.hp_max - self.hp)
        self.hp += heal
        _sfx("heal")
        self.damage_numbers.append({
            "x": self.cursor[0], "y": config.BOX_BOTTOM + 100, "vy": -50, "t": 0,
            "val": heal, "color": config.GREEN,
        })
        self._start_dialog(
            [f"你吃了一塊怪物糖。", f"回復了 {heal} 點 HP。"],
            after=self._begin_enemy_turn,
        )

    def _do_mercy(self):
        if self.mercy >= self.mercy_threshold:
            _sfx("spare")
            self._start_dialog(self.level["spare_lines"], after=self._end_victory)
        else:
            _sfx("select")
            self._start_dialog(self.level["spare_not_ready_lines"],
                               after=self._begin_enemy_turn)

    def _open_act_menu(self):
        _sfx("menu")
        acts = self.level["acts"]
        labels = [a["label"] for a in acts] + ["BACK"]
        n = len(labels)
        gap = 12
        bw = (config.BOX_WIDTH - (n - 1) * gap) // n
        bh = 48
        by = config.BOX_BOTTOM + 22
        self.act_buttons = []
        for i, label in enumerate(labels):
            r = Rect(config.BOX_LEFT + i * (bw + gap), by, bw, bh)
            color = (200, 200, 80) if label != "BACK" else (140, 140, 140)
            self.act_buttons.append({
                "rect": r, "label": label, "hover": 0.0, "color": color,
            })
        self.phase = self.PHASE_ACT_MENU

    def _on_act(self, label):
        if label == "BACK":
            _sfx("menu")
            self.phase = self.PHASE_PLAYER
            return
        _sfx("select")
        for a in self.level["acts"]:
            if a["label"] == label:
                # mercy 變動可正可負;clamp 至 [0, threshold]
                delta = a.get("mercy", 0)
                self.mercy = max(0, min(self.mercy_threshold,
                                        self.mercy + delta))
                self._start_dialog(a["lines"], after=self._begin_enemy_turn)
                return

    def _begin_enemy_turn(self):
        self.phase = self.PHASE_ENEMY
        self.pattern = bullets_mod.make_pattern(self.pattern_id)
        self.bullets = []
        self.turn_elapsed = 0.0
        self.heart_x = float(config.BOX_CENTER_X)
        self.heart_y = float(config.BOX_CENTER_Y)
        self.soul_mode = config.SOUL_RED
        self.vel_y = 0.0
        self.on_ground = False
        self.invuln = 0

    def _end_victory(self):
        if _AUDIO:
            try: audio.stop_bgm()
            except Exception: pass
        self.result = 'win'

    def _end_defeat(self):
        if _AUDIO:
            try: audio.stop_bgm()
            except Exception: pass
        self.result = 'lose'

    # ------------------------------------------------------------------
    def _update_enemy_turn(self, dt, finger_norm, tracker):
        if self.pattern is not None and getattr(self.pattern, "forced_mode", None):
            self._enter_mode(self.pattern.forced_mode)
        self.shield_angle = tracker.angle

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
                if self.vel_y < 0: self.vel_y = 0.0
            if self.jump_cooldown > 0:
                self.jump_cooldown = max(0.0, self.jump_cooldown - dt)
            elif tracker.vy_norm < config.JUMP_VY_THRESHOLD and self.on_ground:
                self.vel_y = -config.JUMP_VELOCITY
                self.jump_cooldown = config.JUMP_COOLDOWN
                self.on_ground = False
        elif self.soul_mode == config.SOUL_GREEN:
            self.heart_x = float(config.BOX_CENTER_X)
            self.heart_y = float(config.BOX_CENTER_Y)

        self.pattern.update(dt, self.bullets)

        hb = heart_rect(self.heart_x, self.heart_y)
        for b in self.bullets:
            b.update(dt)
            if not b.alive: continue
            if (self.soul_mode == config.SOUL_GREEN
                    and not isinstance(b, bullets_mod.LaserBeam)):
                if isinstance(b, bullets_mod.BoneBullet):
                    r = b.rect()
                    cx, cy = r.centerx, r.centery
                else:
                    cx, cy = b.x, b.y
                if shield_blocks(cx, cy, self.heart_x, self.heart_y,
                                 self.shield_angle):
                    b.alive = False
                    self.blocked_flash_t = 0.12
                    continue
            if self.invuln <= 0 and b.hits(hb):
                dmg = b.damage
                self.hp -= dmg
                self.invuln = config.INVULN_FRAMES
                self.shake_t = 0.25
                self.red_flash_t = 0.3
                _sfx("hit")
                self.damage_numbers.append({
                    "x": self.heart_x + random.randint(-8, 8),
                    "y": self.heart_y - 20, "vy": -60, "t": 0,
                    "val": dmg, "color": config.HEART_RED,
                })
                if not isinstance(b, bullets_mod.LaserBeam):
                    b.alive = False
        self.bullets = [b for b in self.bullets if b.alive]

        if self.invuln > 0: self.invuln -= 1

        self.turn_elapsed += dt
        if self.hp <= 0:
            self.hp = 0
            self._end_defeat()
            return
        if self.turn_elapsed >= self.turn_duration:
            self.bullets = []
            self.pattern = None
            self.phase = self.PHASE_PLAYER

    # ------------------------------------------------------------------
    def draw(self, canvas, camera_frame=None, camera_error=None):
        shake = (0, 0)
        if self.shake_t > 0:
            shake = (random.randint(-4, 4), random.randint(-4, 4))

        canvas.fill(config.BLACK)

        # 關卡名 (y 從 36 → 46:讓出頂部給「鍵盤模式」紅色橫幅)
        draw_text_center(canvas, self.font_mid, self.level["name"],
                         config.SCREEN_WIDTH // 2, 46, self.level["color"])
        enemy_color = (config.YELLOW
                       if self.mercy >= self.mercy_threshold
                       else config.WHITE)
        draw_text_center(canvas, self.font_mid, self.enemy_name,
                         config.SCREEN_WIDTH // 2, 92, enemy_color)
        # 敵人 HP 條
        ebw, ebh = 280, 10
        ebx = (config.SCREEN_WIDTH - ebw) // 2
        eby = 120
        canvas.rect((ebx, eby, ebw, ebh), config.DARK_GREY, thickness=-1)
        eratio = self.enemy_hp / max(1, self.enemy_hp_max)
        canvas.rect((ebx, eby, int(ebw * eratio), ebh),
                    config.HEART_RED, thickness=-1)
        canvas.rect((ebx, eby, ebw, ebh), config.WHITE, thickness=1)

        # 怪物 sprite
        if self.sprite is not None:
            self.sprite.draw(canvas, config.SCREEN_WIDTH // 2, 200)

        # 中央區塊
        if self.phase == self.PHASE_DIALOG:
            self.dialog.rect.topleft = (config.BOX_LEFT + shake[0],
                                        config.BOX_TOP + shake[1])
            self.dialog.draw(canvas, bg=config.BLACK,
                             border_color=config.WHITE,
                             border_w=config.BOX_BORDER, padding=22)
        else:
            box = Rect(config.BOX_LEFT + shake[0],
                       config.BOX_TOP + shake[1],
                       config.BOX_WIDTH, config.BOX_HEIGHT)
            canvas.rect(box, config.WHITE, thickness=config.BOX_BORDER)

            if self.phase == self.PHASE_ENEMY:
                if self.soul_mode == config.SOUL_BLUE:
                    floor_y = self._floor_y() + config.HEART_SIZE / 2 + 2
                    canvas.line((config.BOX_LEFT + shake[0],
                                 floor_y + shake[1]),
                                (config.BOX_RIGHT + shake[0],
                                 floor_y + shake[1]),
                                (90, 90, 130), thickness=2)
                if (self.pattern is not None
                        and hasattr(self.pattern, "telegraph_sides")):
                    for side, ratio in self.pattern.telegraph_sides():
                        self._draw_telegraph_arrow(canvas, side, ratio, shake)
                for b in self.bullets:
                    b.draw(canvas)
                if self.soul_mode == config.SOUL_GREEN:
                    shield_color = ((160, 255, 160)
                                    if self.blocked_flash_t > 0
                                    else config.SOUL_COLORS[config.SOUL_GREEN])
                    draw_shield_bar(canvas,
                                    self.heart_x + shake[0],
                                    self.heart_y + shake[1],
                                    self.shield_angle, shield_color)
                if self.invuln <= 0 or (self.invuln // 4) % 2 == 0:
                    heart_color = config.SOUL_COLORS[self.soul_mode]
                    hs = config.HEART_SIZE
                    if self.mode_flash_t > 0:
                        canvas.circle(self.heart_x + shake[0],
                                      self.heart_y + shake[1],
                                      int(hs * 1.5),
                                      config.WHITE, thickness=2)
                        hs = int(hs * 1.15)
                    draw_heart(canvas,
                               self.heart_x + shake[0],
                               self.heart_y + shake[1],
                               size=hs, color=heart_color)
                # 模式指示器
                mi_x = max(20, config.BOX_LEFT - 100)
                mi_y = config.BOX_TOP + 8
                draw_mode_indicator(canvas, self.font_small,
                                    self.soul_mode, mi_x, mi_y)
            else:
                tip = ("* 你的回合。" if self.phase == self.PHASE_PLAYER
                       else "* 想做什麼?")
                canvas.text(tip, box.left + 22, box.top + 22,
                            config.WHITE, self.font_small.size_pt,
                            bold=self.font_small.bold)

        # 行動按鈕
        if self.phase == self.PHASE_PLAYER:
            self._draw_buttons(canvas, self.action_buttons)
        elif self.phase == self.PHASE_ACT_MENU:
            self._draw_buttons(canvas, self.act_buttons)

        # 玩家 HUD
        self._draw_player_hud(canvas)

        # 受傷紅光全螢幕邊框
        if self.red_flash_t > 0:
            alpha = (140 / 255.0) * (self.red_flash_t / 0.3)
            canvas.overlay_border((255, 30, 30), alpha, thickness=28)

        # 傷害數字 (浮上去)
        for d in self.damage_numbers:
            life = max(0.0, 1.0 - d["t"] / 0.8)
            canvas.text(f"{d['val']}",
                        int(d["x"]), int(d["y"]),
                        d["color"], self.font_mid.size_pt,
                        bold=self.font_mid.bold, anchor="center",
                        alpha=life)

        # 游標愛心 (僅選單階段)
        if self.phase in (self.PHASE_PLAYER, self.PHASE_ACT_MENU):
            draw_heart(canvas, self.cursor[0], self.cursor[1],
                       size=14, color=config.HEART_RED)
            canvas.circle(self.cursor[0], self.cursor[1], 22,
                          config.WHITE, thickness=1)

        # 提示
        draw_text_center(canvas, self.font_tiny, self._phase_hint(),
                         config.SCREEN_WIDTH // 2,
                         config.SCREEN_HEIGHT - 12, config.GREY)

        # 攝影機 + 無鏡頭橫幅
        draw_camera_preview(canvas, camera_frame,
                            font=self.font_small, error_msg=camera_error)
        draw_no_camera_banner(canvas, self.font_tiny, camera_error)

    def _draw_telegraph_arrow(self, canvas, side, ratio, shake):
        cx = config.BOX_CENTER_X + shake[0]
        cy = config.BOX_CENTER_Y + shake[1]
        offset = 110
        intensity = 1.0 - ratio
        col = (
            int(120 + 135 * intensity),
            int(30 + 20 * (1 - intensity)),
            int(30 + 20 * (1 - intensity)),
        )
        if side == 'top':
            tip = (cx, cy - offset)
            base1 = (cx - 14, cy - offset - 18)
            base2 = (cx + 14, cy - offset - 18)
        elif side == 'bottom':
            tip = (cx, cy + offset)
            base1 = (cx - 14, cy + offset + 18)
            base2 = (cx + 14, cy + offset + 18)
        elif side == 'left':
            tip = (cx - offset, cy)
            base1 = (cx - offset - 18, cy - 14)
            base2 = (cx - offset - 18, cy + 14)
        else:
            tip = (cx + offset, cy)
            base1 = (cx + offset + 18, cy - 14)
            base2 = (cx + offset + 18, cy + 14)
        canvas.polygon([tip, base1, base2], col, thickness=-1)
        canvas.polygon([tip, base1, base2], config.WHITE, thickness=2)

    # ------------------------------------------------------------------
    def _draw_buttons(self, canvas, buttons):
        mercy_ready = (self.mercy_threshold < 99
                       and self.mercy >= self.mercy_threshold)
        pulse = 0.5 + 0.5 * math.sin(self._anim_t * 6.0)
        font_candidates = (self.font_btn, self.font_small, self.font_tiny)
        for b in buttons:
            r = b["rect"]
            hr = b["hover"] / config.TURN_HOVER_SECONDS
            color = b["color"]
            if b["label"] == "MERCY" and mercy_ready:
                color = config.YELLOW
            bg = tuple(min(255, int(c * (0.18 + 0.55 * hr))) for c in color)
            if b["label"] == "MERCY" and mercy_ready and hr <= 0:
                bg = tuple(min(255, int(c * (0.30 + 0.35 * pulse)))
                           for c in color)
            canvas.rect(r, bg, thickness=-1)
            border_w = 4 if (b["label"] == "MERCY" and mercy_ready) else 3
            canvas.rect(r, color, thickness=border_w)

            inner_w = r.width - 12
            label_font = font_candidates[-1]
            for cf in font_candidates:
                if cf.size(b["label"])[0] <= inner_w:
                    label_font = cf
                    break
            draw_text_center(canvas, label_font, b["label"],
                             r.centerx, r.centery, config.WHITE,
                             max_width=inner_w)
            if hr > 0:
                canvas.rect((r.left + 6, r.bottom - 6,
                             int((r.width - 12) * hr), 3),
                            config.WHITE, thickness=-1)

    def _draw_player_hud(self, canvas):
        y = config.BOX_BOTTOM + 86
        font = self.font_small
        x = config.BOX_LEFT
        # FRISK
        canvas.text("FRISK", x, y, config.WHITE, font.size_pt, bold=font.bold)
        x += font.size("FRISK")[0] + 28
        # LV
        canvas.text("LV 1", x, y, config.WHITE, font.size_pt, bold=font.bold)
        x += font.size("LV 1")[0] + 28
        # HP label
        canvas.text("HP", x, y, config.YELLOW, font.size_pt, bold=font.bold)
        x += font.size("HP")[0] + 8
        # HP bar
        bw = 140
        bh = font.get_height() - 4
        canvas.rect((x, y + 2, bw, bh), config.RED, thickness=-1)
        ratio = max(0.0, self.hp / self.hp_max)
        canvas.rect((x, y + 2, int(bw * ratio), bh),
                    config.YELLOW, thickness=-1)
        x += bw + 10
        # numbers
        hp_text = f"{self.hp} / {self.hp_max}"
        canvas.text(hp_text, x, y, config.WHITE, font.size_pt, bold=font.bold)
        x += font.size(hp_text)[0] + 24
        # ITEM
        item_text = f"ITEM x {self.items}"
        canvas.text(item_text, x, y, config.WHITE, font.size_pt, bold=font.bold)
        x += font.size(item_text)[0] + 24
        # MERCY 進度
        if self.mercy_threshold >= 99:
            canvas.text("MERCY —", x, y, config.GREY,
                        font.size_pt, bold=font.bold)
        else:
            ready = self.mercy >= self.mercy_threshold
            label_color = config.YELLOW if ready else config.WHITE
            text = (f"MERCY {self.mercy}/{self.mercy_threshold}"
                    + ("  READY!" if ready else ""))
            canvas.text(text, x, y, label_color,
                        font.size_pt, bold=font.bold)

    def _phase_hint(self):
        if self.phase == self.PHASE_DIALOG:
            return "..."
        if self.phase == self.PHASE_PLAYER:
            return "懸停按鈕 1 秒確認"
        if self.phase == self.PHASE_ACT_MENU:
            return "選擇行動,或 BACK 返回"
        if self.phase == self.PHASE_ENEMY:
            if self.soul_mode == config.SOUL_RED:
                return "紅心:自由移動 (食指控制)"
            if self.soul_mode == config.SOUL_BLUE:
                return "藍心:重力下墜 / 手往上揮 = 跳"
            return "綠心:心固定 / 盾隨食指方向 (上下左右)"
        return ""


class ResultScene:
    """勝利 / 失敗結束畫面 (用懸停按鈕回主選單)。"""

    BTN_W = 280
    BTN_H = 80

    def __init__(self, result, level, font_big, font_mid, font_small,
                 font_btn=None, font_tiny=None):
        self.result = result
        self.level = level
        self.font_big = font_big
        self.font_mid = font_mid
        self.font_small = font_small
        self.font_btn = font_btn or font_mid
        self.font_tiny = font_tiny or font_small

        cx = config.SCREEN_WIDTH // 2
        cy = config.SCREEN_HEIGHT - 160
        self.btn_back = Rect(cx - self.BTN_W - 20, cy - self.BTN_H // 2,
                             self.BTN_W, self.BTN_H)
        self.btn_retry = Rect(cx + 20, cy - self.BTN_H // 2,
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

    def _draw_button(self, canvas, rect, label, hover, base_color):
        ratio = hover / config.HOVER_SELECT_SECONDS
        bg = tuple(min(255, int(c * (0.25 + 0.65 * ratio))) for c in base_color)
        canvas.rect(rect, bg, thickness=-1)
        canvas.rect(rect, base_color, thickness=3)
        draw_text_center(canvas, self.font_btn, label,
                         rect.centerx, rect.centery - 6, config.WHITE,
                         max_width=rect.width - 32)
        canvas.rect((rect.left + 14, rect.bottom - 14,
                     rect.width - 28, 6),
                    config.DARK_GREY, thickness=-1)
        if ratio > 0:
            canvas.rect((rect.left + 14, rect.bottom - 14,
                         int((rect.width - 28) * ratio), 6),
                        config.WHITE, thickness=-1)

    def draw(self, canvas, camera_frame=None, camera_error=None):
        canvas.fill(config.BLACK)
        title = "VICTORY!" if self.result == 'win' else "GAME OVER"
        color = config.YELLOW if self.result == 'win' else config.RED
        draw_text_center(canvas, self.font_big, title,
                         config.SCREEN_WIDTH // 2, 200, color)
        draw_text_center(canvas, self.font_mid, self.level["name"],
                         config.SCREEN_WIDTH // 2, 280, config.WHITE)
        msg = ("* 你成功撐過了這一關。" if self.result == 'win'
               else "* 不要灰心!再試一次吧。")
        draw_text_center(canvas, self.font_small, msg,
                         config.SCREEN_WIDTH // 2, 330, config.GREY)

        self._draw_button(canvas, self.btn_back, "回主選單",
                          self.hover_back, config.BLUE)
        self._draw_button(canvas, self.btn_retry, "重新挑戰",
                          self.hover_retry, config.GREEN)

        draw_camera_preview(canvas, camera_frame,
                            font=self.font_small, error_msg=camera_error)

        draw_heart(canvas, self.cursor[0], self.cursor[1], size=14)
        canvas.circle(self.cursor[0], self.cursor[1], 22,
                      config.WHITE, thickness=1)

        draw_no_camera_banner(canvas, self.font_tiny, camera_error)
