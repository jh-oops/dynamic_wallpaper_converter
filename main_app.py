#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
动态壁纸 ZIP 生成器 · 桌面启动器（PyInstaller 打包入口）
===================================================
双击运行后：后台启动 Flask 服务 + 自动打开浏览器 + 显示 Tk 控制窗口。
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


def build_window():
    root = tk.Tk()
    root.title(APP_NAME)
    root.geometry("380x190")
    root.resizable(False, False)

    info = tk.Label(root, text=f"{APP_NAME} 正在运行", font=("PingFang SC", 14, "bold"))
    info.pack(pady=(18, 4))
    sub = tk.Label(root, text=f"本地服务：{URL}", fg="#3a6fd8", cursor="hand2")
    sub.pack()
    sub.bind("<Button-1>", lambda e: open_browser())

    hint = tk.Label(root, text="在浏览器中上传 mp4 即可一键生成规范 zip", fg="#666")
    hint.pack(pady=(6, 14))

    btn_row = tk.Frame(root)
    btn_row.pack()

    b_open = tk.Button(btn_row, text="打开网页", width=12, command=open_browser)
    b_open.pack(side=tk.LEFT, padx=8)

    def quit_app():
        root.destroy()
        os._exit(0)

    b_quit = tk.Button(btn_row, text="退出程序", width=12, command=quit_app)
    b_quit.pack(side=tk.LEFT, padx=8)

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
