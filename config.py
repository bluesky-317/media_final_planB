"""遊戲共用常數設定。"""

# 視窗
SCREEN_WIDTH = 960
SCREEN_HEIGHT = 720
FPS = 60
TITLE = "HandTale - Undertale x Hand Tracking"

# 顏色 (Undertale 風)
BLACK = (0, 0, 0)
DARK_GREY = (30, 30, 30)
GREY = (90, 90, 90)
WHITE = (255, 255, 255)
RED = (220, 30, 30)
HEART_RED = (255, 40, 60)
YELLOW = (255, 210, 40)
GREEN = (60, 220, 90)
BLUE = (60, 120, 255)
ORANGE = (255, 130, 30)
PURPLE = (180, 60, 220)
CYAN = (60, 220, 220)

# Undertale 戰鬥框
BOX_WIDTH = 420
BOX_HEIGHT = 300
BOX_CENTER_X = SCREEN_WIDTH // 2
BOX_CENTER_Y = SCREEN_HEIGHT // 2 + 60
BOX_LEFT = BOX_CENTER_X - BOX_WIDTH // 2
BOX_TOP = BOX_CENTER_Y - BOX_HEIGHT // 2
BOX_RIGHT = BOX_LEFT + BOX_WIDTH
BOX_BOTTOM = BOX_TOP + BOX_HEIGHT
BOX_BORDER = 4

# 玩家 (靈魂/心)
HEART_SIZE = 18
MAX_HP = 100
INVULN_FRAMES = 30  # 被擊中後的無敵幀

# 攝影機 / 預覽
CAM_WIDTH = 640
CAM_HEIGHT = 480
PREVIEW_WIDTH = 240
PREVIEW_HEIGHT = 180
PREVIEW_MARGIN = 12

# 手部追蹤：將攝影機中心 70% 區域映射到完整移動範圍
HAND_MARGIN = 0.15
HAND_SMOOTH = 0.55  # EMA 平滑係數 (0 = 不更新, 1 = 不平滑)

# 選單懸停選擇所需時間 (秒)
HOVER_SELECT_SECONDS = 1.5

# ---------------- 靈魂模式 / 手勢 ----------------
# 三種模式：紅心 (預設自由移動) / 藍心 (重力+跳) / 綠心 (固定+盾)
SOUL_RED = "RED"
SOUL_BLUE = "BLUE"
SOUL_GREEN = "GREEN"

SOUL_COLORS = {
    SOUL_RED: HEART_RED,
    SOUL_BLUE: (60, 140, 255),
    SOUL_GREEN: (60, 220, 90),
}

# 手勢辨識：debounce 與閾值
GESTURE_DEBOUNCE_S = 0.15
FINGER_EXTEND_MARGIN = 0.015  # 指尖 y 比 PIP y 小多少才算伸直

# 藍心物理
GRAVITY = 1400.0  # px / s^2
JUMP_VELOCITY = 470.0  # 跳躍初速 (向上為負)
JUMP_VY_THRESHOLD = -0.7  # 食指速度小於此值 (向上) 觸發跳躍
JUMP_COOLDOWN = 0.25

# 綠心盾
SHIELD_RADIUS = 44
SHIELD_LENGTH = 78
SHIELD_THICK = 10
SHIELD_ARC_DEG = 60  # 弧寬 (度)
SHIELD_BLOCK_DIST = 64  # 子彈距離心 ≤ 此值且角度命中 → 被擋

# 關卡資訊
LEVELS = [
    {
        "id": 1,
        "name": "Level 1 - Froggit",
        "subtitle": "簡單彈幕 / 蒼蠅",
        "color": GREEN,
        "duration": 30,
        "hp": 100,
    },
    {
        "id": 2,
        "name": "Level 2 - Napstablook",
        "subtitle": "波形眼淚 / 中等難度",
        "color": BLUE,
        "duration": 40,
        "hp": 100,
    },
    {
        "id": 3,
        "name": "Level 3 - Sans",
        "subtitle": "骨頭 + 雷射 / 困難",
        "color": RED,
        "duration": 50,
        "hp": 100,
    },
]
