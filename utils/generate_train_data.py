#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date  : 2025/8/27 09:48
# @File  : generate_train_data.py
# @Author: johnson
# @Contact : github: johnson7788
# @Desc  : 生成RL的训练数据

# 读取topic_data.jsonl，然后调用接口tools/aippt_outline，生成大纲
# 解析大纲为json格式，保存到outline_data.jsonl

import json
import httpx
import requests
import re
import os

def parse_markdown_to_json(markdown_text):
    """
    Parses a markdown outline into a nested JSON structure.
    Handles headings (#, ##, ...) and list items (- or *).
    """
    match = re.search(r"(# .*)", markdown_text, flags=re.DOTALL)

    if match:
        result = markdown_text[match.start():]
    else:
        result = markdown_text
    lines = result.strip().split('\n')
    # The root of the entire presentation.
    # It might not have a title in the markdown, so we create a placeholder.
    root = {'children': []} 
    # node_stack keeps track of the parent node at each level.
    # node_stack[0] is the root. node_stack[1] is for # headings, etc.
    node_stack = {0: root}

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Match headings like #, ##, etc.
        heading_match = re.match(r'^(#+)\s+(.*)', line)
        if heading_match:
            level = len(heading_match.group(1))
            title = heading_match.group(2).strip()
            
            new_node = {"title": title, "children": []}
            
            # Find the parent node at the correct level.
            # A level 'n' heading is a child of the last seen level 'n-1' heading.
            if level - 1 in node_stack:
                parent_node = node_stack[level - 1]
                parent_node['children'].append(new_node)
            else:
                # If there's a jump in levels (e.g. # to ###), attach to the nearest parent.
                closest_level = max(k for k in node_stack if k < level)
                node_stack[closest_level]['children'].append(new_node)

            # This new node is now the active node for its level.
            node_stack[level] = new_node
            
            # Remove deeper, now invalid, levels from the stack.
            levels_to_remove = [k for k in node_stack if k > level]
            for k in levels_to_remove:
                del node_stack[k]
            continue

        # Match list items like - or *
        list_match = re.match(r'^[\-\*]\s+(.*)', line)
        if list_match:
            title = list_match.group(1).strip()
            new_node = {"title": title, "children": []}
            
            # Attach list item to the last heading seen.
            deepest_level = max(node_stack.keys())
            node_stack[deepest_level]['children'].append(new_node)
            continue
            
    # If the root has only one child, that is the actual root of the outline.
    if len(root['children']) == 1:
        return root['children'][0]
    
    # If there are multiple top-level headings, return a structure containing all of them.
    # We can add a title to the root if the first line was not a heading.
    if lines and not lines[0].startswith('#'):
        root['title'] = 'Presentation Outline'
    return root

def generate_data():
    # The backend API is expected to be running.
    # From backend/main_api/main.py, it runs on port 6800.
    api_url = "http://127.0.0.1:6800/tools/aippt_outline"
    
    # Assuming the script is run from the project root directory.
    input_file = 'topic_data.jsonl'
    output_file = 'outline_data.jsonl'

    # Check if backend is running
    try:
        requests.get("http://127.0.0.1:6800/docs", timeout=5)
    except requests.exceptions.ConnectionError:
        print("Error: The backend service at http://127.0.0.1:6800 seems to be down.")
        print("Please start the backend server by running 'uvicorn main:app --host 127.0.0.1 --port 6800' in 'backend/main_api/' directory.")
        return

    processed_count = 0
    with open(input_file, 'r', encoding='utf-8') as f_in, \
         open(output_file, 'w', encoding='utf-8') as f_out:
        lines = f_in.readlines()
        total_tasks = len(lines)
        print(f"Found {total_tasks} tasks in {input_file}.")

        for i, line in enumerate(lines):
            try:
                data = json.loads(line)
                task = data.get("task")
                if not task:
                    continue

                print(f"Processing task {i+1}/{total_tasks}: {task}")

                # Call the API to get the outline
                request_payload = {
                    "content": task,
                    "language": "Chinese",  # Topics are in Chinese
                    "model": "default",
                    "stream": True
                }
                # Set a generous timeout as the model can be slow
                headers = {'content-type': 'application/json'}
                with httpx.stream("POST", api_url, json=request_payload, headers=headers, timeout=None) as response:
                    markdown_outline = ""
                    for chunk in response.iter_text():
                        markdown_outline += chunk
                print(f"Outline for task '{task}':\n{markdown_outline}")

                if not markdown_outline or not markdown_outline.strip():
                    print(f"Warning: Received empty outline for task: {task}")
                    continue

                # Parse the markdown outline to a structured JSON
                json_outline = parse_markdown_to_json(markdown_outline)
                print(f"JSON outline for task '{task}':\n{json.dumps(json_outline, indent=4, ensure_ascii=False)}")

                # Save the result
                output_record = {
                    "task": task,
                    "difficulty": data.get("difficulty"),
                    "outline_markdown": markdown_outline,
                    "outline_json": json_outline
                }
                f_out.write(json.dumps(output_record, ensure_ascii=False) + '\n')
                processed_count += 1

            except requests.exceptions.RequestException as e:
                print(f"Error calling API for task '{data.get('task', 'N/A')}': {e}")
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON. Line: '{line.strip()}'. Error: {e}")
            except Exception as e:
                print(f"An unexpected error occurred for task '{data.get('task', 'N/A')}': {e}")
    
    print(f"\nProcessing complete. Successfully generated outlines for {processed_count}/{total_tasks} tasks.")
    print(f"Results saved to {output_file}")


if __name__ == '__main__':
    generate_data()
