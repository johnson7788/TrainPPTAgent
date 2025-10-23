#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date  : 2025/10/16 20:16
# @File  : format_json.py
# @Author: johnson
# @Contact : github: johnson7788
# @Desc  : 格式化json文件

import json
from pathlib import Path

def main():
    json_files = sorted(Path(".").glob("*.json"))
    if not json_files:
        print("当前目录没有找到任何 .json 文件。")
        return

    updated, skipped = 0, 0
    for p in json_files:
        try:
            # 读取
            text = p.read_text(encoding="utf-8")
            data = json.loads(text)
        except Exception as e:
            print(f"[跳过] {p.name}: 读取或解析失败 -> {e}")
            skipped += 1
            continue

        # 只处理顶层为对象（dict）的 JSON
        if isinstance(data, dict):
            # 设置/覆盖 intend 字段
            data["intend"] = 4

            try:
                # 保存（美化缩进，保留非 ASCII 字符）
                p.write_text(
                    json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
                print(f"[已更新] {p.name}")
                updated += 1
            except Exception as e:
                print(f"[跳过] {p.name}: 写入失败 -> {e}")
                skipped += 1
        else:
            print(f"[跳过] {p.name}: 顶层不是对象（而是 {type(data).__name__}），未修改。")
            skipped += 1

    print(f"\n完成：更新 {updated} 个文件，跳过 {skipped} 个文件。")

if __name__ == "__main__":
    main()
