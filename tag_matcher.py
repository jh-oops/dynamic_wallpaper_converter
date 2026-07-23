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


def suggest_category(filename, library=None):
    """返回建议的单个 category dict（含 score），无命中时 score 为 0。"""
    library = library or load_library()
    text = _normalize(filename)
    best = {"score": 0}
    for cat in library.get("categories", []):
        score = _score(text, cat.get("keywords", []))
        entry = {
            "name": cat["name"],
            "name_zh": cat.get("name_zh", ""),
            "group": cat.get("group", ""),
            "description": cat.get("description", ""),
            "score": score,
        }
        if score > best["score"]:
            best = entry
    return best


def suggest_tags(filename, library=None, top_n=5):
    """返回建议的 tag list（最多 top_n 个，按 score 降序；只返回有命中的）。"""
    library = library or load_library()
    text = _normalize(filename)
    scored = []
    for tag in library.get("tags", []):
        score = _score(text, tag.get("keywords", []))
        if score > 0:
            scored.append({
                "name": tag["name"],
                "name_zh": tag.get("name_zh", ""),
                "group": tag.get("group", ""),
                "score": score,
            })
    scored.sort(key=lambda x: (-x["score"], x["group"], x["name"]))
    return scored[:top_n]


def suggest(filename, library=None, top_n=5):
    """同时给出 category + tags 的完整建议。"""
    library = library or load_library()
    return {
        "category": suggest_category(filename, library),
        "tags": suggest_tags(filename, library, top_n),
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
