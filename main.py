"""HandTale 主程式。

狀態機：MENU → BATTLE → RESULT → MENU。
ESC 隨時可以結束 / 回主選單。

無鏡頭 / 無 MediaPipe 時不會 crash，會顯示警告並啟動「無輸入模式」。
此時可用鍵盤 1/2/3 選關、R 重玩、ENTER 回選單。
"""
import pygame

import config
from hand_tracker import HandTracker
from menu import LevelMenu
from game import BattleScene, ResultScene


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
    big = pygame.font.SysFont(name, 64, bold=True) if name else pygame.font.Font(None, 64)
    mid = pygame.font.SysFont(name, 30, bold=True) if name else pygame.font.Font(None, 30)
    small = pygame.font.SysFont(name, 20) if name else pygame.font.Font(None, 20)
    return big, mid, small


def main():
    pygame.init()
    pygame.display.set_caption(config.TITLE)
    screen = pygame.display.set_mode((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
    clock = pygame.time.Clock()

    font_big, font_mid, font_small = get_fonts()

    tracker = HandTracker(0)
    camera_error = None
    if not tracker.opened():
        camera_error = tracker.error_msg or "未偵測到攝影機"
        print(f"[警告] {camera_error}。將以無輸入模式啟動，可用鍵盤 1/2/3 選關。")

    state = "MENU"
    menu = LevelMenu(font_big, font_mid, font_small)
    battle = None
    result_scene = None
    current_level = None

    def start_battle(level):
        nonlocal battle, current_level, state
        current_level = level
        battle = BattleScene(level, font_big, font_mid, font_small)
        state = "BATTLE"

    try:
        running = True
        while running:
            dt = clock.tick(config.FPS) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if state == "MENU":
                            running = False
                        else:
                            state = "MENU"
                            menu.reset()
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

            frame, finger_norm = tracker.read()

            if state == "MENU":
                chosen = menu.update(dt, finger_norm, tracker)
                menu.draw(screen, camera_frame=frame, camera_error=camera_error)
                if chosen is not None:
                    start_battle(chosen)

            elif state == "BATTLE":
                result = battle.update(dt, finger_norm, tracker)
                battle.draw(screen, camera_frame=frame, camera_error=camera_error)
                if result is not None:
                    result_scene = ResultScene(result, current_level,
                                               font_big, font_mid, font_small)
                    state = "RESULT"

            elif state == "RESULT":
                choice = result_scene.update(dt, finger_norm, tracker)
                result_scene.draw(screen, camera_frame=frame,
                                  camera_error=camera_error)
                if choice == 'menu':
                    state = "MENU"
                    menu.reset()
                elif choice == 'retry':
                    start_battle(current_level)

            pygame.display.flip()
    finally:
        tracker.release()
        pygame.quit()


if __name__ == "__main__":
    main()
