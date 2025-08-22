#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date  : 2024/10/29 14:17
# @File  : monitor_utils.py
# @Author:
# @Desc  :

import os
import re
import random
import json
import hashlib
import pickle
import asyncio
from functools import wraps

# random.seed(42)

def cal_md5(content):
    content = str(content)
    result = hashlib.md5(content.encode())
    return result.hexdigest()

def async_cache_decorator(func):
    cache_path = "cache"
    if not os.path.exists(cache_path):
        os.mkdir(cache_path)

    @wraps(func)
    async def wrapper(*args, **kwargs):
        usecache = kwargs.get("usecache", True)
        if "usecache" in kwargs:
            del kwargs["usecache"]

        if len(args)> 0:
            if isinstance(args[0],(int, float, str, list, tuple, dict)):
                key = str(args) + str(kwargs) + func.__name__
            else:
                # 第1个参数以后的内容
                key = str(args[1:]) + str(kwargs) + func.__name__
        else:
            key = str(args) + str(kwargs) + func.__name__

        key_file = os.path.join(cache_path, cal_md5(key) + "_cache.pkl")

        if os.path.exists(key_file) and usecache:
            print(f"缓存命中，读取缓存文件: {key_file}")
            with open(key_file, 'rb') as f:
                result = pickle.load(f)
                return result

        # 使用 `await` 调用异步函数
        result = await func(*args, **kwargs)

        if isinstance(result, tuple) and result[0] == False:
            print(f"函数 {func.__name__} 返回结果为 False, 不缓存")
        else:
            with open(key_file, 'wb') as f:
                pickle.dump(result, f)
            print(f"缓存未命中，结果缓存至文件: {key_file}")

        return result

    return wrapper

def cache_decorator(func):
    """
    cache从文件中读取, 当func中存在usecache时，并且为False时，不使用缓存
    Args:
        func ():
    Returns:
    """
    cache_path = "cache" #cache目录
    if not os.path.exists(cache_path):
        os.mkdir(cache_path)

    @wraps(func)
    def wrapper(*args, **kwargs):
        # 将args和kwargs转换为哈希键， 当装饰类中的函数的时候，args的第一个参数是实例化的类，这会通常导致改变，我们不想检测它是否改变，那么就忽略它
        usecache = kwargs.get("usecache", True)
        if "usecache" in kwargs:
            del kwargs["usecache"]
        if len(args)> 0:
            if isinstance(args[0],(int, float, str, list, tuple, dict)):
                key = str(args) + str(kwargs) + func.__name__
            else:
                # 第1个参数以后的内容
                key = str(args[1:]) + str(kwargs) + func.__name__
        else:
            key = str(args) + str(kwargs) + func.__name__
        # 变成md5字符串
        key_file = os.path.join(cache_path, cal_md5(key) + "_cache.pkl")
        # 如果结果已缓存，则返回缓存的结果
        if os.path.exists(key_file) and usecache:
            # 去掉kwargs中的usecache
            print(f"函数{func.__name__}被调用，缓存被命中，使用已缓存结果，对于参数{key}, 读取文件:{key_file}")
            try:
                with open(key_file, 'rb') as f:
                    result = pickle.load(f)
                    return result
            except Exception as e:
                print(f"函数{func.__name__}被调用，缓存被命中，读取文件:{key_file}失败，错误信息:{e}")
        result = func(*args, **kwargs)
        # 将结果缓存到文件中
        # 如果返回的数据是一个元祖，并且第1个参数是False,说明这个函数报错了，那么就不缓存了是我们自己的一个设定
        if isinstance(result, tuple) and result[0] == False:
            print(f"函数{func.__name__}被调用，返回结果为False，对于参数{key}, 不缓存")
        else:
            with open(key_file, 'wb') as f:
                pickle.dump(result, f)
            print(f"函数{func.__name__}被调用，缓存未命中，结果被缓存，对于参数{key}, 写入文件:{key_file}")
        return result

    return wrapper


if __name__ == "__main__":
    cal_md5("hello")