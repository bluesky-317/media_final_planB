"""彈幕物件與三關卡攻擊模式。

座標皆以畫面像素為單位；戰鬥框由 config 提供。
"""
import math
import random

import pygame

import config


class Bullet:
    """子彈基底類別。"""

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
        # 走出戰鬥框過遠就消失
        if (self.x < config.BOX_LEFT - 80 or self.x > config.BOX_RIGHT + 80
                or self.y < config.BOX_TOP - 80 or self.y > config.BOX_BOTTOM + 80):
            self.alive = False

    def draw(self, surf):
        pygame.draw.circle(surf, self.color, (int(self.x), int(self.y)), self.radius)
        pygame.draw.circle(surf, config.WHITE, (int(self.x), int(self.y)), self.radius, 1)

    def hits(self, heart_rect):
        return heart_rect.collidepoint(self.x, self.y)


class WaveBullet(Bullet):
    """沿主軸前進並上下擺動的子彈 (Level 2 用)。"""

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


class BoneBullet:
    """Sans 風骨頭，從邊界穿越戰鬥框的長條子彈。"""

    def __init__(self, axis, pos, speed, length=70, thickness=10, damage=12, color=config.WHITE):
        self.axis = axis  # 'h' = 水平移動, 'v' = 垂直移動
        self.speed = speed
        self.length = length
        self.thickness = thickness
        self.damage = damage
        self.color = color
        self.alive = True
        if axis == 'h':
            # pos 是 y 座標；從左或右進入
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
    """Gaster Blaster 風雷射：先預警，再放出傷害光束。"""

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
            # 預警虛線
            ratio = self.t / self.TELEGRAPH
            color = (
                int(60 + 195 * ratio),
                int(30 * (1 - ratio)),
                int(30 * (1 - ratio)),
            )
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
            inner = r.inflate(-6, -6) if self.axis == 'h' else r.inflate(-6, -6)
            pygame.draw.rect(surf, config.HEART_RED, inner)

    def hits(self, heart_rect):
        if self.t < self.TELEGRAPH:
            return False
        return self._beam_rect().colliderect(heart_rect)


# ---------------------------------------------------------------------------
# 攻擊模式 (依關卡)
# ---------------------------------------------------------------------------

class AttackPattern:
    """基底；子類別實作 update(dt, bullets)。"""

    def __init__(self):
        self.t = 0.0
        self.spawn_t = 0.0

    def update(self, dt, bullets):
        raise NotImplementedError


class Level1Pattern(AttackPattern):
    """Level 1 - Froggit：蒼蠅從四面八方緩慢飛過戰鬥框。"""

    INTERVAL = 0.55

    def update(self, dt, bullets):
        self.t += dt
        self.spawn_t += dt
        if self.spawn_t >= self.INTERVAL:
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


class Level2Pattern(AttackPattern):
    """Level 2 - Napstablook：眼淚從上方落下，含波形與直線兩種。"""

    INTERVAL = 0.32

    def update(self, dt, bullets):
        self.t += dt
        self.spawn_t += dt
        if self.spawn_t >= self.INTERVAL:
            self.spawn_t = 0.0
            kind = random.random()
            x = random.uniform(config.BOX_LEFT + 20, config.BOX_RIGHT - 20)
            if kind < 0.6:
                bullets.append(Bullet(
                    x, config.BOX_TOP - 10, 0, random.uniform(150, 210),
                    damage=8, radius=7, color=config.CYAN))
            else:
                bullets.append(WaveBullet(
                    x, config.BOX_TOP - 10, random.uniform(120, 170),
                    amp=random.uniform(25, 45), freq=random.uniform(2.0, 3.5),
                    damage=10, radius=8, color=config.BLUE))


class Level3Pattern(AttackPattern):
    """Level 3 - Sans：骨頭交叉穿越 + 偶爾的雷射。"""

    BONE_INTERVAL = 0.45
    LASER_INTERVAL = 4.0

    def __init__(self):
        super().__init__()
        self.laser_t = 1.5  # 過一陣子才開始發雷射

    def update(self, dt, bullets):
        self.t += dt
        self.spawn_t += dt
        self.laser_t += dt

        if self.spawn_t >= self.BONE_INTERVAL:
            self.spawn_t = 0.0
            if random.random() < 0.5:
                # 水平骨頭
                y = random.uniform(config.BOX_TOP + 25, config.BOX_BOTTOM - 25)
                speed = random.choice([-1, 1]) * random.uniform(260, 340)
                bullets.append(BoneBullet('h', y, speed,
                                          length=random.randint(60, 110)))
            else:
                # 垂直骨頭
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
        1: Level1Pattern,
        2: Level2Pattern,
        3: Level3Pattern,
    }[level_id]()
