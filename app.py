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
import json
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
import tag_matcher as tm

HERE = os.path.dirname(os.path.abspath(__file__))
HTML_PATH = os.path.join(HERE, "web_ui.html")
LIBRARY_PATH = os.path.join(HERE, "tags_library.json")
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


@app.route("/api/tags/library", methods=["GET"])
def get_library():
    """返回当前标签库（分类 + 标签）。"""
    return jsonify(tm.load_library(LIBRARY_PATH))


@app.route("/api/tags/library", methods=["PUT"])
def put_library():
    """保存标签库。简单校验必须包含 categories 与 tags 数组。"""
    data = request.get_json(force=True, silent=True) or {}
    if not isinstance(data.get("categories"), list) or not isinstance(data.get("tags"), list):
        return jsonify(error="标签库必须包含 categories 和 tags 数组"), 400
    try:
        with open(LIBRARY_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return jsonify(ok=True)
    except Exception as e:
        return jsonify(error=f"保存失败：{e}"), 500


@app.route("/api/analyze", methods=["POST"])
def analyze():
    """上传文件，返回建议的 category + tags（仅基于文件名做离线规则匹配）。"""
    f = request.files.get("file")
    if not f or not f.filename:
        return jsonify(error="请上传文件"), 400
    lib = tm.load_library(LIBRARY_PATH)
    res = tm.suggest(f.filename, lib, top_n=5)
    return jsonify(res)


@app.route("/api/crop", methods=["POST"])
def crop():
    """上传 mp4，按指定目标尺寸和模式裁剪后返回 mp4（base64）。"""
    f = request.files.get("file")
    if not f or not f.filename:
        return jsonify(error="请上传 mp4 文件"), 400

    try:
        target_w = int(request.form.get("target_w", 1080))
        target_h = int(request.form.get("target_h", 2400))
    except ValueError:
        return jsonify(error="target_w / target_h 必须是整数"), 400
    if target_w < 1 or target_h < 1:
        return jsonify(error="目标尺寸必须大于 0"), 400

    mode = request.form.get("mode", "cover")
    if mode not in ("cover", "contain"):
        return jsonify(error='mode 只能是 "cover" 或 "contain"'), 400
    keep_audio = request.form.get("keep_audio") == "1"

    tmp = tempfile.mkdtemp(prefix="wp_crop_")
    src = os.path.join(tmp, os.path.basename(f.filename))
    dst = os.path.join(tmp, "cropped.mp4")
    f.save(src)
    try:
        crf, within = tz.transcode_one(src, dst, keep_audio, target_w, target_h, mode)
        with open(dst, "rb") as fh:
            mp4_bytes = fh.read()
        base = os.path.splitext(os.path.basename(f.filename))[0]
        return jsonify({
            "ok": True,
            "mp4_name": f"{base}_{target_w}x{target_h}_{mode}.mp4",
            "mp4_b64": base64.b64encode(mp4_bytes).decode("ascii"),
            "target_w": target_w,
            "target_h": target_h,
            "mode": mode,
            "crf": crf,
            "within_limit": within,
        })
    except Exception as e:
        return jsonify(error=f"裁剪失败：{e}"), 500
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    url = f"http://localhost:{PORT}/"
    # 1 秒后自动打开浏览器
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    print(f"动态壁纸生成器已启动：{url}")
    print("（关闭此终端窗口即停止服务）")
    app.run(host="127.0.0.1", port=PORT, debug=False)
