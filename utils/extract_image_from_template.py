#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date  : 2025/9/29 23:03
# @File  : extract_image_from_template.py
# @Author: johnson
# @Contact : github: johnson7788
# @Desc  : 提取图片，并下载到本地目录

import json
import os
import requests
from urllib.parse import urlparse

def extract_image_urls(data):
    """
    遍历JSON数据，提取所有图片的URL地址 (src)。
    """
    image_urls = []

    # 检查 'slides' 键是否存在
    if 'slides' in data and isinstance(data['slides'], list):
        for slide in data['slides']:
            # 检查每个幻灯片中的 'elements' 键是否存在
            if 'elements' in slide and isinstance(slide['elements'], list):
                for element in slide['elements']:
                    # 检查元素类型是否为 'image' 且包含 'src' 键
                    if element.get('type') == 'image' and 'src' in element:
                        image_urls.append(element['src'])

    return image_urls

def read_template_file(template_file):
    with open(template_file, 'r', encoding='utf-8') as file:
        data = json.load(file)
        return data

def download_image(url, save_path):
  """   下载图片并保存到本地路径   """
  # 发送GET请求
  try:
    response = requests.get(url, stream=True)
    response.raise_for_status() # 如果请求失败会抛出异常     # 获取图片的内容并写入文件
    with open(save_path, 'wb') as file:
        for chunk in response.iter_content(1024):
            file.write(chunk)
        print(f"图片下载成功: {save_path}")
  except Exception as e:
    print(f"下载图片失败 {url}: {e}")

if __name__ == '__main__':
    template_files = ['../backend/main_api/template/template_1.json',
                      '../backend/main_api/template/template_2.json',
                      '../backend/main_api/template/template_3.json',
                      '../backend/main_api/template/template_4.json',
                      ]
    download_directory = '../backend/main_api/template/static/'
    local_image_url = "/api/data/static/"
    if not os.path.exists(download_directory):
        os.makedirs(download_directory)
    # 是否图片已经下载完成
    images_downloaded = []
    for template_file in template_files:
        json_data = read_template_file(template_file)
        urls = extract_image_urls(json_data)
        print(f"{template_file}中的图片地址列表：共包含{len(urls)}张图片")
        # template_name = os.path.splitext(os.path.basename(template_file))[0]
        for i, url in enumerate(urls, 1):
            image_name = os.path.basename(urlparse(url).path)
            if image_name in images_downloaded:
                print(f"图片 {image_name} 已经下载过了，跳过")
                continue
            save_path = os.path.join(download_directory, image_name)
            print(f"下载图片： {i}. {url} 到 {save_path}")
            download_image(url, save_path)
            images_downloaded.append(image_name)
        # 对template_file图片的链接进行替换成本地的local_image_url