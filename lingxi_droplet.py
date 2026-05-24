#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
灵犀文件精灵 v7.2 - ULW per-pixel alpha + windnd
"""

import os, sys, json, shutil, hashlib, datetime, webbrowser, math, time, random
import ctypes
from ctypes import wintypes
import tkinter as tk
from PIL import Image, ImageDraw, ImageFont
import windnd

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(SCRIPT_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

def log(msg):
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    try:
        with open(os.path.join(LOG_DIR, "lingxi_droplet.log"), "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass

ASSETS_DIR = os.path.join(SCRIPT_DIR, "assets")
HTML_INDEX = r"D:\lingxi-file\index.html"
CONFIG_FILE = os.path.join(SCRIPT_DIR, "config.json")
DB_FILE = os.path.join(SCRIPT_DIR, "filedb.json")

# Win32 constants
WS_EX_LAYERED = 0x00080000
WS_EX_TOOLWINDOW = 0x00000080
GWL_EXSTYLE = -20
ULW_ALPHA = 2
AC_SRC_ALPHA = 1

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

user32.GetWindowLongW.restype = ctypes.c_int64
user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
user32.SetWindowLongW.restype = ctypes.c_int64
user32.SetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_int64]
user32.GetDC.restype = wintypes.HDC
user32.GetDC.argtypes = [wintypes.HWND]
user32.ReleaseDC.restype = ctypes.c_int
user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
user32.UpdateLayeredWindow.restype = wintypes.BOOL
user32.UpdateLayeredWindow.argtypes = [
    wintypes.HWND, wintypes.HDC, ctypes.c_void_p,
    ctypes.POINTER(wintypes.SIZE), wintypes.HDC, ctypes.POINTER(wintypes.POINT),
    ctypes.c_uint32, ctypes.c_void_p, ctypes.c_uint32,
]
gdi32.CreateCompatibleDC.restype = wintypes.HDC
gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
gdi32.DeleteDC.restype = ctypes.c_int
gdi32.DeleteDC.argtypes = [wintypes.HDC]
gdi32.CreateDIBSection.restype = wintypes.HANDLE
gdi32.CreateDIBSection.argtypes = [
    wintypes.HDC, ctypes.c_void_p, ctypes.c_uint32,
    ctypes.POINTER(ctypes.c_void_p), wintypes.HANDLE, ctypes.c_uint32,
]
gdi32.SelectObject.restype = wintypes.HANDLE
gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HANDLE]
gdi32.DeleteObject.restype = ctypes.c_int
gdi32.DeleteObject.argtypes = [wintypes.HANDLE]

class BLENDFUNCTION(ctypes.Structure):
    _fields_ = [
        ("BlendOp", ctypes.c_ubyte), ("BlendFlags", ctypes.c_ubyte),
        ("SourceConstantAlpha", ctypes.c_ubyte), ("AlphaFormat", ctypes.c_ubyte),
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

IDLE = 0; HOVER = 1; RECEIVING = 2; CARRYING = 3; HAPPY = 4; SLEEPING = 5
SURPRISED = 6; SHY = 7

STATE_APNG = {
    IDLE: "idle.apng", HOVER: "idle.apng",
    RECEIVING: "receiving.apng", CARRYING: "receiving.apng",
    HAPPY: "happy.apng", SLEEPING: "sleeping.apng",
    SURPRISED: "surprised.apng", SHY: "shy.apng",
}


class ApngLoader:
    def __init__(self, scale=1.0):
        self._cache = {}
        self._scale = scale

    def preload(self, state, filepath):
        if state in self._cache:
            return
        img = Image.open(filepath)
        n = getattr(img, "n_frames", 1)
        frames = []
        for i in range(n):
            img.seek(i)
            frame = img.copy().convert("RGBA")
            if self._scale != 1.0:
                w = int(frame.width * self._scale)
                h = int(frame.height * self._scale)
                frame = frame.resize((w, h), Image.LANCZOS)
            frames.append(frame)
        self._cache[state] = frames
        log(f"[preload] {os.path.basename(filepath)}: {n} frames")

    def get_frame(self, state, index):
        frames = self._cache.get(state, [])
        if not frames:
            frames = self._cache.get(IDLE, [])
            if not frames:
                return None
        return frames[index % len(frames)]

    def get_frames(self, state):
        return self._cache.get(state, [])


class ULWRenderer:
    def __init__(self):
        self._hdc_mem = None
        self._hbitmap = None
        self._old_bitmap = None
        self._pbits = None
        self._dib_w = 0
        self._dib_h = 0

    def _ensure_dib(self, w, h):
        if w == self._dib_w and h == self._dib_h and self._hbitmap:
            return
        if self._hbitmap and self._hdc_mem:
            gdi32.SelectObject(self._hdc_mem, self._old_bitmap or 0)
            gdi32.DeleteObject(self._hbitmap)
            self._hbitmap = None
            self._old_bitmap = None
        if not self._hdc_mem:
            hdc = user32.GetDC(0)
            self._hdc_mem = gdi32.CreateCompatibleDC(hdc)
            user32.ReleaseDC(0, hdc)
        bmi = BITMAPINFOHEADER(
            biSize=40, biWidth=w, biHeight=h, biPlanes=1, biBitCount=32,
            biCompression=0, biSizeImage=w * h * 4,
        )
        self._pbits = ctypes.c_void_p(0)
        self._hbitmap = gdi32.CreateDIBSection(
            self._hdc_mem, ctypes.byref(bmi), 0, ctypes.byref(self._pbits), None, 0
        )
        if self._hbitmap:
            self._old_bitmap = gdi32.SelectObject(self._hdc_mem, self._hbitmap)
        self._dib_w = w
        self._dib_h = h

    def render(self, hwnd, pil_img):
        w, h = pil_img.size
        self._ensure_dib(w, h)
        if not self._hbitmap or not self._pbits.value:
            return False
        r, g, b, a = pil_img.split()
        bgra = Image.merge("RGBA", (b, g, r, a)).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
        ctypes.memmove(self._pbits.value, bgra.tobytes(), w * h * 4)
        hdc_screen = user32.GetDC(0)
        sz = wintypes.SIZE(w, h)
        src_pt = wintypes.POINT(0, 0)
        blend = BLENDFUNCTION(0, 0, 255, AC_SRC_ALPHA)
        ok = user32.UpdateLayeredWindow(
            hwnd, hdc_screen, None, ctypes.byref(sz),
            self._hdc_mem, ctypes.byref(src_pt),
            0, ctypes.byref(blend), ULW_ALPHA
        )
        user32.ReleaseDC(0, hdc_screen)
        return bool(ok)

    def cleanup(self):
        if self._hbitmap and self._hdc_mem:
            gdi32.SelectObject(self._hdc_mem, self._old_bitmap or 0)
            gdi32.DeleteObject(self._hbitmap)
        if self._hdc_mem:
            gdi32.DeleteDC(self._hdc_mem)


class LingXiCat(tk.Tk):
    WANDER_SPEED = 1.0
    WANDER_IDLE_DELAY = 5.0
    SLEEP_DELAY = 60.0
    FRAME_DELAY = 80

    def __init__(self, config, db):
        super().__init__()
        self.cfg = config
        self.db = db
        self.archive_dir = config["archive_dir"]
        self.temp_dir = config["temp_dir"]
        os.makedirs(self.temp_dir, exist_ok=True)
        os.makedirs(self.archive_dir, exist_ok=True)

        self.state = IDLE
        self._tick = 0
        self._processing = False
        self._dragging = False
        self._happy_timer = 0
        self._surprised_timer = 0
        self._shy_timer = 0
        self._last_interaction = time.time()
        self._bubble_text = ""
        self._bubble_timer = 0
        self._wander_target = None
        self._wander_pause_until = 0
        self._wander_bounds = {}
        self._drag_start_rootx = 0
        self._drag_start_rooty = 0
        self._drag_start_winx = 0
        self._drag_start_winy = 0
        self._apng_frame_index = 0
        self._click_times = []  # timestamps of recent clicks for multi-click detection
        self._cur_w = 0
        self._cur_h = 0

        self.loader = ApngLoader(scale=0.5)
        self._ulw = ULWRenderer()
        self._preload_assets()
        self._setup_window()

    def _preload_assets(self):
        for state, filename in STATE_APNG.items():
            p = os.path.join(ASSETS_DIR, filename)
            if os.path.exists(p):
                self.loader.preload(state, p)

    def _setup_window(self):
        self.title("灵犀文件精灵")
        self.overrideredirect(True)
        self.attributes("-topmost", True)

        idle_frames = self.loader.get_frames(IDLE)
        if idle_frames:
            self._cur_w = idle_frames[0].width
            self._cur_h = idle_frames[0].height
        else:
            self._cur_w = 140
            self._cur_h = 170
        self.geometry(f"{self._cur_w}x{self._cur_h}")

        self.update_idletasks()
        hwnd = int(self.winfo_id())
        ex_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style | WS_EX_LAYERED | WS_EX_TOOLWINDOW)

        self.bind("<Enter>", lambda e: self._on_enter())
        self.bind("<Leave>", lambda e: self._on_leave())
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<B1-Motion>", self._on_motion)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<ButtonPress-3>", self._on_right_click)
        self.protocol("WM_DELETE_WINDOW", self._hide)

        self._move_to_saved()
        # windnd: COM-based OLE drag-drop, works with ULW layered windows
        windnd.hook_dropfiles(self, func=self._on_files_dropped, force_unicode=True)
        self.after(200, self._init_wander)
        self._animate()

    def _move_to_saved(self):
        saved = self.cfg.get("window_position")
        if saved and len(saved) == 2:
            x, y = saved
        else:
            sw = self.winfo_screenwidth()
            x = sw - self._cur_w - 100
            y = 60
        self.geometry(f"+{x}+{y}")

    def _init_wander(self):
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self._wander_bounds = {
            "x_min": sw - 300, "x_max": sw - self._cur_w - 10,
            "y_min": 10, "y_max": sh - self._cur_h - 60,
        }

    def _pick_wander_target(self):
        b = self._wander_bounds
        self._wander_target = (random.randint(b["x_min"], b["x_max"]),
                               random.randint(b["y_min"], b["y_max"]))
        self._wander_pause_until = time.time() + random.uniform(3, 8)

    def _wander_tick(self):
        if not self._wander_bounds:
            return
        if self._dragging or self._processing or self.state == SLEEPING:
            return
        now = time.time()
        if now - self._last_interaction < self.WANDER_IDLE_DELAY:
            return
        if now < self._wander_pause_until:
            return
        if self._wander_target is None:
            self._pick_wander_target()
            return
        tx, ty = self._wander_target
        cx, cy = self.winfo_x(), self.winfo_y()
        dx, dy = tx - cx, ty - cy
        dist = math.hypot(dx, dy)
        if dist < 3:
            self._wander_target = None
            self._wander_pause_until = time.time() + random.uniform(2, 6)
            return
        self.geometry(f"+{int(cx + dx/dist*self.WANDER_SPEED)}+{int(cy + dy/dist*self.WANDER_SPEED)}")

    def _touch(self):
        self._last_interaction = time.time()
        self._wander_target = None

    def _on_enter(self):
        self._touch()

    def _on_leave(self):
        pass

    def _on_press(self, e):
        self._touch()
        # Multi-click detection: 3+ clicks within 0.8s triggers SHY
        now = time.time()
        self._click_times.append(now)
        self._click_times = [t for t in self._click_times if now - t < 0.8]
        if len(self._click_times) >= 3 and self.state not in (RECEIVING, CARRYING, SLEEPING):
            self.state = SHY
            self._shy_timer = 60
            self._click_times.clear()
            self._dragging = False
            return
        # Start drag → switch to SHY
        if self.state not in (RECEIVING, CARRYING, SLEEPING, SHY):
            self.state = SHY
            self._shy_timer = 300  # long timer, cleared on release
        self._dragging = True
        self._drag_start_rootx = e.x_root
        self._drag_start_rooty = e.y_root
        self._drag_start_winx = self.winfo_x()
        self._drag_start_winy = self.winfo_y()

    def _on_motion(self, e):
        if not self._dragging:
            return
        dx = e.x_root - self._drag_start_rootx
        dy = e.y_root - self._drag_start_rooty
        x = self._drag_start_winx + dx
        y = self._drag_start_winy + dy
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = max(0, min(sw - self._cur_w, x))
        y = max(0, min(sh - self._cur_h, y))
        self.geometry(f"+{int(x)}+{int(y)}")

    def _on_release(self, e):
        if self._dragging:
            self._dragging = False
            self.cfg["window_position"] = [self.winfo_x(), self.winfo_y()]
            save_config(self.cfg)
            # Return to IDLE after drag ends (unless in a processing state)
            if self.state == SHY:
                self.state = IDLE

    def _on_right_click(self, e):
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="打开文件导航", command=self._open_html)
        menu.add_command(label="打开归档目录", command=lambda: os.startfile(self.archive_dir))
        menu.add_separator()
        menu.add_command(label="退出", command=self._quit)
        menu.tk_popup(e.x_root, e.y_root)

    def _hide(self):
        self.withdraw()

    def _open_html(self):
        if os.path.exists(HTML_INDEX):
            webbrowser.open(HTML_INDEX)
        else:
            self._update_html()
            webbrowser.open(HTML_INDEX)

    def _quit(self):
        log("退出")
        self._ulw.cleanup()
        self.destroy()

    def _animate(self):
        self._tick += 1
        if self.state == SURPRISED:
            self._surprised_timer -= 1
            if self._surprised_timer <= 0:
                self.state = RECEIVING
        if self.state == HAPPY:
            self._happy_timer -= 1
            if self._happy_timer <= 0:
                self.state = IDLE
        if self.state == SHY:
            self._shy_timer -= 1
            if self._shy_timer <= 0:
                self.state = IDLE
        if self.state == IDLE and not self._dragging and not self._processing:
            if time.time() - self._last_interaction > self.SLEEP_DELAY:
                self.state = SLEEPING
        if self.state == SLEEPING and time.time() - self._last_interaction < self.SLEEP_DELAY:
            self.state = IDLE
        if self._bubble_timer > 0:
            self._bubble_timer -= 1
            if self._bubble_timer <= 0:
                self._bubble_text = ""
        self._wander_tick()
        self._draw()
        self.after(self.FRAME_DELAY, self._animate)

    def _draw(self):
        try:
            frame = self.loader.get_frame(self.state, self._apng_frame_index)
            if frame is None:
                return
            self._apng_frame_index += 1
            fw, fh = frame.width, frame.height
            draw_img = frame.copy()
            if self._bubble_text:
                draw_img = self._draw_bubble_pil(draw_img, fw, fh)
            total_w = draw_img.width
            total_h = draw_img.height
            if total_w != self._cur_w or total_h != self._cur_h:
                old_h = self._cur_h
                self._cur_w = total_w
                self._cur_h = total_h
                self.geometry(f"{total_w}x{total_h}")
                # Compensate y so cat stays in place (bubble grows upward)
                dy = total_h - old_h
                if dy != 0:
                    cur_x = self.winfo_x()
                    cur_y = self.winfo_y()
                    self.geometry(f"+{cur_x}+{cur_y - dy}")
            hwnd = int(self.winfo_id())
            self._ulw.render(hwnd, draw_img)
        except Exception as e:
            log(f"[draw] {e}")

    def _draw_bubble_pil(self, img, win_w, win_h):
        text = self._bubble_text
        # Load font first to measure actual text width
        try:
            font = ImageFont.truetype("msyh.ttc", 18)
        except Exception:
            try:
                font = ImageFont.truetype("C:\\Windows\\Fonts\\msyh.ttc", 18)
            except Exception:
                font = ImageFont.load_default()
        # Use a temp image to measure text length
        tmp_draw = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
        tw = tmp_draw.textlength(text, font=font)
        # Bubble dimensions (200% enlarged)
        pad_x = 32
        pad_y = 14
        bw = max(int(tw) + pad_x * 2, 120)
        bh = 60
        gap = 6  # gap between bubble bottom and cat top
        # Total canvas: bubble on top, cat below
        total_h = bh + gap + win_h
        total_w = max(win_w, bw)
        cat_offset_x = (total_w - win_w) // 2
        # Create larger canvas
        canvas = Image.new("RGBA", (total_w, total_h), (0, 0, 0, 0))
        canvas.paste(img, (cat_offset_x, bh + gap))
        # Draw bubble centered above cat
        bx = total_w // 2 - bw // 2
        by = 0
        cx = total_w // 2
        draw = ImageDraw.Draw(canvas)
        draw.rounded_rectangle([bx, by, bx + bw, by + bh], radius=12,
                               fill="#1E1B2E", outline="#C084FC", width=2)
        # Triangle pointing down to cat
        draw.polygon([(cx - 6, by + bh), (cx + 6, by + bh), (cx + 3, by + bh + gap)],
                     fill="#1E1B2E")
        # Draw text centered in bubble
        draw.text((cx - tw / 2, by + bh // 2 - 12), text, fill="#E2E8F0", font=font)
        return canvas

    def _show_bubble(self, text, duration=60):
        self._bubble_text = text
        self._bubble_timer = duration

    def _on_files_dropped(self, files):
        log(f"[windnd callback] triggered! {len(files)} items")
        """windnd callback: files is a list of file paths"""
        self._touch()
        log(f"[drop] received {len(files)} items")
        items = []
        folders_to_remove = []
        for item in files:
            if os.path.isfile(item):
                items.append(item)
            elif os.path.isdir(item):
                folders_to_remove.append(item)
                for root, dirs, fnames in os.walk(item):
                    for fn in fnames:
                        fp = os.path.join(root, fn)
                        if os.path.isfile(fp):
                            items.append(fp)
        if items:
            self.state = SURPRISED
            self._surprised_timer = 10
            self._apng_frame_index = 0
            self._show_bubble(f"收到 {len(items)} 个文件", 40)
            self.after(800, lambda: self._process(items, folders_to_remove))

    def _process(self, paths, folders_to_remove=None):
        self._processing = True
        self.state = CARRYING
        self._apng_frame_index = 0
        recycled = archived = duplicated = 0
        for p in paths:
            try:
                result = self._process_one(p)
                if result == "recycle": recycled += 1
                elif result == "duplicate": duplicated += 1
                else: archived += 1
            except Exception as e:
                log(f"[err] {os.path.basename(p)}: {e}")
        if folders_to_remove:
            for folder in folders_to_remove:
                if not os.path.exists(folder): continue
                for _ in range(3):
                    try:
                        if os.path.exists(folder):
                            shutil.rmtree(folder)
                        break
                    except Exception:
                        time.sleep(0.3)
        self._processing = False
        self._update_html()
        parts = []
        if recycled: parts.append(f"{recycled} 截图回收")
        if archived: parts.append(f"{archived} 已归档")
        if duplicated: parts.append(f"{duplicated} 重复跳过")
        msg = " · ".join(parts) if parts else "完成"
        log(f"[完成] {msg}")
        if random.random() < 0.25:
            self.state = SHY
            self._shy_timer = 50
        else:
            self.state = HAPPY
            self._happy_timer = 80
        self._apng_frame_index = 0
        self._click_times = []  # timestamps of recent clicks for multi-click detection
        self._show_bubble(msg, 80)

    def _process_one(self, filepath):
        name = os.path.basename(filepath)
        size = os.path.getsize(filepath)
        now = datetime.datetime.now()
        md5 = file_md5(filepath)
        duplicate = None
        for existing in self.db.data:
            if existing.get("md5") == md5 and existing.get("action") != "recycle":
                dest = existing.get("destination", "")
                if dest and dest != "(已回收)" and os.path.exists(dest):
                    duplicate = existing
                    break
        if duplicate:
            log(f"  [跳过] {name} (重复)")
            try: os.remove(filepath)
            except Exception:
                try: move_to_recycle(filepath)
                except Exception: pass
            return "duplicate"
        cat, action = classify_file(filepath, self.cfg)
        rec = {
            "timestamp": now.strftime("%Y%m%d%H%M%S%f"),
            "original_name": name, "original_path": filepath,
            "category": cat, "action": action,
            "date": now.strftime("%Y-%m-%d"), "time": now.strftime("%H:%M:%S"),
            "file_size": size, "md5": md5,
        }
        if action == "recycle":
            move_to_recycle(filepath)
            rec["destination"] = "(已回收)"
            self.db.add_record(rec)
            log(f"  [回收] {name}")
            return "recycle"
        else:
            target = get_archive_path(filepath, cat, self.archive_dir)
            shutil.move(filepath, target)
            rec["destination"] = target
            self.db.add_record(rec)
            log(f"  [归档] {name} → {cat}/")
            return "archive"

    def _update_html(self):
        try:
            html = generate_html_index(self.db, self.archive_dir, self.cfg)
            with open(HTML_INDEX, "w", encoding="utf-8") as f:
                f.write(html)
        except Exception as e:
            log(f"[err] HTML: {e}")


def file_md5(filepath):
    h = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def move_to_recycle(filepath):
    from send2trash import send2trash
    send2trash(filepath)

def classify_file(filepath, config):
    ext = os.path.splitext(filepath)[1].lower()
    name = os.path.basename(filepath).lower()
    if ext in (".png", ".jpg", ".jpeg", ".bmp", ".webp"):
        if any(p in name for p in ["screenshot", "截屏", "截图", "录屏", "屏幕"]):
            return "截图", "recycle"
        return "图片", "archive"
    if ext in (".mp4", ".avi", ".mov", ".mkv", ".wmv", ".flv"):
        return "视频", "archive"
    if ext in (".mp3", ".wav", ".flac", ".aac", ".ogg"):
        return "音频", "archive"
    if ext in (".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".pdf", ".txt", ".csv"):
        return "文档", "archive"
    if ext in (".zip", ".rar", ".7z", ".tar", ".gz"):
        return "压缩包", "archive"
    if ext in (".exe", ".msi", ".dmg", ".iso"):
        return "安装包", "archive"
    if ext in (".py", ".js", ".ts", ".html", ".css", ".json", ".xml", ".yaml", ".yml"):
        return "代码", "archive"
    return "其他", "archive"

def get_archive_path(filepath, category, archive_dir):
    date = datetime.datetime.now().strftime("%Y-%m")
    cat_dir = os.path.join(archive_dir, category, date)
    os.makedirs(cat_dir, exist_ok=True)
    return os.path.join(cat_dir, os.path.basename(filepath))

import winreg
def register_lingxi_protocol():
    try:
        bat = os.path.join(SCRIPT_DIR, "locate.bat")
        loc_py = os.path.join(SCRIPT_DIR, "_locate.py")
        if not os.path.exists(loc_py):
            with open(loc_py, "w", encoding="utf-8") as _f:
                _f.write("import base64,subprocess,sys\n")
                _f.write("u=sys.argv[1].replace(b'lingxi-locate://',b'')\n")
                _f.write("p=base64.b64decode(u).decode('utf-8')\n")
                _f.write("subprocess.Popen(['explorer','/select,',p])\n")
        if not os.path.exists(bat):
            with open(bat, "w") as _f:
                _f.write('@echo off\n')
                _f.write('set PATH=C:\\Program Files\\Python312;C:\\Program Files\\Python312\\Scripts;%SystemRoot%\\System32;%SystemRoot%\n')
                _f.write('set PYTHONHOME=\n')
                _f.write('set PYTHONPATH=\n')
                _f.write('"C:\\Program Files\\Python312\\python.exe" "%~dp0_locate.py" "%~1"\n')
        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\lingxi-locate")
        winreg.SetValue(key, None, winreg.REG_SZ, "URL:lingxi-locate Protocol")
        winreg.SetValueEx(key, "URL Protocol", 0, winreg.REG_SZ, "")
        shell = winreg.CreateKey(key, r"shell\open\command")
        winreg.SetValue(shell, None, winreg.REG_SZ, f'"{bat}" "%1"')
        winreg.CloseKey(shell); winreg.CloseKey(key)
    except Exception: pass
def generate_html_index(db, archive_dir, config):
    import base64, os
    CAT_META = {
        "截图": ("📸", "#ef4444"), "图片": ("🖼️", "#8b5cf6"),
        "视频": ("🎬", "#ec4899"), "音频": ("🎵", "#f59e0b"),
        "文档": ("📄", "#3b82f6"), "压缩包": ("📦", "#06b6d4"),
        "安装包": ("💿", "#6366f1"), "代码": ("💻", "#10b981"),
        "设计稿": ("🎨", "#d946ef"), "其他": ("📁", "#94a3b8"),
    }
    records = sorted(db.data, key=lambda r: r.get("timestamp", ""), reverse=True)
    total_size = sum(r.get("file_size", 0) for r in records)
    if total_size > 1048576: total_str = f"{total_size/1048576:.1f} MB"
    elif total_size > 1024: total_str = f"{total_size/1024:.1f} KB"
    else: total_str = f"{total_size} B"
    cats = {}
    for rec in records:
        c = rec.get("category", "其他")
        if c not in cats: cats[c] = {"count": 0, "size": 0}
        cats[c]["count"] += 1
        cats[c]["size"] += rec.get("file_size", 0)

    stat_cards = ""
    for cat_name, info in sorted(cats.items(), key=lambda x: -x[1]["count"]):
        emoji, color = CAT_META.get(cat_name, ("📁", "#94a3b8"))
        sz = info["size"]
        if sz > 1048576: sz_s = f"{sz/1048576:.1f} MB"
        elif sz > 1024: sz_s = f"{sz/1024:.1f} KB"
        else: sz_s = f"{sz} B"
        stat_cards += '<div class="stat-card" style="border-left: 3px solid ' + color + '"><div class="stat-icon">' + emoji + '</div><div class="stat-info"><div class="stat-name">' + cat_name + '</div><div class="stat-detail">' + str(info["count"]) + ' \u4e2a\u6587\u4ef6 \xb7 ' + sz_s + '</div></div></div>\n'

    cat_options = ""
    for cat_name, info in sorted(cats.items(), key=lambda x: -x[1]["count"]):
        emoji, _ = CAT_META.get(cat_name, ("📁", "#94a3b8"))
        cat_options += '<option value="' + cat_name + '">' + emoji + ' ' + cat_name + ' (' + str(info["count"]) + ')</option>\n'

    rows_html = ""
    for rec in records[:500]:
        cat = rec.get("category", "其他")
        name = rec.get("original_name", "")
        date = rec.get("date", "")
        action = rec.get("action", "")
        dest = rec.get("destination", "")
        sz = rec.get("file_size", 0)
        if sz > 1048576: sz_s = f"{sz/1048576:.1f} MB"
        elif sz > 1024: sz_s = f"{sz/1024:.1f} KB"
        else: sz_s = f"{sz} B"
        emoji, color = CAT_META.get(cat, ("📁", "#94a3b8"))
        badge_cls = "badge-recycle" if action == "recycle" else "badge-archive"
        badge_txt = "\u5df2\u56de\u6536" if action == "recycle" else "\u5df2\u5f52\u6863"
        path_short = os.path.basename(dest) if dest and dest != "(\u5df2\u56de\u6536)" else "(\u5df2\u56de\u6536)"
        locate_btn = ""
        if dest and dest != "(\u5df2\u56de\u6536)" and action == "archive":
            encoded = base64.b64encode(dest.encode("utf-8")).decode("ascii")
            locate_btn = ' <a class="btn-locate" href="lingxi-locate://' + encoded + '" title="\u5b9a\u4f4d">\u5b9a\u4f4d</a>'
        rows_html += '<tr><td><span class="cat-dot" style="background:' + color + '"></span> ' + emoji + ' ' + cat + '</td>'
        rows_html += '<td title="' + name + '">' + name + '</td><td>' + date + '</td><td>' + sz_s + '</td>'
        rows_html += '<td><span class="badge ' + badge_cls + '">' + badge_txt + '</span>' + locate_btn + '</td>'
        rows_html += '<td class="path-cell" title="' + dest + '">' + path_short + '</td></tr>\n'

    archive_url = archive_dir.replace(os.sep, "/")
    html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>\u7075\u7280\u6587\u4ef6\u7cbe\u7075 - \u6587\u4ef6\u5bfc\u822a</title>
<style>
  :root { --bg: #0f1117; --bg2: #1a1d27; --bg3: #242837; --fg: #e2e8f0; --fg2: #94a3b8; --accent: #6366f1; --accent2: #818cf8; --border: #2d3348; --radius: 12px; }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: -apple-system, "Microsoft YaHei", "Segoe UI", sans-serif; background: var(--bg); color: var(--fg); line-height: 1.6; min-height: 100vh; }
  .container { max-width: 1200px; margin: 0 auto; padding: 32px 24px; }
  .header { text-align: center; margin-bottom: 40px; padding: 40px 0; background: linear-gradient(135deg, var(--bg2), var(--bg3)); border-radius: var(--radius); border: 1px solid var(--border); }
  .header h1 { font-size: 32px; font-weight: 700; background: linear-gradient(135deg, var(--accent), #a78bfa); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 8px; }
  .header p { color: var(--fg2); font-size: 14px; }
  .summary { display: flex; gap: 24px; margin-bottom: 32px; flex-wrap: wrap; }
  .summary-card { flex: 1; min-width: 180px; background: var(--bg2); border: 1px solid var(--border); border-radius: var(--radius); padding: 20px; text-align: center; }
  .summary-card .num { font-size: 36px; font-weight: 800; color: var(--accent2); }
  .summary-card .label { color: var(--fg2); font-size: 13px; margin-top: 4px; }
  .stats-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 12px; margin-bottom: 32px; }
  .stat-card { display: flex; align-items: center; gap: 14px; background: var(--bg2); border: 1px solid var(--border); border-radius: var(--radius); padding: 16px 20px; transition: transform 0.15s, box-shadow 0.15s; }
  .stat-card:hover { transform: translateY(-2px); box-shadow: 0 8px 24px rgba(0,0,0,0.3); }
  .stat-icon { font-size: 28px; }
  .stat-name { font-weight: 600; font-size: 15px; }
  .stat-detail { color: var(--fg2); font-size: 12px; }
  .toolbar { display: flex; gap: 12px; margin-bottom: 20px; flex-wrap: wrap; align-items: center; }
  .toolbar input, .toolbar select { background: var(--bg2); border: 1px solid var(--border); color: var(--fg); padding: 10px 16px; border-radius: 8px; font-size: 14px; outline: none; transition: border-color 0.2s; }
  .toolbar input:focus, .toolbar select:focus { border-color: var(--accent); }
  .toolbar input { flex: 1; min-width: 200px; }
  .toolbar select { min-width: 160px; cursor: pointer; }
  .toolbar .btn { padding: 10px 20px; border-radius: 8px; border: 1px solid var(--accent); background: var(--accent); color: #fff; cursor: pointer; font-size: 14px; font-weight: 500; transition: background 0.2s; }
  .toolbar .btn:hover { background: var(--accent2); }
  .table-wrap { background: var(--bg2); border: 1px solid var(--border); border-radius: var(--radius); overflow: hidden; }
  table { width: 100%; border-collapse: collapse; }
  th { background: var(--bg3); padding: 14px 16px; text-align: left; font-weight: 600; font-size: 13px; color: var(--fg2); text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid var(--border); }
  td { padding: 12px 16px; font-size: 14px; border-bottom: 1px solid var(--border); max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  tr:last-child td { border-bottom: none; }
  tr:hover td { background: rgba(99, 102, 241, 0.06); }
  .cat-dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 6px; vertical-align: middle; }
  .badge { display: inline-block; padding: 2px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; }
  .badge-archive { background: rgba(16, 185, 129, 0.15); color: #34d399; }
  .badge-recycle { background: rgba(239, 68, 68, 0.15); color: #f87171; }
  .btn-locate { color: var(--accent2); text-decoration: none; margin-left: 6px; padding: 2px 8px; border: 1px solid var(--accent); border-radius: 4px; font-size: 11px; cursor: pointer; }
  .btn-locate:hover { background: var(--accent); color: #fff; }
  .path-cell { color: var(--fg2); font-size: 12px; }
  .footer { text-align: center; margin-top: 48px; padding: 24px 0; color: var(--fg2); font-size: 12px; border-top: 1px solid var(--border); }
  @media (max-width: 768px) { .summary { flex-direction: column; } .stats-grid { grid-template-columns: 1fr; } .toolbar { flex-direction: column; } .toolbar input, .toolbar select { width: 100%; } th, td { padding: 10px 12px; font-size: 13px; } }
</style>
</head>
<body>
<div class="container">
  <div class="header"><h1>\u7075\u7280\u6587\u4ef6\u7cbe\u7075</h1><p>\u667a\u80fd\u6587\u4ef6\u5206\u7c7b\u5f52\u6863 \xb7 \u62d6\u62fd\u5373\u6574\u7406</p></div>
  <div class="summary">
    <div class="summary-card"><div class="num">""" + str(len(records)) + """</div><div class="label">\u7d2f\u8ba1\u5904\u7406\u6587\u4ef6</div></div>
    <div class="summary-card"><div class="num">""" + str(len(cats)) + """</div><div class="label">\u6587\u4ef6\u5206\u7c7b\u6570</div></div>
    <div class="summary-card"><div class="num">""" + total_str + """</div><div class="label">\u5f52\u6863\u603b\u5927\u5c0f</div></div>
  </div>
  <div class="stats-grid">""" + stat_cards + """</div>
  <div class="toolbar">
    <input type="text" id="search" placeholder="\u641c\u7d22\u6587\u4ef6\u540d..." oninput="filterTable()">
    <select id="catFilter" onchange="filterTable()"><option value="\u5168\u90e8">\u5168\u90e8\u5206\u7c7b</option>""" + cat_options + """</select>
    <button class="btn" onclick="location.reload()">\u5237\u65b0</button>
    <button class="btn" style="background:transparent;border-color:var(--border);color:var(--fg2)" onclick="openArchiveDir()">\u6253\u5f00\u5f52\u6863\u76ee\u5f55</button>
  </div>
  <div class="table-wrap"><table>
    <thead><tr><th>\u5206\u7c7b</th><th>\u6587\u4ef6\u540d</th><th>\u65e5\u671f</th><th>\u5927\u5c0f</th><th>\u64cd\u4f5c</th><th>\u5f52\u6863\u8def\u5f84</th></tr></thead>
    <tbody id="fileBody">""" + rows_html + """</tbody>
  </table></div>
  <div class="footer">\u7075\u7280\u6587\u4ef6\u7cbe\u7075 \xb7 LingXi Droplet \xb7 \u6570\u636e\u5b58\u50a8\u4e8e\u672c\u5730 """ + archive_dir + """</div>
</div>
<script>
function filterTable() {
  var kw = document.getElementById("search").value.toLowerCase();
  var cat = document.getElementById("catFilter").value;
  document.querySelectorAll("#fileBody tr").forEach(function(row) {
    var cells = row.querySelectorAll("td");
    if (cells.length < 6) return;
    var fn = cells[1].textContent.toLowerCase();
    var rc = cells[0].textContent.trim();
    row.style.display = ((!kw || fn.indexOf(kw) >= 0) && (cat === "\u5168\u90e8" || rc.indexOf(cat) === 0)) ? "" : "none";
  });
}
function openArchiveDir() {
  try { new ActiveXObject("Shell.Application").Open(""" + archive_url + """"); } catch(e) { alert("Please open: """ + archive_dir + """"); }
}
document.addEventListener("keydown", function(e) {
  if (e.key === "/" && document.activeElement.tagName !== "INPUT") { e.preventDefault(); document.getElementById("search").focus(); }
});
</script>
</body></html>"""
    return html
def load_config():
    default = {"archive_dir": r"D:\lingxi-file", "temp_dir": r"D:\lingxi-temp", "window_position": None}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                default.update(json.load(f))
        except Exception: pass
    return default

def save_config(cfg):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception: pass

class FileDB:
    def __init__(self, path):
        self.path = path
        self.data = []
        self._load()
    def _load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except Exception: self.data = []
    def add_record(self, rec):
        self.data.append(rec)
        self._save()
    def _save(self):
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception: pass

def main():
    import traceback
    log("=" * 60)
    log("  灵犀文件精灵 v7.2 — ULW + windnd")
    log("=" * 60)
    config = load_config()
    db = FileDB(DB_FILE)
    register_lingxi_protocol()
    generate_html_index(db, config["archive_dir"], config)
    log(f"  归档目录: {config['archive_dir']}")
    log(f"  导航页面: {HTML_INDEX}")
    log("")
    try:
        app = LingXiCat(config, db)
        app.mainloop()
    except Exception as e:
        tb = traceback.format_exc()
        log(f"[fatal] {e}")
        log(tb)

if __name__ == "__main__":
    main()
