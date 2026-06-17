"""HandTale 主程式。

狀態機：MENU → BATTLE → RESULT → MENU。
ESC 隨時可以結束 / 回主選單。

無鏡頭 / 無 MediaPipe 時不會 crash，會顯示警告並啟動「無輸入模式」。
此時可用鍵盤 1/2/3 選關、R 重玩、ENTER 回選單。
"""
import argparse
import math

import pygame

import config
from hand_tracker import HandTracker
from menu import LevelMenu
from game import BattleScene, ResultScene
from post_fx import PostFX


def parse_args():
    p = argparse.ArgumentParser(
        prog="HandTale",
        description="手勢操控的 Undertale 風戰鬥小遊戲")
    p.add_argument(
        "-k", "--keyboard", action="store_true",
        help="強制鍵盤模式 (不啟動攝影機;用方向鍵 / Z X C / SPACE / ENTER 操作)")
    return p.parse_args()

try:
    import audio
    _AUDIO = True
except Exception as e:
    print(f"[警告] 無法載入 audio 模組:{e}")
    _AUDIO = False


def get_fonts():
    """嘗試使用支援中文的字型，找不到則回退到預設字型。"""
    candidates = [
        "Microsoft JhengHei",      # 正體中文 (Windows)
        "Microsoft YaHei",         # 簡體中文 (Windows)
        "Noto Sans CJK TC",
        "PingFang TC",
        "Arial Unicode MS",
    ]
    name = None
    for c in candidates:
        if c in pygame.font.get_fonts() or pygame.font.match_font(c):
            name = c
            break

    def F(size, bold=False):
        if name:
            return pygame.font.SysFont(name, size, bold=bold)
        return pygame.font.Font(None, size)

    # big: 標題  mid: 副標 / 名稱  small: 一般文字 / HUD  btn: 按鈕  tiny: 底部提示
    return F(64, True), F(30, True), F(20), F(22, True), F(15)


def main():
    args = parse_args()

    # 必須在 pygame.init 之前 pre_init 才能低延遲播音訊
    try:
        pygame.mixer.pre_init(44100, -16, 2, 512)
    except pygame.error:
        pass
    pygame.init()
    pygame.display.set_caption(config.TITLE)
    # 視窗鋪滿可視區但保留 HEADER (扣掉標題列 / 工作列大致需要的高度)。
    # 不呼叫 SDL2 maximize,避免某些環境下 pygame screen surface 不同步造成黑屏。
    info = pygame.display.Info()
    init_w = min(info.current_w - 40, 1600)
    init_h = min(info.current_h - 120, 1100)
    screen = pygame.display.set_mode((init_w, init_h), pygame.RESIZABLE)

    # 內部維持 960×720 邏輯解析度；所有場景畫到 game_surface，最後等比縮放貼回實際視窗
    game_surface = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
    clock = pygame.time.Clock()

    if _AUDIO:
        try:
            audio.init()
            audio.play_bgm("menu", volume=0.35)
        except Exception as e:
            print(f"[警告] 音訊啟動失敗：{e}")

    font_big, font_mid, font_small, font_btn, font_tiny = get_fonts()

    tracker = HandTracker(None if args.keyboard else 0)
    camera_error = None
    if not tracker.opened():
        if args.keyboard:
            camera_error = "鍵盤模式 (--keyboard)"
            print("[資訊] 已啟用鍵盤模式 (--keyboard)，不啟動攝影機。")
        else:
            camera_error = tracker.error_msg or "未偵測到攝影機"
            print(f"[警告] {camera_error}。將以無輸入模式啟動，可用鍵盤 1/2/3 選關。")

    state = "MENU"
    menu = LevelMenu(font_big, font_mid, font_small, font_btn, font_tiny)
    battle = None
    result_scene = None
    current_level = None

    # OpenCV 後製特效;由 main 被動觀察 battle 狀態觸發,game.py 不需要任何改動
    fx = PostFX()
    prev_state = state
    prev_battle_id = None
    prev_hp = None

    # 無攝影機鍵盤備援:用方向鍵推一個虛擬「食指」,Z/X/C 切靈魂,SPACE 跳,ENTER 確認
    keyboard_mode = not tracker.opened()
    v_cursor = [0.5, 0.18]   # normalized 0~1;初值高於關卡按鈕,避免進選單立即誤觸
    cursor_speed = 1.2        # normalized units / sec
    jump_pulse = False        # SPACE 按下後一幀內觸發跳躍

    def confirm_hovered():
        """ENTER 立即填滿目前游標下方按鈕的 hover 條 (等同 1 秒懸停)。"""
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

    try:
        running = True
        while running:
            dt = clock.tick(config.FPS) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.VIDEORESIZE:
                    screen = pygame.display.set_mode(
                        (event.w, event.h), pygame.RESIZABLE)
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if state == "MENU":
                            running = False
                        else:
                            state = "MENU"
                            menu.reset()
                            if _AUDIO:
                                try: audio.play_bgm("menu", volume=0.35)
                                except Exception: pass
                    elif event.key == pygame.K_F1:
                        start_battle(config.LEVELS[2])
                    elif state == "MENU" and event.key in (
                            pygame.K_1, pygame.K_2, pygame.K_3):
                        idx = {pygame.K_1: 0, pygame.K_2: 1,
                               pygame.K_3: 2}[event.key]
                        start_battle(config.LEVELS[idx])
                    elif state == "RESULT":
                        if event.key == pygame.K_r and current_level is not None:
                            start_battle(current_level)
                        elif event.key == pygame.K_RETURN:
                            state = "MENU"
                            menu.reset()
                            if _AUDIO:
                                try: audio.play_bgm("menu", volume=0.35)
                                except Exception: pass
                    # 鍵盤備援 (無攝影機時才啟用,不影響有鏡頭的玩法)
                    # 注意:Z/X/C 已移除 — 靈魂模式由敵人 pattern 控制,玩家無法自由切換
                    if keyboard_mode:
                        if event.key == pygame.K_SPACE:
                            jump_pulse = True
                        elif (event.key == pygame.K_RETURN
                              and state != "RESULT"):
                            confirm_hovered()

            frame, finger_norm = tracker.read()

            if keyboard_mode:
                keys = pygame.key.get_pressed()
                dx = ((1 if keys[pygame.K_RIGHT] or keys[pygame.K_d] else 0)
                      - (1 if keys[pygame.K_LEFT] or keys[pygame.K_a] else 0))
                dy = ((1 if keys[pygame.K_DOWN] or keys[pygame.K_s] else 0)
                      - (1 if keys[pygame.K_UP] or keys[pygame.K_w] else 0))
                if dx or dy:
                    n = math.hypot(dx, dy)
                    v_cursor[0] = max(0.0, min(1.0,
                        v_cursor[0] + dx / n * cursor_speed * dt))
                    v_cursor[1] = max(0.0, min(1.0,
                        v_cursor[1] + dy / n * cursor_speed * dt))
                    tracker.angle = math.atan2(dy, dx)   # 給綠心盾用
                finger_norm = (v_cursor[0], v_cursor[1])
                if jump_pulse:
                    tracker.vy_norm = config.JUMP_VY_THRESHOLD - 1.0
                    jump_pulse = False
                else:
                    tracker.vy_norm = 0.0

            if state == "MENU":
                chosen = menu.update(dt, finger_norm, tracker)
                menu.draw(game_surface, camera_frame=frame, camera_error=camera_error)
                if chosen is not None:
                    start_battle(chosen)

            elif state == "BATTLE":
                result = battle.update(dt, finger_norm, tracker)
                battle.draw(game_surface, camera_frame=frame, camera_error=camera_error)
                if result is not None:
                    result_scene = ResultScene(result, current_level,
                                               font_big, font_mid, font_small,
                                               font_btn, font_tiny)
                    state = "RESULT"

            elif state == "RESULT":
                choice = result_scene.update(dt, finger_norm, tracker)
                result_scene.draw(game_surface, camera_frame=frame,
                                  camera_error=camera_error)
                if choice == 'menu':
                    state = "MENU"
                    menu.reset()
                    if _AUDIO:
                        try: audio.play_bgm("menu", volume=0.35)
                        except Exception: pass
                elif choice == 'retry':
                    start_battle(current_level)

            # ---- OpenCV 後製：偵測事件 + 套用特效 (見 post_fx.py) ----
            cur_battle_id = id(battle) if battle is not None else None
            if battle is not None and cur_battle_id == prev_battle_id:
                if prev_hp is not None and battle.hp < prev_hp:
                    dmg = prev_hp - battle.hp
                    fx.trigger_damage(severe=(dmg >= 18 or battle.hp <= 30))
            prev_hp = battle.hp if battle is not None else None
            prev_battle_id = cur_battle_id

            # Sans 抖動已停用 (持續 sin 波會干擾遊玩;若要恢復改為 True 條件)
            fx.set_sans_wave(False)
            fx.set_defeat(
                state == "RESULT"
                and result_scene is not None
                and result_scene.result == 'lose'
            )

            if state != prev_state:
                # 回主選單不做像素化轉場 (回主畫面要乾淨;進關 / 結算才有)
                if state != "MENU":
                    fx.trigger_transition()
                if (state == "RESULT" and result_scene is not None
                        and result_scene.result == 'win'):
                    fx.trigger_victory()
            prev_state = state

            fx.update(dt)
            present_surface = fx.apply(game_surface)

            # 等比縮放到實際視窗，置中並補黑邊（letterbox）
            sw, sh = screen.get_size()
            gw, gh = config.SCREEN_WIDTH, config.SCREEN_HEIGHT
            scale = min(sw / gw, sh / gh)
            tw, th = int(gw * scale), int(gh * scale)
            tx, ty = (sw - tw) // 2, (sh - th) // 2
            screen.fill(config.BLACK)
            screen.blit(pygame.transform.scale(present_surface, (tw, th)), (tx, ty))
            pygame.display.flip()
    finally:
        tracker.release()
        pygame.quit()


if __name__ == "__main__":
    main()
