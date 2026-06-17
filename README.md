# HandTale — 手勢操控的 Undertale 風戰鬥小遊戲

用 **OpenCV + MediaPipe** 偵測右手食指當作搖桿，
搭配 **pygame** 呈現 Undertale 風的**回合制戰鬥** + 像素風心臟 + 彈幕閃避。
OpenCV 不只負責攝影機輸入,還用在**怪物 GIF 解碼**與**整個遊戲畫面的後製特效**(模糊 / 邊緣 / 衝擊波 / 像素化轉場)。

> 期末專題 / 多媒體實作示範用途。彈幕、戰鬥框、像素心等以 `pygame.draw` 程式繪製;怪物 sprite 取自 Undertale Wiki(教學展示用,公開發布請替換成自繪 / CC0 素材);BGM 預設無檔案(請自備,放進 `assets/audio/` 即可)。

---

## 特色

- 🖐 **完全免鍵盤**:用右手食指當游標,懸停按鈕即可確認(也提供完整鍵盤備援)
- ⚔ **Undertale 風回合制**:每回合選 **FIGHT / ACT / ITEM / MERCY**,敵人回合再閃彈幕
- 💬 **打字機式對話框**:每場戰鬥前有開場白,每個 ACT 有專屬反應
- ❤ **像素風心臟**:8×8 sprite,無 antialiasing 的 chunky 風格
- 🎨 **三色靈魂模式**(由敵人 AI 控制,玩家**無法**自由切換)
  - 🔴 **紅心**:自由 2D 移動(預設)
  - 🔵 **藍心**:重力 + 手往上揮跳躍(Sans 強制)
  - 🟢 **綠心**:固定於中央,盾隨食指方向旋轉擋彈(Undyne 強制)
- 🎯 **三種關卡**:Undyne → Froggit → Sans,各有獨立對話、ACT、攻擊模式;Lv1 / Lv3 會強制切換靈魂顏色
- 👾 **怪物 GIF 顯示**:`assets/images/enemies/*.gif` 用 OpenCV 抽幀做成動畫 sprite,戰鬥全程顯示
- 🎬 **OpenCV 畫面後製**:受傷紅光模糊、Sans 階段隨機 glitch、勝利極座標衝擊波、失敗 Sobel 邊緣 + 冷藍色調、進關像素化轉場
- 🩸 **受傷反饋**:紅色全屏邊光 + 浮上飄的傷害數字 + 戰鬥框 shake + cv2 模糊濾鏡
- 🎵 **音樂與音效**:SFX 內建合成嗶聲(不放檔也有聲音);BGM 放 `.ogg/.wav/.mp3` 進去自動播
- 🖥 **可調整大小視窗**:保留標題列,啟動依螢幕大小自動鋪滿,可手動拉 / 最大化
- 📷 **即時攝影機預覽**:右上角顯示手部關節骨架,看得到 CV 抓到什麼
- 🛡 **容錯**:無鏡頭 / 未裝 MediaPipe 也能進入遊戲;`--keyboard` 旗標可強制鍵盤模式

---

## 系統需求

| 項目 | 需求 |
|---|---|
| 作業系統 | Windows 10/11、macOS、Linux |
| Python | 3.9 ~ 3.12(MediaPipe 尚未支援 3.13) |
| 攝影機 | 任何 USB 或內建 webcam(建議 720p 以上);**沒鏡頭也能玩**(用 `--keyboard`) |
| 顯示卡 | 不需要獨顯,內顯即可 60 FPS |
| 喇叭 | 內建喇叭即可(沒喇叭也可玩) |

---

## 安裝

### 1. 取得程式碼

把整個 `media_final1/` 資料夾放到任一位置。

### 2. 建立虛擬環境(建議)

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

`requirements.txt` 內容:

```
pygame>=2.5.0
opencv-python>=4.8.0
mediapipe==0.10.14
numpy>=1.24.0,<2.0
```

> 若你遇到 `module 'mediapipe' has no attribute 'solutions'`,請執行:
> `pip install --upgrade --force-reinstall "mediapipe==0.10.14"`

### 4. 執行

```powershell
python main.py              # 一般模式(用攝影機)
python main.py --keyboard   # 強制鍵盤模式(不啟動攝影機)
python main.py -k           # 同上,簡寫
python main.py --help       # 看說明
```

第一次啟動 MediaPipe 會略慢(~5 秒)。
程式會以**可調整大小的視窗**開啟,初始尺寸鋪滿可視區但保留標題列;ESC 從主選單按可離開。

---

## 🎵 音樂與音效

### 檔案放哪裡?

把音樂 / 音效檔放到專案根目錄下的 `assets/audio/`:

```
media_final1/
└─ assets/
   └─ audio/
      ├─ bgm_menu.ogg         ← 主選單 BGM
      ├─ bgm_level1.ogg       ← Level 1 (Froggit) BGM
      ├─ bgm_level2.ogg       ← Level 2 (Undyne) BGM
      ├─ bgm_level3.ogg       ← Level 3 (Sans) BGM
      ├─ blip.wav             ← (可選) 打字機文字音
      ├─ select.wav           ← (可選) 按鈕確認音
      ├─ menu.wav             ← (可選) 選單切換音
      ├─ hit.wav              ← (可選) 受傷音
      ├─ heal.wav             ← (可選) 用 ITEM 回血音
      └─ spare.wav            ← (可選) MERCY 成功音
```

> 第一次跑沒這個資料夾沒關係,遊戲不會 crash,只是會印一行提示:「BGM 將為靜音」。
> 自己建 `assets/audio/` 資料夾再丟檔進去就好。

### 命名規則(背景音樂 BGM)

| 想播放於 | 檔名(去掉副檔名) |
|---|---|
| 主選單 | `bgm_menu` |
| 第 1 關 (Froggit) | `bgm_level1` |
| 第 2 關 (Undyne) | `bgm_level2` |
| 第 3 關 (Sans) | `bgm_level3` |

副檔名可以是 `.ogg` / `.wav` / `.mp3`(依順序找,找到哪個用哪個)。
所以 `bgm_menu.ogg`、`bgm_menu.wav`、`bgm_menu.mp3` 都行,但**只放一份**。BGM 預設**無限循環**。

> ⚠ **MP3 風險**:某些 MP3(帶 ID3 標籤、嵌入封面、VBR)可能讓 SDL_mixer 在 C 層直接 crash(整個程式閃退、Python try/except 攔不住)。**建議統一用 OGG**;真的要用 MP3 請先用 Audacity 重新匯出成乾淨的 CBR MP3,並去掉 ID3v2 標籤。

### 命名規則(音效 SFX)

| 觸發時機 | 檔名(必須是 .wav) |
|---|---|
| 對話打字機每幾個字 | `blip.wav` |
| 玩家確認動作 / FIGHT / ITEM / MERCY | `select.wav` |
| 切換選單 / BACK | `menu.wav` |
| 受傷(玩家被打 / 揮拳命中) | `hit.wav` |
| 用 ITEM 回血 | `heal.wav` |
| MERCY 成功饒恕 | `spare.wav` |

> SFX **不一定要放**:沒檔案會用 `numpy` 即時合成嗶聲,遊戲一樣有聲音。
> 想自訂音色就把對應 `.wav` 丟進去蓋掉預設。

### 推薦素材來源(CC0 / 免授權)

- BGM:[itch.io chiptune 免費包](https://itch.io/game-assets/free/tag-chiptune)、[OpenGameArt RPG 類別](https://opengameart.org/)
- SFX:[freesound.org](https://freesound.org/)、[Sfxr 自己合成](https://sfxr.me/)

> ⚠ 不要直接用 Undertale 原 OST,那是 Toby Fox 的版權音樂,公開發布會有問題。

### 音量

預設 BGM 音量 0.35(選單) / 0.4(戰鬥);SFX 各自有預設音量。要改在 `audio.py` 找 `_synth(...)` 的 `vol=` 參數或呼叫 `play_bgm(name, volume=...)`。

---

## 👾 怪物 GIF 圖

把 GIF 放在 `assets/images/enemies/`,檔名對應 `config.LEVELS` 裡每關的 `sprite` 欄位:

```
assets/images/enemies/
├─ Froggit.gif   ← Level 1
├─ Undyne.gif    ← Level 2
└─ Sans.gif      ← Level 3
```

載入流程:OpenCV 的 `cv2.VideoCapture(gif_path)` 把 GIF 當影片逐幀解碼 → `cv2.resize(INTER_NEAREST)` 像素風縮放至高 140 px → `cv2.cvtColor(BGR→RGB)` → 轉成 pygame Surface,以黑色為 colorkey(透明背景)。

戰鬥場景 **所有階段都顯示**(對話 / 玩家回合 / 敵人攻擊),搭配 sin 漂浮動效。檔案不存在時不會 crash,只是不顯示。

> ⚠ 範例 GIF 取自 Undertale Wiki,僅供教學展示;公開發布請替換成自繪或 CC0 素材。

---

## 操作說明

### 主選單

1. 把右手伸進鏡頭,**食指伸直**,其他指頭收起來。
2. 移動紅心游標到想玩的關卡按鈕上。
3. **懸停 1.5 秒**(按鈕下方進度條會充滿)→ 進入該關。

> 初始游標放在標題下方,不會壓到關卡按鈕誤觸。

### 戰鬥流程(回合制)

```
開場對話 (打字機)
   ↓
玩家回合:選 FIGHT / ACT / ITEM / MERCY
   ↓
觸發對應對話
   ↓
敵人回合:閃彈幕 6~12 秒 (依關卡)
   ↓ 回到玩家回合
```

### 玩家回合 — 四個動作

| 動作 | 效果 |
|---|---|
| **FIGHT** | 對敵人扣 7~13 HP;扣到 0 → 勝利 (擊倒)。**Sans 有 50% 機率閃開**(顯示 MISS 不扣血,而且仍會輪到敵人回合) |
| **ACT** | 開啟子選單(每關不同),選不同 ACT 對話 + 累積 **MERCY 點數**(HUD 會即時顯示 `MERCY x/y`) |
| **ITEM** | 吃一塊怪物糖回 **10 HP**,每場限 **3 顆** |
| **MERCY** | MERCY 點數達門檻時可成功饒恕 → 勝利 (饒恕);不夠則對方拒絕。**集滿後 MERCY 鈕會變黃色脈動**,HUD 額外顯示 `READY!` |

懸停在按鈕上 **1 秒**會確認(比主選單的 1.5 秒快)。

### 敵人回合 — 靈魂模式(敵人控制)

紅心被放進白色戰鬥框,閃避從各方向飛來的彈幕。
**玩家不能自由切換靈魂顏色** — 模式完全由當前關卡的敵人 AI 決定:

| 模式 | 由誰觸發 | 行為 |
|---|---|---|
| 🔴 **紅心** | 預設 / Lv2 全程 | 自由 2D 移動,食指控制位置 |
| 🔵 **藍心** | **Lv3 Sans 強制** | 重力下墜,食指**往上快速揮**(或 SPACE)= 跳;X 軸跟食指 |
| 🟢 **綠心** | **Lv1 Undyne 強制** | 心固定中央,食指指向哪邊(上下左右)就用盾擋哪邊 |

靈魂顏色切換的瞬間會**清空場上所有舊彈幕**,玩家從空場面對新階段。
切換瞬間紅心會放大並閃出白色光環。

戰鬥框左側有三段式 **模式指示器** (RED / BLUE / GREEN),目前模式那格會亮起。

> Undyne 綠心階段:每支矛射出前都有 **0.5 秒紅色三角預警箭頭**指向會來的方向,看到後把食指比向該方向就會擋下。
> Sans 藍心階段:骨牆高度由 `JUMP_VELOCITY` 與 `GRAVITY` 自動算出,保證「跳得過去」。

### 受傷反饋

- 紅心被擊中 → 螢幕**邊框紅光閃光** + **傷害數字浮上飄走** + 戰鬥框 shake + **無敵閃爍 0.5 秒**
- 同時 OpenCV 套上 **Gaussian 模糊**;重傷(單次扣 ≥18 或剩血 ≤30)再追加 **`cv2.blur` 馬賽克**

### 結算畫面

- 敵人 HP 歸零(FIGHT)或 MERCY 成功 → **VICTORY**(黃字),畫面用 `cv2.warpPolar` 極座標衝擊波特效
- 玩家 HP 歸零 → **GAME OVER**(紅字),畫面持續 `cv2.Sobel` 邊緣強化 + 冷藍色調
- 用食指懸停按鈕:「**回主選單**」或「**重新挑戰**」

---

## 關卡介紹

| Lv | 敵人 | 敵 HP | 回合長度 | 彈幕 | 強制靈魂 | MERCY 門檻 |
|----|------|------|----------|------|----------|------------|
| 1 | Froggit (簡單) | 30 | 6 秒 | 綠色蒼蠅從四面緩飛 | 全程 RED | 2 次 ACT |
| 2 | **Undyne** (中等) | 60 | 9 秒 | 自由 RED 矛雨 ↔ GREEN 四向矛 | RED 2.5s ↔ GREEN 3.5s | 3 次 ACT |
| 3 | **Sans** (困難) | 40 | 12 秒 | 自由 RED 骨頭+雷射 ↔ BLUE 跳骨牆 | RED 3.5s ↔ BLUE 3.0s | 無法饒恕,只能 FIGHT |

> 雷射有 0.7 秒「紅色虛線預警」→ 0.35 秒「白色實心光束」(扣血 20),看到紅線就要躲。
> 綠心的盾**無法擋雷射**(光束太寬)。
> Sans 的 `mercy_threshold` 設成 99 → 無法靠 ACT 饒恕,**必須打到 HP 歸零**;且他 **有 50% 機率閃開** FIGHT (`dodge_chance: 0.5`),所以實際需要更多次揮拳才能擊倒。
> 矛 (Undyne) 的命中判定用**沿矛身多點 + 上一幀位置 swept 取樣**,避免高速階段 (綠心 500 px/s) 矛尖穿過心、中心點卻沒進入 hitbox 而「明明畫面打中卻沒扣血」的破綻。

### 各關 ACT 選項

- **Froggit**:Check / Compliment / Threat(後兩者各 +1 mercy,門檻 2 → ACT 2 次後 MERCY 可饒恕)
- **Undyne**:Check / Plead / Cheer / Challenge(Plead / Cheer / Challenge 各 +1 mercy,門檻 3 → ACT 3 次後 MERCY 可饒恕)
- **Sans**:Check / Talk(皆 +0 mercy,純粹氣氛用 — 門檻 99 鎖死饒恕路線)

> 玩家 HUD 會即時顯示 `MERCY x/y`,達到門檻時數字變黃且加上 `READY!`,同時 MERCY 鈕本身會變成黃色脈動。
> 也就是說,**選 ACT 後不要忘了再回 PLAYER 階段點 MERCY**,點數對了直接饒恕勝利。

---

## 無鏡頭 / 鍵盤備援

如果偵測不到攝影機 (或 `--keyboard` 強制鍵盤模式),遊戲不會 crash,會:

- 右上角顯示 **NO CAMERA** 紅色佔位符
- 螢幕下方出現紅色橫幅 + 按鍵提示

### 鍵盤備援操作(僅無攝影機時啟用)

| 按鍵 | 功能 |
|------|------|
| **方向鍵 / WASD** | 移動虛擬游標(同食指) |
| **ENTER** | 立即確認目前 hover 中的按鈕(不用等 1 秒) |
| **SPACE** | 藍心跳躍 |
| `1` / `2` / `3` | 在主選單直接選關 |
| `R` | 在結算畫面重新挑戰 |
| `ESC` | 離開遊戲 / 回主選單 |
| `F1` | 任意狀態 → 直接跳到 Lv3 (Debug 用) |

> 鍵盤模式下完整可玩 — 從選關、戰鬥對話、選 FIGHT/ACT/ITEM/MERCY、閃彈幕到結算都可控。

---

## 🎬 OpenCV 在本專案的使用

cv2 出現在四個檔,**19 個獨立函式 + 一票常數旗標**,涵蓋輸入、視覺化、影像解碼、後製特效。

### ① `hand_tracker.py` — 攝影機輸入 + MediaPipe 銜接 + 預覽繪圖

| 函式 / 常數 | 用途 |
|---|---|
| `cv2.VideoCapture(cam, CAP_DSHOW)` | 開 webcam (Windows DirectShow 後端) |
| `cap.set(CAP_PROP_FRAME_WIDTH / HEIGHT)` | 設定擷取解析度 |
| `cv2.flip(frame, 1)` | 水平鏡像 (selfie view,讓 MediaPipe 的 "Left" 對應使用者右手) |
| `cv2.cvtColor(BGR → RGB)` | 給 MediaPipe Hands 推論用 |
| `cv2.circle(frame, ...)` | 在預覽上標食指尖 |
| `cv2.putText(FONT_HERSHEY_SIMPLEX)` | 顯示當前手勢字樣 (RED / BLUE / GREEN) |

### ② `utils.py — load_enemy_sprite` — GIF 怪物動畫解碼

| 函式 | 用途 |
|---|---|
| `cv2.VideoCapture(gif_path)` | 把 GIF 當影片逐幀解碼 (OpenCV 內建 FFmpeg) |
| `cv2.resize(..., INTER_NEAREST)` | 像素風縮放至統一高度 140 px |
| `cv2.cvtColor(BGR → RGB)` | 轉成 pygame Surface |

### ③ `utils.py — cv_frame_to_surface` — 攝影機預覽縮圖

| 函式 | 用途 |
|---|---|
| `cv2.resize` | 縮成右上角預覽尺寸 (240×180) |
| `cv2.cvtColor(BGR → RGB)` | pygame 顯示 |

### ④ `post_fx.py` — 遊戲畫面後製特效 (Pack D)

每幀 pygame Surface → numpy → cv2 處理 → 貼回 pygame。沒有效果活躍時 `apply()` 直接 bypass,不付 round-trip 成本。

| 函式 | 在哪個效果 |
|---|---|
| `cv2.cvtColor` (RGB↔BGR / BGR↔GRAY) | 全部效果的進出轉換 |
| `cv2.GaussianBlur` | 受傷模糊 |
| `cv2.addWeighted` | 受傷紅光、馬賽克、衝擊波、結算 (5 處融合) |
| `cv2.blur` | 重傷時的馬賽克區塊化 |
| `cv2.remap` | Sans sin 波位移 (目前已停用但程式碼保留) |
| `cv2.split` / `cv2.merge` | BGR 通道分離 → glitch 色差 / 結算冷藍化 |
| `cv2.warpAffine` | glitch 通道平移、勝利衝擊波極座標平移 |
| `cv2.Laplacian` | glitch 邊緣鬼影 |
| `cv2.Sobel` (X + Y) | GAME OVER 邊緣偵測 |
| `cv2.convertScaleAbs` | Sobel 結果轉 8-bit |
| `cv2.add` / `cv2.subtract` | 結算飽和加減 (藍 +45 / 紅 −25) |
| `cv2.warpPolar` (含 `WARP_INVERSE_MAP`) | 勝利環狀錯動 |
| `cv2.resize` (`INTER_AREA` + `INTER_NEAREST`) | 進關 / 結算的像素化轉場 |

### 用到的常數旗標

```
色彩:    COLOR_BGR2RGB, COLOR_RGB2BGR, COLOR_BGR2GRAY, COLOR_GRAY2BGR
資料型別: CV_8U, CV_16S
插值:    INTER_LINEAR, INTER_NEAREST, INTER_AREA
邊界:    BORDER_REFLECT, BORDER_REPLICATE, BORDER_WRAP
warp:    WARP_FILL_OUTLIERS, WARP_INVERSE_MAP
擷取:    CAP_DSHOW, CAP_PROP_FRAME_WIDTH, CAP_PROP_FRAME_HEIGHT
字型:    FONT_HERSHEY_SIMPLEX
```

### 統計

| 用途分類 | cv2 函式數 |
|---|---|
| 攝影機輸入 + MediaPipe 銜接 | 4 (VideoCapture, set, flip, cvtColor) |
| 即時手部追蹤視覺化 | 2 (circle, putText) |
| GIF 怪物 sprite 載入 | 3 (VideoCapture, resize, cvtColor) |
| 攝影機預覽縮圖 | 2 (resize, cvtColor) |
| 後製特效 (Pack D) | 15 |
| **不重複總計** | **19 個獨立函式** |

---

## 專案結構

```
media_final1/
├─ main.py            進入點 / 狀態機 (MENU → BATTLE → RESULT);鍵盤備援;事件偵測 + fx 觸發
├─ config.py          視窗、戰鬥框、HP、靈魂模式、物理常數、每關敵人/ACT/sprite 資料
├─ hand_tracker.py    OpenCV + MediaPipe,偵測右手食指、手勢、角度、垂直速度
├─ bullets.py         子彈基底 + 矛 / 蒼蠅 / 骨頭 / 雷射 + 三關攻擊模式 (含 RED↔GREEN/BLUE 強制切換)
├─ menu.py            選關介面 (食指懸停 1.5 秒選擇)
├─ game.py            戰鬥場景 (回合制 + 對話 + ACT/FIGHT/ITEM/MERCY) + 結算場景 + 怪物 sprite 顯示
├─ utils.py           繪圖輔助 + EnemySprite GIF 載入 + DialogBox 打字機
├─ audio.py           音樂與音效 (BGM 檔載入 + SFX numpy 合成 fallback)
├─ post_fx.py         OpenCV 畫面後製特效 (受傷模糊 / 衝擊波 / glitch / 像素化轉場)
├─ assets/audio/      (自備) BGM 與 SFX 檔案放這裡
├─ assets/images/enemies/  怪物 GIF (Undyne.gif / Froggit.gif / Sans.gif)
├─ sample_attack/     攻擊參考影片 (Undyne.mp4 / Sans.mp4,設計用,執行不需要)
├─ requirements.txt   套件需求
└─ README.md          本檔
```

---

## 常見問題

**Q: 開啟後攝影機畫面是黑的 / 卡很久?**
A: 1) 可能被其他程式佔用(Zoom / Teams / OBS / Chrome 開了視訊),把它們關掉重試;2) Windows 隱私權設定關了相機存取;3) 直接用 `python main.py --keyboard` 跳過攝影機。

**Q: 食指明明伸著,但被判定為其他手勢?**
A: 1) 確認手心正對鏡頭;2) 食指完全伸直、其他手指確實收進掌心;3) 光線太暗會降低偵測精度。

**Q: 為什麼我不能用手勢自由切換靈魂顏色?**
A: 本版本**改成由敵人 AI 控制**靈魂模式(Lv1 Undyne 強制 GREEN、Lv3 Sans 強制 BLUE,其餘時間 RED)。讓 Undertale 風更道地,且玩家專心應付當下的攻擊模式。

**Q: 跳躍太敏感 / 不夠靈敏?**
A: 在 `config.py` 調整 `JUMP_VY_THRESHOLD`(更負 = 更難觸發)和 `JUMP_COOLDOWN`。改 `JUMP_VELOCITY` 會自動連動 Sans 藍心階段的牆高(由 `bullets.SansPattern._safe_wall_heights()` 計算)。

**Q: 紅心太抖?**
A: `config.py` 的 `HAND_SMOOTH` 調小(例如 0.35)會更平滑但反應較慢。

**Q: 想換攝影機 (筆電有兩顆鏡頭)?**
A: `main.py` 開頭把 `HandTracker(0)` 改成 `HandTracker(1)` 或 `HandTracker(2)`。

**Q: 全螢幕 / 視窗大小?**
A: 啟動會根據螢幕大小開一個大視窗並保留標題列,可手動拉邊框或按右上「□」最大化。內部固定 960×720 邏輯解析度,letterbox 等比縮放到實際視窗。

**Q: 程式啟動就黑屏 / 看不到畫面?**
A: 1) 拖視窗邊框縮小看遊戲是否縮在角落 → 可能是 maximize 同步問題,目前版本已改成「開出來就大視窗」應該不會再發生;2) 看 console 有沒有錯誤訊息;3) 試 `--keyboard` 跳過攝影機初始化。

**Q: 放音樂檔程式就閃退?**
A: 多半是 **MP3 帶 ID3 標籤 / VBR 編碼**讓 SDL_mixer 在 C 層直接 crash(Python 攔不住)。建議統一用 **OGG**,或用 Audacity 把 MP3 重新匯出成乾淨檔。

**Q: 沒聲音?**
A: 1) `assets/audio/` 資料夾不存在 → BGM 靜音,但 SFX 還會用合成嗶聲;2) numpy 沒裝 → 連 SFX 都沒;3) 系統沒喇叭 → 終端應該會印 `[警告] 音訊初始化失敗`。

**Q: 戰鬥太難 / 太簡單?**
A: 改 `config.py` 的 `LEVELS` 裡:
- `enemy_hp`:越高越難打 (FIGHT 次數變多)
- `turn_duration`:每回合彈幕時間,越短越輕鬆
- `mercy_threshold`:要 ACT 幾次才能饒恕
- 玩家 `hp`:玩家血量
- ITEM 數量 / 回血量:在 `game.py` BattleScene `self.items` / `self.heal_amount` 改

**Q: 想跳過開場對話?**
A: 目前對話會自動播完,沒有快轉鍵。要快可把 `game.py` 的 `chars_per_sec=30` 調到 60+。

---

## 技術備註

- **手部偵測**:MediaPipe Hands `model_complexity=0` (最輕量) + `min_detection_confidence=0.6`
- **手勢辨識**:判斷四指 `tip.y < pip.y` 是否伸直 → 1/2/4 指對應 RED/BLUE/GREEN;加 0.15 秒 debounce 防抖。**注意**:本版本玩家手勢偵測結果**不再用於切換靈魂模式**(模式由敵人 pattern 控制),但 angle / vy_norm 仍用於綠心盾方向 / 藍心跳躍判定。
- **右手過濾**:影像水平翻轉 (selfie view) 後,MediaPipe 標籤為 "Left" 的即為使用者的右手
- **座標映射**:取攝影機畫面中央 70% 區域 (`HAND_MARGIN=0.15`) 映射到整個目標矩形 → 不用伸到鏡頭邊
- **平滑**:對食指座標套 EMA (`alpha=0.55`)
- **跳躍偵測**:用未平滑的原始食指 y 值計算瞬時 vy (image-norm / 秒),再 EMA 一次後與閾值比較;鍵盤模式 SPACE 直接合成一幀 `vy_norm = JUMP_VY_THRESHOLD - 1`
- **盾擋彈**:用心到子彈中心的 atan2 角度與盾角度差 < 30° 且距離 < 64 px 判定
- **像素心**:8×8 bitmap,依 `size` 參數動態縮放 (`scale = round(size/6)`)
- **打字機對話**:`DialogBox` 類別,逐字 reveal、每 3 字觸發 blip、行末等 0.7 秒自動換行
- **判定框**:玩家心碰撞框為視覺 sprite 的 **1.2 倍**(傷害判定較寬鬆 → 容易被打到,可在 `utils.heart_rect` 改回 0.9 變更嚴格)
- **音效合成**:無 `.wav` 檔時用 `numpy` 生成 sine/square wave + 指數衰減包絡,再透過 `pygame.sndarray.make_sound` 變成 `Sound`
- **視窗**:`pygame.RESIZABLE`,啟動依螢幕大小開大視窗,內部固定 960×720 邏輯解析度,主迴圈最後用 `pygame.transform.scale` letterbox 等比縮放到實際視窗
- **Sans 藍心牆高自動計算**:`bullets.SansPattern._safe_wall_heights()` 用 `JUMP_VELOCITY² / (2·GRAVITY)` 算出 max 跳高,扣掉心 hitbox 半徑與 20 px 安全餘裕,給出三檔牆高,保證玩家「跳得過去」
- **靈魂切換清場**:`UndynePattern` / `SansPattern` 階段切換瞬間呼叫 `bullets.clear()`,清空上一階段所有殘留子彈,避免跨模式干擾
- **怪物 sprite 載入**:`utils.load_enemy_sprite` 用 `cv2.VideoCapture` 抽 GIF 每幀,結果快取(同檔名只解碼一次)

---

## 參考連結

### BGM 來源範例
- Level 1 (Froggit): https://www.youtube.com/watch?v=g6aia0GQMRw
- Level 2 (Undyne): https://www.youtube.com/watch?v=xhklZR11iaE
- Level 3 (Sans): https://www.youtube.com/watch?v=PpDvm1X6zG0

### 怪物 GIF 來源
- https://undertale.fandom.com/zh/wiki/Undyne
- (僅供教學展示用;公開發布請替換成自繪 / CC0 素材)
