"""HandTale 主程式 (OpenCV 純畫面 + 純鍵盤事件版本)。

狀態機:MENU → BATTLE → RESULT → MENU。
ESC 隨時可以結束 / 回主選單。

無鏡頭 / 無 MediaPipe 時不會 crash,會顯示警告並啟動「無輸入模式」。
此時可用鍵盤 1/2/3 選關、R 重玩、ENTER 回選單。
"""
import argparse
import math
import sys
import time

import cv2

import config
from hand_tracker import HandTracker
from menu import LevelMenu
from game import BattleScene, ResultScene
from post_fx import PostFX
from canvas import Canvas
from utils import Font
import win_input


def parse_args():
    p = argparse.ArgumentParser(
        prog="HandTale",
        description="手勢操控的 Undertale 風戰鬥小遊戲")
    p.add_argument(
        "-k", "--keyboard", action="store_true",
        help="強制鍵盤模式 (不啟動攝影機;用方向鍵 / SPACE / ENTER 操作)")
    return p.parse_args()


try:
    import audio
    _AUDIO = True
except Exception as e:
    print(f"[警告] 無法載入 audio 模組:{e}")
    _AUDIO = False


def get_fonts():
    """big / mid / small / btn / tiny 五個字級。"""
    return (Font(64, True), Font(30, True), Font(20),
            Font(22, True), Font(15))


# ----------------------------------------------------------------------
# cv2.waitKey 的按鍵碼 (Windows + Linux/macOS 大致相同的部份)
# ----------------------------------------------------------------------
_KEY_ESC = 27
_KEY_ENTER = (13, 10)
_KEY_SPACE = 32
_KEY_F1 = (7340032, 1114000, 8454144, 4128769)   # F1 在不同平台
_KEYS_1 = (49,)
_KEYS_2 = (50,)
_KEYS_3 = (51,)
_KEYS_R = (114, 82)


def _is_key(key, code_or_codes):
    if isinstance(code_or_codes, (tuple, list)):
        return key in code_or_codes
    return key == code_or_codes


def main():
    args = parse_args()

    # 音訊 (唯一還用 pygame 的子系統)
    if _AUDIO:
        try:
            audio.init()
            audio.play_bgm("menu", volume=0.35)
        except Exception as e:
            print(f"[警告] 音訊啟動失敗:{e}")

    fonts = get_fonts()
    font_big, font_mid, font_small, font_btn, font_tiny = fonts

    tracker = HandTracker(None if args.keyboard else 0)
    camera_error = None
    if not tracker.opened():
        if args.keyboard:
            camera_error = "鍵盤模式 (--keyboard)"
            print("[資訊] 已啟用鍵盤模式 (--keyboard)。")
        else:
            camera_error = tracker.error_msg or "未偵測到攝影機"
            print(f"[警告] {camera_error}。將以無輸入模式啟動。")

    # OpenCV 視窗
    cv2.namedWindow(config.TITLE, cv2.WINDOW_NORMAL | cv2.WINDOW_KEEPRATIO)
    cv2.resizeWindow(config.TITLE,
                     min(1600, config.SCREEN_WIDTH * 2),
                     min(1100, config.SCREEN_HEIGHT * 2))

    # 邏輯解析度畫布 (960×720),所有東西都畫到這上面
    canvas = Canvas(config.SCREEN_WIDTH, config.SCREEN_HEIGHT)

    state = "MENU"
    menu = LevelMenu(font_big, font_mid, font_small, font_btn, font_tiny)
    battle = None
    result_scene = None
    current_level = None

    fx = PostFX()
    prev_state = state
    prev_battle_id = None
    prev_hp = None

    # 無攝影機鍵盤備援
    keyboard_mode = not tracker.opened()
    v_cursor = [0.5, 0.18]
    # 正規化座標 / 秒;0.45 → 大約 1.5 秒掃過全螢幕,符合一般 UI 手感
    cursor_speed = 0.45
    space_was_down = False

    def confirm_hovered():
        if state == "MENU":
            for b in menu.buttons:
                if b["rect"].collidepoint(menu.cursor):
                    b["hover"] = config.HOVER_SELECT_SECONDS
                    return
        elif state == "BATTLE" and battle is not None:
            if battle.phase == BattleScene.PHASE_PLAYER:
                btns = battle.action_buttons
            elif battle.phase == BattleScene.PHASE_ACT_MENU:
                btns = battle.act_buttons
            else:
                return
            for b in btns:
                if b["rect"].collidepoint(battle.cursor):
                    b["hover"] = config.TURN_HOVER_SECONDS
                    return
        elif state == "RESULT" and result_scene is not None:
            if result_scene.btn_retry.collidepoint(result_scene.cursor):
                result_scene.hover_retry = config.HOVER_SELECT_SECONDS
            elif result_scene.btn_back.collidepoint(result_scene.cursor):
                result_scene.hover_back = config.HOVER_SELECT_SECONDS

    def start_battle(level):
        nonlocal battle, current_level, state
        current_level = level
        battle = BattleScene(level, font_big, font_mid, font_small,
                             font_btn, font_tiny)
        state = "BATTLE"

    target_dt = 1.0 / config.FPS
    last_time = time.perf_counter()
    running = True

    try:
        while running:
            now = time.perf_counter()
            dt = now - last_time
            last_time = now
            # 卡頓的一幀不該讓游標 (或 game 物理) 一口氣跳很遠
            if dt > 0.05:
                dt = 0.05

            # ---- 鍵盤事件 (單次觸發類:ESC / ENTER / 數字鍵 / R / F1) ----
            key = cv2.waitKeyEx(1)
            if key != -1:
                # 印出 key 對除錯有用,但實際遊戲關掉
                # print(f"key={key}")
                if _is_key(key, _KEY_ESC):
                    if state == "MENU":
                        running = False
                    else:
                        state = "MENU"
                        menu.reset()
                        if _AUDIO:
                            try: audio.play_bgm("menu", volume=0.35)
                            except Exception: pass
                elif _is_key(key, _KEY_F1):
                    start_battle(config.LEVELS[2])
                elif state == "MENU" and key in (_KEYS_1[0],
                                                  _KEYS_2[0], _KEYS_3[0]):
                    idx = {_KEYS_1[0]: 0, _KEYS_2[0]: 1,
                           _KEYS_3[0]: 2}[key]
                    start_battle(config.LEVELS[idx])
                elif state == "RESULT":
                    if key in _KEYS_R and current_level is not None:
                        start_battle(current_level)
                    elif _is_key(key, _KEY_ENTER):
                        state = "MENU"
                        menu.reset()
                        if _AUDIO:
                            try: audio.play_bgm("menu", volume=0.35)
                            except Exception: pass
                # 鍵盤模式下,ENTER 可立刻確認懸停中的按鈕 (不用等 1 秒)
                if (keyboard_mode and _is_key(key, _KEY_ENTER)
                        and state != "RESULT"):
                    confirm_hovered()

            # ---- 連續鍵 (鍵盤模式專屬;靠 GetAsyncKeyState 持續輪詢) ----
            frame, finger_norm = tracker.read()

            if keyboard_mode:
                dx = (win_input.axis_pair(win_input.VK_LEFT, win_input.VK_RIGHT)
                      or win_input.axis_pair(win_input.VK_A, win_input.VK_D))
                dy = (win_input.axis_pair(win_input.VK_UP, win_input.VK_DOWN)
                      or win_input.axis_pair(win_input.VK_W, win_input.VK_S))
                if dx or dy:
                    n = math.hypot(dx, dy)
                    v_cursor[0] = max(0.0, min(1.0,
                        v_cursor[0] + dx / n * cursor_speed * dt))
                    v_cursor[1] = max(0.0, min(1.0,
                        v_cursor[1] + dy / n * cursor_speed * dt))
                    tracker.angle = math.atan2(dy, dx)
                finger_norm = (v_cursor[0], v_cursor[1])

                # SPACE:edge-trigger 跳躍
                space_now = win_input.is_down(win_input.VK_SPACE)
                if space_now and not space_was_down:
                    tracker.vy_norm = config.JUMP_VY_THRESHOLD - 1.0
                else:
                    tracker.vy_norm = 0.0
                space_was_down = space_now

            # ---- 更新 / 繪製 各場景 ----
            if state == "MENU":
                chosen = menu.update(dt, finger_norm, tracker)
                menu.draw(canvas, camera_frame=frame, camera_error=camera_error)
                if chosen is not None:
                    start_battle(chosen)
            elif state == "BATTLE":
                result = battle.update(dt, finger_norm, tracker)
                battle.draw(canvas, camera_frame=frame, camera_error=camera_error)
                if result is not None:
                    result_scene = ResultScene(result, current_level, *fonts)
                    state = "RESULT"
            elif state == "RESULT":
                choice = result_scene.update(dt, finger_norm, tracker)
                result_scene.draw(canvas, camera_frame=frame,
                                  camera_error=camera_error)
                if choice == 'menu':
                    state = "MENU"
                    menu.reset()
                    if _AUDIO:
                        try: audio.play_bgm("menu", volume=0.35)
                        except Exception: pass
                elif choice == 'retry':
                    start_battle(current_level)

            # ---- PostFX 觸發 (沿用原版偵測規則) ----
            cur_battle_id = id(battle) if battle is not None else None
            if battle is not None and cur_battle_id == prev_battle_id:
                if prev_hp is not None and battle.hp < prev_hp:
                    dmg = prev_hp - battle.hp
                    fx.trigger_damage(severe=(dmg >= 18 or battle.hp <= 30))
            prev_hp = battle.hp if battle is not None else None
            prev_battle_id = cur_battle_id

            fx.set_sans_wave(False)
            fx.set_defeat(
                state == "RESULT"
                and result_scene is not None
                and result_scene.result == 'lose'
            )

            if state != prev_state:
                if state != "MENU":
                    fx.trigger_transition()
                if (state == "RESULT" and result_scene is not None
                        and result_scene.result == 'win'):
                    fx.trigger_victory()
            prev_state = state

            fx.update(dt)
            present = fx.apply(canvas.arr)

            # ---- 顯示 ----
            cv2.imshow(config.TITLE, present)

            # 偵測 X 按鈕關閉
            try:
                if cv2.getWindowProperty(config.TITLE,
                                          cv2.WND_PROP_VISIBLE) < 1:
                    running = False
            except cv2.error:
                running = False

            # 簡單的 FPS 上限 (cv2.waitKey(1) 已消耗 ~1ms)
            spent = time.perf_counter() - now
            if spent < target_dt:
                time.sleep(target_dt - spent)
    finally:
        tracker.release()
        cv2.destroyAllWindows()
        if _AUDIO:
            try: audio.stop_bgm()
            except Exception: pass


if __name__ == "__main__":
    main()
