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

# ── 马里奥经典调色板 ──
C_BG = "#5c94fc"       # 天蓝背景
C_PANEL = "#ffffff"    # 白面板
C_RED = "#e52521"      # 马里奥红
C_COIN = "#fbd000"     # 金币黄
C_GREEN = "#43b047"    # 管道绿
C_BROWN = "#8b4513"    # 砖块棕
C_TEXT = "#111111"     # 黑字
C_DIM = "#8a8a8a"      # 暗字
C_BLACK = "#000000"    # 描边黑


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

    # 等宽字体，若系统没有则回退
    mono_fonts = ("Courier", "Menlo", "Monaco", "Consolas", "monospace")
    title_font = (mono_fonts[0], 18, "bold")
    body_font = (mono_fonts[0], 11, "bold")
    small_font = (mono_fonts[0], 9)
    chinese_font = ("PingFang SC", 14, "bold")
    hint_font = ("PingFang SC", 10)

    canvas = tk.Canvas(root, width=W, height=H, bg=C_BG, highlightthickness=0)
    canvas.pack(fill="both", expand=True)

    # 1. 顶/底砖块带
    def _brick_band(y0):
        _pixel_rect(canvas, 0, y0, W, 12, C_BROWN)
        for bx in range(0, W, 26):
            canvas.create_line(bx, y0, bx, y0 + 12, fill=C_BLACK, width=2)
        canvas.create_line(0, y0 + 6, W, y0 + 6, fill=C_BLACK, width=1)
    _brick_band(0)
    _brick_band(H - 12)

    # 2. 扫描线
    for y in range(0, H, 4):
        canvas.create_line(0, y, W, y, fill="#000000", width=1, stipple="gray12")

    # 3. 白色面板 + 黑边
    _pixel_rect(canvas, 16, 20, W - 32, H - 40, C_PANEL)
    canvas.create_rectangle(16, 20, W - 16, H - 20, outline=C_BLACK, width=4)

    # 4. 左上金币装饰
    canvas.create_oval(40, 40, 58, 58, fill=C_COIN, outline=C_BLACK, width=3)
    _pixel_rect(canvas, 47, 43, 3, 12, C_BROWN)

    # 5. 标题（红字带黑投影）
    canvas.create_text(W // 2 + 2, 50, text="DYNAMIC WALLPAPER", font=title_font, fill=C_BLACK)
    canvas.create_text(W // 2, 48, text="DYNAMIC WALLPAPER", font=title_font, fill=C_RED)
    canvas.create_text(W // 2, 76, text=APP_NAME, font=chinese_font, fill=C_TEXT)

    # 6. 状态行（管道绿）
    _pixel_rect(canvas, 52, 100, 12, 12, C_GREEN)
    canvas.create_rectangle(52, 100, 64, 112, outline=C_BLACK, width=2)
    canvas.create_text(72, 106, text="SERVER ONLINE", font=body_font, fill=C_GREEN, anchor="w")
    cursor = canvas.create_text(204, 106, text="▮", font=body_font, fill=C_GREEN, anchor="w")

    # 7. 本地地址（红字，可点击）
    canvas.create_text(W // 2, 134, text="LOCAL URL:", font=small_font, fill=C_DIM)
    url_text = canvas.create_text(W // 2, 154, text=URL, font=(mono_fonts[0], 11, "bold"), fill=C_RED)
    url_line = canvas.create_line(110, 164, W - 110, 164, fill=C_RED, width=2, state="hidden")

    def _url_enter(_):
        canvas.itemconfig(url_text, fill=C_TEXT)
        canvas.itemconfig(url_line, state="normal")
        canvas.config(cursor="hand2")

    def _url_leave(_):
        canvas.itemconfig(url_text, fill=C_RED)
        canvas.itemconfig(url_line, state="hidden")
        canvas.config(cursor="")

    for tag in (url_text, url_line):
        canvas.tag_bind(tag, "<Enter>", _url_enter)
        canvas.tag_bind(tag, "<Leave>", _url_leave)
        canvas.tag_bind(tag, "<Button-1>", lambda _=None: open_browser())

    # 8. 像素按钮：打开网页 / 退出程序
    def _make_button(x, y, w, h, label, hotkey, bg, fg, tag, action):
        _pixel_rect(canvas, x + 4, y + 4, w, h, C_BLACK)  # 阴影
        body = _pixel_rect(canvas, x, y, w, h, bg, tags=tag)
        canvas.create_rectangle(x, y, x + w, y + h, outline=C_BLACK, width=3, tags=tag)
        txt = canvas.create_text(x + w // 2, y + h // 2 - 4, text=label, font=body_font, fill=fg, tags=tag)
        hk = canvas.create_text(x + w // 2, y + h // 2 + 12, text=hotkey, font=small_font, fill=fg, tags=tag)

        def _hover_in(_):
            canvas.itemconfig(body, fill=fg)
            canvas.itemconfig(txt, fill=bg)
            canvas.itemconfig(hk, fill=bg)

        def _hover_out(_):
            canvas.itemconfig(body, fill=bg)
            canvas.itemconfig(txt, fill=fg)
            canvas.itemconfig(hk, fill=fg)

        canvas.tag_bind(tag, "<Enter>", _hover_in)
        canvas.tag_bind(tag, "<Leave>", _hover_out)
        canvas.tag_bind(tag, "<Button-1>", lambda _=None: action())
        return body, txt

    # A：金币黄底黑字；B：管道绿底白字
    _make_button(48, 182, 130, 44, "打开网页", "PRESS A", C_COIN, C_BLACK, "btn_open", open_browser)
    _make_button(W - 178, 182, 130, 44, "退出程序", "PRESS B", C_GREEN, C_PANEL, "btn_quit", lambda: (root.destroy(), os._exit(0)))

    # 9. 底部提示
    canvas.create_text(W // 2, 240, text="拖入 MP4 到浏览器 → 一键生成规范 ZIP", font=hint_font, fill=C_DIM)

    # 10. 右侧：马里奥超级蘑菇（红帽+白点+米色菌柄+黑眼）
    mx, my = 350, 92
    _pixel_rect(canvas, mx - 10, my + 20, 26, 24, "#f7d9a0")
    canvas.create_rectangle(mx - 10, my + 20, mx + 16, my + 44, outline=C_BLACK, width=3)
    _pixel_rect(canvas, mx - 4, my + 28, 4, 7, C_BLACK)
    _pixel_rect(canvas, mx + 5, my + 28, 4, 7, C_BLACK)
    canvas.create_oval(mx - 13, my, mx + 19, my + 28, fill=C_RED, outline=C_BLACK, width=3)
    canvas.create_oval(mx - 9, my + 8, mx - 1, my + 16, fill=C_PANEL, outline=C_BLACK, width=2)
    canvas.create_oval(mx + 6, my + 5, mx + 14, my + 13, fill=C_PANEL, outline=C_BLACK, width=2)
    canvas.create_oval(mx - 1, my + 2, mx + 5, my + 8, fill=C_PANEL, outline=C_BLACK, width=2)

    # 11. 闪烁光标动画
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
