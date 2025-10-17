#!/usr/bin/env python
# -*- coding: utf-8 -*-

# python qwen_vl_2dgrounding.py \
#   --image ./slide0.png \
#   --in-json ./未标注pptx.json \
#   --out-json ./ai_template_pptx.json \
#   --page-index 0 \
#   --viz bbox \
#   --viz-out ./slide0_vis.png


import os
import io
import ast
import json
import time
import copy
import base64
import argparse
import traceback
from io import BytesIO
from typing import List, Tuple, Optional, Dict, Any

import requests
from PIL import Image, ImageDraw, ImageFont, ImageColor
from dotenv import load_dotenv

# ----------------------------
# 全局常量与默认配置
# ----------------------------

DEFAULT_MODEL = "qwen3-vl-235b-a22b-instruct"
OPENAI_COMPAT_BASE = "https://dashscope.aliyuncs.com/compatible-mode/v1"

BASE_COLORS = [
    'red', 'green', 'blue', 'yellow', 'orange', 'pink', 'purple', 'brown', 'gray',
    'beige', 'turquoise', 'cyan', 'magenta', 'lime', 'navy', 'maroon', 'teal',
    'olive', 'coral', 'lavender', 'violet', 'gold', 'silver',
]
ADDITIONAL_COLORS = [name for (name, _) in ImageColor.colormap.items()]
ALL_COLORS = BASE_COLORS + ADDITIONAL_COLORS

PAGE_TYPES = [
    "cover",              # 封面：大标题 + 副标题/点缀
    "title-content",      # 标题 + 正文段落或要点
    "two-column",         # 左右双栏
    "image-caption",      # 大图 + 配图说明
    "section",            # 章节页
    "thankyou",           # 致谢/结束
    "list",               # 列表/要点
    "unknown"
]

ROLE_TEXT = ["title", "subtitle", "content", "caption"]
ROLE_NON_TEXT = ["image", "chart", "table", "logo", "decorative", "shape"]
ALL_ROLES = ROLE_TEXT + ROLE_NON_TEXT

# ----------------------------
# 通用工具
# ----------------------------

def parse_json_fenced(text: str) -> str:
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.strip().lower() == "```json":
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
            return None

def load_image_any(path_or_url: str) -> Image.Image:
    if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
        resp = requests.get(path_or_url, timeout=30)
        resp.raise_for_status()
        return Image.open(BytesIO(resp.content)).convert("RGB")
    else:
        return Image.open(path_or_url).convert("RGB")

def pick_font(size: int = 16) -> ImageFont.FreeTypeFont:
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

# ----------------------------
# 可视化（保留你原来的）
# ----------------------------

def draw_bboxes(img: Image.Image, model_text: str) -> Image.Image:
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
        ax1 = int(float(x1) / 1000.0 * w)
        ay1 = int(float(y1) / 1000.0 * h)
        ax2 = int(float(x2) / 1000.0 * w)
        ay2 = int(float(y2) / 1000.0 * h)
        if ax1 > ax2: ax1, ax2 = ax2, ax1
        if ay1 > ay2: ay1, ay2 = ay2, ay1
        draw.rectangle([(ax1, ay1), (ax2, ay2)], outline=color, width=3)
        label = box.get("label") or box.get("role")
        if label:
            draw.text((ax1 + 8, ay1 + 6), str(label), fill=color, font=font)
    return out

def draw_points(img: Image.Image, model_text: str) -> Image.Image:
    out = img.copy()
    draw = ImageDraw.Draw(out)
    w, h = out.size
    font = pick_font(16)
    obj = safe_json_loads(model_text) or []
    if isinstance(obj, dict): obj = [obj]
    pts = [o for o in obj if "point_2d" in o]
    for i, item in enumerate(pts):
        color = ALL_COLORS[i % len(ALL_COLORS)]
        x, y = item["point_2d"]
        ax = float(x) / 1000.0 * w
        ay = float(y) / 1000.0 * h
        r = 3
        draw.ellipse([(ax - r, ay - r), (ax + r, ay + r)], fill=color)
        text = item.get("label") or item.get("role") or f"p{i+1}"
        draw.text((ax + 2*r, ay + 2*r), str(text), fill=color, font=font)
    return out

# ----------------------------
# Qwen 调用
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
    from openai import OpenAI
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

# ----------------------------
# 模板打标相关：Prompt, IoU, 合并
# ----------------------------

PROMPT_TEMPLATE = """你是一个 PPT 版式与视觉元素分析器。请只输出 JSON，绝不输出解释或多余文字。
坐标系：使用相对坐标 0~1000。bbox_2d = [x1,y1,x2,y2]，x1<x2,y1<y2。

目标：识别该幻灯片的页面类型与各元素的角色与位置，用于把“普通 JSON”转换为“可复用 PPT 模版 JSON”。

页面类型（page_type）仅能取以下枚举之一：
{page_types}

元素角色（role）仅能取以下枚举之一：
- 文本：{role_text}
- 非文本：{role_non_text}

输出 JSON 的**唯一**合法结构如下（严格遵守键名与大小写）：
{{
  "page_type": "cover|title-content|two-column|image-caption|section|thankyou|list|unknown",
  "elements": [
    {{
      "role": "title|subtitle|content|caption|image|chart|table|logo|decorative|shape",
      "bbox_2d": [x1,y1,x2,y2]
    }},
    ...
  ]]
}}

约束与规则：
- 只检测版面中“信息承载”或“版式结构”的元素，背景花纹可标为 decorative 或忽略。
- 文本框只使用 role: title / subtitle / content / caption 四种之一。
- 如果是封面，通常有 title 与可选 subtitle；章节页可用 page_type=section。
- 不确定时使用最保守的 page_type=unknown，role=content。
- 仅输出一个 JSON，对齐示例结构并且是合法 JSON（不要 markdown 围栏）。
"""

def build_prompt_for_template() -> str:
    return PROMPT_TEMPLATE.format(
        page_types=", ".join(PAGE_TYPES),
        role_text=", ".join(ROLE_TEXT),
        role_non_text=", ".join(ROLE_NON_TEXT),
    )

def iou_xyxy(a: List[float], b: List[float]) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    inter_w = max(0.0, min(ax2, bx2) - max(ax1, bx1))
    inter_h = max(0.0, min(ay2, by2) - max(ay1, by1))
    inter = inter_w * inter_h
    area_a = max(0.0, (ax2 - ax1)) * max(0.0, (ay2 - ay1))
    area_b = max(0.0, (bx2 - bx1)) * max(0.0, (by2 - by1))
    union = area_a + area_b - inter + 1e-6
    return inter / union

def abs_bbox_to_rel(x1: float, y1: float, x2: float, y2: float, W: float, H: float) -> List[float]:
    return [max(0, min(1000, 1000*x1/W)),
            max(0, min(1000, 1000*y1/H)),
            max(0, min(1000, 1000*x2/W)),
            max(0, min(1000, 1000*y2/H))]

def rel_bbox_to_abs(x1: float, y1: float, x2: float, y2: float, W: float, H: float) -> List[float]:
    return [x1/1000.0*W, y1/1000.0*H, x2/1000.0*W, y2/1000.0*H]

def element_to_rel_bbox(elem: Dict[str, Any], W: float, H: float) -> Optional[List[float]]:
    # 你的 JSON 元素通常含 left/top/width/height（以 px 表示）
    if all(k in elem for k in ["left", "top", "width", "height"]):
        x1, y1 = elem["left"], elem["top"]
        x2, y2 = x1 + elem["width"], y1 + elem["height"]
        return abs_bbox_to_rel(x1, y1, x2, y2, W, H)
    return None

def role_is_text(role: str) -> bool:
    return role in ROLE_TEXT

def merge_template_types(
    raw_slide_json: Dict[str, Any],
    model_result: Dict[str, Any],
    iou_thresh: float = 0.25
) -> Dict[str, Any]:
    """把模型的角色/框写回原始 slide JSON，返回修改后的 slide JSON"""
    W = raw_slide_json.get("__canvas_width") or raw_slide_json.get("width")
    H = raw_slide_json.get("__canvas_height") or raw_slide_json.get("height")
    # 某些导出结构是全局含 width/height；这里尝试从顶层或参数传入
    # 保险策略：如果 slide 层没有宽高，就从上层拿（用户会传整文件，这里演示单页合并）
    if not W or not H:
        # 尝试顶层
        pass

    # 1) 写入页面类型
    page_type = model_result.get("page_type")
    if page_type in PAGE_TYPES:
        raw_slide_json["type"] = page_type

    # 2) 预计算每个元素的相对 bbox
    elems = raw_slide_json.get("elements", [])
    rel_boxes = []
    for e in elems:
        rb = element_to_rel_bbox(e, W, H)
        rel_boxes.append(rb)

    # 3) 逐个模型元素去匹配
    model_elems = model_result.get("elements", []) or []
    used = set()
    for m in model_elems:
        role = m.get("role")
        bbox = m.get("bbox_2d")
        if not role or role not in ALL_ROLES or not bbox or len(bbox) != 4:
            continue
        # 文本 → 只匹配 type == 'text'；非文本 → 匹配非 text
        best_iou, best_idx = 0.0, -1
        for idx, (e, rb) in enumerate(zip(elems, rel_boxes)):
            if rb is None or idx in used:
                continue
            is_text_elem = (e.get("type") == "text")
            if role_is_text(role) and not is_text_elem:
                continue
            if (not role_is_text(role)) and is_text_elem:
                continue
            iou = iou_xyxy(rb, bbox)
            if iou > best_iou:
                best_iou, best_idx = iou, idx

        if best_idx >= 0 and best_iou >= iou_thresh:
            used.add(best_idx)
            tgt = elems[best_idx]
            # 写文本类型
            if role_is_text(role):
                # 统一写到 textType
                tgt["textType"] = role
            else:
                # 给非文本元素写一个语义 role（不破坏原有 type）
                tgt["role"] = role

    raw_slide_json["elements"] = elems
    return raw_slide_json

# ----------------------------
# 命令行与主流程
# ----------------------------

def main():
    load_dotenv()

    parser = argparse.ArgumentParser(description="Qwen3-VL 模板打标工具（页面类型 & 元素角色）")
    parser.add_argument("--image", required=True, help="该页截图/渲染图路径或 URL")
    parser.add_argument("--in-json", required=True, help="该页对应的未标注 JSON 路径（仅该页或整文件都可）")
    parser.add_argument("--out-json", required=True, help="输出模板 JSON 路径")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="模型名称")
    parser.add_argument("--viz", choices=["bbox", "points"], default="bbox", help="可视化类型（可选保存调试）")
    parser.add_argument("--viz-out", default="", help="可选：可视化结果输出路径（png），留空则不导出")
    parser.add_argument("--max-side", type=int, default=1280, help="可视化前缩放显示用")
    parser.add_argument("--min-pixels", type=int, default=64*32*32, help="Qwen 参数")
    parser.add_argument("--max-pixels", type=int, default=9800*32*32, help="Qwen 参数")
    parser.add_argument("--base-url", default=OPENAI_COMPAT_BASE, help="OpenAI 兼容端点 base_url")
    parser.add_argument("--iou", type=float, default=0.25, help="匹配 IoU 阈值")
    parser.add_argument("--page-index", type=int, default=0, help="当 in-json 是整文件时：要处理的 slides[index]")

    args = parser.parse_args()

    api_key = os.getenv("ALI_API_KEY")
    if not api_key:
        raise EnvironmentError("未找到 ALI_API_KEY。请在 .env 中配置或导出环境变量。")

    # 载入 JSON
    with open(args.in_json, "r", encoding="utf-8") as f:
        doc = json.load(f)

    # 取宽高（顶层或 slide 层）
    width = doc.get("width")
    height = doc.get("height")

    # 拿到要处理的 slide 结构
    if "slides" in doc and isinstance(doc["slides"], list):
        slide = doc["slides"][args.page_index]
        # 把画布尺寸写给 slide，供相对坐标换算
        if width and height:
            slide["width"] = width
            slide["height"] = height
    else:
        # 传入就是单页
        slide = doc

    # 1) 构造强约束 Prompt
    prompt = build_prompt_for_template()

    # 2) 调 Qwen
    model_text = infer_with_openai_compat(
        api_key=api_key,
        image_path_or_url=args.image,
        prompt=prompt,
        model=args.model,
        min_pixels=args.min_pixels,
        max_pixels=args.max_pixels,
        base_url=args.base_url,
    )

    # 3) 解析模型输出
    model_obj = safe_json_loads(model_text)
    if not isinstance(model_obj, dict):
        raise RuntimeError("模型未返回合法 JSON 对象，请检查 Prompt 或图片质量。\n输出片段：\n" + (model_text[:400] if model_text else ""))

    # 4) 合并写回
    merged_slide = merge_template_types(slide, model_obj, iou_thresh=args.iou)

    # 5) 写回到文档
    if "slides" in doc and isinstance(doc["slides"], list):
        doc["slides"][args.page_index] = merged_slide
    else:
        doc = merged_slide

    with open(args.out_json, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)

    print(f"✅ 模板 JSON 已写入：{args.out_json}")

    # 6) （可选）可视化调试
    if args.viz_out:
        img = load_image_any(args.image)
        W, H = img.size
        # 将模型 obj 的 bbox 可视化
        # 转成绘图所需的 “数组形式”
        draw_list = []
        for it in model_obj.get("elements", []) or []:
            if "bbox_2d" in it:
                draw_list.append({"bbox_2d": it["bbox_2d"], "label": it.get("role")})
        vis_text = json.dumps(draw_list, ensure_ascii=False)
        if args.viz == "bbox":
            vis = draw_bboxes(img, vis_text)
        else:
            vis = draw_points(img, vis_text)
        # 缩放保存
        w, h = vis.size
        max_side = max(w, h)
        if max_side > args.max_side:
            scale = args.max_side / max_side
            vis = vis.resize((int(w * scale), int(h * scale)), resample=Image.Resampling.LANCZOS)
        vis.save(args.viz_out)
        print(f"🖼️ 可视化结果：{args.viz_out}")

if __name__ == "__main__":
    main()
