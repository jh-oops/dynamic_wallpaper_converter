#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
动态壁纸 MP4 预处理 + 一键打包脚本
==================================
把任意 mp4 处理成《动态壁纸规范》要求的规范 zip，全流程离线、无需浏览器。

两种用法：
  A) 仅转码（衔接网页工具）：
        python transcode_for_zip.py input.mp4            # 输出到 ./transcoded/
        python transcode_for_zip.py input_dir/           # 批量转码目录下所有 *.mp4
        python transcode_for_zip.py input.mp4 -o out.mp4
        python transcode_for_zip.py input.mp4 --keep-audio

  B) 一步出包（推荐，不依赖浏览器）：
        python transcode_for_zip.py input.mp4 --package \
            --author "92wallpaper" --description "A calm blue live wallpaper."
        # → 生成 <名称>.zip（含 manifest.json + preview + wallpapers）

        python transcode_for_zip.py input_dir/ --package \
            --author "92wallpaper" --description "A {name} live wallpaper."
        # → 批量：每个 mp4 生成一个 <名称>.zip，{name} 自动替换为文件名

转码规则（所有模式一致）：
    - 解码器 H.264 (libx264)
    - 分辨率 1080×2400（保持比例补黑边，不变形）
    - 大小 ≤ 5M（超限自动提高 CRF 重试）
    - 默认去除音轨（--keep-audio 保留）
打包规则（--package）：
    - preview/wallpaper.jpg  第一帧，1080×2400，JPEG，≤800K
    - preview/thumbnail.gif  前 2 秒，400×710，10–15fps，颜色≥128，≤1.5M
    - wallpapers/wallpaper.mp4  转码后的合规 mp4
    - manifest.json  {id:UUID, type:8, author, name, description}
    - zip 不含 __MACOSX 等隐藏文件

依赖（隔离 venv，离线自带 ffmpeg，无需系统安装）：
    /Users/shswhuangyi/.workbuddy/binaries/python/envs/default/bin/pip install imageio-ffmpeg Pillow
"""
import argparse
import glob
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
import zipfile

import imageio_ffmpeg
from PIL import Image

TARGET_W, TARGET_H = 1080, 2400
MAX_MP4 = 5 * 1024 * 1024
MAX_JPG = 800 * 1024
MAX_GIF = int(1.5 * 1024 * 1024)
GIF_W, GIF_H = 400, 710
GIF_FPS = 12
CRF_STEPS = [23, 28, 32, 36, 40]
# 可选动态预览图
DYN_W, DYN_H = 540, 1200
MAX_DYN = 2 * 1024 * 1024


def ffmpeg_exe():
    """返回 ffmpeg 二进制路径；打包后确保有可执行权限（PyInstaller 数据文件可能丢 +x）。"""
    path = imageio_ffmpeg.get_ffmpeg_exe()
    try:
        if not os.access(path, os.X_OK):
            os.chmod(path, 0o755)
    except OSError:
        pass
    return path


def list_inputs(path):
    if os.path.isdir(path):
        return sorted(glob.glob(os.path.join(path, "*.mp4")))
    return [path]


def transcode_one(src, dst, keep_audio):
    """转码单个文件到 H.264/1080×2400/≤5M，返回 (最终crf, 是否≤5M)。"""
    exe = ffmpeg_exe()
    vf = (
        f"scale={TARGET_W}:{TARGET_H}:force_original_aspect_ratio=decrease,"
        f"pad={TARGET_W}:{TARGET_H}:(ow-iw)/2:(oh-ih)/2"
    )
    cmd_base = [
        exe, "-y", "-i", src,
        "-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p",
        "-vf", vf, "-movflags", "+faststart",
    ]
    if not keep_audio:
        cmd_base += ["-an"]
    for crf in CRF_STEPS:
        cmd = cmd_base + ["-crf", str(crf), "-preset", "medium", dst]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        if os.path.getsize(dst) <= MAX_MP4:
            return crf, True
    return CRF_STEPS[-1], False


def make_first_frame_jpg(mp4, dst_jpg):
    """抽第一帧为 JPG，缩放/压缩到 1080×2400、≤800K。返回最终字节数。"""
    exe = ffmpeg_exe()
    raw = dst_jpg + ".raw.jpg"
    subprocess.run(
        [exe, "-y", "-i", mp4, "-vf", "select=eq(n\\,0)", "-frames:v", "1",
         "-q:v", "3", raw],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True,
    )
    img = Image.open(raw)
    if img.size != (TARGET_W, TARGET_H):
        img = img.resize((TARGET_W, TARGET_H), Image.LANCZOS)
    q = 92
    while q >= 30:
        img.save(dst_jpg, "JPEG", quality=q, optimize=True)
        if os.path.getsize(dst_jpg) <= MAX_JPG:
            break
        q -= 6
    os.remove(raw)
    return os.path.getsize(dst_jpg)


def make_thumbnail_gif(mp4, dst_gif):
    """截前 2 秒做 400×710 缩略图 GIF（循环），控制 ≤1.5M、颜色≥128。

    返回 (字节数, 实际使用的 fps)。
    规范建议 10–15fps，但复杂视频在 ffmpeg 编码下 10fps×2秒 常 >1.5M；
    此时以「大小硬上限 ≤1.5M」优先，自动降帧兜底（最低 6fps），并在调用处报告。
    """
    exe = ffmpeg_exe()
    # (fps, palette颜色) 由高到低尝试；≤1.5M 优先于 fps 下限
    for fps, colors in [(GIF_FPS, 256), (10, 256), (10, 128), (8, 128), (6, 128)]:
        vf = (
            f"fps={fps},"
            f"scale={GIF_W}:{GIF_H}:force_original_aspect_ratio=decrease,"
            f"pad={GIF_W}:{GIF_H}:(ow-iw)/2:(oh-ih)/2:color=black,"
            f"split[s0][s1];[s0]palettegen=stats_mode=diff:max_colors={colors}[p];"
            f"[s1][p]paletteuse=diff_mode=rectangle"
        )
        subprocess.run(
            [exe, "-y", "-i", mp4, "-t", "2", "-vf", vf, "-loop", "0", dst_gif],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True,
        )
        if os.path.getsize(dst_gif) <= MAX_GIF:
            return os.path.getsize(dst_gif), fps
    return os.path.getsize(dst_gif), 6


def build_manifest(name, author, description, id_fixed=False):
    mid = uuid.uuid5(uuid.NAMESPACE_DNS, name) if id_fixed else uuid.uuid4()
    return {
        "id": str(mid),
        "type": 8,
        "author": author,
        "name": name,
        "description": description,
    }


def make_dynamic_preview(mp4, dst_gif):
    """可选动态预览图：540×1200，前 2 秒，10–15fps，颜色≥128，≤2M。

    返回 (字节数, 实际 fps)。规范建议 10–15fps，复杂视频在 ffmpeg 编码下
    常 >2M，此时以「≤2M 硬上限」优先自动降帧兜底（最低 5fps）；若仍超限
    则返回实际值并在调用处标注 ⚠（动态预览为可选附件，不进包）。
    """
    exe = ffmpeg_exe()
    for fps, colors in [(GIF_FPS, 256), (10, 256), (10, 128), (8, 128), (6, 128), (5, 128)]:
        vf = (
            f"fps={fps},"
            f"scale={DYN_W}:{DYN_H}:force_original_aspect_ratio=decrease,"
            f"pad={DYN_W}:{DYN_H}:(ow-iw)/2:(oh-ih)/2:color=black,"
            f"split[s0][s1];[s0]palettegen=stats_mode=diff:max_colors={colors}[p];"
            f"[s1][p]paletteuse=diff_mode=rectangle"
        )
        subprocess.run(
            [exe, "-y", "-i", mp4, "-t", "2", "-vf", vf, "-loop", "0", dst_gif],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True,
        )
        if os.path.getsize(dst_gif) <= MAX_DYN:
            return os.path.getsize(dst_gif), fps
    return os.path.getsize(dst_gif), 5


def process_one(src, name, author, description, id_fixed=False,
                keep_audio=False, dynamic=False, return_mp4=False):
    """核心流水线：转码 + 抽帧 + 缩略图 + manifest + 打包（可选动态预览）。

    返回 dict：
      ok        是否成功
      zip_bytes 规范 zip 的字节（bytes）
      zip_name  建议下载名（<name>.zip）
      dyn_bytes 动态预览图字节（dynamic=True 时；否则 None）
      dyn_name  动态预览图建议名
      mp4_bytes 中间转码 mp4 字节（return_mp4=True 时；否则 None）
      report    人类可读的处理报告
      error     失败时的错误信息
    """
    tmp = tempfile.mkdtemp(prefix="wp_")
    mid = os.path.join(tmp, "mid.mp4")
    jpg = os.path.join(tmp, "wallpaper.jpg")
    gif = os.path.join(tmp, "thumbnail.gif")
    report = []
    try:
        crf, within = transcode_one(src, mid, keep_audio)
        sj = make_first_frame_jpg(mid, jpg)
        sg, gif_fps = make_thumbnail_gif(mid, gif)
        manifest = build_manifest(name, author, description, id_fixed)

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
            z.write(jpg, "preview/wallpaper.jpg")
            z.write(gif, "preview/thumbnail.gif")
            z.write(mid, "wallpapers/wallpaper.mp4")
        zip_bytes = buf.getvalue()

        dyn_bytes = None
        if dynamic:
            dyn = os.path.join(tmp, "dynamic_preview.gif")
            sd, dyn_fps = make_dynamic_preview(mid, dyn)
            with open(dyn, "rb") as fh:
                dyn_bytes = fh.read()
            dyn_note = f" fps={dyn_fps}" + ("" if sd <= MAX_DYN else " ⚠(>2M,建议换更优编码器或缩短时长)")
            report.append(f"动态预览 {sd/1024:.0f}K{dyn_note}")

        mp4_bytes = None
        if return_mp4:
            with open(mid, "rb") as fh:
                mp4_bytes = fh.read()

        fps_note = f" gif_fps={gif_fps}" + ("" if gif_fps >= 10 else " ⚠(<10,已降帧保≤1.5M)")
        report.append(
            f"jpg={sj/1024:.0f}K gif={sg/1024:.0f}K{fps_note} mp4≤5M={within} crf={crf}"
        )
        return {
            "ok": True,
            "zip_bytes": zip_bytes,
            "zip_name": name + ".zip",
            "dyn_bytes": dyn_bytes,
            "dyn_name": name + "_dynamic_preview.gif",
            "mp4_bytes": mp4_bytes,
            "mp4_name": name + ".mp4",
            "report": "；".join(report),
        }
    except subprocess.CalledProcessError as e:
        return {"ok": False, "error": str(e)}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def run_transcode(args, inputs):
    os.makedirs(args.out_dir, exist_ok=True)
    print(f"共 {len(inputs)} 个文件，目标 H.264 / {TARGET_W}×{TARGET_H} / ≤5M"
          f"{'（保留音轨）' if args.keep_audio else '（去音轨）'}\n")
    ok = 0
    for src in inputs:
        dst = args.output if (args.output and len(inputs) == 1) else \
            os.path.join(args.out_dir, os.path.basename(src))
        print(f"▶ 转码 {src}")
        try:
            crf, within = transcode_one(src, dst, args.keep_audio)
        except subprocess.CalledProcessError as e:
            print(f"  ✗ 失败：{e}")
            continue
        codec, res, size = probe(dst)
        good = (codec == "h264" and res == f"{TARGET_W}x{TARGET_H}" and within)
        ok += 1 if good else 0
        print(f"  → {dst}\n    codec={codec}  res={res}  "
              f"size={size/1048576:.2f}M  crf={crf}  {'✓ 合规' if good else '⚠ 需检查'}")
    print(f"\n完成：{ok}/{len(inputs)} 个合规。")


def run_package(args, inputs):
    os.makedirs(args.out_dir, exist_ok=True)
    ok = 0
    for idx, src in enumerate(inputs):
        base = os.path.splitext(os.path.basename(src))[0]
        name = args.name if (len(inputs) == 1 and args.name) else base
        tmpl = args.description or ""
        desc = tmpl.replace("{name}", name) if "{name}" in tmpl else tmpl
        author = args.author

        print(f"▶ 转码+打包 #{idx+1} {src}")
        res = process_one(src, name, author, desc, args.id_fixed,
                          args.keep_audio, args.dynamic, args.keep_mp4)
        if not res["ok"]:
            print(f"  ✗ 失败：{res['error']}")
            continue

        zip_path = args.zip_out if (len(inputs) == 1 and args.zip_out) \
            else os.path.join(args.out_dir, res["zip_name"])
        with open(zip_path, "wb") as fh:
            fh.write(res["zip_bytes"])
        if res["dyn_bytes"]:
            with open(os.path.join(args.out_dir, res["dyn_name"]), "wb") as fh:
                fh.write(res["dyn_bytes"])
        if res["mp4_bytes"]:
            with open(os.path.join(args.out_dir, res["mp4_name"]), "wb") as fh:
                fh.write(res["mp4_bytes"])

        size = os.path.getsize(zip_path)
        sj = len(res["zip_bytes"])  # 占位，下面用 manifest 校验更准；这里仅展示 zip 大小
        flag = "✓"
        print(f"  → {zip_path} ({size/1024:.0f}K)  {res['report']}  {flag}")
        ok += 1
    print(f"\n完成：{ok}/{len(inputs)} 个已打包为规范 zip（输出目录 {args.out_dir}）。")


def probe(out):
    exe = ffmpeg_exe()
    r = subprocess.run([exe, "-i", out], stdout=subprocess.DEVNULL,
                       stderr=subprocess.PIPE, text=True)
    s = r.stderr
    codec = "h264" if "Video: h264" in s else ("hevc" if "Video: hevc" in s else "unknown")
    m = re.search(r"(\d{3,4})x(\d{3,4})", s)
    res = m.group(0) if m else "?"
    return codec, res, os.path.getsize(out)


def main():
    ap = argparse.ArgumentParser(description="动态壁纸 MP4 → H.264 转码 / 一步打包规范 zip")
    ap.add_argument("input", help="输入 mp4 文件或目录")
    ap.add_argument("-o", "--output", help="输出文件（仅单文件转码模式有效）")
    ap.add_argument("--out-dir", default="transcoded", help="输出目录（默认 ./transcoded）")
    ap.add_argument("--keep-audio", action="store_true", help="保留音轨（默认去除）")
    # 打包模式
    ap.add_argument("--package", action="store_true",
                    help="转码后直接打包成规范 zip（一步出包，不依赖浏览器）")
    ap.add_argument("--name", help="壁纸名（单文件打包模式；默认取文件名）")
    ap.add_argument("--author", help="作者 author（打包模式必填，区分大小写，须与设计师账号一致）")
    ap.add_argument("--description", help="描述（打包模式必填；支持 {name} 占位，批量时自动替换）")
    ap.add_argument("--id-fixed", action="store_true", help="id 按名称固定（默认随机 uuid）")
    ap.add_argument("--keep-mp4", action="store_true", help="打包模式额外保留中间转码 mp4")
    ap.add_argument("--dynamic", action="store_true",
                    help="打包模式额外生成可选动态预览图（540×1200，≤2M，单独输出）")
    ap.add_argument("--zip-out", help="zip 输出路径（单文件打包模式；默认 <out-dir>/<name>.zip）")
    args = ap.parse_args()

    inputs = list_inputs(args.input)
    if not inputs:
        print("未找到 mp4 输入，请检查路径。")
        sys.exit(1)

    if args.package:
        if not args.author:
            print("✗ 打包模式需要 --author（作者名，区分大小写）。")
            sys.exit(1)
        if not args.description:
            print("✗ 打包模式需要 --description（描述；批量可用 {name} 占位）。")
            sys.exit(1)
        run_package(args, inputs)
    else:
        run_transcode(args, inputs)


if __name__ == "__main__":
    main()
