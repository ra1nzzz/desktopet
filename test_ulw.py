"""最小 ULW 测试 — 验证 UpdateLayeredWindow per-pixel alpha"""
import ctypes, time
from ctypes import wintypes
from PIL import Image, ImageDraw

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

# --- 函数原型 ---
user32.UpdateLayeredWindow.restype = wintypes.BOOL
user32.UpdateLayeredWindow.argtypes = [
    wintypes.HWND, wintypes.HDC, ctypes.POINTER(wintypes.POINT),
    ctypes.POINTER(wintypes.SIZE), wintypes.HDC, ctypes.POINTER(wintypes.POINT),
    ctypes.c_uint32, ctypes.c_void_p, ctypes.c_uint32,
]
user32.GetDC.restype = wintypes.HDC
user32.GetDC.argtypes = [wintypes.HWND]
user32.ReleaseDC.restype = ctypes.c_int
user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
gdi32.CreateCompatibleDC.restype = wintypes.HDC
gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
gdi32.DeleteDC.restype = ctypes.c_int
gdi32.DeleteDC.argtypes = [wintypes.HDC]
gdi32.SelectObject.restype = wintypes.HANDLE
gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HANDLE]
gdi32.CreateDIBSection.restype = wintypes.HANDLE
gdi32.CreateDIBSection.argtypes = [
    wintypes.HDC, ctypes.c_void_p, ctypes.c_uint32,
    ctypes.POINTER(ctypes.c_void_p), wintypes.HANDLE, ctypes.c_uint32,
]

class BLENDFUNCTION(ctypes.Structure):
    _fields_ = [
        ("BlendOp", ctypes.c_ubyte),
        ("BlendFlags", ctypes.c_ubyte),
        ("SourceConstantAlpha", ctypes.c_ubyte),
        ("AlphaFormat", ctypes.c_ubyte),
    ]

class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", ctypes.c_uint32), ("biWidth", ctypes.c_int32),
        ("biHeight", ctypes.c_int32), ("biPlanes", ctypes.c_uint16),
        ("biBitCount", ctypes.c_uint16), ("biCompression", ctypes.c_uint32),
        ("biSizeImage", ctypes.c_uint32), ("biXPelsPerMeter", ctypes.c_int32),
        ("biYPelsPerMeter", ctypes.c_int32), ("biClrUsed", ctypes.c_uint32),
        ("biClrImportant", ctypes.c_uint32),
    ]

# 创建测试图：红色圆形 + 半透明边缘
img = Image.new("RGBA", (200, 200), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)
draw.ellipse([30, 30, 170, 170], fill=(255, 50, 50, 255))
# 加个半透明圆环测试抗锯齿
draw.ellipse([10, 10, 190, 190], outline=(50, 200, 50, 128), width=3)

# RGBA -> BGRA bottom-up (Win32 DIB 要求)
r, g, b, a = img.split()
bgra = Image.merge("RGBA", (b, g, r, a)).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
pixels = bgra.tobytes()

# 创建 layered window (WS_EX_LAYERED | WS_POPUP | WS_VISIBLE)
WS_EX_LAYERED = 0x00080000
WS_POPUP = 0x80000000
WS_VISIBLE = 0x10000000

hwnd = user32.CreateWindowExW(
    WS_EX_LAYERED, "Static", "ULWTest",
    WS_POPUP | WS_VISIBLE,
    100, 100, 200, 200,
    0, 0, 0, 0
)
print(f"hwnd = {hwnd}")

if not hwnd:
    err = ctypes.GetLastError()
    print(f"CreateWindowExW failed! GetLastError = {err}")
    import sys; sys.exit(1)

# 创建 DIB Section
bmi = BITMAPINFOHEADER(
    biSize=40, biWidth=200, biHeight=200, biPlanes=1, biBitCount=32,
    biCompression=0, biSizeImage=200*200*4,
    biXPelsPerMeter=0, biYPelsPerMeter=0, biClrUsed=0, biClrImportant=0,
)

hdc_screen = user32.GetDC(0)
hdc_mem = gdi32.CreateCompatibleDC(hdc_screen)
pbits = ctypes.c_void_p(0)
hbmp = gdi32.CreateDIBSection(hdc_mem, ctypes.byref(bmi), 0, ctypes.byref(pbits), None, 0)
print(f"hbmp = {hbmp}, pbits = {pbits.value}")

if hbmp and pbits.value:
    # 关键: 必须将 DIB 选入内存 DC
    old = gdi32.SelectObject(hdc_mem, hbmp)
    print(f"SelectObject old handle = {old}")
    
    # 写入像素
    ctypes.memmove(pbits.value, pixels, len(pixels))
    
    # ULW 渲染
    pt = wintypes.POINT(100, 100)
    sz = wintypes.SIZE(200, 200)
    src_pt = wintypes.POINT(0, 0)
    blend = BLENDFUNCTION(0, 0, 255, 1)  # AC_SRC_ALPHA = 1
    
    ok = user32.UpdateLayeredWindow(
        hwnd, hdc_screen,
        ctypes.byref(pt), ctypes.byref(sz),
        hdc_mem, ctypes.byref(src_pt),  # 必须传指针!
        0, ctypes.byref(blend), 2  # ULW_ALPHA = 2
    )
    err = ctypes.GetLastError() if not ok else 0
    print(f"UpdateLayeredWindow = {ok}, GetLastError = {err}")
else:
    print("CreateDIBSection failed!")
    err = ctypes.GetLastError()
    print(f"GetLastError = {err}")

user32.ReleaseDC(0, hdc_screen)
gdi32.DeleteDC(hdc_mem)

print("窗口应显示红色圆形，3秒后关闭...")
time.sleep(3)
user32.DestroyWindow(hwnd)
print("done")
