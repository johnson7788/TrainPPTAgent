from google.adk.agents.llm_agent import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmRequest, LlmResponse
from google.genai import types
from typing import Dict, List, Any, AsyncGenerator, Optional, Union
from ...config import SPLIT_TOPIC_AGENT_CONFIG
from ...create_model import create_model
from . import prompt


def my_before_model_callback(callback_context: CallbackContext, llm_request: LlmRequest) -> Optional[LlmResponse]:
    # 1. 检查用户输入
    user_input = callback_context.user_content.parts[0].text
    callback_context.state["outline"] = user_input
    print("调用了SplitTopicAgent的Outline的callback，存储outline信息")
    #为啥需要手动加入user_input
    llm_request.contents.append(
        types.Content(role="user", parts=[types.Part(text=user_input)])
    )
    # 返回 None，继续调用 LLM
    return None

split_topic_agent = Agent(
    name="SplitTopicAgent",
    model=create_model(model=SPLIT_TOPIC_AGENT_CONFIG["model"], provider=SPLIT_TOPIC_AGENT_CONFIG["provider"]),
    description="专门负责分析写作大纲并将其拆分成独立的研究主题",
    instruction=prompt.SPLIT_TOPIC_AGENT_PROMPT,
    output_key="split_topics",
    before_model_callback=my_before_model_callback
)