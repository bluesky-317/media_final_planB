# HandTale — 手勢操控的 Undertale 風戰鬥小遊戲

用 **OpenCV + MediaPipe** 偵測右手食指當作搖桿，
搭配 **pygame** 呈現 Undertale 風的**回合制戰鬥** + 像素風心臟 + 彈幕閃避。

> 期末專題 / 多媒體實作示範用途。所有圖形皆以 `pygame.draw` 程式繪製，未使用任何版權素材；音效為 numpy 即時合成嗶聲；BGM 預設無檔案（請自備）。

---

## 特色

- 🖐 **完全免鍵盤**：用右手食指當游標，懸停按鈕即可確認
- ⚔ **Undertale 風回合制**：每回合選 **FIGHT / ACT / ITEM / MERCY**，敵人回合再閃彈幕
- 💬 **打字機式對話框**：每場戰鬥前有開場白，每個 ACT 有專屬反應
- ❤ **像素風心臟**：8×8 sprite，無 antialiasing 的 chunky 風格
- 🎨 **三色靈魂模式** (CV 手勢即時切換，僅敵人回合)
  - ☝ 食指 → 🔴 **紅心**：自由 2D 移動
  - ✌ 食指+中指 → 🔵 **藍心**：重力 + 手往上揮跳躍
  - 🖐 整隻手張開 → 🟢 **綠心**：固定於中央，盾隨食指方向旋轉擋彈
- 🎯 **三種關卡**：Napstablook → Froggit → Sans，各有獨立對話、ACT、攻擊模式
- 🩸 **受傷反饋**：紅色全屏邊光 + 浮上飄的傷害數字 + 戰鬥框 shake
- 🎵 **音樂與音效**：SFX 內建合成嗶聲（不放檔也有聲音）；BGM 放 .ogg/.wav/.mp3 進去自動播
- 🖥 **全螢幕**：用 `FULLSCREEN | SCALED` 直接全屏，內部仍是 960×720
- 📷 **即時攝影機預覽**：右上角顯示手部關節骨架，看得到 CV 抓到什麼
- 🛡 **容錯**：無鏡頭 / 未裝 MediaPipe 也能進入遊戲（顯示 NO CAMERA + 鍵盤備援）

---

## 系統需求

| 項目 | 需求 |
|---|---|
| 作業系統 | Windows 10/11、macOS、Linux |
| Python | 3.9 ~ 3.12（MediaPipe 尚未支援 3.13） |
| 攝影機 | 任何 USB 或內建 webcam (建議 720p 以上) |
| 顯示卡 | 不需要獨顯，內顯即可 60 FPS |
| 喇叭 | 內建喇叭即可（沒喇叭也可玩） |

---

## 安裝

### 1. 取得程式碼

把整個 `media_final1/` 資料夾放到任一位置。

### 2. 建立虛擬環境（建議）

```powershell
# Windows PowerShell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

```bash
# macOS / Linux
python3.12 -m venv .venv
source .venv/bin/activate
```

### 3. 安裝套件

```powershell
pip install -r requirements.txt
```

`requirements.txt` 內容：

```
pygame>=2.5.0
opencv-python>=4.8.0
mediapipe==0.10.14
numpy>=1.24.0,<2.0
```

> 若你遇到 `module 'mediapipe' has no attribute 'solutions'`，請執行：
> `pip install --upgrade --force-reinstall "mediapipe==0.10.14"`

### 4. 執行

```powershell
python main.py
```

第一次啟動 MediaPipe 會下載手部偵測模型，等候約 5~10 秒。
程式會以**全螢幕**開啟；ESC 從主選單按可離開。

---

## 🎵 音樂與音效

### 檔案放哪裡？

把音樂 / 音效檔放到專案根目錄下的 `assets/audio/`：

```
media_final1/
└─ assets/
   └─ audio/
      ├─ bgm_menu.ogg         ← 主選單 BGM
      ├─ bgm_level1.ogg       ← Level 1 (Napstablook) BGM
      ├─ bgm_level2.ogg       ← Level 2 (Froggit) BGM
      ├─ bgm_level3.ogg       ← Level 3 (Sans) BGM
      ├─ blip.wav             ← (可選) 打字機文字音
      ├─ select.wav           ← (可選) 按鈕確認音
      ├─ menu.wav             ← (可選) 選單切換音
      ├─ hit.wav              ← (可選) 受傷音
      ├─ heal.wav             ← (可選) 用 ITEM 回血音
      └─ spare.wav             ← (可選) MERCY 成功音
```

> 第一次跑沒這個資料夾沒關係，遊戲不會 crash，只是會印一行提示：「BGM 將為靜音」。
> 自己建 `assets/audio/` 資料夾再丟檔進去就好。

### 命名規則（背景音樂 BGM）

| 想播放於 | 檔名（去掉副檔名） |
|---|---|
| 主選單 | `bgm_menu` |
| 第 1 關（Napstablook） | `bgm_level1` |
| 第 2 關（Froggit） | `bgm_level2` |
| 第 3 關（Sans） | `bgm_level3` |

副檔名可以是 `.ogg` / `.wav` / `.mp3`（依順序找，找到哪個用哪個）。
所以 `bgm_menu.ogg`、`bgm_menu.wav`、`bgm_menu.mp3` 都行，但**只放一份**。

### 命名規則（音效 SFX）

| 觸發時機 | 檔名（必須是 .wav） |
|---|---|
| 對話打字機每幾個字 | `blip.wav` |
| 玩家確認動作 / FIGHT / ITEM / MERCY | `select.wav` |
| 切換選單 / BACK | `menu.wav` |
| 受傷（玩家被打 / 揮拳命中） | `hit.wav` |
| 用 ITEM 回血 | `heal.wav` |
| MERCY 成功饒恕 | `spare.wav` |

> SFX **不一定要放**：沒檔案會用 `numpy` 即時合成嗶聲，遊戲一樣有聲音。
> 想自訂音色就把對應 `.wav` 丟進去蓋掉預設。

### 推薦素材來源（CC0 / 免授權）

- BGM：[itch.io 的 "chiptune" 免費包](https://itch.io/game-assets/free/tag-chiptune)、[OpenGameArt RPG 類別](https://opengameart.org/art-search-advanced?keys=undertale&field_art_type_tid%5B%5D=12)
- SFX：[freesound.org](https://freesound.org/)、[Sfxr 自己合成](https://sfxr.me/)

> ⚠ 不要直接用 Undertale 原 OST，那是 Toby Fox 的版權音樂，公開發布會有問題。

### 音量

預設 BGM 音量 0.35，SFX 各自有預設音量。要改在 `audio.py` 裡找 `_synth(...)` 的 `vol=` 參數或呼叫 `play_bgm(name, volume=...)`。

---

## 操作說明

### 主選單

1. 把右手伸進鏡頭，**食指伸直**，其他指頭收起來。
2. 移動紅心游標到想玩的關卡按鈕上。
3. **懸停 1.5 秒**（按鈕下方進度條會充滿）→ 進入該關。

> 初始游標放在標題下方，不會壓到關卡按鈕誤觸。

### 戰鬥流程（回合制）

每關依照以下流程進行：

```
開場對話 (打字機)
   ↓
玩家回合：選 FIGHT / ACT / ITEM / MERCY
   ↓
觸發對應對話
   ↓
敵人回合：閃彈幕 6~10 秒 (依關卡)
   ↓ 回到玩家回合
```

### 玩家回合 — 四個動作

| 動作 | 效果 |
|---|---|
| **FIGHT** | 對敵人扣 7~13 HP；扣到 0 → 勝利 (擊倒) |
| **ACT** | 開啟子選單（每關不同），選不同 ACT 對話 + 累積 MERCY 點數 |
| **ITEM** | 吃一塊怪物糖回 30 HP，每場 2 顆 |
| **MERCY** | MERCY 點數達門檻時可成功饒恕 → 勝利 (饒恕)；不夠則對方拒絕 |

懸停在按鈕上 **1 秒**會確認（比主選單的 1.5 秒快）。

### 敵人回合 — 三色靈魂模式

紅心被放進白色戰鬥框，閃避從各方向飛來的彈幕。

| 操作 | 效果 |
|---|---|
| ☝ 食指 (1 指伸) | 🔴 **紅心** — 自由 2D 移動 |
| ✌ 食指+中指 (2 指伸) | 🔵 **藍心** — 重力下墜，手往上快速揮 = 跳 |
| 🖐 手張開 (4 指伸) | 🟢 **綠心** — 固定中央，食指指向哪邊就用盾擋哪邊 |
| `ESC` | 隨時回主選單 |

模式切換需要連續維持手勢 **0.15 秒**，避免誤判。
切換瞬間紅心會放大並閃出白色光環。

戰鬥框左側有三段式 **模式指示器** (RED / BLUE / GREEN)，目前模式那格會亮起。

### 受傷反饋

- 紅心被擊中 → 螢幕**邊框紅光閃光** + **傷害數字浮上飄走** + 戰鬥框 shake + **無敵閃爍 0.5 秒**

### 結算畫面

- 敵人 HP 歸零（FIGHT）或 MERCY 成功 → **VICTORY**（黃字）
- 玩家 HP 歸零 → **GAME OVER**（紅字）
- 用食指懸停按鈕：「**回主選單**」或「**重新挑戰**」。

---

## 關卡介紹

| Lv | 敵人 | 敵 HP | 回合長度 | 彈幕 | MERCY 門檻 |
|----|------|------|----------|------|------------|
| 1 | Napstablook (中等) | 25 | 7 秒 | 眼淚直落 + 波形彈 | 2 次 ACT |
| 2 | Froggit (簡單) | 30 | 6 秒 | 綠色蒼蠅從四面緩飛 | 2 次 ACT |
| 3 | Sans (困難) | 40 | 10 秒 | 交叉骨頭 + Gaster Blaster 雷射 | 無法饒恕，只能 FIGHT |

> 第 1、2 關是「故意對調」的：先 Napstablook（節奏練習）再 Froggit（容錯練習）。
> 雷射有 0.7 秒「紅色虛線預警」→ 0.35 秒「白色實心光束」(扣血 20)，看到紅線就要躲。
> 綠心的盾**無法擋雷射**（光束太寬）。
> Sans 的 mercy_threshold 設成 99 → 無法靠 ACT 饒恕，**必須打到 HP 歸零**。

### 各關 ACT 選項

- **Napstablook**：Check / Cheer / Flirt（Cheer & Flirt 各 +1 mercy）
- **Froggit**：Check / Compliment / Threat（兩者各 +1 mercy）
- **Sans**：Check / Talk（皆 +0 mercy，純粹氣氛用）

---

## 無鏡頭 / 鍵盤備援

如果偵測不到攝影機 (或 mediapipe 沒裝)，遊戲不會 crash，會：

- 右上角顯示 **NO CAMERA** 紅色佔位符
- 螢幕下方出現紅色橫幅警告
- 紅心無法靠手控制（停在初始位置）

此時可用鍵盤推進狀態，方便檢查場景 / 截圖：

| 按鍵 | 功能 |
|------|------|
| `1` / `2` / `3` | 在主選單直接選關 |
| `R` | 在結算畫面重新挑戰 |
| `ENTER` | 在結算畫面回主選單 |
| `ESC` | 離開遊戲 / 回主選單 |
| `F1` | 任意狀態 → 直接跳到 Lv3 (Debug 用) |

> 鍵盤備援模式下無法在戰鬥中選 FIGHT/ACT/ITEM/MERCY（按鈕要靠游標懸停），對話會自動推進但不會進入下個回合。Debug 建議還是接上鏡頭。

---

## 專案結構

```
media_final1/
├─ main.py            進入點 / 狀態機 (MENU → BATTLE → RESULT)
├─ config.py          視窗、戰鬥框、HP、靈魂模式、物理常數、每關敵人/ACT 資料
├─ hand_tracker.py    OpenCV + MediaPipe，偵測右手食指、手勢、角度、垂直速度
├─ bullets.py         子彈基底 + 波形彈 / 骨頭 / 雷射 + 三關攻擊模式
├─ menu.py            選關介面 (食指懸停 1.5 秒選擇)
├─ game.py            戰鬥場景 (回合制 + 對話 + ACT/FIGHT/ITEM/MERCY) + 結算場景
├─ utils.py           繪圖輔助 (像素心、盾、攝影機預覽、HUD、DialogBox 打字機)
├─ audio.py           音樂與音效 (BGM 檔載入 + SFX numpy 合成 fallback)
├─ assets/audio/      (自備) BGM 與 SFX 檔案放這裡
├─ requirements.txt   套件需求
└─ README.md          本檔
```

---

## 常見問題

**Q: 開啟後攝影機畫面是黑的？**
A: 可能被其他程式佔用（Zoom / Teams / OBS）。把它們關掉重試。

**Q: 食指明明伸著，但被判定為其他手勢？**
A: 1) 確認手心正對鏡頭；2) 食指完全伸直、其他手指確實收進掌心；3) 光線太暗會降低偵測精度。

**Q: 跳躍太敏感 / 不夠靈敏？**
A: 在 `config.py` 調整 `JUMP_VY_THRESHOLD`（更負 = 更難觸發）和 `JUMP_COOLDOWN`。

**Q: 紅心太抖？**
A: `config.py` 的 `HAND_SMOOTH` 調小（例如 0.35）會更平滑但反應較慢。

**Q: 想換攝影機 (筆電有兩顆鏡頭)？**
A: `main.py` 開頭把 `HandTracker(0)` 改成 `HandTracker(1)` 或 `HandTracker(2)`。

**Q: 全螢幕邊角有黑邊？**
A: 那是 `SCALED` 模式為了保持 4:3 比例，黑邊正常。如果不想要可改成 `pygame.FULLSCREEN`（畫面會被拉伸變形）或拿掉 `FULLSCREEN` 用視窗模式。

**Q: 沒聲音？**
A: 1) `assets/audio/` 資料夾不存在 → BGM 靜音，但 SFX 還會用合成嗶聲；2) numpy 沒裝 → 連 SFX 都沒；3) 系統沒喇叭 → 終端應該會印 `[警告] 音訊初始化失敗`。

**Q: 戰鬥太難 / 太簡單？**
A: 改 `config.py` 的 `LEVELS` 裡：
- `enemy_hp`：越高越難打（FIGHT 次數變多）
- `turn_duration`：每回合彈幕時間，越短越輕鬆
- `mercy_threshold`：要 ACT 幾次才能饒恕
- 玩家 `hp`：玩家血量

**Q: 想跳過開場對話？**
A: 目前對話會自動播完，沒有快轉鍵。要快可把 `game.py` 的 `chars_per_sec=30` 調到 60+。

---

## 技術備註

- **手部偵測**：MediaPipe Hands `model_complexity=0` (最輕量) + `min_detection_confidence=0.6`
- **手勢辨識**：判斷四指 `tip.y < pip.y` 是否伸直 → 1/2/4 指對應 RED/BLUE/GREEN；加 0.15 秒 debounce 防抖
- **右手過濾**：影像水平翻轉 (selfie view) 後，MediaPipe 標籤為 "Left" 的即為使用者的右手
- **座標映射**：取攝影機畫面中央 70% 區域 (`HAND_MARGIN=0.15`) 映射到整個目標矩形 → 不用伸到鏡頭邊
- **平滑**：對食指座標套 EMA (`alpha=0.55`)
- **跳躍偵測**：用未平滑的原始食指 y 值計算瞬時 vy (image-norm / 秒)，再 EMA 一次後與閾值比較
- **盾擋彈**：用心到子彈中心的 atan2 角度與盾角度差 < 30° 且距離 < 64 px 判定
- **像素心**：8×8 bitmap，依 `size` 參數動態縮放 (`scale = round(size/6)`)
- **打字機對話**：`DialogBox` 類別，逐字 reveal、每 3 字觸發 blip、行末等 0.7 秒自動換行
- **判定框**：玩家心碰撞框為視覺 sprite 的 **1.2 倍**（傷害判定較寬鬆 → 容易被打到，可在 `utils.heart_rect` 改回 0.9 變更嚴格）
- **音效合成**：無 .wav 檔時用 `numpy` 生成 sine/square wave + 指數衰減包絡，再透過 `pygame.sndarray.make_sound` 變成 `Sound`
- **全螢幕**：`pygame.FULLSCREEN | pygame.SCALED`，內部仍是 960×720，pygame 自動 letterbox 縮放

## BGM 參考
- level1: https://www.youtube.com/watch?v=xhklZR11iaE&list=RDxhklZR11iaE&start_radio=1
- level2: https://www.youtube.com/watch?v=g6aia0GQMRw&list=RDg6aia0GQMRw&start_radio=1
- level3: https://www.youtube.com/watch?v=PpDvm1X6zG0&list=RDPpDvm1X6zG0&start_radio=1

## gif 參考
https://undertale.fandom.com/zh/wiki/Undyne