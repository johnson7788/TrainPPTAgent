# 🧠 TrainPPTAgent 自动生成 PPT 内容

本项目基于多智能体（Multi-Agent）协作架构，实现从内容大纲出发，自动完成主题拆解、信息调研与汇总生成 PPT 内容的流程。

---

## 🔧 核心功能模块

| Agent 名称                | 功能描述                   |
|-------------------------|------------------------|
| `split_outline_agent`   | 将输入的大纲内容拆解为每页的ppt要写的内容 |
| `ppt_generator_loop_agent`  | 为每页ppt的大纲生成ppt的内容      |

---

## 🚀 快速开始

---

### 1. 修改 Agent 使用的模型

编辑模型配置文件以自定义每个 Agent 所调用的模型（如 GPT-4、Claude、Gemini 等）：

```python
# 配置模型的路径
backend/slide_agent/slide_agent/config.py
```

---

### 2. 启动本地测试

直接运行多智能体流程测试：

```bash
python main.py
```

---

### 3. 启动后端 API 服务（供前端调用）

提供标准 API 接口（支持 SSE 流式返回），供前端请求：

```bash
python main_api.py
```

## 注意需要修改tools.py中的搜索引擎
slide_agent/sub_agents/research_topic/tools.py

## 传入不同的metadata使用不同的搜索和不同的prompt
详细参考a2a_client.py中metada信息和slide_agent/slide_agent/sub_agents/ppt_writer/agent.py中的函数_get_dynamic_instruction

'metadata': {"user_id": "123456", "search_engine": ["KnowledgeBaseSearch","SearchImage"]}

| 最终 `search_engine` 内容           | 选用的前缀提示词                                                          | 额外强制要求                            |
| ------------------------------- | ----------------------------------------------------------------- | --------------------------------- |
| 空（无可用工具）                        | `PREFIX_PAGE_PROMPT`                                              | 不带搜索、不带图片                         |
| 仅为 `["SearchImage"]`            | `PREFIX_PAGE_PROMPT_WITH_IMAGE`                                   | 必须为每页搜索并填充配图，JSON 中新增 `images` 字段 |
| 其他任意非空组合（如只文档搜索、或文档+图片、或含 KB 等） | `PREFIX_PAGE_PROMPT_WITH_SEARCH.format(tool_names=search_engine)` | **必须**使用列出的工具做搜索后再写内容             |


---

## 📁 项目结构简要说明

```text
.
├── README.md                    # 使用说明文档
├── __init__.py                 # 包初始化文件
├── a2a_client.py               # 示例客户端，用于测试向 Agent 发送请求
├── adk_agent_executor.py       # 基于 ADK 的 Agent 调度执行器
├── api.log                     # 接口运行日志文件
├── env_example                 # 环境变量模板文件（用于创建 .env）
├── main.py                     # 本地测试入口，运行完整 Agent 流程
├── main_api.py                 # 提供 HTTP/SSE API 的主程序（供前端调用）
├── pyproject.toml              # Python 项目配置文件（依赖与构建）
└── slide_agent/                # 多 Agent 核心逻辑目录
    ├── __init__.py
    ├── agent.py                # 核心 Agent 管理逻辑（注册与调度）
    ├── agent_utils.py          # Agent 辅助工具函数（如日志、格式转换等）
    ├── config.py               # Agent 配置文件（模型参数、Agent 路由等）
    ├── create_model.py         # 创建和初始化模型实例
    └── sub_agents/             # 各子任务的智能体模块
        ├── __init__.py
        ├── research_topic/     # 研究任务 Agent：对主题进行调研并提取信息
        │   ├── agent.py        # Research Agent 主体
        │   ├── prompt.py       # Research Agent 使用的提示词模板
        │   ├── tools.py        # 调研用工具函数（如搜索、摘要等）
        │   └── mcpserver/
        │       ├── research_tool.py  # MCP 工具包装，用于调研时调用，暂时未使用
        ├── split_topic/        # 拆分任务 Agent：将大纲拆分为多个主题
        │   ├── agent.py
        │   └── prompt.py
        └── summary_writer/     # 汇总任务 Agent：汇总多个研究结果生成PPT内容
            ├── agent.py
            └── prompt.py

```



## 📊 并发的多Agent的协作流程
```mermaid
flowchart TD
    A[大纲生成 Agent<br>根据用户需求生成初步内容大纲] --> B[Topic 拆分 Agent<br>将大纲细分为多个主题]
    B --> C1[Research Agent 1<br>对主题 1 调研]
    B --> C2[Research Agent 2<br>对主题 2 调研]
    B --> C3[Research Agent N<br>对主题 N 调研]
    C1 --> D[Summary Agent 汇总输出<br>整合调研结果生成 PPT 内容]
    C2 --> D
    C3 --> D
    D --> E[实时流式返回前端]
```

## a2a_client.py 客户端测试
输出结果:
```
/Users/admin/miniforge3/envs/multiagent/bin/python3.12 /Users/admin/git/MultiAgentPPT/backend/slide_agent/a2a_client.py 

```

## 注意：
main_api.py服务器部署时的agent_url，是对外提供服务的url，有时可能和监听地址不同，尤其是内外网环境时。

