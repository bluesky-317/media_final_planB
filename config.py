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
# 設計目標:JUMP_VELOCITY 必須讓玩家能跨過 Sans BLUE 階段的最高骨牆,
# 牆高由 bullets.SansPattern._safe_wall_heights() 依這兩個常數動態算出,
# 改 JUMP_VELOCITY 或 GRAVITY 時牆高會自動跟著縮放,不需要手動配對。
GRAVITY = 1400.0  # px / s^2
JUMP_VELOCITY = 540.0  # 跳躍初速 (向上為負);max 跳高 ≈ V²/(2g) = 104 px
JUMP_VY_THRESHOLD = -0.7  # 食指速度小於此值 (向上) 觸發跳躍
JUMP_COOLDOWN = 0.25

# 綠心盾
SHIELD_RADIUS = 44
SHIELD_LENGTH = 78
SHIELD_THICK = 10
SHIELD_ARC_DEG = 60  # 弧寬 (度)
SHIELD_BLOCK_DIST = 64  # 子彈距離心 ≤ 此值且角度命中 → 被擋

# 戰鬥節奏
TURN_HOVER_SECONDS = 1.0   # 戰鬥內按鈕懸停確認時間 (比主選單快)

# 關卡資訊
# id         = 顯示用編號 (按鈕上 1/2/3)
# pattern_id = 對應 bullets.make_pattern (1=Undyne, 2=Froggit, 3=Sans)
# sprite     = assets/images/enemies/ 下的 GIF 檔名;載不到則隱藏圖片
LEVELS = [
    {
        "id": 1,
        "pattern_id": 2,
        "name": "Level 1 - Froggit",
        "subtitle": "簡單 / 躲避光球",
        "color": GREEN,
        "hp": 100,
        "enemy_name": "FROGGIT",
        "enemy_hp": 30,
        "turn_duration": 6,
        "mercy_threshold": 2,
        "sprite": "Froggit.gif",
        "intro": [
            "一隻 Froggit 從草叢裡跳了出來。",
            "牠歪著頭看著你。",
        ],
        "acts": [
            {"label": "Check",
             "lines": ["FROGGIT  ATK 4  DEF 5",
                       "剛離開家的小青蛙。"],
             "mercy": 0},
            {"label": "Compliment",
             "lines": ["你稱讚了 Froggit 的眼睛。",
                       "Froggit 開心地拍了拍腳。"],
             "mercy": 1},
            {"label": "Threat",
             "lines": ["你瞪了 Froggit 一眼。",
                       "Froggit 嚇得後退,看你的眼神變得更警戒了。"],
             "mercy": -1},
        ],
        "fight_lines": ["你揮拳。", "命中。"],
        "kill_lines":  ["你擊倒了 Froggit。"],
        "spare_lines": ["你選擇饒恕 Froggit。",
                        "牠跳走了。"],
        "spare_not_ready_lines": ["Froggit 看起來不打算放過你。"],
    },
    {
        "id": 2,
        "pattern_id": 1,
        "name": "Level 2 - Undyne",
        "subtitle": "中等 / 矛雨 + 綠心格擋",
        "color": BLUE,
        "hp": 100,
        "enemy_name": "UNDYNE",
        "enemy_hp": 60,
        "turn_duration": 9,
        "mercy_threshold": 3,
        "sprite": "Undyne.gif",
        "intro": [
            "Undyne 重重落地擋在你面前。",
            "「人類!你打算溜進皇家領地嗎?」",
            "她舉起一支發光的長矛。",
        ],
        "acts": [
            {"label": "Check",
             "lines": ["UNDYNE  ATK 18  DEF 12",
                       "皇家守衛隊長,熱血滿點。"],
             "mercy": 0},
            {"label": "Plead",
             "lines": ["你開口求她放你過。",
                       "「呃啊啊啊—這只會讓我更興奮!」"],
             "mercy": 1},
            {"label": "Cheer",
             "lines": ["「不愧是隊長!架式好帥!」",
                       "她愣了半秒,然後咧嘴一笑。"],
             "mercy": 1},
            {"label": "Challenge",
             "lines": ["你擺出戰鬥架式回應她。",
                       "「想正面開打?那就別想我手下留情!」"],
             "mercy": -1},
        ],
        "fight_lines": ["你揮拳!", "Undyne 的盔甲叮了一聲。"],
        "kill_lines":  ["Undyne 單膝跪地。",
                        "「...好戰士。下次,我會贏。」"],
        "spare_lines": ["你選擇饒恕 Undyne。",
                        "「...哼。算你今天運氣好。」"],
        "spare_not_ready_lines": ["「想跑?還早得很!」"],
    },
    {
        "id": 3,
        "pattern_id": 3,
        "name": "Level 3 - Sans",
        "subtitle": "困難 / 骨頭 + 雷射 + 藍心",
        "color": RED,
        "hp": 100,
        "enemy_name": "SANS",
        "enemy_hp": 40,
        "turn_duration": 12,
        "mercy_threshold": 99,
        "sprite": "Sans.gif",
        "intro": [
            "Sans 把手插在口袋裡。",
            "「想聽個笑話嗎?」",
            "「...其實,你的靈魂該變藍了。」",
        ],
        "acts": [
            {"label": "Check",
             "lines": ["SANS  ATK 1  DEF 1",
                       "比看起來危險的怪物。"],
             "mercy": 0},
            {"label": "Talk",
             "lines": ["你嘗試和 Sans 聊天。",
                       "他只是聳了聳肩。"],
             "mercy": 0},
        ],
        "fight_lines": ["你揮拳!", "勉強擦到了 Sans 的衣角。"],
        "dodge_chance": 0.5,
        "dodge_lines": ["你揮拳!", "...Sans 閃開了。"],
        "kill_lines":  ["......", "Sans 緩緩地閉上了眼。"],
        "spare_lines": ["......", "「...好吧,這次放你過。」"],
        "spare_not_ready_lines": ["Sans 不打算這麼簡單放你走。"],
    },
]
