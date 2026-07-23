#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
可插拔视觉识别后端
==================
把“图片识别”抽象成可切换的后端，方便从离线像素分析平滑升级到 AI 视觉模型：

  - offline（默认）：复用 image_analyzer 的像素特征分析，零成本、零联网、可复现。
    能稳定识别 颜色 / 情绪 / 风格，但无法识别“这是什么物体/场景”。
  - ai：调用 OpenAI 兼容的视觉对话接口（gpt-4o / Claude / Qwen-VL / 本地 Ollama 等均可，
    只要暴露 /chat/completions 且支持 image_url）。可识别物体/场景/内容，需 API key。

配置存于 vision_config.json：
  {
    "backend": "offline" | "ai",
    "base_url": "https://api.openai.com/v1/chat/completions",  # AI 模式必填
    "api_key":  "sk-...",                                       # AI 模式必填
    "model":    "gpt-4o-mini",                                  # AI 模式必填
    "prompt":   "自定义系统提示词（可选）"
  }

AI 模式失败会自动回退 offline，保证批量任务不中断。
"""
import base64
import json
import os
import urllib.request

import image_analyzer as ia

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(HERE, "vision_config.json")

DEFAULT_PROMPT = (
    "你是一个壁纸资源标注助手。请分析用户上传的壁纸图片，并只返回一个 JSON 对象，"
    "不要输出任何额外文字。JSON 格式：{\"category\": \"单个分类名\", \"tags\": [\"标签1\",\"标签2\",...]}，"
    "tags 取 3–5 个最能描述该图的标签。只能从下方给定的分类与标签中选择，不要自创。"
)


# ── 配置读写 ──
def load_config():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    except Exception:
        cfg = {}
    cfg.setdefault("backend", "offline")
    cfg.setdefault("prompt", DEFAULT_PROMPT)
    return cfg


def save_config(cfg):
    cfg = dict(cfg)
    cfg.setdefault("backend", "offline")
    cfg.setdefault("prompt", DEFAULT_PROMPT)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    return cfg


# ── offline 后端 ──
def _analyze_offline(data):
    feats = ia.analyze_image_bytes(data)
    return (
        ia.feature_to_tag_scores(feats),
        ia.feature_to_category_scores(feats),
        feats,
        "offline",
    )


# ── ai 后端（OpenAI 兼容）──
def _normalize_endpoint(base_url):
    base_url = (base_url or "").strip()
    if not base_url:
        return ""
    if base_url.endswith("/chat/completions"):
        return base_url
    return base_url.rstrip("/") + "/chat/completions"


def _call_ai(data, cfg, library):
    endpoint = _normalize_endpoint(cfg.get("base_url"))
    if not endpoint:
        raise ValueError("AI 模式未配置 base_url")
    api_key = cfg.get("api_key") or ""
    model = cfg.get("model") or "gpt-4o-mini"

    tag_names = [t["name"] for t in library.get("tags", [])]
    cat_names = [c["name"] for c in library.get("categories", [])]
    sys_prompt = (
        cfg.get("prompt") or DEFAULT_PROMPT
    ) + f"\n可用分类（单选）：{cat_names}\n可用标签（可多选，3-5 个）：{tag_names}"

    b64 = base64.b64encode(data).decode("ascii")
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": sys_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "请识别这张图片并返回 JSON。"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                ],
            },
        ],
        "temperature": 0.2,
    }
    # 部分兼容服务支持 json 输出；不支持则模型自行返回 JSON 文本
    try:
        payload["response_format"] = {"type": "json_object"}
    except Exception:
        pass

    req = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=90) as resp:
        obj = json.loads(resp.read().decode("utf-8"))

    content = obj["choices"][0]["message"]["content"]
    parsed = json.loads(content)

    cat = parsed.get("category")
    tags = parsed.get("tags", []) or []
    valid_tags = [t for t in tags if t in tag_names][:5]
    valid_cat = cat if cat in cat_names else None

    tag_scores = {t: 1.0 for t in valid_tags}
    cat_scores = {valid_cat: 1.0} if valid_cat else {}
    return tag_scores, cat_scores, None, "ai"


# ── 统一入口 ──
def analyze(data, filename="", cfg=None, library=None):
    """输入图片字节，返回 (tag_scores, cat_scores, features, source_label)。

    source_label: "offline" / "ai" / "offline-fallback:<err>"
    """
    cfg = cfg or load_config()
    backend = (cfg.get("backend") or "offline").lower()
    library = library or {"tags": [], "categories": []}

    if backend == "ai" and cfg.get("base_url") and cfg.get("api_key"):
        try:
            ts, cs, feats, src = _call_ai(data, cfg, library)
            return ts, cs, feats, src
        except Exception as e:
            ts, cs, feats, src = _analyze_offline(data)
            return ts, cs, feats, f"offline-fallback:{type(e).__name__}"

    ts, cs, feats, src = _analyze_offline(data)
    return ts, cs, feats, src
