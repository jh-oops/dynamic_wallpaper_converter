#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
动态壁纸 ZIP 生成器 · 本地 Web 服务
===================================
把 `transcode_for_zip.py` 的全部流水线（转码 H.264 / 改分辨率 / 抽帧 / 缩略图 /
manifest / 打包，可选动态预览图）通过一个网页前端暴露出来，任何人用浏览器即可操作，
无需命令行。

启动：
    python app.py
    # 自动打开 http://localhost:8000/ ；若未自动打开，手动访问该地址。

依赖（已在隔离 venv 安装）：flask、imageio-ffmpeg、Pillow
若 flask 缺失，脚本会尝试自动 pip 安装。
"""
import base64
import os
import shutil
import sys
import tempfile
import threading
import webbrowser

# ---- 自举：缺 flask 时尝试安装 ----
try:
    from flask import Flask, request, jsonify
except ImportError:
    import subprocess
    print("未检测到 flask，正在自动安装…")
    subprocess.run([sys.executable, "-m", "pip", "install", "flask", "-q"], check=True)
    from flask import Flask, request, jsonify

import transcode_for_zip as tz

HERE = os.path.dirname(os.path.abspath(__file__))
HTML_PATH = os.path.join(HERE, "web_ui.html")
PORT = 8000

app = Flask(__name__)


@app.route("/")
def index():
    with open(HTML_PATH, "r", encoding="utf-8") as f:
        return f.read()


@app.route("/api/package", methods=["POST"])
def package():
    f = request.files.get("file")
    if not f or not f.filename:
        return jsonify(error="请上传 mp4 文件"), 400

    name = (request.form.get("name") or os.path.splitext(f.filename)[0]).strip()
    author = (request.form.get("author") or "").strip()
    desc = (request.form.get("description") or "").strip()
    id_fixed = request.form.get("id_fixed") == "1"
    dynamic = request.form.get("dynamic") == "1"

    # 必填校验（与规范 / 网页工具一致）
    errs = []
    if not name:
        errs.append("名称 name 不能为空")
    if not author:
        errs.append("作者 author 不能为空（须与设计师账号一致，区分大小写）")
    if not desc:
        errs.append("描述 description 不能为空")
    if errs:
        return jsonify(error="；".join(errs)), 400

    # 落盘上传文件到临时目录
    tmp = tempfile.mkdtemp(prefix="wp_up_")
    src = os.path.join(tmp, os.path.basename(f.filename))
    f.save(src)
    try:
        res = tz.process_one(src, name, author, desc, id_fixed, False, dynamic)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    if not res["ok"]:
        return jsonify(error="处理失败：" + res.get("error", "未知错误")), 500

    return jsonify({
        "zip_name": res["zip_name"],
        "zip_b64": base64.b64encode(res["zip_bytes"]).decode("ascii"),
        "dyn_name": res["dyn_name"],
        "dyn_b64": base64.b64encode(res["dyn_bytes"]).decode("ascii") if res["dyn_bytes"] else None,
        "report": res["report"],
    })


if __name__ == "__main__":
    url = f"http://localhost:{PORT}/"
    # 1 秒后自动打开浏览器
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    print(f"动态壁纸生成器已启动：{url}")
    print("（关闭此终端窗口即停止服务）")
    app.run(host="127.0.0.1", port=PORT, debug=False)
