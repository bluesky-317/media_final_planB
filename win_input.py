"""Windows 鍵盤輪詢 (GetAsyncKeyState)。

cv2.waitKey 只能拿「按下事件」,沒有 release;鍵盤模式的「按住方向鍵連續移動游標」
就需要 OS 層級的狀態查詢。Windows 上直接用 ctypes 呼叫 user32.GetAsyncKeyState,
回傳值最高位 (0x8000) = 該鍵目前處於按下狀態。

非 Windows 平台呼叫所有 is_down() 一律回 False;keyboard 模式還是能用 cv2.waitKey
的單次事件 (只是按住不會自動連續觸發)。
"""
import sys

try:
    import ctypes
    _user32 = ctypes.windll.user32 if sys.platform == "win32" else None
except Exception:
    _user32 = None


# Virtual-key codes (https://learn.microsoft.com/windows/win32/inputdev/virtual-key-codes)
VK_LEFT  = 0x25
VK_UP    = 0x26
VK_RIGHT = 0x27
VK_DOWN  = 0x28
VK_SPACE = 0x20
VK_RETURN = 0x0D
VK_ESCAPE = 0x1B
VK_A = 0x41
VK_D = 0x44
VK_S = 0x53
VK_W = 0x57
VK_R = 0x52
VK_1 = 0x31
VK_2 = 0x32
VK_3 = 0x33
VK_F1 = 0x70


def is_down(vk):
    """該虛擬鍵當下是否按下。沒有 Windows 環境永遠回 False。"""
    if _user32 is None:
        return False
    return bool(_user32.GetAsyncKeyState(int(vk)) & 0x8000)


def axis_pair(neg_vk, pos_vk):
    """傳回 -1 / 0 / 1 — 方便算 X / Y 軸方向。"""
    return (1 if is_down(pos_vk) else 0) - (1 if is_down(neg_vk) else 0)
