#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date  : 2025/6/18 14:44
# @File  : create_model.py.py
# @Author: johnson
# @Contact : github: johnson7788
# @Desc  : little llm 不要设置timeout，超过一定时间会断
import os
import litellm
from google.adk.models.lite_llm import LiteLlm
from dotenv import load_dotenv
# 开启LLM的debug模式
litellm._turn_on_debug()

load_dotenv()
def create_model(model:str, provider: str):
    """
    创建模型，返回字符串或者LiteLlm
    LiteLlm(model="deepseek/deepseek-chat", api_key="xxx", api_base="")
    :return:
    """
    if provider == "google":
        # google的模型直接使用名称
        assert os.environ.get("GOOGLE_API_KEY"), "GOOGLE_API_KEY is not set"
        return model
    elif provider == "claude":
        # Claude 模型需要使用 LiteLlm，并遵循 LiteLLM 的模型命名规范
        assert os.environ.get("CLAUDE_API_KEY"), "CLAUDE_API_KEY is not set"
        # 正确的做法是使用 "claude/" 前缀
        if not model.startswith("anthropic/"):
            model = "anthropic/" + model

        return LiteLlm(
            model=model,  # 例如: "claude/claude-3-opus-20240229"
            api_key=os.environ.get("CLAUDE_API_KEY"),
        )
    elif provider == "openai":
        # openai的模型需要使用LiteLlm
        assert os.environ.get("OPENAI_API_KEY"), "OPENAI_API_KEY is not set"
        if not model.startswith("openai/"):
            # 表示兼容openai的模型请求
            model = "openai/" + model
        return LiteLlm(model=model, api_key=os.environ.get("OPENAI_API_KEY"), api_base="https://api.openai.com/v1")
    elif provider == "deepseek":
        # deepseek的模型需要使用LiteLlm
        assert os.environ.get("DEEPSEEK_API_KEY"),  "DEEPSEEK_API_KEY is not set"
        if not model.startswith("openai/"):
            # 表示兼容openai的模型请求
            model = "openai/" + model
        return LiteLlm(model=model, api_key=os.environ.get("DEEPSEEK_API_KEY"), api_base="https://api.deepseek.com/v1")
    elif provider == "local_google":
        assert os.environ.get("GOOGLE_API_KEY"),  "GOOGLE_API_KEY is not set"
        if not model.startswith("openai/"):
            # 表示兼容openai的模型请求
            model = "openai/" + model
        return LiteLlm(model=model, api_key=os.environ.get("GOOGLE_API_KEY"), api_base="http://localhost:6688")
    elif provider == "local_deepseek":
        # deepseek的模型需要使用LiteLlm
        assert os.environ.get("DEEPSEEK_API_KEY"),  "DEEPSEEK_API_KEY is not set"
        if not model.startswith("openai/"):
            # 表示兼容openai的模型请求
            model = "openai/" + model
        return LiteLlm(model=model, api_key=os.environ.get("DEEPSEEK_API_KEY"), api_base="http://localhost:6688")
    elif provider == "ali":
        # huggingface的模型需要使用LiteLlm
        assert os.environ.get("ALI_API_KEY"), "ALI_API_KEY is not set"
        if not model.startswith("openai/"):
            # 表示兼容openai的模型请求
            model = "openai/" + model
        return LiteLlm(model=model, api_key=os.environ.get("ALI_API_KEY"), api_base="https://dashscope.aliyuncs.com/compatible-mode/v1")
    elif provider == "local_ali":
        assert os.environ.get("ALI_API_KEY"), "ALI_API_KEY is not set"
        if not model.startswith("openai/"):
            # 表示兼容openai的模型请求
            model = "openai/" + model
        return LiteLlm(model=model, api_key=os.environ.get("ALI_API_KEY"), api_base="http://localhost:6688")
    elif provider == "doubao":
        # huggingface的模型需要使用LiteLlm
        assert os.environ.get("DOUBAO_API_KEY"), "DOUBAO_API_KEY is not set"
        if not model.startswith("openai/"):
            # 表示兼容openai的模型请求
            model = "openai/" + model
        return LiteLlm(model=model, api_key=os.environ.get("DOUBAO_API_KEY"), api_base="https://ark.cn-beijing.volces.com/api/v3")
    elif provider == "vllm":
        # huggingface的模型需要使用LiteLlm
        assert os.environ.get("VLLM_API_KEY"), "VLLM_API_KEY is not set"
        assert os.environ.get("VLLM_API_URL"), "VLLM_API_URL is not set"
        if not model.startswith("openai/"):
            # 表示兼容openai的模型请求
            model = "openai/" + model
        return LiteLlm(model=model, api_key=os.environ.get("VLLM_API_KEY"), api_base=os.environ.get("VLLM_API_URL"))
    elif provider == "silicon":
        # huggingface的模型需要使用LiteLlm
        assert os.environ.get("SILICON_API_KEY"), "SILICON_API_KEY is not set"
        if not model.startswith("openai/"):
            # 表示兼容openai的模型请求
            model = "openai/" + model
        return LiteLlm(model=model, api_key=os.environ.get("SILICON_API_KEY"), api_base="https://api.siliconflow.cn/v1")
    elif provider == "ollama":
        # huggingface的模型需要使用LiteLlm
        assert os.environ.get("OLLAMA_API_KEY"), "OLLAMA_API_KEY is not set"
        assert os.environ.get("OLLAMA_API_URL"), "OLLAMA_API_URL is not set"
        if not model.startswith("openai/"):
            # 表示兼容openai的模型请求
            model = "openai/" + model
        return LiteLlm(model=model, api_key=os.environ.get("OLLAMA_API_KEY"), api_base=os.environ.get("OLLAMA_API_URL"))
    elif provider == "local_openai":
        assert os.environ.get("OPENAI_API_KEY"), "OPENAI_API_KEY is not set"
        if not model.startswith("openai/"):
            # 表示兼容openai的模型请求
            model = "openai/" + model
        return LiteLlm(model=model, api_key=os.environ.get("OPENAI_API_KEY"), api_base="http://localhost:6688")
    else:
        raise ValueError(f"Unsupported provider: {provider}")
