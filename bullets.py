"""彈幕物件與三關卡攻擊模式。

座標皆以畫面像素為單位;戰鬥框由 config 提供。

每個 AttackPattern 都暴露 ``forced_mode`` 屬性,讓 BattleScene 在敵人回合
每幀讀取並切換玩家的靈魂模式 (玩家無法自行切換,完全由敵人控制)。
"""
import math
import random

import pygame

import config


class Bullet:
    """子彈基底類別 (圓形)。"""

    def __init__(self, x, y, vx, vy, damage=8, radius=8, color=config.WHITE):
        self.x = float(x)
        self.y = float(y)
        self.vx = float(vx)
        self.vy = float(vy)
        self.damage = damage
        self.radius = radius
        self.color = color
        self.alive = True

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        if (self.x < config.BOX_LEFT - 80 or self.x > config.BOX_RIGHT + 80
                or self.y < config.BOX_TOP - 80 or self.y > config.BOX_BOTTOM + 80):
            self.alive = False

    def draw(self, surf):
        pygame.draw.circle(surf, self.color, (int(self.x), int(self.y)), self.radius)
        pygame.draw.circle(surf, config.WHITE, (int(self.x), int(self.y)), self.radius, 1)

    def hits(self, heart_rect):
        return heart_rect.collidepoint(self.x, self.y)


class WaveBullet(Bullet):
    """沿主軸前進並上下擺動的子彈 (Level 2 Froggit 替代用)。"""

    def __init__(self, x, y, vy, amp=40, freq=2.5, **kwargs):
        super().__init__(x, y, 0, vy, **kwargs)
        self.base_x = x
        self.t = 0.0
        self.amp = amp
        self.freq = freq

    def update(self, dt):
        self.t += dt
        self.y += self.vy * dt
        self.x = self.base_x + math.sin(self.t * self.freq) * self.amp
        if self.y > config.BOX_BOTTOM + 80 or self.y < config.BOX_TOP - 80:
            self.alive = False


class SpearBullet(Bullet):
    """Undyne 風長矛:多邊形外觀,沿速度方向朝向。"""

    def __init__(self, x, y, vx, vy, damage=10, length=46, thickness=10,
                 color=(255, 220, 60)):
        super().__init__(x, y, vx, vy, damage=damage, radius=6, color=color)
        self.length = length
        self.thickness = thickness
        # 上一幀座標,用於快速移動時的 swept hit-test
        self.prev_x = float(x)
        self.prev_y = float(y)

    def update(self, dt):
        self.prev_x = self.x
        self.prev_y = self.y
        super().update(dt)

    def _polygon(self):
        ang = math.atan2(self.vy, self.vx)
        cos_a, sin_a = math.cos(ang), math.sin(ang)
        hl, ht = self.length / 2, self.thickness / 2
        local = [(-hl, -ht), (hl - 8, -ht), (hl + 12, 0),
                 (hl - 8, ht), (-hl, ht), (-hl - 10, 0)]
        pts = []
        for lx, ly in local:
            rx = self.x + cos_a * lx - sin_a * ly
            ry = self.y + sin_a * lx + cos_a * ly
            pts.append((rx, ry))
        return pts

    def draw(self, surf):
        pts = self._polygon()
        pygame.draw.polygon(surf, self.color, pts)
        pygame.draw.polygon(surf, config.WHITE, pts, 2)

    def hits(self, heart_rect):
        # 用「沿矛身多點 + 上一幀位置 swept」的近似命中測試:
        # 1) 矛本體是長 polygon (length≈46, 含頭尾尖端共約 68px), 只測中心點
        #    在高速 (GREEN 階段 500 px/s) 會有矛尖穿過心、但中心沒進入 hitbox 的破綻;
        # 2) 一幀 16ms × 500 px/s = 8 px, 加上心 22 px hitbox 雖然不容易 tunneling,
        #    但矛若以斜角從邊緣劃過,中心仍可能整段都不在 hitbox 內 → 表現為「明明畫面打中卻沒扣血」。
        # 解法:沿著矛軸方向取 5 個點 (頭尾尖端 + 中心 + 兩個 1/4 位置),
        # 並對「上一幀的本體」與「這一幀的本體」之間用線性插值再多取一組,確保連續命中。
        ang = math.atan2(self.vy, self.vx)
        cos_a, sin_a = math.cos(ang), math.sin(ang)
        hl = self.length / 2
        offsets = (-hl - 8, -hl / 2, 0.0, hl / 2, hl + 10)
        # 主要:對「現在」+「上一幀」兩個位置都做多點測試
        for base_x, base_y in ((self.x, self.y), (self.prev_x, self.prev_y)):
            for off in offsets:
                px = base_x + cos_a * off
                py = base_y + sin_a * off
                if heart_rect.collidepoint(px, py):
                    return True
        # 補強:位移大於矛長時,中間補一個取樣點防 tunneling
        dx = self.x - self.prev_x
        dy = self.y - self.prev_y
        step2 = dx * dx + dy * dy
        if step2 > (self.length * 0.5) ** 2:
            mid_x = (self.x + self.prev_x) * 0.5
            mid_y = (self.y + self.prev_y) * 0.5
            for off in offsets:
                if heart_rect.collidepoint(mid_x + cos_a * off,
                                           mid_y + sin_a * off):
                    return True
        return False


class BoneBullet:
    """Sans 風骨頭,從邊界穿越戰鬥框的長條子彈。"""

    def __init__(self, axis, pos, speed, length=70, thickness=10,
                 damage=12, color=config.WHITE):
        self.axis = axis  # 'h' = 水平移動, 'v' = 垂直移動
        self.speed = speed
        self.length = length
        self.thickness = thickness
        self.damage = damage
        self.color = color
        self.alive = True
        if axis == 'h':
            self.y = pos
            self.x = config.BOX_LEFT - length - 5 if speed > 0 else config.BOX_RIGHT + 5
        else:
            self.x = pos
            self.y = config.BOX_TOP - length - 5 if speed > 0 else config.BOX_BOTTOM + 5

    def update(self, dt):
        if self.axis == 'h':
            self.x += self.speed * dt
            if (self.speed > 0 and self.x > config.BOX_RIGHT + 10) or \
               (self.speed < 0 and self.x + self.length < config.BOX_LEFT - 10):
                self.alive = False
        else:
            self.y += self.speed * dt
            if (self.speed > 0 and self.y > config.BOX_BOTTOM + 10) or \
               (self.speed < 0 and self.y + self.length < config.BOX_TOP - 10):
                self.alive = False

    def rect(self):
        if self.axis == 'h':
            return pygame.Rect(int(self.x), int(self.y - self.thickness / 2),
                               int(self.length), int(self.thickness))
        return pygame.Rect(int(self.x - self.thickness / 2), int(self.y),
                           int(self.thickness), int(self.length))

    def draw(self, surf):
        r = self.rect()
        pygame.draw.rect(surf, self.color, r, border_radius=4)
        pygame.draw.rect(surf, config.BLACK, r, 2, border_radius=4)

    def hits(self, heart_rect):
        return self.rect().colliderect(heart_rect)


class LaserBeam:
    """Gaster Blaster 風雷射:先預警,再放出傷害光束。"""

    TELEGRAPH = 0.7
    FIRE = 0.35

    def __init__(self, axis, pos, thickness=28, damage=20):
        self.axis = axis
        self.pos = pos
        self.thickness = thickness
        self.damage = damage
        self.alive = True
        self.t = 0.0

    def update(self, dt):
        self.t += dt
        if self.t >= self.TELEGRAPH + self.FIRE:
            self.alive = False

    def _beam_rect(self):
        if self.axis == 'h':
            return pygame.Rect(config.BOX_LEFT, int(self.pos - self.thickness / 2),
                               config.BOX_WIDTH, self.thickness)
        return pygame.Rect(int(self.pos - self.thickness / 2), config.BOX_TOP,
                           self.thickness, config.BOX_HEIGHT)

    def draw(self, surf):
        r = self._beam_rect()
        if self.t < self.TELEGRAPH:
            ratio = self.t / self.TELEGRAPH
            color = (int(60 + 195 * ratio),
                     int(30 * (1 - ratio)),
                     int(30 * (1 - ratio)))
            if self.axis == 'h':
                y = r.centery
                step = 16
                for x in range(r.left, r.right, step):
                    pygame.draw.line(surf, color, (x, y), (x + step // 2, y), 2)
            else:
                x = r.centerx
                step = 16
                for y in range(r.top, r.bottom, step):
                    pygame.draw.line(surf, color, (x, y), (x, y + step // 2), 2)
        else:
            pygame.draw.rect(surf, config.WHITE, r)
            inner = r.inflate(-6, -6)
            pygame.draw.rect(surf, config.HEART_RED, inner)

    def hits(self, heart_rect):
        if self.t < self.TELEGRAPH:
            return False
        return self._beam_rect().colliderect(heart_rect)


# ---------------------------------------------------------------------------
# 攻擊模式
# ---------------------------------------------------------------------------

class AttackPattern:
    """所有攻擊模式的基底。

    forced_mode  : str — 強制玩家進入的靈魂模式 (RED/BLUE/GREEN)。每幀讀。
    """

    def __init__(self):
        self.t = 0.0
        self.spawn_t = 0.0
        self.forced_mode = config.SOUL_RED

    def update(self, dt, bullets):
        raise NotImplementedError


class UndynePattern(AttackPattern):
    """Level 1 - Undyne:長矛攻擊。

    交替 RED / GREEN 兩階段:
      RED   2.5s:矛從隨機側飛入,玩家自由移動閃避
      GREEN 3.5s:矛只從上下左右四個方向直接射向中心,
                 玩家心被鎖在中央,須用食指方向擺盾擋下
    """

    PHASE_RED_DUR = 2.5
    PHASE_GREEN_DUR = 3.5
    INTERVAL_RED = 0.42
    INTERVAL_GREEN = 0.55

    def __init__(self):
        super().__init__()
        self.phase = "RED"
        self.phase_t = 0.0
        self.forced_mode = config.SOUL_RED
        # 綠心階段:預先預警再射,讓玩家有時間轉盾
        self._green_queue = []  # list of (fire_time, side)
        self._tele_time = 0.5   # 預警秒數

    def update(self, dt, bullets):
        self.t += dt
        self.spawn_t += dt
        self.phase_t += dt

        # ------ phase switch ------
        # 切換愛心顏色時清空場上所有舊矛,避免上一階段的子彈干擾新階段
        if self.phase == "RED" and self.phase_t >= self.PHASE_RED_DUR:
            self.phase = "GREEN"
            self.phase_t = 0.0
            self.spawn_t = 0.0
            self.forced_mode = config.SOUL_GREEN
            self._green_queue.clear()
            bullets.clear()
        elif self.phase == "GREEN" and self.phase_t >= self.PHASE_GREEN_DUR:
            self.phase = "RED"
            self.phase_t = 0.0
            self.spawn_t = 0.0
            self.forced_mode = config.SOUL_RED
            self._green_queue.clear()
            bullets.clear()

        if self.phase == "RED":
            self._update_red(bullets)
        else:
            self._update_green(bullets)

    # -- RED -----------------------------------------------------------
    def _update_red(self, bullets):
        if self.spawn_t < self.INTERVAL_RED:
            return
        self.spawn_t = 0.0
        # 從隨機邊射入,角度略指向戰鬥框中心 (玩家須左右閃)
        side = random.choice(['top', 'bottom', 'left', 'right'])
        cx, cy = config.BOX_CENTER_X, config.BOX_CENTER_Y
        speed = random.uniform(260, 330)
        if side == 'top':
            x = random.uniform(config.BOX_LEFT + 20, config.BOX_RIGHT - 20)
            y = config.BOX_TOP - 30
        elif side == 'bottom':
            x = random.uniform(config.BOX_LEFT + 20, config.BOX_RIGHT - 20)
            y = config.BOX_BOTTOM + 30
        elif side == 'left':
            x = config.BOX_LEFT - 30
            y = random.uniform(config.BOX_TOP + 20, config.BOX_BOTTOM - 20)
        else:
            x = config.BOX_RIGHT + 30
            y = random.uniform(config.BOX_TOP + 20, config.BOX_BOTTOM - 20)
        # 朝向靠近中心區域 (帶亂數)
        tgt_x = cx + random.uniform(-60, 60)
        tgt_y = cy + random.uniform(-50, 50)
        dx, dy = tgt_x - x, tgt_y - y
        d = max(1.0, math.hypot(dx, dy))
        vx, vy = dx / d * speed, dy / d * speed
        bullets.append(SpearBullet(x, y, vx, vy, damage=10))

    # -- GREEN ---------------------------------------------------------
    def _update_green(self, bullets):
        # 每隔 INTERVAL_GREEN 排一支新矛到佇列 (帶預警時間)
        if self.spawn_t >= self.INTERVAL_GREEN:
            self.spawn_t = 0.0
            side = random.choice(['top', 'bottom', 'left', 'right'])
            fire_time = self.phase_t + self._tele_time
            self._green_queue.append((fire_time, side))

        # 觸發到時間的矛
        ready = [q for q in self._green_queue if q[0] <= self.phase_t]
        for q in ready:
            self._green_queue.remove(q)
            self._spawn_cardinal_spear(q[1], bullets)

    def _spawn_cardinal_spear(self, side, bullets):
        cx, cy = config.BOX_CENTER_X, config.BOX_CENTER_Y
        speed = 500
        if side == 'top':
            x, y, vx, vy = cx, config.BOX_TOP - 30, 0, speed
        elif side == 'bottom':
            x, y, vx, vy = cx, config.BOX_BOTTOM + 30, 0, -speed
        elif side == 'left':
            x, y, vx, vy = config.BOX_LEFT - 30, cy, speed, 0
        else:
            x, y, vx, vy = config.BOX_RIGHT + 30, cy, -speed, 0
        bullets.append(SpearBullet(x, y, vx, vy, damage=14,
                                   color=(255, 240, 100)))

    def telegraph_sides(self):
        """目前 phase_t 之前 0~_tele_time 秒會射的方向 (給 BattleScene 畫預警)。"""
        if self.phase != "GREEN":
            return []
        out = []
        for fire_time, side in self._green_queue:
            remain = fire_time - self.phase_t
            if 0 <= remain <= self._tele_time:
                out.append((side, remain / self._tele_time))   # (side, 1=還久 ~ 0=快來)
        return out


class FroggitPattern(AttackPattern):
    """Level 2 - Froggit:蒼蠅從四面八方緩慢飛過戰鬥框 (原 Level1Pattern)。"""

    INTERVAL = 0.55

    def __init__(self):
        super().__init__()
        self.forced_mode = config.SOUL_RED

    def update(self, dt, bullets):
        self.t += dt
        self.spawn_t += dt
        if self.spawn_t < self.INTERVAL:
            return
        self.spawn_t = 0.0
        for _ in range(2):
            side = random.choice(['top', 'bottom', 'left', 'right'])
            speed = random.uniform(110, 160)
            if side == 'top':
                x = random.uniform(config.BOX_LEFT, config.BOX_RIGHT)
                y = config.BOX_TOP - 20
                vx, vy = random.uniform(-30, 30), speed
            elif side == 'bottom':
                x = random.uniform(config.BOX_LEFT, config.BOX_RIGHT)
                y = config.BOX_BOTTOM + 20
                vx, vy = random.uniform(-30, 30), -speed
            elif side == 'left':
                x = config.BOX_LEFT - 20
                y = random.uniform(config.BOX_TOP, config.BOX_BOTTOM)
                vx, vy = speed, random.uniform(-30, 30)
            else:
                x = config.BOX_RIGHT + 20
                y = random.uniform(config.BOX_TOP, config.BOX_BOTTOM)
                vx, vy = -speed, random.uniform(-30, 30)
            bullets.append(Bullet(x, y, vx, vy, damage=6, radius=9,
                                  color=config.GREEN))


class SansPattern(AttackPattern):
    """Level 3 - Sans:骨頭 + 雷射;會隨機把愛心切成藍色。

    階段:
      RED  3.5s  自由閃避;混合水平/垂直骨頭 + 偶發雷射 (原版)
      BLUE 3.0s  愛心藍 (重力);骨牆從兩側貼地飛過,玩家須跳過
    """

    PHASE_RED_DUR = 3.5
    PHASE_BLUE_DUR = 3.0
    BONE_INTERVAL_RED = 0.45
    BONE_INTERVAL_BLUE = 0.85
    LASER_INTERVAL = 4.0

    def __init__(self):
        super().__init__()
        self.phase = "RED"
        self.phase_t = 0.0
        self.forced_mode = config.SOUL_RED
        self.laser_t = 1.5

    def update(self, dt, bullets):
        self.t += dt
        self.spawn_t += dt
        self.laser_t += dt
        self.phase_t += dt

        # 階段切換 — 清空場上所有舊骨頭 / 雷射,避免上一階段攻擊跨入新模式
        if self.phase == "RED" and self.phase_t >= self.PHASE_RED_DUR:
            self.phase = "BLUE"
            self.phase_t = 0.0
            self.spawn_t = 0.0
            self.laser_t = 0.0
            self.forced_mode = config.SOUL_BLUE
            bullets.clear()
        elif self.phase == "BLUE" and self.phase_t >= self.PHASE_BLUE_DUR:
            self.phase = "RED"
            self.phase_t = 0.0
            self.spawn_t = 0.0
            self.laser_t = 0.0
            self.forced_mode = config.SOUL_RED
            bullets.clear()

        if self.phase == "BLUE":
            self._update_blue(bullets)
        else:
            self._update_red(bullets)

    @staticmethod
    def _safe_wall_heights():
        """依 config 物理常數算出「保證跳得過」的三檔牆高 (高/中/低)。

        max_jump = V²/(2g);心頂在 apex 距離地板:max_jump + 1.2·HEART_SIZE/2 + 2
        牆頂位置 = BOX_BOTTOM - wall_h - 2;
        為了不必 pixel-perfect 時機,額外留 20 px 餘裕。
        """
        max_jump = (config.JUMP_VELOCITY ** 2) / (2.0 * config.GRAVITY)
        heart_half = config.HEART_SIZE * 1.2 / 2.0
        safety = 20  # 玩家不必 pixel-perfect 時機就能跨過
        max_h = max(20, int(max_jump - heart_half - 2 - safety))
        return [int(max_h * 0.55), int(max_h * 0.8), max_h]

    # -- BLUE 階段 (跳骨牆) ---------------------------------------------
    def _update_blue(self, bullets):
        if self.spawn_t < self.BONE_INTERVAL_BLUE:
            return
        self.spawn_t = 0.0
        # 從邊界貼地飛來的「骨牆」(細直立矩形,水平移動)
        speed = random.choice([-1, 1]) * random.uniform(360, 460)
        wall_h = random.choice(self._safe_wall_heights())
        y = config.BOX_BOTTOM - wall_h / 2 - 2
        bullets.append(BoneBullet('h', y, speed,
                                  length=18, thickness=wall_h,
                                  damage=12, color=(220, 220, 255)))
        # 偶爾來一段「高骨頭」貼天花板 (純視覺壓迫,跳起來碰不到)
        if random.random() < 0.30:
            top_h = random.choice([55, 75])
            y2 = config.BOX_TOP + top_h / 2 + 2
            bullets.append(BoneBullet('h', y2, speed,
                                      length=18, thickness=top_h,
                                      damage=12, color=(180, 180, 255)))

    # -- RED 階段 (原版) ----------------------------------------------
    def _update_red(self, bullets):
        if self.spawn_t >= self.BONE_INTERVAL_RED:
            self.spawn_t = 0.0
            if random.random() < 0.5:
                y = random.uniform(config.BOX_TOP + 25, config.BOX_BOTTOM - 25)
                speed = random.choice([-1, 1]) * random.uniform(260, 340)
                bullets.append(BoneBullet('h', y, speed,
                                          length=random.randint(60, 110)))
            else:
                x = random.uniform(config.BOX_LEFT + 25, config.BOX_RIGHT - 25)
                speed = random.choice([-1, 1]) * random.uniform(260, 340)
                bullets.append(BoneBullet('v', x, speed,
                                          length=random.randint(60, 110)))

        if self.laser_t >= self.LASER_INTERVAL:
            self.laser_t = 0.0
            if random.random() < 0.5:
                pos = random.uniform(config.BOX_TOP + 30, config.BOX_BOTTOM - 30)
                bullets.append(LaserBeam('h', pos))
            else:
                pos = random.uniform(config.BOX_LEFT + 30, config.BOX_RIGHT - 30)
                bullets.append(LaserBeam('v', pos))


def make_pattern(level_id):
    return {
        1: UndynePattern,
        2: FroggitPattern,
        3: SansPattern,
    }[level_id]()
