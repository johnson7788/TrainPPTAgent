#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date  : 2023/7/5 10:44
# @File  : embedding_api.py
# @Author:
# @Desc  : 对于给定的内容进行Embedding

import os
from typing import Any, Dict, List, Optional
import time
import copy
import json
import logging
import requests
import numpy as np
import pickle
import hashlib
from functools import wraps
import string
import chromadb  #pip install chromadb
from chromadb.config import Settings
from openai import OpenAI
from dotenv import load_dotenv
# 加载环境变量
load_dotenv()


logger = logging.getLogger(__name__)

def cal_md5(content):
    """
    计算content字符串的md5
    :param content:
    :return:
    """
    # 使用encode
    content = str(content)
    result = hashlib.md5(content.encode())
    # 打印hash
    md5 = result.hexdigest()
    return md5


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
                key = str(args) + str(kwargs)
            else:
                # 第1个参数以后的内容
                key = str(args[1:]) + str(kwargs)
        else:
            key = str(args) + str(kwargs)
        # 变成md5字符串
        key_file = os.path.join(cache_path, cal_md5(key) + "_cache.pkl")
        # 如果结果已缓存，则返回缓存的结果
        if os.path.exists(key_file) and usecache:
            # 去掉kwargs中的usecache
            print(f"函数{func.__name__}被调用，缓存被命中，使用已缓存结果，对于参数{key}")
            try:
                with open(key_file, 'rb') as f:
                    result = pickle.load(f)
                    return result
            except Exception as e:
                print(f"函数{func.__name__}被调用，缓存被命中，读取文件:{key_file}失败，错误信息:{e}")
        result = func(*args, **kwargs)
        # 将结果缓存到文件中
        # 如果返回的数据是一个元祖，并且第1个参数是False,说明这个函数报错了，那么就不缓存了，这是我们自己的一个设定
        if isinstance(result, tuple) and result[0] == False:
            print(f"函数{func.__name__}被调用，返回结果为False，对于参数{key}, 不缓存")
        else:
            with open(key_file, 'wb') as f:
                pickle.dump(result, f)
            print(f"函数{func.__name__}被调用，缓存未命中，结果被缓存，对于参数{key}, 写入文件:{key_file}")
        return result

    return wrapper


class ChromaDB(object):
    def __init__(self, embedder, db_dir="cache/chromadb"):
        """
        Args:
            embedder: 实例化后的embedding
            chromadb的相关操作
        """
        # 目前支持的模型,
        self.embedder = embedder
        if not os.path.exists(db_dir):
            os.makedirs(db_dir)
        self.client = chromadb.PersistentClient(path=db_dir, settings=Settings(anonymized_telemetry=False))

    def delete_one_collection(self, collection):
        """
        删除1个collection
        Args:
            collection ():
        Returns:
        """
        try:
            self.client.delete_collection(name=collection)
        except Exception as e:
            print(f"删除collection:{collection}失败，错误信息:{e}")
            return "fail"
        return "success"

    def delete_one_document(self, collection, doc_id):
        """
        删除指定集合中的一条数据（根据 ID），并验证是否删除成功。
        Args:
            collection (str): 集合名称。
            doc_id (str): 要删除的文档 ID。
        Returns:
            str: "success" 表示删除成功，"fail" 表示失败。
        """
        try:
            col = self.client.get_or_create_collection(collection)
            # 删除指定 ID 的文档
            col.delete(ids=[doc_id])
            print(f"尝试删除集合 '{collection}' 中的文档 ID '{doc_id}'。")

            # 验证是否删除成功：查询该 ID，如果结果为空，则成功
            check_result = col.get(ids=[doc_id])
            if not check_result['ids']:  # 如果 IDs 列表为空，说明已删除
                print(f"验证成功：集合 '{collection}' 中的文档 ID '{doc_id}' 已删除。")
                return "success"
            else:
                print(f"验证失败：集合 '{collection}' 中的文档 ID '{doc_id}' 仍存在。")
                return "fail"
        except Exception as e:
            print(f"删除集合 '{collection}' 中的文档 ID '{doc_id}' 失败，错误信息: {e}")
            return "fail"



    def insert2collection(self, collection, documents, meta=None):
        """
        Args:
            collection ():
            documents: list[str]
            meta: 插入collection的meta信息, list[]
        Returns:
        """
        col = self.client.get_or_create_collection(collection, metadata={"hnsw:space": "cosine"})
        vectors_result = self.embedder.do_embedding(documents)
        vectors = vectors_result["data"]
        embeddings = [one["embedding"] for one in vectors]
        col.add(
            embeddings=embeddings,
            documents=documents,
            metadatas=meta,
            ids=[str(i) for i in range(len(documents))]
        )
        return "success"

    def query2collection(self, collection, query_documents, keyword="", topk=3):
        """
        查询向量，混合搜索
        Args:
            collection ():
            query_documents (): list[str]
            keyword: 是否同时对documents执行关键字搜索
        Returns:
        """
        col = self.client.get_or_create_collection(collection)
        vectors_result = self.embedder.do_embedding(texts=query_documents)
        vectors = vectors_result["data"]
        embeddings = [one["embedding"] for one in vectors]
        if keyword:
            query_result = col.query(
                query_embeddings=embeddings,
                n_results=topk,
                where_document={"$contains": keyword},
                include=["metadatas", "documents", "distances"]
            )
        else:
            query_result = col.query(
                query_embeddings=embeddings,
                n_results=topk,
                include=["metadatas", "documents", "distances"]
            )
        return query_result


    def delete_file_vectors(self, user_id: int, file_id: int):
        """
        根据用户ID和文件ID删除对应的向量
        Args:
            user_id (int): 用户ID
            file_id (int): 文件ID
        Returns:
            str: "success" 表示删除成功，"fail" 表示失败
        """
        try:
            collection_name = f"user_{user_id}"
            col = self.client.get_or_create_collection(collection_name)
            col.delete(where={"file_id": file_id})
            logger.info(f"成功删除用户 {user_id} 的文件 {file_id} 对应的向量")
            return "success"
        except Exception as e:
            logger.error(f"删除用户 {user_id} 的文件 {file_id} 向量失败: {str(e)}", exc_info=True)
            return "fail"

    def insert_file_vectors(self, file_name:str, user_id: int, file_id: int, file_type: str, url: str, folder_id: int, documents: List[str]):
        """
        将文件内容插入到ChromaDB中，生成并存储embedding向量
        Args:
            file_name: file_name, 文件名称
            user_id (int): 用户ID
            file_id (int): 文件ID
            file_type (str): 文件类型
            url (str): 文件URL
            folder_id (int): 文件夹ID
            documents (List[str]): 文件内容列表
        Returns:
            dict: 包含embedding结果
        """
        try:
            collection_name = f"user_{user_id}"
            vectors_result = self.embedder.do_embedding(texts=documents)
            vectors = vectors_result["data"]
            embeddings = [one["embedding"] for one in vectors]
            meta = [{"file_name": file_name,"file_id": file_id, "user_id": user_id, "folder_id": folder_id, "url": url, "file_type": file_type} for _ in documents]
            ids = [f"{file_id}_{i}" for i in range(len(documents))]
            col = self.client.get_or_create_collection(collection_name, metadata={"hnsw:space": "cosine"})
            col.add(
                embeddings=embeddings,
                documents=documents,
                metadatas=meta,
                ids=ids
            )
            logger.info(f"成功插入文件 {file_id} 的向量到集合 {collection_name}")
            return vectors_result
        except Exception as e:
            logger.error(f"插入用户 {user_id} 的文件 {file_id} 向量失败: {str(e)}", exc_info=True)
            raise ValueError(f"插入向量失败: {str(e)}")



    def list_collection(self, collection, number=100):
        """
        列出某个集后的内容
        Returns:
        """
        col = self.client.get_or_create_collection(collection)
        data = col.peek(number)
        total = col.count()
        result = {
            "data": data,
            "number": number,
            "total": total
        }
        return result

    def list_exist_collections(self):
        """
        列出所有已有的collections
        Returns:
        """
        collections_info = self.client.list_collections()
        collections = [i.name for i in collections_info]
        return collections

class EmbeddingModel(object):
    def __init__(self, model="text-embedding-v4", provider="aliyun"):
        """
        Args:
        """
        self.model = model
        self.provider = provider
        if provider == "aliyun":
            api_key = os.getenv("ALI_API_KEY")
            assert api_key, "ALI_API_KEY没有设置，无法使用嵌入模型"
            self.client = OpenAI(
                api_key=api_key,  # 如果您没有配置环境变量，请在此处用您的API Key进行替换
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"  # 百炼服务的base_url
            )
        else:
            raise Exception("目前只支持阿里云的模型")

    @cache_decorator
    def do_embedding(self, texts: list[str]):
        """
        对数据进行embedding，处理批量大小限制，确保所有文本都被处理
        Args:
            texts: 数据，为一个list，每个元素为一个字符串
        Returns:
            dict: 包含所有输入文本的embedding结果
        """
        max_batch_size = 10  # 最大批量大小限制 避免报错
        result = {"data": []}  # 用于收集所有批次的嵌入结果

        # 循环处理所有文本，分割成批次
        for i in range(0, len(texts), max_batch_size):
            batch_texts = texts[i:i + max_batch_size]  # 取当前批次（最多10个）
            try:
                completion = self.client.embeddings.create(
                    model=self.model,
                    input=batch_texts,
                    dimensions=1024,
                    encoding_format="float"
                )
                batch_result = completion.dict()
                result["data"].extend(batch_result["data"])  # 合并当前批次的嵌入结果
                logger.info(f"成功嵌入批次 {i // max_batch_size + 1}，包含 {len(batch_texts)} 个文本")
            except Exception as e:
                logger.error(f"嵌入批次 {i // max_batch_size + 1} 失败: {e}")
                # 如果需要，可以在这里返回错误，但为了继续处理，我们只记录日志
                # 如果想在出错时停止，可以 raise e 或返回 {"error": str(e), "data": []}

        logger.info(f"所有 {len(texts)} 个文本嵌入完成")
        return result

if __name__ == '__main__':
    embedder = EmbeddingModel()
    chromadb_instance = ChromaDB(embedder=embedder)
    # 列出所有已有的collections
    print(chromadb_instance.list_exist_collections())
    # 列出collection的内容
    collection="test"
    number = 3
    print(chromadb_instance.list_collection(collection, number))
    query_documents = ["hello", "world"]
    keyword = "yes"
    result = chromadb_instance.query2collection(collection, query_documents, keyword=keyword,topk=3)
    documents = ["hello", "world"]
    result = chromadb_instance.insert2collection(collection, documents, meta=[])

    result = chromadb_instance.delete_one_collection(collection)

    # doc_id = "0"  # 假设您要删除 ID 为 "0" 的文档
    # result = chromadb_instance.delete_one_document(collection, doc_id)
    # print(f"删除结果: {result}")

