# 灵犀文件精灵 (LingXi Droplet)

> 桌面拖拽文件自动分类归档工具

## 功能

- **悬浮拖拽区** — 桌面右上角呼吸灯图标，拖入文件即自动整理
- **智能分类** — 截图自动回收，其它文件按类型归档（文档/图片/视频/音频/代码/压缩包/设计稿/电子书等）
- **日期归档** — 按 `类型/年-月/` 目录结构存放
- **HTML 导航** — 自动生成暗色主题文件索引页面，支持搜索和分类筛选
- **系统托盘** — 最小化到托盘，开机自启动

## 快速开始

### 方式一：直接运行

```bash
# 双击运行
启动文件精灵.bat

# 或命令行
python lingxi_droplet.py
```

### 方式二：一键安装

```bash
# 安装（快捷方式 + 开机自启）
python install.py install

# 查看状态
python install.py status

# 卸载
python install.py uninstall
```

## 目录结构

```
D:\lingxi-temp\          ← 拖入文件的临时暂存目录
D:\lingxi-file\          ← 归档根目录
  ├── index.html         ← HTML 导航页面
  ├── .filedb.json       ← 文件数据库（自动维护）
  ├── 截图\
  ├── 文档\
  │   └── 2026-05\       ← 按月归档
  ├── 图片\
  ├── 视频\
  ├── 音频\
  ├── 代码\
  ├── 压缩包\
  ├── 设计稿\
  ├── 电子书\
  └── 其他\
```

## 截图识别规则

文件被判定为「临时截图」并自动移入回收站的条件（满足任一即可）：

1. 文件名包含关键词：`截图`、`截屏`、`Screenshot`、`Screen Shot`、`微信截图`、`QQ截图`、`Snipaste`、`Capture` 等
2. 文件位于临时目录（`Temp`、`AppData`、`Clipboard` 等）
3. 图片分辨率接近当前屏幕分辨率（宽 ≥ 屏幕80% 且 高 ≥ 屏幕50%）

## 自定义配置

编辑 `config.json`（首次运行后自动生成）：

```json
{
  "temp_dir": "D:\\lingxi-temp",
  "archive_dir": "D:\\lingxi-file",
  "window_opacity": 0.85,
  "auto_open_html": false,
  "categories": {
    "文档": { "exts": [".doc", ".docx", ".pdf", ...], "action": "archive" },
    "截图": { "exts": [".png", ".jpg", ...], "action": "recycle" }
  }
}
```

## 依赖

- **必须**: `PyQt5`
- **推荐**: `send2trash`（安全回收站）、`Pillow`（智能截图识别）

```bash
pip install PyQt5 send2trash Pillow
```

## 使用技巧

- 悬浮图标可**拖动**到桌面任意位置，位置会自动记忆
- 拖入多文件时**批量处理**，处理过程有旋转动画提示
- 按 `/` 键在 HTML 导航页面可快速聚焦搜索框
- 右键系统托盘图标可打开导航页面、归档目录或退出
