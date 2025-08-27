#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date  : 2025/8/27 11:16
# @File  : simple_process.py
# @Author: johnson
# @Contact : github: johnson7788
# @Desc  : 读取文件outline_data.jsonl，里面是dict，只需要difficulty和task这2个字段


# -*- coding: utf-8 -*-
import json
from pathlib import Path
import sys

in_file = Path("outline_data.jsonl")
out_file = Path("outline_data_min.jsonl")

if not in_file.exists():
    sys.exit(f"找不到文件: {in_file.resolve()}")

kept = 0
with in_file.open("r", encoding="utf-8") as fin, out_file.open("w", encoding="utf-8") as fout:
    for lineno, line in enumerate(fin, 1):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as e:
            print(f"[第{lineno}行] JSON 解析失败：{e}", file=sys.stderr)
            continue
        if not isinstance(obj, dict):
            print(f"[第{lineno}行] 非 dict，已跳过", file=sys.stderr)
            continue

        mini = {"difficulty": obj.get("difficulty"), "task": obj.get("outline_json")}
        fout.write(json.dumps(mini, ensure_ascii=False) + "\n")
        kept += 1

print(f"已写入 {kept} 行到 {out_file}")
