import os
import random

from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmRequest, LlmResponse
from google.adk.tools.tool_context import ToolContext
from google.adk.tools import BaseTool
from typing import Dict, List, Any, AsyncGenerator, Optional, Union
from create_model import create_model
from tools import DocumentSearch
from dotenv import load_dotenv
load_dotenv()

instruction = """
根据用户的描述生成大纲。首先使用DocumentSearch进行一些关键词搜索，然后按下面的格式生成大纲，仅生成大纲即可，无需多余说明。
输出格式与规则（严格遵守）：
- 使用Markdown标题层级：# 标题 → ## 一级部分 → ### 二级小节 → 列表要点
- 一级部分数量：5个；每个一级部分下含3–4个二级小节
- 每个二级小节列出3–5个要点；要点使用短句，动词开头，不超过18字，不要句号
- 全文不写引言/结语/目录，不写解释性段落，不加任何额外说明
- 术语统一、风格一致，必要时加入可量化指标或示例
- 语言：简体中文

输出示例格式如下：
# 标题

## 一级部分
### 二级小节
- 要点1
- 要点2
- 要点3

### 二级小节
- 要点1
- 要点2
- 要点3
- 要点4
- 要点5
"""

model = create_model(model=os.environ["LLM_MODEL"], provider=os.environ["MODEL_PROVIDER"])

def before_model_callback(callback_context: CallbackContext, llm_request: LlmRequest) -> Optional[LlmResponse]:
    # 1. 检查用户输入
    agent_name = callback_context.agent_name
    history_length = len(llm_request.contents)
    metadata = callback_context.state.get("metadata")
    print(f"调用了{agent_name}模型前的callback, 现在Agent共有{history_length}条历史记录,metadata数据为：{metadata}")
    #清空contents,不需要上一步的拆分topic的记录, 不能在这里清理，否则，每次调用工具都会清除记忆，白操作了
    # llm_request.contents.clear()
    # 返回 None，继续调用 LLM
    return None
def after_model_callback(callback_context: CallbackContext, llm_response: LlmResponse) -> Optional[LlmResponse]:
    # 1. 检查用户输入，注意如果是llm的stream模式，那么response_data的结果是一个token的结果，还有可能是工具的调用
    agent_name = callback_context.agent_name
    response_parts = llm_response.content.parts
    part_texts =[]
    for one_part in response_parts:
        part_text = one_part.text
        if part_text is not None:
            part_texts.append(part_text)
    part_text_content = "\n".join(part_texts)
    metadata = callback_context.state.get("metadata")
    print(f"调用了{agent_name}模型后的callback, 这次模型回复{response_parts}条信息,metadata数据为：{metadata},回复内容是: {part_text_content}")
    #清空contents,不需要上一步的拆分topic的记录, 不能在这里清理，否则，每次调用工具都会清除记忆，白操作了
    # llm_request.contents.clear()
    # 返回 None，继续调用 LLM
    return None

def after_tool_callback(
    tool: BaseTool, args: Dict[str, Any], tool_context: ToolContext, tool_response: Dict
) -> Optional[Dict]:

  tool_name = tool.name
  print(f"调用了{tool_name}工具后的callback, tool_response数据为：{tool_response}")
  return None

root_agent = Agent(
    name="outline_agent",
    model=model,
    description=(
        "generate outline"
    ),
    instruction=instruction,
    before_model_callback=before_model_callback,
    after_model_callback=after_model_callback,
    after_tool_callback=after_tool_callback,
    tools=[DocumentSearch],
)
