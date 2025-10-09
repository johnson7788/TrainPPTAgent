#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date  : 2025/9/28 15:25
# @File  : split_data.py.py
# @Author: johnson
# @Contact : github: johnson7788
# @Desc  :

import os
import json

# 输入的原始字符串
with open('temp_data.txt', 'r', encoding='utf-8') as f:
    raw_data = f.read()

# 处理字符串，将每个字典按 "type" 分隔
# 重新组合每个字典，并确保每个字典格式正确
split_data = raw_data.split('}{')
split_data[0] = split_data[0] + '}'
split_data[-1] = '{' + split_data[-1]

# 将每个部分都包装为字典
for i in range(1, len(split_data) - 1):
    split_data[i] = '{' + split_data[i] + '}'

data = []
for item in split_data:
    item = item.strip()
    # print(f"开始加载: {item}")
    item_data = json.loads(item)
    # print(f"加载完成: {item_data}")
    # print(json.dumps(item_data, ensure_ascii=False, indent=2))
    data.append(item_data)
print(data)