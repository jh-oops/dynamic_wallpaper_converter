#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
马里奥配色 · 像素控制窗口独立预览（不启动 Flask，仅看 UI）
运行：python3 preview_window.py
"""
import tkinter as tk

# ── 马里奥经典调色板 ──
C_SKY = "#5c94fc"       # 天蓝背景
C_PANEL = "#ffffff"     # 白面板
C_RED = "#e52521"       # 马里奥红
C_COIN = "#fbd000"      # 金币黄
C_GREEN = "#43b047"     # 管道绿
C_BROWN = "#8b4513"     # 砖块棕
C_TEXT = "#111111"      # 黑字
C_DIM = "#8a8a8a"       # 暗字
C_BLACK = "#000000"     # 描边黑


def _pixel_rect(canvas, x, y, w, h, color, tags=None):
    return canvas.create_rectangle(x, y, x + w, y + h, fill=color, outline="", tags=tags)


def build_window():
    root = tk.Tk()
    root.title("动态壁纸 ZIP 生成器 · 预览")
    W, H = 420, 280
    root.geometry(f"{W}x{H}")
    root.resizable(False, False)
    root.configure(bg=C_SKY)

    mono_fonts = ("Courier", "Menlo", "Monaco", "Consolas", "monospace")
    title_font = (mono_fonts[0], 18, "bold")
    body_font = (mono_fonts[0], 11, "bold")
    small_font = (mono_fonts[0], 9)
    chinese_font = ("PingFang SC", 14, "bold")
    hint_font = ("PingFang SC", 10)

    canvas = tk.Canvas(root, width=W, height=H, bg=C_SKY, highlightthickness=0)
    canvas.pack(fill="both", expand=True)

    # 顶部/底部砖块带
    def _brick_band(y0):
        _pixel_rect(canvas, 0, y0, W, 12, C_BROWN)
        for bx in range(0, W, 26):
            canvas.create_line(bx, y0, bx, y0 + 12, fill=C_BLACK, width=2)
        canvas.create_line(0, y0 + 6, W, y0 + 6, fill=C_BLACK, width=1)
    _brick_band(0)
    _brick_band(H - 12)

    # 扫描线
    for y in range(0, H, 4):
        canvas.create_line(0, y, W, y, fill="#000000", width=1, stipple="gray12")

    # 白色面板 + 黑边
    _pixel_rect(canvas, 16, 20, W - 32, H - 40, C_PANEL)
    canvas.create_rectangle(16, 20, W - 16, H - 20, outline=C_BLACK, width=4)

    # 左上金币装饰
    canvas.create_oval(40, 40, 58, 58, fill=C_COIN, outline=C_BLACK, width=3)
    _pixel_rect(canvas, 47, 43, 3, 12, C_BROWN)

    # 标题（红字带黑投影）
    canvas.create_text(W // 2 + 2, 50, text="DYNAMIC WALLPAPER", font=title_font, fill=C_BLACK)
    canvas.create_text(W // 2, 48, text="DYNAMIC WALLPAPER", font=title_font, fill=C_RED)
    canvas.create_text(W // 2, 76, text="动态壁纸 ZIP 生成器", font=chinese_font, fill=C_TEXT)

    # 状态行（管道绿）
    _pixel_rect(canvas, 52, 100, 12, 12, C_GREEN)
    canvas.create_rectangle(52, 100, 64, 112, outline=C_BLACK, width=2)
    canvas.create_text(72, 106, text="SERVER ONLINE", font=body_font, fill=C_GREEN, anchor="w")
    cursor = canvas.create_text(204, 106, text="▮", font=body_font, fill=C_GREEN, anchor="w")

    # 本地地址（红字，可点击）
    canvas.create_text(W // 2, 134, text="LOCAL URL:", font=small_font, fill=C_DIM)
    url_text = canvas.create_text(W // 2, 154, text="http://localhost:8000/", font=(mono_fonts[0], 11, "bold"), fill=C_RED)
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

    # 像素按钮
    def _make_button(x, y, w, h, label, hotkey, bg, fg, tag):
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
        return body, txt

    # A：金币黄底黑字；B：管道绿底白字
    _make_button(48, 182, 130, 44, "打开网页", "PRESS A", C_COIN, C_BLACK, "btn_open")
    _make_button(W - 178, 182, 130, 44, "退出程序", "PRESS B", C_GREEN, C_PANEL, "btn_quit")

    # 底部提示
    canvas.create_text(W // 2, 240, text="拖入 MP4 到浏览器 → 一键生成规范 ZIP", font=hint_font, fill=C_DIM)

    # 右侧：马里奥超级蘑菇（红帽 + 白点 + 米色菌柄 + 黑眼）
    mx, my = 350, 92
    # 菌柄（米色）
    _pixel_rect(canvas, mx - 10, my + 20, 26, 24, "#f7d9a0")
    canvas.create_rectangle(mx - 10, my + 20, mx + 16, my + 44, outline=C_BLACK, width=3)
    # 眼睛
    _pixel_rect(canvas, mx - 4, my + 28, 4, 7, C_BLACK)
    _pixel_rect(canvas, mx + 5, my + 28, 4, 7, C_BLACK)
    # 菌盖（红半圆）
    canvas.create_oval(mx - 13, my, mx + 19, my + 28, fill=C_RED, outline=C_BLACK, width=3)
    # 白点
    canvas.create_oval(mx - 9, my + 8, mx - 1, my + 16, fill=C_PANEL, outline=C_BLACK, width=2)
    canvas.create_oval(mx + 6, my + 5, mx + 14, my + 13, fill=C_PANEL, outline=C_BLACK, width=2)
    canvas.create_oval(mx - 1, my + 2, mx + 5, my + 8, fill=C_PANEL, outline=C_BLACK, width=2)

    # 闪烁光标
    def _blink():
        if not canvas.winfo_exists():
            return
        state = canvas.itemcget(cursor, "state")
        canvas.itemconfig(cursor, state="hidden" if state == "normal" else "normal")
        root.after(530, _blink)

    _blink()
    root.mainloop()


if __name__ == "__main__":
    build_window()
