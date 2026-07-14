#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
动态壁纸 ZIP 生成器 · 桌面启动器（PyInstaller 打包入口）
===================================================
双击运行后：后台启动 Flask 服务 + 自动打开浏览器 + 显示复古像素游戏风格的 Tk 控制窗口。
既可作为打包入口（--windowed 无终端），也可直接 `python main_app.py` 本地运行。
"""
import os
import socket
import sys
import threading
import webbrowser

import tkinter as tk

import app as wpapp  # Flask app + 路由（/ 与 /api/package）

PORT = 8000
URL = f"http://localhost:{PORT}/"
APP_NAME = "动态壁纸 ZIP 生成器"

# ── 复古像素游戏配色 ──
C_BG = "#171727"       # 深紫蓝背景
C_DARK = "#0f0f1a"     # 暗部
C_PANEL = "#1e1e33"    # 面板
C_GREEN = "#39ff14"    # 霓虹绿
C_MAGENTA = "#ff2a6d"  # 霓虹洋红
C_CYAN = "#05d9e8"     # 霓虹青
C_GOLD = "#ffd700"     # 金币黄
C_TEXT = "#e8e8ff"     # 主文字
C_DIM = "#6c6c99"      # 暗文字


def server_alive():
    try:
        with socket.create_connection(("127.0.0.1", PORT), timeout=1):
            return True
    except OSError:
        return False


def start_server():
    # 在子线程跑 Flask；debug/reloader 关闭，避免多线程下重复加载
    wpapp.app.run(host="127.0.0.1", port=PORT, debug=False, use_reloader=False)


def open_browser():
    try:
        webbrowser.open(URL)
    except Exception:
        pass


def _pixel_rect(canvas, x, y, w, h, color, tags=None):
    """绘制一个像素块（无圆角，无描边）。"""
    return canvas.create_rectangle(x, y, x + w, y + h, fill=color, outline="", tags=tags)


def build_window():
    root = tk.Tk()
    root.title(APP_NAME)
    W, H = 420, 280
    root.geometry(f"{W}x{H}")
    root.resizable(False, False)
    root.configure(bg=C_BG)

    # 尝试使用等宽字体，若系统没有则回退
    mono_fonts = ("Courier", "Menlo", "Monaco", "Consolas", "monospace")
    title_font = (mono_fonts[0], 18, "bold")
    body_font = (mono_fonts[0], 11, "bold")
    small_font = (mono_fonts[0], 9)
    chinese_font = ("PingFang SC", 14, "bold")
    hint_font = ("PingFang SC", 10)

    canvas = tk.Canvas(root, width=W, height=H, bg=C_BG, highlightthickness=0)
    canvas.pack(fill="both", expand=True)

    # 1. 扫描线：横向半透明细线，模拟 CRT
    for y in range(0, H, 4):
        canvas.create_line(0, y, W, y, fill="#ffffff", width=1, stipple="gray25")

    # 2. 背景面板与边框
    _pixel_rect(canvas, 14, 14, W - 28, H - 28, C_PANEL, tags="panel")
    # 外框霓虹绿
    _pixel_rect(canvas, 8, 8, W - 16, 8, C_GREEN)     # 上
    _pixel_rect(canvas, 8, H - 16, W - 16, 8, C_GREEN)  # 下
    _pixel_rect(canvas, 8, 8, 8, H - 16, C_GREEN)    # 左
    _pixel_rect(canvas, W - 16, 8, 8, H - 16, C_GREEN)  # 右
    # 四角洋红装饰块
    corners = [
        (4, 4, 16, 8), (4, 4, 8, 16),
        (W - 20, 4, 16, 8), (W - 12, 4, 8, 16),
        (4, H - 12, 16, 8), (4, H - 20, 8, 16),
        (W - 20, H - 12, 16, 8), (W - 12, H - 20, 8, 16),
    ]
    for cx, cy, cw, ch in corners:
        _pixel_rect(canvas, cx, cy, cw, ch, C_MAGENTA)

    # 3. 标题：英文像素大标题 + 中文副标题
    canvas.create_text(W // 2, 48, text="DYNAMIC WALLPAPER", font=title_font, fill=C_GREEN)
    canvas.create_text(W // 2, 76, text=APP_NAME, font=chinese_font, fill=C_TEXT)

    # 4. 状态行：在线 LED + 闪烁光标
    _pixel_rect(canvas, 62, 108, 12, 12, C_GREEN)  # 状态灯
    canvas.create_text(82, 114, text="SERVER ONLINE", font=body_font, fill=C_GREEN, anchor="w")
    cursor = canvas.create_text(214, 114, text="▮", font=body_font, fill=C_GREEN, anchor="w")

    # 5. 本地地址（可点击打开）
    canvas.create_text(W // 2, 150, text="LOCAL URL:", font=small_font, fill=C_DIM)
    url_text = canvas.create_text(W // 2, 170, text=URL, font=(mono_fonts[0], 11, "bold"), fill=C_CYAN, cursor="hand2")
    url_line = canvas.create_line(110, 178, W - 110, 178, fill=C_CYAN, width=2, state="hidden")

    def _url_enter(_):
        canvas.itemconfig(url_text, fill="#ffffff")
        canvas.itemconfig(url_line, state="normal")

    def _url_leave(_):
        canvas.itemconfig(url_text, fill=C_CYAN)
        canvas.itemconfig(url_line, state="hidden")

    for tag in (url_text, url_line):
        canvas.tag_bind(tag, "<Enter>", _url_enter)
        canvas.tag_bind(tag, "<Leave>", _url_leave)
        canvas.tag_bind(tag, "<Button-1>", lambda _=None: open_browser())

    # 6. 像素按钮：打开网页 / 退出程序
    def _make_button(x, y, w, h, label, hotkey, color, action, tag):
        # 阴影
        _pixel_rect(canvas, x + 4, y + 4, w, h, "#000000")
        # 按钮体
        body = _pixel_rect(canvas, x, y, w, h, color, tags=tag)
        # 3D 高光边
        _pixel_rect(canvas, x, y, w, 3, "#ffffff")  # 上亮边
        _pixel_rect(canvas, x, y + h - 3, w, 3, "#000000")  # 下暗边
        # 文字
        txt = canvas.create_text(x + w // 2, y + h // 2 - 2, text=label, font=body_font, fill=C_DARK, tags=tag)
        hk = canvas.create_text(x + w // 2, y + h // 2 + 12, text=hotkey, font=small_font, fill=C_DARK, tags=tag)

        def _hover_in(_):
            canvas.itemconfig(body, fill="#ffffff")
            canvas.itemconfig(txt, fill=color)
            canvas.itemconfig(hk, fill=color)

        def _hover_out(_):
            canvas.itemconfig(body, fill=color)
            canvas.itemconfig(txt, fill=C_DARK)
            canvas.itemconfig(hk, fill=C_DARK)

        canvas.tag_bind(tag, "<Enter>", _hover_in)
        canvas.tag_bind(tag, "<Leave>", _hover_out)
        canvas.tag_bind(tag, "<Button-1>", lambda _=None: action())
        return body, txt

    _make_button(62, 198, 130, 44, "打开网页", "PRESS A", C_GREEN, open_browser, "btn_open")
    _make_button(W - 192, 198, 130, 44, "退出程序", "PRESS B", C_MAGENTA, lambda: (root.destroy(), os._exit(0)), "btn_quit")

    # 7. 底部提示
    canvas.create_text(W // 2, 252, text="拖入 MP4 到浏览器 → 一键生成规范 ZIP", font=hint_font, fill=C_DIM)

    # 8. 装饰：右侧像素小手机
    px, py = 356, 110
    for dx, dy, pw, ph in [(0, 0, 4, 32), (20, 0, 4, 32), (4, 3, 16, 2), (4, 27, 16, 2), (8, 10, 8, 12)]:
        _pixel_rect(canvas, px + dx, py + dy, pw, ph, C_DIM)

    # 9. 闪烁光标动画
    def _blink():
        if not canvas.winfo_exists():
            return
        state = canvas.itemcget(cursor, "state")
        canvas.itemconfig(cursor, state="hidden" if state == "normal" else "normal")
        root.after(530, _blink)

    _blink()

    root.mainloop()


def main():
    if server_alive():
        # 已有实例在跑，直接打开页面并退出本进程
        open_browser()
        return

    if os.environ.get("WP_NO_GUI"):
        # 无界面模式（如服务器/CI/沙箱）：直接阻塞运行后端
        start_server()
        return

    threading.Thread(target=start_server, daemon=True).start()
    threading.Timer(1.2, open_browser).start()
    build_window()


if __name__ == "__main__":
    main()
