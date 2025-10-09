#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date  : 2025/9/29 23:03
# @File  : extract_image_from_template.py
# @Author: johnson
# @Contact : github: johnson7788
# @Desc  : 提取图片，并下载到本地目录，并替换模板文件里的图片链接，并修改前端的frontend/public/mocks/imgs.json

import json
import os
import requests
from urllib.parse import urlparse


def extract_image_urls(data):
    """遍历JSON数据，提取所有图片的URL地址 (src)。"""
    image_urls = []
    if 'slides' in data and isinstance(data['slides'], list):
        for slide in data['slides']:
            if 'elements' in slide and isinstance(slide['elements'], list):
                for element in slide['elements']:
                    if element.get('type') == 'image' and 'src' in element:
                        image_urls.append(element['src'])
    return image_urls


def extract_front_images(data):
    """遍历 front_images 的 JSON 数据，提取所有 src。"""
    image_urls = []
    if isinstance(data, list):
        for item in data:
            if 'src' in item:
                image_urls.append(item['src'])
    return image_urls


def read_json_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)


def write_json_file(file_path, data):
    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def download_image(url, save_path):
    """下载图片并保存到本地路径"""
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        with open(save_path, 'wb') as file:
            for chunk in response.iter_content(1024):
                file.write(chunk)
        print(f"图片下载成功: {save_path}")
    except Exception as e:
        print(f"下载图片失败 {url}: {e}")


def replace_image_urls(data, url_to_image_map, local_image_url):
    """用本地路径替换模板 JSON 数据中的图片URL"""
    if 'slides' in data and isinstance(data['slides'], list):
        for slide in data['slides']:
            if 'elements' in slide and isinstance(slide['elements'], list):
                for element in slide['elements']:
                    if element.get('type') == 'image' and 'src' in element:
                        old_url = element['src']
                        if old_url in url_to_image_map:
                            image_name = url_to_image_map[old_url]
                            element['src'] = os.path.join(local_image_url, image_name).replace("\\", "/")
    return data


def replace_front_images(data, url_to_image_map, local_image_url):
    """用本地路径替换 front_images JSON 数据中的图片URL"""
    if isinstance(data, list):
        for item in data:
            if 'src' in item:
                old_url = item['src']
                if old_url in url_to_image_map:
                    image_name = url_to_image_map[old_url]
                    item['src'] = os.path.join(local_image_url, image_name).replace("\\", "/")
    return data


if __name__ == '__main__':
    template_files = [
        '../backend/main_api/template/template_1.json',
        '../backend/main_api/template/template_2.json',
        '../backend/main_api/template/template_3.json',
        '../backend/main_api/template/template_4.json',
    ]
    download_directory = '../backend/main_api/template/'
    local_image_url = "/api/data/"

    front_images_file = '../frontend/public/mocks/imgs.json'

    if not os.path.exists(download_directory):
        os.makedirs(download_directory)

    images_downloaded = []
    url_to_image_map = {}  # 维护URL与本地文件名的对应关系

    # # 处理模板文件
    for template_file in template_files:
        json_data = read_json_file(template_file)
        urls = extract_image_urls(json_data)
        print(f"{template_file}中的图片地址列表：共包含{len(urls)}张图片")

        for i, url in enumerate(urls, 1):
            image_name = os.path.basename(urlparse(url).path)
            if image_name not in images_downloaded:
                save_path = os.path.join(download_directory, image_name)
                print(f"下载图片： {i}. {url} 到 {save_path}")
                download_image(url, save_path)
                images_downloaded.append(image_name)
            else:
                print(f"图片 {image_name} 已经下载过了，跳过")

            url_to_image_map[url] = image_name

        updated_data = replace_image_urls(json_data, url_to_image_map, local_image_url)
        write_json_file(template_file, updated_data)
        print(f"{template_file} 图片链接已更新完成！")

    # 处理 front_images 文件
    if os.path.exists(front_images_file):
        front_data = read_json_file(front_images_file)
        urls = extract_front_images(front_data)
        print(f"{front_images_file}中的图片地址列表：共包含{len(urls)}张图片")

        for i, url in enumerate(urls, 1):
            image_name = os.path.basename(urlparse(url).path)
            if image_name not in images_downloaded:
                save_path = os.path.join(download_directory, image_name)
                print(f"下载 front_images 图片： {i}. {url} 到 {save_path}")
                download_image(url, save_path)
                images_downloaded.append(image_name)
            else:
                print(f"front_images 图片 {image_name} 已经下载过了，跳过")

            url_to_image_map[url] = image_name

        updated_front_data = replace_front_images(front_data, url_to_image_map, local_image_url)
        write_json_file(front_images_file, updated_front_data)
        print(f"{front_images_file} 图片链接已更新完成！")
