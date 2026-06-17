"""使用 OpenCV + MediaPipe 偵測右手食指尖座標，並辨識靈魂模式手勢。

由於畫面已水平鏡像 (selfie view)，MediaPipe 回報的 'Left' 對應到使用者的右手。

對外暴露的屬性：
  tracker.has_hand     bool          這一幀是否偵測到右手
  tracker.gesture      str           當前 debounce 後的手勢 (RED/BLUE/GREEN)
  tracker.angle        float         手腕→食指尖 的方向角 (rad, pygame 座標)
  tracker.vy_norm      float         食指 y 軸速度 (image-norm / 秒, 負值=向上)
"""
import math
import time

import cv2

# 直接從子模組 import，避開部分 mediapipe 版本 lazy-loading 失敗
# 造成的 "module 'mediapipe' has no attribute 'solutions'" 錯誤。
# 若整個 mediapipe 缺失，仍允許 HandTracker 用「無輸入模式」啟動。
try:
    from mediapipe.python.solutions import hands as _mp_hands_mod
    from mediapipe.python.solutions import drawing_utils as _mp_draw_mod
    from mediapipe.python.solutions import drawing_styles as _mp_styles_mod
    _MEDIAPIPE_OK = True
    _MEDIAPIPE_ERROR = None
except ImportError as _e:
    _mp_hands_mod = _mp_draw_mod = _mp_styles_mod = None
    _MEDIAPIPE_OK = False
    _MEDIAPIPE_ERROR = (
        "MediaPipe 未安裝或無法載入。"
        "請執行: pip install --upgrade --force-reinstall \"mediapipe==0.10.14\""
    )

import config


# 食指 / 中指 / 無名指 / 小指 的 (tip, pip) 對 (用來判定有無伸直)
_FINGER_PAIRS = [(8, 6), (12, 10), (16, 14), (20, 18)]


def _detect_gesture(lms):
    """根據 landmark 判斷手勢，回傳 'RED'/'BLUE'/'GREEN'/None。

    規則 (假設手心正對鏡頭)：
      只有食指伸直         → RED
      食指 + 中指          → BLUE
      四指都伸 (含食指)    → GREEN
      其他組合             → None (不切換)
    """
    extended = []
    for tip, pip in _FINGER_PAIRS:
        extended.append(lms[tip].y < lms[pip].y - config.FINGER_EXTEND_MARGIN)
    idx, mid, ring, pinky = extended

    if idx and not mid and not ring and not pinky:
        return config.SOUL_RED
    if idx and mid and not ring and not pinky:
        return config.SOUL_BLUE
    if idx and sum(extended) >= 4:
        return config.SOUL_GREEN
    return None


class HandTracker:
    def __init__(self, cam_index=0):
        # 所有狀態屬性即使無鏡頭/無 mediapipe 也存在，提供安全預設值
        self.cap = None
        self.hands = None
        self.mp_hands = _mp_hands_mod
        self.mp_draw = _mp_draw_mod
        self.mp_styles = _mp_styles_mod
        self.error_msg = None

        # 平滑後的食指尖座標 (供位置控制)
        self.smooth_x = 0.5
        self.smooth_y = 0.5
        self.has_hand = False

        # 手勢 + debounce
        self.gesture = config.SOUL_RED
        self._candidate = config.SOUL_RED
        self._candidate_t = 0.0

        # 角度 / 速度
        self.angle = 0.0
        self.vy_norm = 0.0
        self._last_raw_y = None
        self._last_perf = None

        # 1) mediapipe 是否可用
        if not _MEDIAPIPE_OK:
            self.error_msg = _MEDIAPIPE_ERROR
            return

        # 顯式停用攝影機 (例如 main.py 用 --keyboard 強制鍵盤模式)
        if cam_index is None:
            self.error_msg = "鍵盤模式 (--keyboard)"
            return

        # 2) 嘗試開啟攝影機
        try:
            cap = cv2.VideoCapture(cam_index, cv2.CAP_DSHOW)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.CAM_WIDTH)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAM_HEIGHT)
            if not cap.isOpened():
                cap.release()
                self.error_msg = f"找不到攝影機 (cam_index={cam_index})"
            else:
                # 試讀一幀確認真的可用
                ok, _frame = cap.read()
                if not ok or _frame is None:
                    cap.release()
                    self.error_msg = "攝影機無法讀取畫面"
                else:
                    self.cap = cap
        except Exception as e:  # pragma: no cover
            self.error_msg = f"開啟攝影機例外: {e}"

        # 3) 嘗試建立 MediaPipe Hands 推論器
        if self.cap is not None:
            try:
                self.hands = self.mp_hands.Hands(
                    max_num_hands=2,
                    model_complexity=0,
                    min_detection_confidence=0.6,
                    min_tracking_confidence=0.5,
                )
            except Exception as e:  # pragma: no cover
                self.error_msg = f"MediaPipe 初始化失敗: {e}"
                self.cap.release()
                self.cap = None

    # ------------------------------------------------------------------
    def opened(self):
        return self.cap is not None and self.cap.isOpened()

    def read(self):
        """讀取一幀並回傳 (frame_bgr, finger_xy_or_None)。

        finger_xy 為 0~1 平滑後的正規化座標。手勢/角度/速度透過 self 屬性取得。
        """
        if not self.opened():
            return None, None

        ok, frame = self.cap.read()
        if not ok or frame is None:
            return None, None

        frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        results = self.hands.process(rgb)
        rgb.flags.writeable = True

        finger_norm = None
        right_hand = None
        if results.multi_hand_landmarks and results.multi_handedness:
            for lms, hd in zip(results.multi_hand_landmarks, results.multi_handedness):
                if hd.classification[0].label == "Left":
                    right_hand = lms
                    break
            if right_hand is None:
                right_hand = results.multi_hand_landmarks[0]

            self.mp_draw.draw_landmarks(
                frame,
                right_hand,
                self.mp_hands.HAND_CONNECTIONS,
                self.mp_styles.get_default_hand_landmarks_style(),
                self.mp_styles.get_default_hand_connections_style(),
            )

            idx_tip = right_hand.landmark[8]
            wrist = right_hand.landmark[0]
            finger_norm = (float(idx_tip.x), float(idx_tip.y))

            # 角度：手腕→食指尖 (image 座標 = pygame 座標, y 向下)
            self.angle = math.atan2(idx_tip.y - wrist.y, idx_tip.x - wrist.x)

            # 手勢 debounce
            now = time.perf_counter()
            raw_gesture = _detect_gesture(right_hand.landmark)
            if raw_gesture is None:
                self._candidate_t = now  # 不切換
            elif raw_gesture != self._candidate:
                self._candidate = raw_gesture
                self._candidate_t = now
            elif (now - self._candidate_t) >= config.GESTURE_DEBOUNCE_S:
                self.gesture = raw_gesture

            # 垂直速度 (用原始 y 計算，平滑後 EMA)
            if self._last_raw_y is not None and self._last_perf is not None:
                dt = max(1e-3, now - self._last_perf)
                inst = (idx_tip.y - self._last_raw_y) / dt
                self.vy_norm = 0.5 * inst + 0.5 * self.vy_norm
            self._last_raw_y = idx_tip.y
            self._last_perf = now

            # 在攝影機預覽上標出食指尖 + 當前手勢
            h, w = frame.shape[:2]
            cx, cy = int(idx_tip.x * w), int(idx_tip.y * h)
            cv2.circle(frame, (cx, cy), 10, (0, 255, 255), -1)
            cv2.circle(frame, (cx, cy), 14, (0, 0, 0), 2)
            label_color = {
                config.SOUL_RED: (40, 40, 230),
                config.SOUL_BLUE: (255, 160, 60),
                config.SOUL_GREEN: (80, 220, 80),
            }[self.gesture]
            cv2.putText(frame, self.gesture, (cx + 18, cy - 12),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 3)
            cv2.putText(frame, self.gesture, (cx + 18, cy - 12),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, label_color, 2)

        if finger_norm is not None:
            a = config.HAND_SMOOTH
            self.smooth_x = a * finger_norm[0] + (1 - a) * self.smooth_x
            self.smooth_y = a * finger_norm[1] + (1 - a) * self.smooth_y
            self.has_hand = True
            return frame, (self.smooth_x, self.smooth_y)

        # 沒手：保留上一筆手勢與位置，但把速度衰減
        self.has_hand = False
        self.vy_norm *= 0.5
        self._last_raw_y = None
        self._last_perf = None
        return frame, None

    # ------------------------------------------------------------------
    def map_to_rect(self, norm_xy, rect):
        """把正規化手部座標映射到指定矩形 (x, y, w, h)。

        中央 (1 - 2*margin) 區域對應整個矩形，超出範圍會被夾住。
        """
        if norm_xy is None:
            return None
        m = config.HAND_MARGIN
        nx = (norm_xy[0] - m) / max(1e-6, (1 - 2 * m))
        ny = (norm_xy[1] - m) / max(1e-6, (1 - 2 * m))
        nx = min(1.0, max(0.0, nx))
        ny = min(1.0, max(0.0, ny))
        x, y, w, h = rect
        return (x + nx * w, y + ny * h)

    def release(self):
        try:
            if self.cap is not None:
                self.cap.release()
        finally:
            self.cap = None
        try:
            self.hands.close()
        except Exception:
            pass
