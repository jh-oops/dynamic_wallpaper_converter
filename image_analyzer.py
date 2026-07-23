#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图像理解模块（离线、零模型）
==========================
不再只看文件名，而是真正“读图”——用 Pillow 抽取像素级视觉特征，
再把特征映射成与 tags_library.json 对齐的 分类/标签 打分。

抽取的特征：
  - 主色（中位切分量化取前 8 色，含占比与中文色名）
  - 亮度 mean_lum / 对比度 contrast
  - 饱和度 mean_sat / 峰值饱和 max_sat
  - 冷暖 warmth（平均 R-B）
  - 细节密度 edge_density（灰度梯度均值）
  - 色彩丰富度 colorfulness（Hasler–Süsstrunk 指标）

映射到的标签组：
  - Color  （主色 + 多彩 + 渐变 + 霓虹）
  - Emotion（快乐/平静/温暖/浪漫/兴奋/神秘/治愈/励志，由亮度+饱和度+冷暖推导）
  - Design / Style（简约/扁平/插画/油画/卡通/摄影/抽象/复古，由细节密度+调色推导）
  - Category（主要是 Style 组；Topic 组靠文件名更可靠，图像只做弱补充）

说明：纯像素无法可靠识别“这是什么物体/场景”（猫/城市/食物），
那是之前讨论过的「AI 视觉识别」（需模型或外部 API）。本模块覆盖的是
颜色、情绪、风格这类“看得见”的属性，确定、可复现、零成本。
"""
import colorsys
import io

from PIL import Image


# ── 颜色命名：RGB → 中文色名（与 tags_library.json 的 Color 组对齐）──
def _name_color(r, g, b):
    r, g, b = r / 255.0, g / 255.0, b / 255.0
    mx, mn = max(r, g, b), min(r, g, b)
    if mx == 0:
        return "Black"
    s = (mx - mn) / mx
    v = mx
    if s < 0.12:
        if v < 0.20:
            return "Black"
        if v > 0.85:
            return "White"
        return "Gray"
    if v < 0.22:
        return "Black"
    h = colorsys.rgb_to_hsv(r, g, b)[0]  # 0..1
    deg = h * 360.0
    # 棕：低亮度暖色
    if v < 0.5 and 10 < deg < 50:
        return "Brown"
    # 粉：红相但高明度
    if (deg <= 12 or deg >= 345) and v > 0.70 and s > 0.32:
        return "Pink"
    if 290 <= deg < 345 and v > 0.68 and s > 0.30:
        return "Pink"
    if 10 < deg < 42:
        if v > 0.80 and s < 0.78:
            return "Gold"
        return "Orange"
    if deg <= 12 or deg >= 345:
        return "Red"
    if 42 <= deg < 66:
        if v > 0.82 and s < 0.70:
            return "Gold"
        return "Yellow"
    if 66 <= deg < 170:
        return "Green"
    if 170 <= deg < 262:
        return "Blue"
    if 262 <= deg < 292:
        return "Purple"
    if 292 <= deg < 345:
        return "Purple"
    return "Gray"


def _edge_density(img):
    """灰度图相邻像素绝对差均值（0..~120），衡量细节/纹理密度。"""
    g = img.convert("L").resize((96, 96))
    px = g.load()
    w, h = 96, 96
    tot = 0
    cnt = 0
    for y in range(h - 1):
        for x in range(w - 1):
            d1 = abs(px[x + 1, y] - px[x, y])
            d2 = abs(px[x, y + 1] - px[x, y])
            tot += d1 + d2
            cnt += 2
    return tot / cnt if cnt else 0.0


def analyze_image_bytes(data):
    """输入图片字节，返回特征 dict。"""
    img = Image.open(io.BytesIO(data))
    img = img.convert("RGB")
    small = img.resize((128, 128))
    px = list(small.getdata())
    n = len(px)

    # 亮度（Rec.709 加权）与对比度
    lum = [0.299 * r + 0.587 * g + 0.114 * b for (r, g, b) in px]
    mean_lum = sum(lum) / n
    var = sum((x - mean_lum) ** 2 for x in lum) / n
    contrast = var ** 0.5

    # 饱和度与冷暖
    hsvs = [colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0) for (r, g, b) in px]
    sats = [s for (_, s, _) in hsvs]
    mean_sat = sum(sats) / n
    max_sat = max(sats) if sats else 0.0
    warmth = sum(r - b for (r, g, b) in px) / n  # >0 偏暖

    # 主色：中位切分量化
    q = small.quantize(colors=8, method=Image.MEDIANCUT)
    palette = q.getpalette()
    counts = q.getcolors()
    total = sum(c for c, _ in counts) or 1
    named = []
    for cnt, idx in sorted(counts, reverse=True)[:8]:
        r, g, b = palette[idx * 3:idx * 3 + 3]
        ratio = cnt / total
        named.append({
            "ratio": round(ratio, 3),
            "name": _name_color(r, g, b),
            "rgb": [r, g, b],
            "hex": "#%02X%02X%02X" % (r, g, b),
        })
    dominant = named[0] if named else {"ratio": 0, "name": "Gray", "rgb": [128, 128, 128], "hex": "#808080"}
    max_color_ratio = dominant["ratio"]

    # 色彩丰富度（Hasler–Süsstrunk）
    rg = [r - g for (r, g, b) in px]
    yb = [0.5 * (r + g) - b for (r, g, b) in px]
    rg_mean = sum(rg) / n
    yb_mean = sum(yb) / n
    rg_std = (sum((x - rg_mean) ** 2 for x in rg) / n) ** 0.5
    yb_std = (sum((x - yb_mean) ** 2 for x in yb) / n) ** 0.5
    colorfulness = (rg_std ** 2 + yb_std ** 2) ** 0.5 + 0.3 * (rg_mean ** 2 + yb_mean ** 2) ** 0.5

    edge = _edge_density(img)

    # 不同彩色（去黑白灰，且去重）数量
    seen = set()
    distinct = []
    for d in named:
        if d["ratio"] > 0.06 and d["name"] not in ("Black", "White", "Gray") and d["name"] not in seen:
            seen.add(d["name"])
            distinct.append(d["name"])

    return {
        "size": list(img.size),
        "mean_lum": round(mean_lum, 1),
        "contrast": round(contrast, 1),
        "mean_sat": round(mean_sat, 3),
        "max_sat": round(max_sat, 3),
        "warmth": round(warmth, 1),
        "colorfulness": round(colorfulness, 1),
        "edge_density": round(edge, 1),
        "dominant": dominant,
        "named": named,
        "distinct_colors": distinct,
        "max_color_ratio": round(max_color_ratio, 3),
    }


# ── 特征 → 标签打分（仅图像来源）──
def feature_to_tag_scores(f):
    s = {}

    def add(name, v):
        s[name] = s.get(name, 0) + v

    # Color 组：主色 → 对应色标签，权重按占比
    color_map = {
        "Pink": "Pink", "Blue": "Blue", "Red": "Red", "Green": "Green",
        "Yellow": "Yellow", "Purple": "Purple", "Orange": "Orange",
        "Gold": "Gold", "Silver": "Silver", "Brown": "Brown",
        "Black": "Black", "White": "White", "Gray": "Gray",
    }
    for d in f["named"]:
        if d["name"] in color_map:
            add(color_map[d["name"]], d["ratio"] * 3.0)

    distinct = f["distinct_colors"]
    if len(distinct) >= 4:
        add("Colorful", 2.0)
    elif len(distinct) >= 3:
        add("Colorful", 1.0)

    # 渐变：平滑大色块过渡（细节低但色彩丰富且多色）
    if f["edge_density"] < 14 and f["colorfulness"] > 40 and len(distinct) >= 2:
        add("Gradient", 1.5)

    # 霓虹：暗底 + 高饱和“亮”色（明度也高，排除暗 saturation 的暗绿等）
    if f["mean_lum"] < 120:
        for d in f["named"]:
            r, g, b = d["rgb"]
            mx, mn = max(r, g, b), min(r, g, b)
            val = mx / 255.0
            sat = (mx - mn) / mx if mx else 0
            if d["ratio"] > 0.06 and val > 0.5 and sat > 0.55:
                add("Neon", 2.0)
                break

    # Emotion 组
    lum, sat, warmth = f["mean_lum"], f["mean_sat"], f["warmth"]
    if lum > 170 and sat > 0.4:
        add("Happy", 2.0)
    if warmth > 25:
        add("Warm", 1.5)
    if 80 <= lum <= 185 and sat < 0.30:
        add("Calm", 2.0)
        add("Relax", 1.5)
    if sat < 0.30 and lum >= 120:
        add("Healing", 1.2)
    if lum < 80 and f["contrast"] > 30:
        add("Mysterious", 1.5)
    if sat > 0.5 and lum > 150:
        add("Excited", 1.2)
    if lum > 175 and f["contrast"] > 60:
        add("Inspirational", 1.0)
    for d in f["named"]:
        if d["name"] in ("Pink", "Red") and d["ratio"] > 0.22:
            add("Romantic", 1.5)
            add("Love", 1.2)

    # Design / Style 组
    ed = f["edge_density"]
    if lum > 180 and sat < 0.20 and ed < 12:
        add("Minimal", 2.5)
        add("Flat", 1.5)
    if ed < 10 and len(distinct) <= 3:
        add("Flat", 2.0)
    if ed < 8 and len(distinct) <= 2:
        add("Abstract", 1.5)
    if 15 <= ed <= 45 and sat > 0.25:
        add("Illustration", 1.5)
    if ed > 35 and f["colorfulness"] > 30:
        add("Photography", 1.5)
    if ed > 40 and sat > 0.40 and len(distinct) <= 4:
        add("Cartoon", 1.2)
    if 15 <= ed <= 40 and len(distinct) >= 4 and warmth > 0:
        add("Oil Painting", 1.0)
    if 0.15 < sat < 0.40 and warmth > 10 and f["contrast"] < 45:
        add("Retro", 1.2)
    return s


# ── 特征 → 分类打分（仅图像来源，主要覆盖 Style 组）──
def feature_to_category_scores(f):
    cs = {}
    distinct = f["distinct_colors"]

    def add(name, v):
        cs[name] = cs.get(name, 0) + v

    if f["mean_lum"] > 180 and f["mean_sat"] < 0.20 and f["edge_density"] < 12:
        add("Minimal", 2.5)
    if f["edge_density"] < 10:
        add("Minimal", 1.0)
    if f["contrast"] > 55 and len(distinct) <= 4 and 90 <= f["mean_lum"] <= 200:
        add("Modern", 1.5)
    for d in f["named"]:
        if d["name"] == "Pink" and d["ratio"] > 0.18:
            add("Cute", 2.0)
        if d["name"] in ("Pink", "Red") and f["mean_lum"] > 140:
            add("Cute", 1.0)
    if len(distinct) >= 4 and f["edge_density"] < 45:
        add("Artistic", 1.5)
    if f["edge_density"] < 8:
        add("Artistic", 1.0)
    if f["edge_density"] > 40 and f["mean_sat"] > 0.40:
        add("Cartoon", 1.5)
    if 0.15 < f["mean_sat"] < 0.40 and f["warmth"] > 10 and f["contrast"] < 45:
        add("Retro", 1.5)
    if f["mean_sat"] > 0.45 and f["edge_density"] > 20:
        add("Fashion/Cool", 1.2)
    return cs


if __name__ == "__main__":
    import sys
    sample = sys.argv[1] if len(sys.argv) > 1 else None
    if not sample:
        print("用法：python image_analyzer.py <图片路径>")
        sys.exit(1)
    with open(sample, "rb") as fh:
        data = fh.read()
    f = analyze_image_bytes(data)
    print("特征：")
    for k, v in f.items():
        if k == "named":
            continue
        print(f"  {k}: {v}")
    print("  主色（前8）：")
    for d in f["named"]:
        print(f"    {d['hex']} {d['name']:>6} 占比 {d['ratio']:.2f}")
    print("\n图像来源 标签打分：")
    for name, sc in sorted(feature_to_tag_scores(f).items(), key=lambda kv: -kv[1]):
        print(f"  {name:<18} {sc:.2f}")
    print("\n图像来源 分类打分：")
    for name, sc in sorted(feature_to_category_scores(f).items(), key=lambda kv: -kv[1]):
        print(f"  {name:<18} {sc:.2f}")
