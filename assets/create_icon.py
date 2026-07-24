#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成复古风格应用图标（macOS .icns + Windows .ico）。"""
import os
import subprocess
from PIL import Image, ImageDraw

BASE = os.path.dirname(os.path.abspath(__file__))
ICONSET = os.path.join(BASE, "app_icon.iconset")

# 复古调色板
C_BG = "#F4A261"      # 暖橙背景
C_BODY = "#2A9D8F"    # 青绿机身
C_DARK = "#264653"    # 深青（山/阴影）
C_OUTLINE = "#1A1A1A" # 粗黑边
C_SCREEN_TOP = "#A8DADC"
C_SCREEN_BOT = "#F4D03F"
C_SUN = "#E9C46A"
C_KNOB = "#E76F51"
C_LIGHT = "#F1FAEE"


def rounded_rect(draw, xy, radius, fill, outline=None, width=1):
    x0, y0, x1, y1 = xy
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def draw_tv(size):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # 背景：带圆角的橙色方块（占满画布，留出一点透明边距给 macOS 圆角裁剪）
    pad = size // 16
    bg_r = size // 8
    rounded_rect(d, (pad, pad, size - pad, size - pad), bg_r, fill=C_BG,
                 outline=C_OUTLINE, width=max(size // 64, 2))

    # 电视机外框（青绿圆角矩形）
    tv_pad = size // 5
    tv_x0, tv_y0 = tv_pad, tv_pad + size // 20
    tv_x1, tv_y1 = size - tv_pad, size - tv_pad - size // 20
    tv_r = size // 18
    rounded_rect(d, (tv_x0, tv_y0, tv_x1, tv_y1), tv_r, fill=C_BODY,
                 outline=C_OUTLINE, width=max(size // 48, 3))

    # 内部阴影凹槽
    inner_pad = size // 32
    rounded_rect(d, (tv_x0 + inner_pad, tv_y0 + inner_pad,
                     tv_x1 - inner_pad, tv_y1 - inner_pad), tv_r // 2,
                 fill="#238B7E", outline=C_OUTLINE, width=max(size // 96, 1))

    # 屏幕区域（天空渐变用纯色近似：上浅蓝下暖黄）
    screen_margin = size // 12
    sx0, sy0 = tv_x0 + screen_margin, tv_y0 + screen_margin
    sx1, sy1 = tv_x1 - screen_margin - size // 10, tv_y1 - screen_margin
    sr = size // 24
    rounded_rect(d, (sx0, sy0, sx1, sy1), sr, fill=C_SCREEN_TOP,
                 outline=C_OUTLINE, width=max(size // 80, 2))
    # 下半部分暖黄覆盖，模拟渐变
    horizon_y = (sy0 + sy1) // 2 + size // 40
    d.rounded_rectangle((sx0, horizon_y, sx1, sy1), radius=sr,
                        fill=C_SCREEN_BOT, outline=None)
    # 重描屏幕边
    rounded_rect(d, (sx0, sy0, sx1, sy1), sr, fill=None,
                 outline=C_OUTLINE, width=max(size // 80, 2))

    # 太阳
    sun_r = size // 14
    sun_cx = sx0 + (sx1 - sx0) * 3 // 4
    sun_cy = sy0 + (horizon_y - sy0) // 3
    d.ellipse((sun_cx - sun_r, sun_cy - sun_r,
               sun_cx + sun_r, sun_cy + sun_r),
              fill=C_SUN, outline=C_OUTLINE, width=max(size // 120, 1))

    # 远山（两层）
    def draw_mountain(base_y, peak_offset, color, width_frac):
        w = sx1 - sx0
        peak_x = sx0 + w * width_frac
        peak_y = base_y - peak_offset
        d.polygon([(sx0, base_y), (peak_x, peak_y), (sx1, base_y)],
                  fill=color, outline=C_OUTLINE)

    draw_mountain(sy1 - size // 80, size // 7, C_DARK, 0.35)
    draw_mountain(sy1 - size // 80, size // 10, "#3C6E71", 0.65)

    # 右侧旋钮面板
    knob_x = sx1 + size // 30
    knob_w = tv_x1 - sx1 - size // 30
    knob_y1 = sy0 + (sy1 - sy0) // 4
    knob_y2 = sy0 + (sy1 - sy0) * 3 // 4
    knob_r = min(knob_w, (sy1 - sy0) // 8) // 2
    for ky in (knob_y1, knob_y2):
        d.ellipse((knob_x + knob_w // 2 - knob_r, ky - knob_r,
                   knob_x + knob_w // 2 + knob_r, ky + knob_r),
                  fill=C_KNOB, outline=C_OUTLINE, width=max(size // 120, 1))

    # 顶部天线
    ant_x = (tv_x0 + tv_x1) // 2
    ant_y = tv_y0
    d.line([(ant_x - size // 12, ant_y - size // 10),
            (ant_x - size // 30, ant_y),
            (ant_x + size // 30, ant_y - size // 14),
            (ant_x + size // 12, ant_y - size // 8)],
           fill=C_OUTLINE, width=max(size // 48, 3))
    d.ellipse((ant_x + size // 12 - size // 80, ant_y - size // 8 - size // 80,
               ant_x + size // 12 + size // 80, ant_y - size // 8 + size // 80),
              fill=C_LIGHT, outline=C_OUTLINE, width=1)

    # 底部支脚
    foot_w, foot_h = size // 10, size // 18
    foot_y = tv_y1 - size // 120
    d.rounded_rectangle((tv_x0 + size // 12, foot_y,
                         tv_x0 + size // 12 + foot_w, foot_y + foot_h),
                        radius=size // 80, fill=C_DARK, outline=C_OUTLINE,
                        width=max(size // 120, 1))
    d.rounded_rectangle((tv_x1 - size // 12 - foot_w, foot_y,
                         tv_x1 - size // 12, foot_y + foot_h),
                        radius=size // 80, fill=C_DARK, outline=C_OUTLINE,
                        width=max(size // 120, 1))

    return img


def main():
    os.makedirs(ICONSET, exist_ok=True)
    # 清理旧文件
    for f in os.listdir(ICONSET):
        os.remove(os.path.join(ICONSET, f))

    sizes = [16, 32, 64, 128, 256, 512, 1024]
    for s in sizes:
        im = draw_tv(s)
        im.save(os.path.join(ICONSET, f"icon_{s}x{s}.png"))
        if s <= 512:
            im2 = draw_tv(s * 2)
            im2.save(os.path.join(ICONSET, f"icon_{s}x{s}@2x.png"))

    # 生成 .icns
    icns_path = os.path.join(BASE, "app_icon.icns")
    subprocess.run(["iconutil", "-c", "icns", "-o", icns_path, ICONSET], check=True)

    # 生成 .ico（多尺寸）
    ico_path = os.path.join(BASE, "app_icon.ico")
    ico_imgs = [draw_tv(s) for s in [16, 32, 48, 256]]
    ico_imgs[0].save(ico_path, format="ICO", sizes=[(s, s) for s in [16, 32, 48, 256]])

    print("Generated:")
    print(" ", icns_path)
    print(" ", ico_path)


if __name__ == "__main__":
    main()
