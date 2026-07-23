#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分类/标签规则匹配引擎
======================
纯离线：基于文件名关键词命中 tags_library.json 里的 keywords 做定向匹配。
- 分类：单选，返回得分最高的 category。
- 标签：多选，返回得分最高的前 N 个 tag（默认 3-5）。

扩展点：
    - 在 library 里加 manual_rules 可做强制映射。
    - 后续可加入首帧颜色/内容描述做辅助打分。
"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_LIBRARY = os.path.join(HERE, "tags_library.json")


def load_library(path=DEFAULT_LIBRARY):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _normalize(text):
    """把文件名/说明转成统一小写、去掉扩展名、把常见分隔符替换为空格的字符串。"""
    if not text:
        return ""
    # 去扩展名
    text = os.path.splitext(text)[0]
    # 统一小写，并把 _ - . / + 等换成空格
    text = text.lower()
    text = re.sub(r"[_\-\.\/+,|]+", " ", text)
    # 去掉首尾空格，压缩连续空格
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _score(text, keywords):
    """统计 keywords 里有多少个是 text 的子串（每个 keyword 只计一次）。"""
    if not text or not keywords:
        return 0
    return sum(1 for kw in keywords if kw and kw in text)


def _find_category(library, name):
    for cat in library.get("categories", []):
        if cat["name"] == name:
            return cat
    return None


def _find_tag(library, name):
    for tag in library.get("tags", []):
        if tag["name"] == name:
            return tag
    return None


def suggest_category(filename, library=None, image_cat_scores=None):
    """返回建议的单个 category dict（含 score）。

    score = 文件名命中分 + 图像特征分（image_cat_scores 提供，主要覆盖 Style 组）。
    无命中时 score 为 0。
    """
    library = library or load_library()
    text = _normalize(filename)
    merged = {}
    for cat in library.get("categories", []):
        fn = _score(text, cat.get("keywords", []))
        img = (image_cat_scores or {}).get(cat["name"], 0)
        merged[cat["name"]] = fn + img
    best_name = max(merged, key=lambda k: merged[k])
    best = merged[best_name]
    cat = _find_category(library, best_name) or {}
    return {
        "name": best_name,
        "name_zh": cat.get("name_zh", ""),
        "group": cat.get("group", ""),
        "description": cat.get("description", ""),
        "score": round(best, 2),
    }


def suggest_tags(filename, library=None, top_n=5, image_scores=None):
    """返回建议的 tag list（最多 top_n 个，按 score 降序）。

    每条带 source 标记：filename / image / both，便于前端展示“识别依据”。
    image_scores 为 image_analyzer.feature_to_tag_scores 的结果。
    """
    library = library or load_library()
    text = _normalize(filename)
    merged = {}
    for tag in library.get("tags", []):
        fn = _score(text, tag.get("keywords", []))
        img = (image_scores or {}).get(tag["name"], 0)
        total = fn + img
        if total > 0:
            if tag["name"] in merged:
                merged[tag["name"]]["score"] += total
            else:
                merged[tag["name"]] = {
                    "name": tag["name"],
                    "name_zh": tag.get("name_zh", ""),
                    "group": tag.get("group", ""),
                    "score": total,
                    "fn_score": fn,
                    "img_score": img,
                }
    # 标记来源
    for v in merged.values():
        has_fn = v["fn_score"] > 0
        has_img = v["img_score"] > 0
        v["source"] = "both" if (has_fn and has_img) else ("filename" if has_fn else "image")
        v["score"] = round(v["score"], 2)
    scored = list(merged.values())
    scored.sort(key=lambda x: (-x["score"], x["group"], x["name"]))
    return scored[:top_n]


def suggest(filename, library=None, top_n=5, image_scores=None, image_cat_scores=None):
    """同时给出 category + tags 的完整建议（合并文件名与图像特征）。"""
    library = library or load_library()
    return {
        "category": suggest_category(filename, library, image_cat_scores),
        "tags": suggest_tags(filename, library, top_n, image_scores),
    }


if __name__ == "__main__":
    import sys
    samples = sys.argv[1:] or [
        "cute_cat_neon_pink.mp4",
        "retro_cityscape_night.mp4",
        "minimal_oil_painting_landscape.mp4",
    ]
    lib = load_library()
    for s in samples:
        res = suggest(s, lib)
        print(f"\n输入：{s}")
        cat = res["category"]
        print(f"  分类：{cat['name_zh']}({cat['name']})[{cat['group']}] score={cat['score']}")
        for t in res["tags"]:
            print(f"    标签：{t['name_zh']}({t['name']})[{t['group']}] score={t['score']}")
