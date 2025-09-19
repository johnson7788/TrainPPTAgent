#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date  : 2025/9/19 14:49
# @File  : utils.py
# @Author: johnson
# @Contact : github: johnson7788
# @Desc  :
import json
from typing import Dict, List, Any, AsyncGenerator, Optional, Union, Tuple

# ================== JSON 解析与规则校验 ==================
def only_json(text: str) -> Optional[dict]:
    """从文本中尽力截取并解析首个 JSON 对象，失败返回 None。"""
    if not text:
        return None
    text = text.strip()
    try:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            text = text[start:end + 1]
        return json.loads(text)
    except Exception:
        return None


def validate_slide(data: Any, required_schema: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    校验生成结果是否为 dict，且包含 required_schema 的所有 key（可多不可少）。
    额外：如果某个必须字段在 required_schema 中是 dict（如 'data'），则继续校验其下一级 keys。
    仅检查两层：顶层 + 第二层（例如 data.*）。
    返回 (是否通过, 缺失key路径列表)。
    """
    missing: List[str] = []

    # 顶层必须是 dict
    if not isinstance(data, dict) or not isinstance(required_schema, dict):
        # 顶层都不是 dict，直接把 required_schema 顶层 key 视作缺失
        return False, sorted(list(required_schema.keys()))

    # 逐个顶层键校验
    for key, sub_schema in required_schema.items():
        if key not in data:
            # 顶层缺失
            missing.append(key)
            continue

        # 如果 schema 指定该键是 dict，则进一步校验第二层
        if isinstance(sub_schema, dict):
            # 被校验的数据对应值必须也是 dict
            sub_data = data.get(key)
            if not isinstance(sub_data, dict):
                # 子层不是 dict，视为该子层的所有必需键都缺失
                for sub_key in sub_schema.keys():
                    missing.append(f"{key}.{sub_key}")
            else:
                # 对比第二层键
                required_sub_keys = set(sub_schema.keys())
                got_sub_keys = set(sub_data.keys())
                for sub_key in sorted(required_sub_keys - got_sub_keys):
                    missing.append(f"{key}.{sub_key}")

        # 如果 schema 指定该键不是 dict（比如 list/str 等），这里只要求“键存在”，不深入校验其内部结构

    return (len(missing) == 0), sorted(missing)


if __name__ == '__main__':
    # 生成的数据data
    data = {'data': {'items': [{'text': '生成式AI通过学习海量数据，可自动生成符合语境的文章、脚本和配乐。这降低了内容生产门槛，提升企业营销效率。例如，广告公司可用AI快速产出多版本短视频，用于测试不同受众反应。', 'title': '内容创作行业全面变革，自动化生成高质量文章、视频和音乐'}, {'text': 'AI模型能预测分子特性与生物活性，加速候选药物筛选过程。这显著减少实验室试错成本，加快创新药上市时间。制药企业已开始用AI生成化合物库，再结合实验验证，实现高效研发闭环。', 'title': '药物研发周期缩短，AI辅助设计新分子结构'}, {'text': '设计师输入需求后，AI可生成多个结构方案并评估性能参数，如强度、重量或能耗。这使产品开发从数周缩短至数天，同时提高设计合理性。汽车厂商正用AI优化零部件布局，提升整车能效。', 'title': '工业设计领域实现快速原型迭代和优化'}], 'title': '生成式AI的商业应用'}, 'images': [{'alt': 'technology background', 'height': 1080, 'id': 'image-1', 'src': 'https://images.pexels.com/photos/1103970/pexels-photo-1103970.jpeg?auto=compress&cs=tinysrgb&w=1260&h=750&dpr=1', 'width': 1920}], 'type': 'content'}
    # 已有的ppt的schema
    current_slide_schema = {'data': {'items': [{'text': 'Detailed content about 脑机接口技术取得重大突破，实现更高精度的思维解码', 'title': '脑机接口技术取得重大突破，实现更高精度的思维解码'}, {'text': 'Detailed content about 神经形态芯片模仿人脑结构，大幅提升能效比', 'title': '神经形态芯片模仿人脑结构，大幅提升能效比'}, {'text': 'Detailed content about AI辅助脑疾病诊断和治疗，实现精准医疗', 'title': 'AI辅助脑疾病诊断和治疗，实现精准医疗'}], 'title': 'AI与脑科学的交叉研究'}, 'type': 'content'}

    validate_result = validate_slide(data, current_slide_schema)
    print(validate_result)