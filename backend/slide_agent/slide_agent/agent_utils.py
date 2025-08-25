#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date  : 2025/6/18 20:01
# @File  : agent_utils.py
# @Author: johnson
# @Contact : github: johnson7788
# @Desc  :

import os
import json
from functools import lru_cache

@lru_cache(maxsize=16) # 使用缓存避免重复读取文件
def load_prompt_template(prompt_name: str) -> str:
    """从prompts文件夹加载指定的prompt模板。"""
    current_dir = os.path.dirname(__file__)
    prompt_path = os.path.join(current_dir, 'prompts', f'{prompt_name}.txt')
    try:
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        # 在Agent中，抛出异常比返回错误字符串更好，便于上层捕获
        raise FileNotFoundError(f"Prompt模板文件未找到: {prompt_path}")


def parse_event(event):
    parsed_output = {}

    if event.content and event.content.parts:
        part = event.content.parts[0]

        # Parse text content
        if part.text:
            parsed_output = {"type": "text", "content": part.text}

        # Parse function call information
        if part.function_call:
            function_call_name = part.function_call.name
            function_call_args = part.function_call.args
            parsed_output = {
                "type": "function call",
                "content": f"function_name: {function_call_name}, function_args: {function_call_args}"
            }

        # Parse function result information
        if part.function_response:
            function_response_name = part.function_response.name # Assuming name is always present for function_response
            function_response_result = None

            if part.function_response.response and 'result' in part.function_response.response:
                result_obj = part.function_response.response['result']
                if hasattr(result_obj, 'content') and result_obj.content:
                    extracted_texts = []
                    for content_part in result_obj.content:
                        if hasattr(content_part, 'text') and content_part.text:
                            extracted_texts.append(content_part.text)
                    function_response_result = "\n".join(extracted_texts)
                else:
                    function_response_result = result_obj # Fallback if 'content' is not found

            if function_response_result is not None:
                parsed_output = {
                    "type": "function result",
                    "content": f"function_name: {function_response_name}, function_result: {function_response_result}"
                }
            else:
                 # Handle cases where function_response has no result or an empty result
                parsed_output = {
                    "type": "function result",
                    "content": f"function_name: {function_response_name}, function_result: No result or empty result found."
                }

    return parsed_output