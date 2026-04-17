"""测试窗口置顶 API"""
import sys
import ctypes
from ctypes import wintypes

# 加载 user32.dll
user32 = ctypes.windll.user32

# 定义函数
SetWindowLongW = user32.SetWindowLongW
SetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_long]
SetWindowLongW.restype = ctypes.c_long

SetWindowPos = user32.SetWindowPos
SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint]
SetWindowPos.restype = wintypes.BOOL

# 常量
GWL_EXSTYLE = -20
WS_EX_TOPMOST = 0x00000008
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_NOACTIVATE = 0x0010

print("测试脚本 - 检查 Windows API 是否可用")
print(f"SetWindowLongW 地址: {SetWindowLongW}")
print(f"SetWindowPos 地址: {SetWindowPos}")
print("API 检查通过！")

# 如果有窗口句柄，可以测试
# hwnd = ctypes.c_void_p(你的窗口句柄)
# SetWindowLongW(hwnd, GWL_EXSTYLE, WS_EX_TOPMOST)
# SetWindowPos(hwnd, -1, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)