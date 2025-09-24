"""
LLM管理器 - 处理不同LLM提供商的配置和初始化
"""

import os
from typing import Optional, Dict, Any
import logging
from langchain_core.language_models.chat_models import BaseChatModel

logger = logging.getLogger(__name__)


class LLMManager:
    """LLM管理器，支持多种LLM提供商"""
    
    SUPPORTED_PROVIDERS = {
        "openai": "langchain_openai",
        "anthropic": "langchain_anthropic",
        "azure": "langchain_openai",
        "ollama": "langchain_ollama",
        "gemini": "langchain_google_genai",
        "google": "langchain_google_genai",  # Alias for gemini
    }
    
    SUPPORTED_MODELS = {
        "openai": [
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4-turbo",
            "gpt-4",
            "gpt-3.5-turbo",
        ],
        "anthropic": [
            "claude-3-5-sonnet-20241022",
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307",
        ],
        "azure": [
            "gpt-4o",
            "gpt-4",
            "gpt-35-turbo",
        ],
        "ollama": [
            "llama3.2",
            "llama3.1",
            "llama3",
            "llama2",
            "mistral",
            "codellama",
            "qwen2.5",
            "qwen2",
            "gemma2",
            "phi3",
        ],
        "gemini": [
            "gemini-1.5-pro",
            "gemini-1.5-flash",
            "gemini-1.0-pro",
            "gemini-pro-vision",
        ],
        "google": [  # Alias for gemini
            "gemini-1.5-pro",
            "gemini-1.5-flash",
            "gemini-1.0-pro",
            "gemini-pro-vision",
        ],
    }
    
    def __init__(self):
        self._llm_cache: Dict[str, BaseChatModel] = {}
    
    def get_llm(
        self,
        model: str = "gpt-4o-mini",
        provider: str = "openai",
        temperature: float = 0.7,
        max_tokens: int = 4000,
        **kwargs
    ) -> BaseChatModel:
        """
        获取LLM实例
        
        Args:
            model: 模型名称
            provider: 提供商名称
            temperature: 温度参数
            max_tokens: 最大token数
            **kwargs: 其他参数
            
        Returns:
            LLM实例
            
        Raises:
            ValueError: 不支持的提供商或模型
            ImportError: 缺少必要的依赖
        """
        cache_key = f"{provider}:{model}:{temperature}:{max_tokens}"
        
        if cache_key in self._llm_cache:
            return self._llm_cache[cache_key]
        
        if provider not in self.SUPPORTED_PROVIDERS:
            raise ValueError(f"不支持的提供商: {provider}. 支持的提供商: {list(self.SUPPORTED_PROVIDERS.keys())}")
        
        if model not in self.SUPPORTED_MODELS.get(provider, []):
            logger.info(f"提供商: {provider} 模型: {model}")
        
        llm = self._create_llm(provider, model, temperature, max_tokens, **kwargs)
        self._llm_cache[cache_key] = llm
        
        return llm
    
    def _create_llm(
        self,
        provider: str,
        model: str,
        temperature: float,
        max_tokens: int,
        **kwargs
    ) -> BaseChatModel:
        """创建LLM实例"""
        
        if provider == "openai":
            return self._create_openai_llm(model, temperature, max_tokens, **kwargs)
        elif provider == "anthropic":
            return self._create_anthropic_llm(model, temperature, max_tokens, **kwargs)
        elif provider == "azure_openai":
            return self._create_azure_llm(model, temperature, max_tokens, **kwargs)
        elif provider == "ollama":
            return self._create_ollama_llm(model, temperature, max_tokens, **kwargs)
        elif provider == "google":
            return self._create_gemini_llm(model, temperature, max_tokens, **kwargs)
        elif provider == "gemini":
            return self._create_gemini_llm(model, temperature, max_tokens, **kwargs)
        else:
            raise ValueError(f"不支持的提供商: {provider}")
    
    def _create_openai_llm(
        self,
        model: str,
        temperature: float,
        max_tokens: int,
        **kwargs
    ) -> BaseChatModel:
        """创建OpenAI LLM"""
        try:
            from langchain_openai import ChatOpenAI
        except ImportError:
            raise ImportError("请安装 langchain-openai: pip install langchain-openai")

        api_key = kwargs.get("api_key") or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("未找到OpenAI API密钥。请设置OPENAI_API_KEY环境变量或传递api_key参数")

        # 处理自定义base_url
        base_url = kwargs.get("base_url") or os.getenv("OPENAI_BASE_URL")

        # 构建参数
        openai_kwargs = {
            "model": model,
            "temperature": temperature,
            # "max_tokens": max_tokens,
            "api_key": api_key,
        }

        # 添加base_url（如果提供）
        if base_url:
            openai_kwargs["base_url"] = base_url
            logger.info(f"使用自定义OpenAI端点: {base_url}")

        # 添加其他参数（排除已处理的）
        excluded_keys = {"api_key", "base_url"}
        openai_kwargs.update({k: v for k, v in kwargs.items() if k not in excluded_keys})

        return ChatOpenAI(**openai_kwargs)
    
    def _create_anthropic_llm(
        self,
        model: str,
        temperature: float,
        max_tokens: int,
        **kwargs
    ) -> BaseChatModel:
        """创建Anthropic LLM"""
        try:
            from langchain_anthropic import ChatAnthropic
        except ImportError:
            raise ImportError("请安装 langchain-anthropic: pip install langchain-anthropic")
        
        api_key = kwargs.get("api_key") or os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("未找到Anthropic API密钥。请设置ANTHROPIC_API_KEY环境变量或传递api_key参数")
        
        return ChatAnthropic(
            model=model,
            temperature=temperature,
            # max_tokens=max_tokens,
            api_key=api_key,
            **{k: v for k, v in kwargs.items() if k != "api_key"}
        )
    
    def _create_azure_llm(
        self,
        model: str,
        temperature: float,
        max_tokens: int,
        **kwargs
    ) -> BaseChatModel:
        """创建Azure OpenAI LLM"""
        try:
            from langchain_openai import AzureChatOpenAI
        except ImportError:
            raise ImportError("请安装 langchain-openai: pip install langchain-openai")
        
        api_key = kwargs.get("api_key") or os.getenv("AZURE_OPENAI_API_KEY")
        azure_endpoint = kwargs.get("azure_endpoint") or os.getenv("AZURE_OPENAI_ENDPOINT")
        api_version = kwargs.get("api_version") or os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
        
        if not api_key:
            raise ValueError("未找到Azure OpenAI API密钥。请设置AZURE_OPENAI_API_KEY环境变量")
        if not azure_endpoint:
            raise ValueError("未找到Azure OpenAI端点。请设置AZURE_OPENAI_ENDPOINT环境变量")
        
        return AzureChatOpenAI(
            deployment_name=model,
            temperature=temperature,
            # max_tokens=max_tokens,
            api_key=api_key,
            azure_endpoint=azure_endpoint,
            api_version=api_version,
            **{k: v for k, v in kwargs.items() if k not in ["api_key", "azure_endpoint", "api_version"]}
        )

    def _create_ollama_llm(
        self,
        model: str,
        temperature: float,
        max_tokens: int,
        **kwargs
    ) -> BaseChatModel:
        """创建Ollama LLM"""
        try:
            from langchain_ollama import ChatOllama
        except ImportError:
            raise ImportError("请安装 langchain-ollama: pip install langchain-ollama")

        # Ollama默认运行在本地，可以通过base_url自定义
        base_url = kwargs.get("base_url") or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

        # 构建参数
        ollama_kwargs = {
            "model": model,
            "temperature": temperature,
            # "num_predict": max_tokens,  # Ollama使用num_predict而不是max_tokens
            "base_url": base_url,
        }

        # 添加其他参数（排除已处理的）
        excluded_keys = {"base_url", "max_tokens"}
        ollama_kwargs.update({k: v for k, v in kwargs.items() if k not in excluded_keys})

        logger.info(f"使用Ollama端点: {base_url}")
        return ChatOllama(**ollama_kwargs)

    def _create_gemini_llm(
        self,
        model: str,
        temperature: float,
        max_tokens: int,
        **kwargs
    ) -> BaseChatModel:
        """创建Google Gemini LLM"""
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
        except ImportError:
            raise ImportError("请安装 langchain-google-genai: pip install langchain-google-genai")

        api_key = kwargs.get("api_key") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("未找到Google API密钥。请设置GOOGLE_API_KEY环境变量或传递api_key参数")

        # 构建参数
        gemini_kwargs = {
            "model": model,
            "temperature": temperature,
            # "max_output_tokens": max_tokens,  # Gemini使用max_output_tokens
            "google_api_key": api_key,
        }

        # 添加其他参数（排除已处理的）
        excluded_keys = {"api_key", "max_tokens"}
        gemini_kwargs.update({k: v for k, v in kwargs.items() if k not in excluded_keys})

        return ChatGoogleGenerativeAI(**gemini_kwargs)
    
    def validate_configuration(self, provider: str, **kwargs) -> bool:
        """
        验证LLM配置是否正确
        
        Args:
            provider: 提供商名称
            **kwargs: 配置参数
            
        Returns:
            配置是否有效
        """
        try:
            if provider == "openai":
                api_key = kwargs.get("api_key") or os.getenv("OPENAI_API_KEY")
                return bool(api_key)
            elif provider == "anthropic":
                api_key = kwargs.get("api_key") or os.getenv("ANTHROPIC_API_KEY")
                return bool(api_key)
            elif provider == "azure_openai":
                api_key = kwargs.get("api_key") or os.getenv("AZURE_OPENAI_API_KEY")
                endpoint = kwargs.get("azure_endpoint") or os.getenv("AZURE_OPENAI_ENDPOINT")
                return bool(api_key and endpoint)
            elif provider == "ollama":
                # Ollama通常不需要API密钥，只需要确保服务可访问
                base_url = kwargs.get("base_url") or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
                return bool(base_url)
            elif provider == "google" or provider == "gemini":
                api_key = kwargs.get("api_key") or os.getenv("GOOGLE_API_KEY")
                return bool(api_key)
            else:
                return False
        except Exception:
            return False
    
    def list_available_models(self, provider: str) -> list:
        """
        列出指定提供商的可用模型
        
        Args:
            provider: 提供商名称
            
        Returns:
            可用模型列表
        """
        return self.SUPPORTED_MODELS.get(provider, [])
    
    def clear_cache(self):
        """清空LLM缓存"""
        self._llm_cache.clear()
