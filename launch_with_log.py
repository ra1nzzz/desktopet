#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
灵犀文件精灵 - 带日志重定向的启动器
解决直接运行 GUI 无法看到输出的问题。
用法: python launch_with_log.py
"""

import sys
import os
import io
import datetime
import subprocess
import threading
import time

# 脚本所在目录
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(SCRIPT_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(LOG_DIR, f"run_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log")


class Tee:
    """同时输出到控制台和文件"""
    def __init__(self, *targets):
        self.targets = targets

    def write(self, data):
        for t in self.targets:
            try:
                t.write(data)
            except Exception:
                pass

    def flush(self):
        for t in self.targets:
            try:
                t.flush()
            except Exception:
                pass


def main():
    # 重定向 stdout/stderr 到文件 + 控制台
    log_f = open(LOG_FILE, "w", encoding="utf-8", buffering=1)
    sys.stdout = Tee(sys.stdout, log_f)
    sys.stderr = Tee(sys.stderr, log_f)

    def log(msg):
        ts = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
        line = f"[{ts}] {msg}"
        print(line)

    log("=" * 60)
    log("灵犀文件精灵 - 启动器")
    log("=" * 60)
    log(f"Python: {sys.executable}")
    log(f"版本:   {sys.version}")
    log(f"工作目录: {os.getcwd()}")
    log(f"脚本目录: {SCRIPT_DIR}")
    log(f"日志文件: {LOG_FILE}")
    log("")

    # 检查 PyQt5
    try:
        import PyQt5
        log(f"PyQt5 路径: {PyQt5.__file__}")
        from PyQt5.QtWidgets import QApplication
        log("PyQt5.QtWidgets 导入: OK")
        from PyQt5.QtCore import Qt
        log("PyQt5.QtCore 导入: OK")
        from PyQt5.QtGui import QIcon, QPixmap, QPainter
        log("PyQt5.QtGui 导入: OK")
    except ImportError as e:
        log(f"[错误] PyQt5 未安装: {e}")
        log("请执行: pip install PyQt5")
        input("按回车退出...")
        sys.exit(1)
    except Exception as e:
        log(f"[错误] PyQt5 导入异常: {type(e).__name__}: {e}")
        input("按回车退出...")
        sys.exit(1)

    # 检查可选依赖
    for dep in ["send2trash", "PIL"]:
        try:
            __import__(dep)
            log(f"{dep}: 已安装")
        except ImportError:
            log(f"[警告] {dep}: 未安装（功能降级）")

    # 导入主程序
    log("")
    log("导入主程序 lingxi_droplet ...")
    try:
        # 确保脚本目录在 sys.path 中
        if SCRIPT_DIR not in sys.path:
            sys.path.insert(0, SCRIPT_DIR)

        from lingxi_droplet import (
            load_config, save_config, FileDatabase,
            generate_html_index, TEMP_DIR, ARCHIVE_DIR, HTML_INDEX,
            DropZone, create_tray_icon, FileProcessor, check_dependencies
        )
        log("lingxi_droplet 模块导入: OK")
    except Exception as e:
        import traceback
        log(f"[错误] 导入 lingxi_droplet 失败:")
        log(traceback.format_exc())
        input("按回车退出...")
        sys.exit(1)

    # 加载配置
    log("")
    config = load_config()
    log(f"配置: temp_dir = {config['temp_dir']}")
    log(f"配置: archive_dir = {config['archive_dir']}")
    log(f"配置: 分类数 = {len(config.get('categories', {}))}")

    # 初始化 HTML
    try:
        db = FileDatabase(HTML_INDEX.replace("index.html", ".filedb.json"))
        log(f"数据库: {len(db.data)} 条记录")

        os.makedirs(config['archive_dir'], exist_ok=True)
        html = generate_html_index(db, config['archive_dir'], config)
        with open(HTML_INDEX, "w", encoding="utf-8") as f:
            f.write(html)
        log(f"HTML 导航页已生成: {HTML_INDEX}")
    except Exception as e:
        import traceback
        log(f"[警告] 生成 HTML 失败:")
        log(traceback.format_exc())

    # 创建 Qt 应用
    log("")
    log("创建 QApplication ...")
    try:
        app = QApplication(sys.argv)
        app.setQuitOnLastWindowClosed(False)
        log(f"QApplication 创建成功")
        log(f"  屏幕数: {len(app.screens())}")
        screen = app.primaryScreen()
        log(f"  主屏幕: {screen.size().width()}x{screen.size().height()}")
        log(f"  可用区域: {screen.availableGeometry()}")
        log(f"  DPI缩放: {screen.logicalDotsPerInch()}")
    except Exception as e:
        import traceback
        log(f"[错误] QApplication 创建失败:")
        log(traceback.format_exc())
        input("按回车退出...")
        sys.exit(1)

    # 创建悬浮窗口
    log("")
    log("创建悬浮拖拽窗口 ...")
    try:
        drop_zone = DropZone(config)
        pos = drop_zone.pos()
        log(f"  窗口大小: {drop_zone.width()}x{drop_zone.height()}")
        log(f"  窗口位置: ({pos.x()}, {pos.y()})")
        log(f"  窗口标志: {int(drop_zone.windowFlags())}")
        log(f"  置顶: {(drop_zone.windowFlags() & Qt.WindowStaysOnTopHint) != 0}")
        log(f"  无边框: {(drop_zone.windowFlags() & Qt.FramelessWindowHint) != 0}")
        drop_zone.show()
        log("  drop_zone.show() 调用成功")
        log(f"  可见: {drop_zone.isVisible()}")
    except Exception as e:
        import traceback
        log(f"[错误] 创建悬浮窗口失败:")
        log(traceback.format_exc())
        input("按回车退出...")
        sys.exit(1)

    # 创建系统托盘
    log("")
    log("创建系统托盘图标 ...")
    try:
        tray = create_tray_icon(drop_zone, app)
        log("  系统托盘: OK")
    except Exception as e:
        import traceback
        log(f"[警告] 系统托盘创建失败（窗口仍可使用）:")
        log(traceback.format_exc())

    # 创建文件处理器
    log("")
    log("创建文件处理器 ...")
    try:
        processor = FileProcessor(config, db, drop_zone)

        def on_files_dropped(files):
            log(f"[事件] 拖入 {len(files)} 个文件:")
            for f in files:
                log(f"  - {f}")
            processor.process_files(files)

        drop_zone.files_dropped.connect(on_files_dropped)
        log("  文件处理器: OK")
    except Exception as e:
        import traceback
        log(f"[错误] 创建文件处理器失败:")
        log(traceback.format_exc())
        input("按回车退出...")
        sys.exit(1)

    # 启动完成
    log("")
    log("=" * 60)
    log("  灵犀文件精灵启动成功!")
    log("  请将文件拖拽到右上角悬浮图标上")
    log("=" * 60)
    log("")

    # 进入事件循环
    log("进入 Qt 事件循环 ...")
    exit_code = app.exec_()
    log(f"Qt 事件循环退出, code={exit_code}")

    # 清理
    log_f.close()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
