#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
2D grounding CLI 工具
--------------------
特性：
- 通过 DashScope (OpenAI 兼容端点) 或 DashScope 原生 HTTP 调用 Qwen3-VL
- 支持 bbox 与 point 两种可视化
- 坐标系使用 Qwen3-VL 的相对坐标（0~1000）
- 使用 .env 管理密钥（ALI_API_KEY）
- argparse 命令行参数，便于测试与集成

用法示例：
1) 使用 OpenAI 兼容接口（推荐）并渲染 bbox：
   python qwen_vl_2dgrounding.py \
     --image ./cakes.png \
     --prompt "定位最右上角的棕色蛋糕，以JSON格式输出其bbox坐标" \
     --backend openai \
     --viz bbox \
     --out output_bbox.png

2) 使用 DashScope 原生 HTTP 并渲染 points：
   python qwen_vl_2dgrounding.py \
     --image ./football_field.jpg \
     --prompt prompt = '''Locate every person inside the football field with points, report their point coordinates, role(player, referee or unknown) and shirt color in JSON format like this: {"point_2d": [x, y], "label": "person", "role": "player/referee/unknown", "shirt_color": "the person's shirt color"}''' \
     --backend dashscope \
     --viz points \
     --out output_points.png

准备：
- pip install pillow requests openai python-dotenv
- 在项目根目录创建 .env，写入：ALI_API_KEY=你的密钥
"""

import os
import io
import ast
import json
import time
import copy
import base64
import random
import argparse
import traceback
from io import BytesIO
from typing import List, Tuple, Optional

import requests
from PIL import Image, ImageDraw, ImageFont, ImageColor
from dotenv import load_dotenv

# ----------------------------
# 全局常量与默认配置
# ----------------------------

DEFAULT_MODEL = "qwen3-vl-235b-a22b-instruct"
OPENAI_COMPAT_BASE = "https://dashscope.aliyuncs.com/compatible-mode/v1"
DASHSCOPE_HTTP_URL = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"  # 原生HTTP兼容地址（与上类似）
# 说明：两者均为“兼容模式”域名；--backend=openai 时走 openai SDK，--backend=dashscope 时走 requests

# 颜色池（先给一组常见颜色，不够再补 ImageColor 内置颜色）
BASE_COLORS = [
    'red', 'green', 'blue', 'yellow', 'orange', 'pink', 'purple', 'brown', 'gray',
    'beige', 'turquoise', 'cyan', 'magenta', 'lime', 'navy', 'maroon', 'teal',
    'olive', 'coral', 'lavender', 'violet', 'gold', 'silver',
]
ADDITIONAL_COLORS = [name for (name, _) in ImageColor.colormap.items()]
ALL_COLORS = BASE_COLORS + ADDITIONAL_COLORS


# ----------------------------
# 工具函数：解析与绘图
# ----------------------------

def parse_json_fenced(text: str) -> str:
    """去掉 ```json ... ``` 的 Markdown 包裹，返回纯 JSON 文本"""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.strip().lower() == "```json":
            # 取之后直到下一个 ```
            body = "\n".join(lines[i+1:])
            if "```" in body:
                body = body.split("```")[0]
            return body.strip()
    return text.strip()


def safe_json_loads(text: str):
    """
    尝试将模型返回的文本解析为 JSON。
    - 先去掉 markdown 栅栏
    - 先试 json.loads；失败再试 ast.literal_eval（有些模型会吐列表/字典字面量）
    - 再失败尝试截断修复
    返回：解析后的对象 或 None
    """
    raw = parse_json_fenced(text)
    try:
        return json.loads(raw)
    except Exception:
        try:
            return ast.literal_eval(raw)
        except Exception:
            # 粗暴修补：尝试找到可能的收尾位置
            try:
                end_idx = raw.rfind('"}') + len('"}')
                candidate = raw[:end_idx] + "]"
                return ast.literal_eval(candidate)
            except Exception:
                return None


def decode_points_from_jsonish(text: str) -> Tuple[List[List[float]], List[str]]:
    """
    从模型返回中解析点坐标列表。
    期望格式示例：
      [{"point_2d":[x,y], "label":"person"}, ...]
    返回：points=[[x,y],...], labels=[...]
    """
    obj = safe_json_loads(text)
    points, labels = [], []
    if not obj:
        return points, labels
    if isinstance(obj, dict):
        obj = [obj]
    for item in obj:
        if isinstance(item, dict) and "point_2d" in item:
            x, y = item["point_2d"]
            points.append([float(x), float(y)])
            labels.append(item.get("label", f"point_{len(points)}"))
    return points, labels


def load_image_any(path_or_url: str) -> Image.Image:
    """加载本地或 HTTP 图片，返回 PIL Image"""
    if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
        resp = requests.get(path_or_url, timeout=30)
        resp.raise_for_status()
        return Image.open(BytesIO(resp.content)).convert("RGB")
    else:
        return Image.open(path_or_url).convert("RGB")


def pick_font(size: int = 16) -> ImageFont.FreeTypeFont:
    """
    尝试选择一个可用字体（优先中文/日文 Noto）。
    找不到则用默认字体（不支持中文时会方框）。
    """
    candidates = [
        "NotoSansCJK-Regular.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for p in candidates:
        try:
            return ImageFont.truetype(p, size=size)
        except Exception:
            continue
    return ImageFont.load_default()


def draw_bboxes(img: Image.Image, model_text: str) -> Image.Image:
    """
    根据模型返回的 bbox JSON 绘制到图片上。
    期望格式（相对坐标 0~1000）：
      [{"bbox_2d": [x1,y1,x2,y2], "label": "xxx"}, ...]
    """
    out = img.copy()
    draw = ImageDraw.Draw(out)
    w, h = out.size
    font = pick_font(16)

    obj = safe_json_loads(model_text)
    if not obj:
        return out
    if isinstance(obj, dict):
        obj = [obj]

    for i, box in enumerate(obj):
        if not isinstance(box, dict) or "bbox_2d" not in box:
            continue
        color = ALL_COLORS[i % len(ALL_COLORS)]
        x1, y1, x2, y2 = box["bbox_2d"]
        # 相对坐标 → 绝对像素
        ax1 = int(float(x1) / 1000.0 * w)
        ay1 = int(float(y1) / 1000.0 * h)
        ax2 = int(float(x2) / 1000.0 * w)
        ay2 = int(float(y2) / 1000.0 * h)
        # 纠正顺序
        if ax1 > ax2: ax1, ax2 = ax2, ax1
        if ay1 > ay2: ay1, ay2 = ay2, ay1

        draw.rectangle([(ax1, ay1), (ax2, ay2)], outline=color, width=3)
        label = box.get("label")
        if label:
            draw.text((ax1 + 8, ay1 + 6), str(label), fill=color, font=font)

    return out


def draw_points(img: Image.Image, model_text: str) -> Image.Image:
    """
    根据模型返回的 points JSON 绘制到图片上。
    期望格式：
      [{"point_2d":[x,y], "label":"xxx"}, ...]
    """
    out = img.copy()
    draw = ImageDraw.Draw(out)
    w, h = out.size
    font = pick_font(16)

    points, labels = decode_points_from_jsonish(model_text)
    if not points:
        return out

    for i, pt in enumerate(points):
        color = ALL_COLORS[i % len(ALL_COLORS)]
        ax = float(pt[0]) / 1000.0 * w
        ay = float(pt[1]) / 1000.0 * h
        r = 3
        draw.ellipse([(ax - r, ay - r), (ax + r, ay + r)], fill=color)
        text = labels[i] if i < len(labels) else f"p{i+1}"
        draw.text((ax + 2*r, ay + 2*r), str(text), fill=color, font=font)

    return out


# ----------------------------
# 推理：两种后端
# ----------------------------

def infer_with_openai_compat(
    api_key: str,
    image_path_or_url: str,
    prompt: str,
    model: str = DEFAULT_MODEL,
    min_pixels: int = 64 * 32 * 32,
    max_pixels: int = 9800 * 32 * 32,
    base_url: str = OPENAI_COMPAT_BASE,
) -> str:
    """
    通过 OpenAI 兼容接口调用 Qwen3-VL。
    - 将图片转 base64 作为 image_url data URI（即便本地路径也可）
    - 返回文本（模型 message.content）
    """
    from openai import OpenAI
    # 准备 base64
    if image_path_or_url.startswith("http://") or image_path_or_url.startswith("https://"):
        resp = requests.get(image_path_or_url, timeout=30)
        resp.raise_for_status()
        b64 = base64.b64encode(resp.content).decode("utf-8")
    else:
        with open(image_path_or_url, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")

    client = OpenAI(api_key=api_key, base_url=base_url)
    messages = [{
        "role": "user",
        "content": [
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
                "min_pixels": min_pixels,
                "max_pixels": max_pixels
            },
            {"type": "text", "text": prompt},
        ],
    }]
    completion = client.chat.completions.create(model=model, messages=messages)
    return completion.choices[0].message.content


def _dash_http_call(call_url: str, headers: dict, payload: dict, max_try: int = 5, sleep_sec: int = 5) -> str:
    """DashScope 原生 HTTP 调用（带重试）"""
    for _ in range(max_try):
        try:
            ret = requests.post(call_url, json=payload, headers=headers, timeout=180)
            if ret.status_code != 200:
                raise RuntimeError(f"http {ret.status_code}: {ret.text}")
            ret_json = ret.json()
            content = ret_json.get("output", {}).get("choices", [{}])[0].get("message", {}).get("content", "")
            # content 为数组（其中 text 段拼接）
            if isinstance(content, list):
                return ''.join(seg.get('text', '') for seg in content if isinstance(seg, dict))
            return str(content)
        except Exception:
            traceback.print_exc()
            time.sleep(sleep_sec)
    raise RuntimeError("DashScope HTTP 重试失败")


def infer_with_dashscope_http(
    api_key: str,
    image_path_or_url: str,
    prompt: str,
    model: str = DEFAULT_MODEL,
    min_pixels: int = 64 * 32 * 32,
    max_pixels: int = 9800 * 32 * 32,
    call_url: str = DASHSCOPE_HTTP_URL,
) -> str:
    """
    通过 DashScope 原生 HTTP 方式调用（兼容模式），传入图片 URL（本地会读文件转为 bytes 再用 data URI）。
    """
    # 为保持与 openai 方式一致，这里也统一转 data URI，API 端会处理
    if image_path_or_url.startswith("http://") or image_path_or_url.startswith("https://"):
        resp = requests.get(image_path_or_url, timeout=30)
        resp.raise_for_status()
        b64 = base64.b64encode(resp.content).decode("utf-8")
    else:
        with open(image_path_or_url, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    messages = [{
        "role": "user",
        "content": [
            {"image": f"data:image/jpeg;base64,{b64}", "min_pixels": min_pixels, "max_pixels": max_pixels},
            {"type": "text", "text": prompt},
        ],
    }]
    payload = {"model": model, "input": {"messages": messages}}
    return _dash_http_call(call_url, headers, payload)


# ----------------------------
# 命令行与主流程
# ----------------------------

def main():
    load_dotenv()  # 读取 .env

    parser = argparse.ArgumentParser(description="Qwen3-VL 2D Grounding 命令行工具（bbox/points 可视化）")
    parser.add_argument("--image", required=True, help="图片路径或 URL")
    parser.add_argument("--prompt", required=True, help="传给模型的提示词")
    parser.add_argument("--backend", choices=["openai", "dashscope"], default="openai",
                        help="选择后端：openai (OpenAI 兼容端点) 或 dashscope (原生 HTTP)")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="模型名称")
    parser.add_argument("--viz", choices=["bbox", "points"], default="bbox", help="可视化类型：bbox 或 points")
    parser.add_argument("--out", default="vis_output.png", help="可视化结果输出路径")
    parser.add_argument("--max-side", type=int, default=1280, help="可视化前缩放的最长边像素（仅影响显示/保存）")
    parser.add_argument("--min-pixels", type=int, default=64*32*32, help="推理图像下限像素（接口参数）")
    parser.add_argument("--max-pixels", type=int, default=9800*32*32, help="推理图像上限像素（接口参数）")
    parser.add_argument("--base-url", default=OPENAI_COMPAT_BASE, help="OpenAI 兼容端点 base_url")
    parser.add_argument("--http-url", default=DASHSCOPE_HTTP_URL, help="DashScope 原生 HTTP 调用 URL")

    args = parser.parse_args()

    api_key = os.getenv("ALI_API_KEY")
    if not api_key:
        raise EnvironmentError("未找到 ALI_API_KEY。请在 .env 中配置或导出环境变量。")

    # 推理
    if args.backend == "openai":
        model_text = infer_with_openai_compat(
            api_key=api_key,
            image_path_or_url=args.image,
            prompt=args.prompt,
            model=args.model,
            min_pixels=args.min_pixels,
            max_pixels=args.max_pixels,
            base_url=args.base_url,
        )
    else:
        model_text = infer_with_dashscope_http(
            api_key=api_key,
            image_path_or_url=args.image,
            prompt=args.prompt,
            model=args.model,
            min_pixels=args.min_pixels,
            max_pixels=args.max_pixels,
            call_url=args.http_url,
        )

    print("\n=== 原始模型输出（截断展示） ===")
    preview = (model_text or "")[:800]
    print(preview + ("..." if len(model_text or "") > 800 else ""))

    # 加载图片并缩放（仅用于可视化结果）
    img = load_image_any(args.image)
    w, h = img.size
    max_side = max(w, h)
    if max_side > args.max_side:
        scale = args.max_side / max_side
        img = img.resize((int(w * scale), int(h * scale)), resample=Image.Resampling.LANCZOS)

    # 绘制
    if args.viz == "bbox":
        vis = draw_bboxes(img, model_text)
    else:
        vis = draw_points(img, model_text)

    # 保存
    vis.save(args.out)
    print(f"\n✅ 可视化结果已保存：{args.out}")


if __name__ == "__main__":
    main()
