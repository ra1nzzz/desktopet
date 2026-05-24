# -*- coding: utf-8 -*-
"""基于 index_preview.html 样式生成 index.html，增加筛选修复+stat-card点击+定位按钮"""
import base64, os, json

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "filedb.json")
ARCHIVE_DIR = r"D:\lingxi-file"
ARCHIVE_URL = "D:/lingxi-file"
DISPLAY_LIMIT = 500

CAT_META = {
    "截图": ("\U0001f4f8", "#ef4444"), "图片": ("\U0001f5bc\ufe0f", "#8b5cf6"),
    "视频": ("\U0001f3ac", "#ec4899"), "音频": ("\U0001f3b5", "#f59e0b"),
    "文档": ("\U0001f4c4", "#3b82f6"), "压缩包": ("\U0001f4e6", "#06b6d4"),
    "安装包": ("\U0001f4bf", "#6366f1"), "代码": ("\U0001f4bb", "#10b981"),
    "设计稿": ("\U0001f3a8", "#d946ef"), "其他": ("\U0001f4c1", "#94a3b8"),
}

def fmt_size(sz):
    if sz > 1073741824: return f"{sz/1073741824:.1f} GB"
    if sz > 1048576: return f"{sz/1048576:.1f} MB"
    if sz > 1024: return f"{sz/1024:.1f} KB"
    return f"{sz} B"

def main():
    with open(DB_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    records = sorted(data, key=lambda r: r.get("timestamp", ""), reverse=True)

    total_size = sum(r.get("file_size", 0) for r in records)
    cats = {}
    for rec in records:
        c = rec.get("category", "\u5176\u4ed6")
        if c not in cats: cats[c] = {"count": 0, "size": 0}
        cats[c]["count"] += 1
        cats[c]["size"] += rec.get("file_size", 0)

    # === stat cards ===
    sc = []
    for cn, info in sorted(cats.items(), key=lambda x: -x[1]["count"]):
        emoji, color = CAT_META.get(cn, ("\U0001f4c1", "#94a3b8"))
        sc.append(
            '        <div class="stat-card" data-cat="' + cn + '" style="border-left: 3px solid ' + color + '">\n'
            '            <div class="stat-icon">' + emoji + '</div>\n'
            '            <div class="stat-info">\n'
            '                <div class="stat-name">' + cn + '</div>\n'
            '                <div class="stat-detail">' + str(info["count"]) + ' \u4e2a\u6587\u4ef6 \xb7 ' + fmt_size(info["size"]) + '</div>\n'
            '            </div>\n'
            '        </div>'
        )
    stat_cards_html = "\n".join(sc)

    # === cat options ===
    co = []
    for cn, info in sorted(cats.items(), key=lambda x: -x[1]["count"]):
        emoji, _ = CAT_META.get(cn, ("\U0001f4c1", "#94a3b8"))
        co.append('<option value="' + cn + '">' + emoji + ' ' + cn + ' (' + str(info["count"]) + ')</option>')
    cat_options_html = "".join(co)

    # === rows ===
    rows = []
    for rec in records[:DISPLAY_LIMIT]:
        cat = rec.get("category", "\u5176\u4ed6")
        name = rec.get("original_name", "")
        date = rec.get("date", "")
        action = rec.get("action", "")
        dest = rec.get("destination", "")
        sz = rec.get("file_size", 0)
        emoji, color = CAT_META.get(cat, ("\U0001f4c1", "#94a3b8"))
        badge_cls = "badge-recycle" if action == "recycle" else "badge-archive"
        badge_txt = "\u5df2\u56de\u6536" if action == "recycle" else "\u5df2\u5f52\u6863"
        path_short = os.path.basename(dest) if dest and dest != "(\u5df2\u56de\u6536)" else "(\u5df2\u56de\u6536)"
        locate_btn = ""
        if dest and dest != "(\u5df2\u56de\u6536)" and action == "archive":
            encoded = base64.b64encode(dest.encode("utf-8")).decode("ascii")
            locate_btn = ' <a class="btn-locate" href="lingxi-locate://' + encoded + '" title="\u5b9a\u4f4d">\u5b9a\u4f4d</a>'
        rows.append(
            '        <tr>\n'
            '            <td><span class="cat-dot" style="background:' + color + '"></span> ' + emoji + ' ' + cat + '</td>\n'
            '            <td title="' + name + '">' + name + '</td>\n'
            '            <td>' + date + '</td>\n'
            '            <td>' + fmt_size(sz) + '</td>\n'
            '            <td><span class="badge ' + badge_cls + '">' + badge_txt + '</span>' + locate_btn + '</td>\n'
            '            <td class="path-cell" title="' + dest + '">' + path_short + '</td>\n'
            '        </tr>'
        )
    rows_html = "\n".join(rows)

    # === footer ===
    if len(records) > DISPLAY_LIMIT:
        footer_text = "\u7075\u7280\u6587\u4ef6\u7cbe\u7075 \xb7 LingXi Droplet \xb7 \u663e\u793a\u524d" + str(DISPLAY_LIMIT) + "\u6761 / \u5171" + str(len(records)) + "\u6761 \xb7 \u6570\u636e\u5b58\u50a8\u4e8e\u672c\u5730 " + ARCHIVE_DIR
    else:
        footer_text = "\u7075\u7280\u6587\u4ef6\u7cbe\u7075 \xb7 LingXi Droplet \xb7 \u6570\u636e\u5b58\u50a8\u4e8e\u672c\u5730 " + ARCHIVE_DIR

    html = (
        '<!DOCTYPE html>\n'
        '<html lang="zh-CN">\n'
        '<head>\n'
        '<meta charset="UTF-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        '<title>\u7075\u7280\u6587\u4ef6\u7cbe\u7075 - \u6587\u4ef6\u5bfc\u822a</title>\n'
        '<style>\n'
        '  :root {\n'
        '    --bg: #0f1117;\n'
        '    --bg2: #1a1d27;\n'
        '    --bg3: #242837;\n'
        '    --fg: #e2e8f0;\n'
        '    --fg2: #94a3b8;\n'
        '    --accent: #6366f1;\n'
        '    --accent2: #818cf8;\n'
        '    --border: #2d3348;\n'
        '    --radius: 12px;\n'
        '  }\n'
        '  * { margin: 0; padding: 0; box-sizing: border-box; }\n'
        '  body {\n'
        '    font-family: -apple-system, "Microsoft YaHei", "Segoe UI", sans-serif;\n'
        '    background: var(--bg);\n'
        '    color: var(--fg);\n'
        '    line-height: 1.6;\n'
        '    min-height: 100vh;\n'
        '  }\n'
        '  .container { max-width: 1200px; margin: 0 auto; padding: 32px 24px; }\n'
        '  .header {\n'
        '    text-align: center;\n'
        '    margin-bottom: 40px;\n'
        '    padding: 40px 0;\n'
        '    background: linear-gradient(135deg, var(--bg2), var(--bg3));\n'
        '    border-radius: var(--radius);\n'
        '    border: 1px solid var(--border);\n'
        '  }\n'
        '  .header h1 {\n'
        '    font-size: 32px;\n'
        '    font-weight: 700;\n'
        '    background: linear-gradient(135deg, var(--accent), #a78bfa);\n'
        '    -webkit-background-clip: text;\n'
        '    -webkit-text-fill-color: transparent;\n'
        '    margin-bottom: 8px;\n'
        '  }\n'
        '  .header p { color: var(--fg2); font-size: 14px; }\n'
        '  .summary {\n'
        '    display: flex;\n'
        '    gap: 24px;\n'
        '    margin-bottom: 32px;\n'
        '    flex-wrap: wrap;\n'
        '  }\n'
        '  .summary-card {\n'
        '    flex: 1;\n'
        '    min-width: 180px;\n'
        '    background: var(--bg2);\n'
        '    border: 1px solid var(--border);\n'
        '    border-radius: var(--radius);\n'
        '    padding: 20px;\n'
        '    text-align: center;\n'
        '  }\n'
        '  .summary-card .num {\n'
        '    font-size: 36px;\n'
        '    font-weight: 800;\n'
        '    color: var(--accent2);\n'
        '  }\n'
        '  .summary-card .label { color: var(--fg2); font-size: 13px; margin-top: 4px; }\n'
        '  .stats-grid {\n'
        '    display: grid;\n'
        '    grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));\n'
        '    gap: 12px;\n'
        '    margin-bottom: 32px;\n'
        '  }\n'
        '  .stat-card {\n'
        '    display: flex;\n'
        '    align-items: center;\n'
        '    gap: 14px;\n'
        '    background: var(--bg2);\n'
        '    border: 1px solid var(--border);\n'
        '    border-radius: var(--radius);\n'
        '    padding: 16px 20px;\n'
        '    transition: transform 0.15s, box-shadow 0.15s, opacity 0.15s;\n'
        '    cursor: pointer;\n'
        '  }\n'
        '  .stat-card:hover {\n'
        '    transform: translateY(-2px);\n'
        '    box-shadow: 0 8px 24px rgba(0,0,0,0.3);\n'
        '  }\n'
        '  .stat-card.active {\n'
        '    border-color: var(--accent);\n'
        '    box-shadow: 0 0 0 1px var(--accent), 0 4px 16px rgba(99,102,241,0.2);\n'
        '  }\n'
        '  .stat-card.dimmed { opacity: 0.4; }\n'
        '  .stat-icon { font-size: 28px; }\n'
        '  .stat-name { font-weight: 600; font-size: 15px; }\n'
        '  .stat-detail { color: var(--fg2); font-size: 12px; }\n'
        '  .toolbar {\n'
        '    display: flex;\n'
        '    gap: 12px;\n'
        '    margin-bottom: 20px;\n'
        '    flex-wrap: wrap;\n'
        '    align-items: center;\n'
        '  }\n'
        '  .toolbar input, .toolbar select {\n'
        '    background: var(--bg2);\n'
        '    border: 1px solid var(--border);\n'
        '    color: var(--fg);\n'
        '    padding: 10px 16px;\n'
        '    border-radius: 8px;\n'
        '    font-size: 14px;\n'
        '    outline: none;\n'
        '    transition: border-color 0.2s;\n'
        '  }\n'
        '  .toolbar input:focus, .toolbar select:focus {\n'
        '    border-color: var(--accent);\n'
        '  }\n'
        '  .toolbar input { flex: 1; min-width: 200px; }\n'
        '  .toolbar select { min-width: 160px; cursor: pointer; }\n'
        '  .toolbar .btn {\n'
        '    padding: 10px 20px;\n'
        '    border-radius: 8px;\n'
        '    border: 1px solid var(--accent);\n'
        '    background: var(--accent);\n'
        '    color: #fff;\n'
        '    cursor: pointer;\n'
        '    font-size: 14px;\n'
        '    font-weight: 500;\n'
        '    transition: background 0.2s;\n'
        '  }\n'
        '  .toolbar .btn:hover { background: var(--accent2); }\n'
        '  .table-wrap {\n'
        '    background: var(--bg2);\n'
        '    border: 1px solid var(--border);\n'
        '    border-radius: var(--radius);\n'
        '    overflow: hidden;\n'
        '  }\n'
        '  table { width: 100%; border-collapse: collapse; }\n'
        '  th {\n'
        '    background: var(--bg3);\n'
        '    padding: 14px 16px;\n'
        '    text-align: left;\n'
        '    font-weight: 600;\n'
        '    font-size: 13px;\n'
        '    color: var(--fg2);\n'
        '    text-transform: uppercase;\n'
        '    letter-spacing: 0.5px;\n'
        '    border-bottom: 1px solid var(--border);\n'
        '  }\n'
        '  td {\n'
        '    padding: 12px 16px;\n'
        '    font-size: 14px;\n'
        '    border-bottom: 1px solid var(--border);\n'
        '    max-width: 200px;\n'
        '    overflow: hidden;\n'
        '    text-overflow: ellipsis;\n'
        '    white-space: nowrap;\n'
        '  }\n'
        '  tr:last-child td { border-bottom: none; }\n'
        '  tr:hover td { background: rgba(99, 102, 241, 0.06); }\n'
        '  .cat-dot {\n'
        '    display: inline-block;\n'
        '    width: 8px; height: 8px;\n'
        '    border-radius: 50%;\n'
        '    margin-right: 6px;\n'
        '    vertical-align: middle;\n'
        '  }\n'
        '  .badge {\n'
        '    display: inline-block;\n'
        '    padding: 2px 10px;\n'
        '    border-radius: 20px;\n'
        '    font-size: 11px;\n'
        '    font-weight: 600;\n'
        '  }\n'
        '  .badge-archive { background: rgba(16, 185, 129, 0.15); color: #34d399; }\n'
        '  .badge-recycle { background: rgba(239, 68, 68, 0.15); color: #f87171; }\n'
        '  .btn-locate {\n'
        '    color: var(--accent2);\n'
        '    text-decoration: none;\n'
        '    margin-left: 6px;\n'
        '    padding: 2px 8px;\n'
        '    border: 1px solid var(--accent);\n'
        '    border-radius: 4px;\n'
        '    font-size: 11px;\n'
        '    cursor: pointer;\n'
        '    transition: background 0.2s, color 0.2s;\n'
        '  }\n'
        '  .btn-locate:hover { background: var(--accent); color: #fff; }\n'
        '  .path-cell { color: var(--fg2); font-size: 12px; }\n'
        '  .footer {\n'
        '    text-align: center;\n'
        '    margin-top: 48px;\n'
        '    padding: 24px 0;\n'
        '    color: var(--fg2);\n'
        '    font-size: 12px;\n'
        '    border-top: 1px solid var(--border);\n'
        '  }\n'
        '  @media (max-width: 768px) {\n'
        '    .summary { flex-direction: column; }\n'
        '    .stats-grid { grid-template-columns: 1fr; }\n'
        '    .toolbar { flex-direction: column; }\n'
        '    .toolbar input, .toolbar select { width: 100%; }\n'
        '    th, td { padding: 10px 12px; font-size: 13px; }\n'
        '  }\n'
        '</style>\n'
        '</head>\n'
        '<body>\n'
        '<div class="container">\n'
        '\n'
        '  <div class="header">\n'
        '    <h1>\u7075\u7280\u6587\u4ef6\u7cbe\u7075</h1>\n'
        '    <p>\u667a\u80fd\u6587\u4ef6\u5206\u7c7b\u5f52\u6863 \xb7 \u62d6\u62fd\u5373\u6574\u7406</p>\n'
        '  </div>\n'
        '\n'
        '  <div class="summary">\n'
        '    <div class="summary-card">\n'
        '      <div class="num">' + str(len(records)) + '</div>\n'
        '      <div class="label">\u7d2f\u8ba1\u5904\u7406\u6587\u4ef6</div>\n'
        '    </div>\n'
        '    <div class="summary-card">\n'
        '      <div class="num">' + str(len(cats)) + '</div>\n'
        '      <div class="label">\u6587\u4ef6\u5206\u7c7b\u6570</div>\n'
        '    </div>\n'
        '    <div class="summary-card">\n'
        '      <div class="num">' + fmt_size(total_size) + '</div>\n'
        '      <div class="label">\u5f52\u6863\u603b\u5927\u5c0f</div>\n'
        '    </div>\n'
        '  </div>\n'
        '\n'
        '  <div class="stats-grid">\n'
        + stat_cards_html + '\n'
        '  </div>\n'
        '\n'
        '  <div class="toolbar">\n'
        '    <input type="text" id="search" placeholder="\u641c\u7d22\u6587\u4ef6\u540d..." oninput="filterTable()">\n'
        '    <select id="catFilter" onchange="filterTable()">\n'
        '      <option value="\u5168\u90e8">\u5168\u90e8\u5206\u7c7b</option>' + cat_options_html + '\n'
        '    </select>\n'
        '    <button class="btn" onclick="location.reload()">\u5237\u65b0</button>\n'
        '    <button class="btn" style="background:transparent;border-color:var(--border);color:var(--fg2)" onclick="openArchiveDir()">\u6253\u5f00\u5f52\u6863\u76ee\u5f55</button>\n'
        '  </div>\n'
        '\n'
        '  <div class="table-wrap">\n'
        '    <table>\n'
        '      <thead>\n'
        '        <tr>\n'
        '          <th>\u5206\u7c7b</th>\n'
        '          <th>\u6587\u4ef6\u540d</th>\n'
        '          <th>\u65e5\u671f</th>\n'
        '          <th>\u5927\u5c0f</th>\n'
        '          <th>\u64cd\u4f5c</th>\n'
        '          <th>\u5f52\u6863\u8def\u5f84</th>\n'
        '        </tr>\n'
        '      </thead>\n'
        '      <tbody id="fileBody">\n'
        + rows_html + '\n'
        '      </tbody>\n'
        '    </table>\n'
        '  </div>\n'
        '\n'
        '  <div class="footer">\n'
        '    ' + footer_text + '\n'
        '  </div>\n'
        '\n'
        '</div>\n'
        '\n'
        '<script>\n'
        "function filterTable(catVal) {\n"
        "  const keyword = document.getElementById('search').value.toLowerCase();\n"
        "  const cat = catVal !== undefined ? catVal : document.getElementById('catFilter').value;\n"
        "  if (catVal !== undefined) document.getElementById('catFilter').value = catVal;\n"
        "  const rows = document.querySelectorAll('#fileBody tr');\n"
        "  rows.forEach(row => {\n"
        "    const cells = row.querySelectorAll('td');\n"
        "    if (cells.length < 6) return;\n"
        "    const fileName = cells[1].textContent.toLowerCase();\n"
        "    const rowCat = cells[0].textContent.trim();\n"
        "    const matchKeyword = !keyword || fileName.includes(keyword);\n"
        "    const matchCat = cat === '\u5168\u90e8' || rowCat.includes(cat);\n"
        "    row.style.display = (matchKeyword && matchCat) ? '' : 'none';\n"
        "  });\n"
        "  document.querySelectorAll('.stat-card').forEach(c => {\n"
        "    const d = c.getAttribute('data-cat');\n"
        "    c.classList.toggle('active', d === cat && cat !== '\u5168\u90e8');\n"
        "    c.classList.toggle('dimmed', cat !== '\u5168\u90e8' && d !== cat);\n"
        "  });\n"
        "}\n"
        "\n"
        "function openArchiveDir() {\n"
        "  try {\n"
        "    var shell = new ActiveXObject('Shell.Application');\n"
        "    shell.Open('" + ARCHIVE_URL + "');\n"
        "  } catch(e) {\n"
        "    alert('\u8bf7\u624b\u52a8\u6253\u5f00\u76ee\u5f55: " + ARCHIVE_DIR + "');\n"
        "  }\n"
        "}\n"
        "\n"
        "document.addEventListener('DOMContentLoaded', function() {\n"
        "  document.querySelectorAll('.stat-card').forEach(card => {\n"
        "    card.addEventListener('click', function() {\n"
        "      const c = this.getAttribute('data-cat');\n"
        "      filterTable(c === document.getElementById('catFilter').value ? '\u5168\u90e8' : c);\n"
        "    });\n"
        "  });\n"
        "});\n"
        "\n"
        "document.addEventListener('keydown', function(e) {\n"
        "  if (e.key === '/' && document.activeElement.tagName !== 'INPUT') {\n"
        "    e.preventDefault();\n"
        "    document.getElementById('search').focus();\n"
        "  }\n"
        "});\n"
        '</script>\n'
        '</body>\n'
        '</html>'
    )

    out_path = os.path.join(ARCHIVE_DIR, "index.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Generated: {out_path} ({len(html)} bytes)")

if __name__ == "__main__":
    main()
