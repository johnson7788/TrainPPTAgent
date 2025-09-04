# 如何配置和使用自定义模型

本项目通过 [LiteLLM](https://github.com/BerriAI/litellm) 兼容各种开源和商业语言模型。模型的配置分为两个主要部分：**大纲生成** (`simpleOutline`) 和 **内容生成** (`slide_agent`)，它们需要分别进行配置。

## 通用步骤

无论使用哪个厂商的模型，通常都需要：
1.  获取对应厂商的 API Key。
2.  在项目指定目录下的 `.env` 文件中配置该 Key。
3.  修改配置文件，指定要使用的模型。

---

## 1. 大纲生成模型配置 (`simpleOutline`)

此部分用于配置生成演示文稿大纲（Outline）时所使用的模型。

### 配置文件

配置文件位于 `backend/simpleOutline/.env`。如果该文件不存在，请将 `backend/simpleOutline/env_template` 复制一份并重命名为 `.env`。

### 配置方法

在 `.env` 文件中，你需要设置以下两个变量：

*   `MODEL_PROVIDER`: 指定模型提供商。
*   `LLM_MODEL`: 指定具体的模型名称。

同时，你需要确保对应的 API Key 已经配置。

### 各厂商配置示例

下面是不同模型提供商的配置方法。

#### Google Gemini
- **`.env` 配置:**
  ```env
  # 1. 设置 API Key
  GOOGLE_API_KEY=您的Google_API_Key

  # 2. 指定提供商和模型
  MODEL_PROVIDER=google
  LLM_MODEL=gemini-2.0-flash
  ```

#### DeepSeek
- **`.env` 配置:**
  ```env
  # 1. 设置 API Key
  DEEPSEEK_API_KEY=您的DeepSeek_API_Key

  # 2. 指定提供商和模型
  MODEL_PROVIDER=deepseek
  LLM_MODEL=deepseek-chat
  ```

#### 阿里云 (Dashscope)
- **`.env` 配置:**
  ```env
  # 1. 设置 API Key
  ALI_API_KEY=您的阿里云API_Key

  # 2. 指定提供商和模型
  MODEL_PROVIDER=ali
  LLM_MODEL=qwen-turbo
  ```

#### OpenAI
- **`.env` 配置:**
  ```env
  # 1. 设置 API Key
  OPENAI_API_KEY=您的OpenAI_API_Key

  # 2. 指定提供商和模型
  MODEL_PROVIDER=openai
  LLM_MODEL=gpt-4o
  ```

#### Anthropic Claude
- **`.env` 配置:**
  ```env
  # 1. 设置 API Key
  CLAUDE_API_KEY=您的Claude_API_Key

  # 2. 指定提供商和模型
  MODEL_PROVIDER=claude
  LLM_MODEL=claude-3-sonnet-20240229
  ```

#### 豆包 (Volcengine)
- **`.env` 配置:**
  ```env
  # 1. 设置 API Key
  DOUBAO_API_KEY=您的豆包API_Key

  # 2. 指定提供商和模型
  MODEL_PROVIDER=doubao
  LLM_MODEL=Doubao-pro-32k
  ```

#### SiliconFlow
- **`.env` 配置:**
  ```env
  # 1. 设置 API Key
  SILICON_API_KEY=您的SiliconFlow_API_Key

  # 2. 指定提供商和模型
  MODEL_PROVIDER=silicon
  LLM_MODEL=Qwen/Qwen2-7B-Instruct
  ```

#### ModelScope
- **`.env` 配置:**
  ```env
  # 1. 设置 API Key
  MODELSCOPE_API_KEY=您的ModelScope_API_Key

  # 2. 指定提供商和模型
  MODEL_PROVIDER=modelscope
  LLM_MODEL=qwen/qwen-14b-chat
  ```

#### 本地或自托管模型 (Ollama, vLLM等)

对于本地部署的模型，你需要提供服务的 URL。

- **Ollama `.env` 配置:**
  ```env
  # 1. 设置 API Key (通常可随意填写)
  OLLAMA_API_KEY=ollama

  # 2. 提供服务地址
  OLLAMA_API_URL=http://localhost:11434

  # 3. 指定提供商和模型
  MODEL_PROVIDER=ollama
  LLM_MODEL=qwen:7b
  ```

- **vLLM `.env` 配置:**
  ```env
  # 1. 设置 API Key (通常可随意填写)
  VLLM_API_KEY=EMPTY

  # 2. 提供服务地址
  VLLM_API_URL=http://localhost:8000/v1

  # 3. 指定提供商和模型
  MODEL_PROVIDER=vllm
  LLM_MODEL=Qwen/Qwen2-7B-Instruct
  ```

---

## 2. 内容生成模型配置 (`slide_agent`)

此部分用于配置生成每页幻灯片具体内容时所使用的模型。其配置方式与大纲生成不同，分为两步。

### 步骤 1: 配置 API Key

API Key 统一在 `backend/slide_agent/.env` 文件中进行配置。如果该文件不存在，请将 `backend/slide_agent/env_template` 复制一份并重命名为 `.env`。

- **`backend/slide_agent/.env` 示例:**
  ```env
  # 根据您要使用的模型，配置对应的Key
  GOOGLE_API_KEY=xx
  DEEPSEEK_API_KEY=xx
  OPENAI_API_KEY=xx
  CLAUDE_API_KEY=xx
  ALI_API_KEY=sk-xx
  DOUBAO_API_KEY=xx
  SILICON_API_KEY=xx
  MODELSCOPE_API_KEY=xx
  ```

### 步骤 2: 选择模型

直接修改代码文件 `backend/slide_agent/slide_agent/config.py` 来选择模型。该文件中定义了两个 Agent 的配置：
*   `PPT_WRITER_AGENT_CONFIG`: 用于生成幻灯片内容。
*   `PPT_CHECKER_AGENT_CONFIG`: 用于检查和修正内容。

你需要修改文件中的 `provider` 和 `model` 字段。

- **`config.py` 文件修改示例:**

假设你想使用阿里云的 `qwen-max` 模型，你需要修改 `config.py` 如下：

```python
# backend/slide_agent/slide_agent/config.py

# ...

# 对所有的上面的研究员Agent的研究结果写PPT
PPT_WRITER_AGENT_CONFIG = {
    # "provider": "openai",
    # "model": "gpt-4o-2024-08-06",
    # "provider": "google",
    # "model": "gemini-1.5-flash",
    "provider": "ali",         # <--- 修改这里
    "model": "qwen-max",       # <--- 修改这里
}
# 检查每一页的PPT是否符合要求，不符合要求的会被重写
PPT_CHECKER_AGENT_CONFIG = {
    # "provider": "openai",
    # "model": "gpt-4o-2024-08-06",
    # "provider": "google",
    # "model": "gemini-1.5-flash",
    "provider": "ali",         # <--- 修改这里
    "model": "qwen-max",       # <--- 修改这里
}
```

### 各厂商配置速查

| 提供商             | `provider` 值      | `.env` 中所需 Key     | `model` 示例 (在 config.py 中) |
| ------------------ | ------------------ | --------------------- |----------------------------|
| Google Gemini      | `google`           | `GOOGLE_API_KEY`      | `gemini-2.0-flash`         |
| DeepSeek           | `deepseek`         | `DEEPSEEK_API_KEY`    | `deepseek-chat`            |
| 阿里云 (Dashscope) | `ali`              | `ALI_API_KEY`         | `qwen-max`                 |
| OpenAI             | `openai`           | `OPENAI_API_KEY`      | `gpt-4o`                   |
| Anthropic Claude   | `claude`           | `CLAUDE_API_KEY`      | `claude-3-sonnet-20240229` |
| 豆包 (Volcengine)  | `doubao`           | `DOUBAO_API_KEY`      | `Doubao-pro-32k`           |
| SiliconFlow        | `silicon`          | `SILICON_API_KEY`     | `Qwen/Qwen2-7B-Instruct`   |
| ModelScope         | `modelscope`       | `MODELSCOPE_API_KEY`  | `qwen/qwen-14b-chat`       |
| Ollama (本地)      | `ollama`           | `OLLAMA_API_KEY`      | `qwen:7b`                  |
| vLLM (本地)        | `vllm`             | `VLLM_API_KEY`        | `Qwen/Qwen2-7B-Instruct`   |
| 其他本地模型       | `local_openai` 等  | `OPENAI_API_KEY` 等   | `gpt-4.1`                  |

**注意**: 对于 `ollama` 和 `vllm`，除了在 `.env` 中设置对应的 Key 之外，还需要设置 `OLLAMA_API_URL` 或 `VLLM_API_URL`。