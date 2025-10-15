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

    def insert_file_vectors(self, file_name:str, user_id: int|str, file_id: int, file_type: str, url: str, folder_id: int, documents: List[str]):
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
        # 首先删除已有存在的相同文件
        del_status = self.delete_file_vectors(user_id, file_id)
        # 然后插入新的向量
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

    def list_files_by_user(self, user_id: int) -> List[Dict[str, Any]]:
        """
        根据用户ID列出该用户的所有文件信息
        Args:
            user_id (int): 用户ID
        Returns:
            List[Dict[str, Any]]: 文件信息列表
        """
        try:
            collection_name = f"user_{user_id}"
            # 确认集合存在
            collections = self.list_exist_collections()
            if collection_name not in collections:
                logger.warning(f"集合 {collection_name} 不存在，用户 {user_id} 没有任何文件。")
                return []

            col = self.client.get_collection(collection_name)

            # 获取所有与该用户ID相关的文档元数据
            # 注意：get()方法在没有where条件时返回所有文档，数据量可能很大
            # 但由于我们是按用户集合来操作的，所以这里获取的是该用户的所有数据
            results = col.get()

            metadatas = results.get('metadatas', [])

            # 文件信息可能重复，需要去重
            unique_files = {}
            for meta in metadatas:
                # 确保meta是字典且包含file_id
                if isinstance(meta, dict) and 'file_id' in meta:
                    file_id = meta.get('file_id')
                    # 过滤掉无效的file_id
                    if file_id is None:
                        continue

                    # 检查用户ID是否匹配
                    if meta.get('user_id') == user_id:
                        if file_id not in unique_files:
                            unique_files[file_id] = {
                                "file_id": file_id,
                                "file_name": meta.get('file_name'),
                                "file_type": meta.get('file_type'),
                                "url": meta.get('url'),
                                "folder_id": meta.get('folder_id'),
                                "user_id": meta.get('user_id')
                            }

            return list(unique_files.values())
        except Exception as e:
            # 如果collection不存在或其他异常
            logger.error(f"为用户 {user_id} 列出文件失败: {str(e)}", exc_info=True)
            return []

    def list_exist_collections(self):
        """
        列出所有已有的collections
        Returns:
        """
        collections_info = self.client.list_collections()
        collections = [i.name for i in collections_info]
        return collections

class EmbeddingModel(object):
    def __init__(self):
        """
        环境变量：
        - EMBEDDING_PROVIDER: aliyun | ollama | vllm | xinference
        - EMBEDDING_MODEL:    各提供方的模型名
        - 通用：EMBEDDING_DIM (可选，部分提供方不支持自定义维度)
        - aliyun:   ALI_API_KEY
        - doubao:   DOUBAO_API_KEY
        - vllm:     VLLM_BASE_URL(如 http://127.0.0.1:8000/v1)，VLLM_API_KEY(可选)
        - xinference:XINFERENCE_BASE_URL(如 http://127.0.0.1:9997/v1)，XINFERENCE_API_KEY(可选)
        - ollama:   OLLAMA_BASE_URL(默认 http://127.0.0.1:11434)
        """
        self.model = os.environ["EMBEDDING_MODEL"]
        self.provider = os.environ["EMBEDDING_PROVIDER"].lower()
        self.dimensions = int(os.getenv("EMBEDDING_DIM", "0")) or None

        if self.provider == "aliyun":
            api_key = os.getenv("ALI_API_KEY")
            assert api_key, "ALI_API_KEY没有设置，无法使用阿里云嵌入模型"
            self.client = OpenAI(
                api_key=api_key,
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            )
            self._impl = self._impl_openai_compatible  # 走OpenAI兼容
        elif self.provider == "doubao":
            api_key = os.getenv("DOUBAO_API_KEY")
            assert api_key, "DOUBAO_API_KEY没有设置，无法使用阿里云嵌入模型"
            self.client = OpenAI(
                api_key=api_key,
                base_url="https://ark.cn-beijing.volces.com/api/v3",
            )
            self._impl = self._impl_openai_compatible  # 走OpenAI兼容
        elif self.provider == "vllm":
            base = os.getenv("VLLM_BASE_URL")
            assert base, "VLLM_BASE_URL 未设置，例如 http://127.0.0.1:8000/v1"
            self.client = OpenAI(
                api_key=os.getenv("VLLM_API_KEY", "EMPTY"),  # 有些部署不校验
                base_url=base.rstrip("/"),
            )
            self._impl = self._impl_openai_compatible  # vLLM自带OpenAI兼容
        elif self.provider == "xinference":
            base = os.getenv("XINFERENCE_BASE_URL")
            assert base, "XINFERENCE_BASE_URL 未设置，例如 http://127.0.0.1:9997/v1"
            self.client = OpenAI(
                api_key=os.getenv("XINFERENCE_API_KEY", "EMPTY"),
                base_url=base.rstrip("/"),
            )
            self._impl = self._impl_openai_compatible  # Xinference也提供OpenAI兼容
        elif self.provider == "ollama":
            # 使用Ollama原生 /api/embeddings，兼容性最稳妥
            self.ollama_base = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
            self.session = requests.Session()
            self._impl = self._impl_ollama_native
        else:
            raise Exception(f"不支持的EMBEDDING_PROVIDER: {self.provider}")

    @cache_decorator
    def do_embedding(self, texts: List[str]):
        """
        对数据进行embedding。返回：{"data":[{"embedding":[...]}, ...]}
        """
        assert isinstance(texts, list) and all(isinstance(t, str) for t in texts), "texts必须为字符串列表"
        max_batch_size = 10  # 可根据不同后端调整
        result = {"data": []}
        for i in range(0, len(texts), max_batch_size):
            batch = texts[i:i + max_batch_size]
            try:
                batch_out = self._impl(batch)
                # 规范化为 {"data":[{"embedding":[...]}...]}
                if isinstance(batch_out, dict) and "data" in batch_out:
                    result["data"].extend(batch_out["data"])
                else:
                    # 兜底：如果只是返回了向量列表
                    result["data"].extend([{"embedding": emb} for emb in batch_out])
                logger.info(f"成功嵌入批次 {i // max_batch_size + 1}，包含 {len(batch)} 个文本")
            except Exception as e:
                logger.error(f"嵌入批次 {i // max_batch_size + 1} 失败: {e}", exc_info=True)
        logger.info(f"所有 {len(texts)} 个文本嵌入完成")
        return result

    # ---------- 各提供方实现 ----------
    def _impl_openai_compatible(self, texts: List[str]):
        """
        适用于：阿里云(百炼兼容)、vLLM、Xinference等OpenAI兼容服务
        注意：有些后端不支持dimensions；不支持时自动忽略
        """
        kwargs = {"model": self.model, "input": texts}
        # 尝试传维度；如后端不支持则自动降级
        if self.dimensions:
            kwargs["dimensions"] = self.dimensions
        try:
            resp = self.client.embeddings.create(**kwargs)
        except Exception as e:
            # 如果是因不支持dimensions导致，去掉维度再试一次
            if self.dimensions:
                logger.warning(f"后端可能不支持自定义维度，去掉dimensions重试。错误：{e}")
                kwargs.pop("dimensions", None)
                resp = self.client.embeddings.create(**kwargs)
            else:
                raise
        # 统一输出格式
        out = resp.dict()
        # 有些实现不会返回encoding_format/等字段，不影响
        return {"data": [{"embedding": item["embedding"]} for item in out["data"]]}

    def _impl_ollama_native(self, texts: List[str]):
        """
        适用于Ollama原生接口：POST {OLLAMA_BASE_URL}/api/embeddings
        body: {"model": "...", "prompt": "..."}
        不支持批量输入 => 逐条请求
        """
        url = f"{self.ollama_base}/api/embeddings"
        data = []
        for t in texts:
            payload = {"model": self.model, "prompt": t}
            r = self.session.post(url, json=payload, timeout=120)
            if r.status_code != 200:
                raise RuntimeError(f"Ollama embeddings失败: {r.status_code} {r.text}")
            j = r.json()
            # 返回形如 {"embedding":[...]}
            data.append({"embedding": j.get("embedding")})
        return {"data": data}


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

