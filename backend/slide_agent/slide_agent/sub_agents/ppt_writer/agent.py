import json
import logging
from typing import Dict, List, Any, AsyncGenerator, Optional, Union
from google.genai import types
from google.adk.agents.llm_agent import LlmAgent  # Renamed Agent to LlmAgent for clarity/convention
from google.adk.agents import LoopAgent, BaseAgent  # Import LoopAgent and BaseAgent
from google.adk.events import Event, EventActions
from google.adk.agents.invocation_context import InvocationContext
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmRequest, LlmResponse
from .tools import SearchImage
from ...config import PPT_WRITER_AGENT_CONFIG,PPT_CHECKER_AGENT_CONFIG
from ...create_model import create_model
from . import prompt

logger = logging.getLogger(__name__)
def my_before_model_callback(callback_context: CallbackContext, llm_request: LlmRequest) -> Optional[LlmResponse]:
    # 1. 检查用户输入
    agent_name = callback_context.agent_name
    history_length = len(llm_request.contents)
    metadata = callback_context.state.get("metadata")
    print(f"调用了{agent_name}模型前的callback, 现在Agent共有{history_length}条历史记录,metadata数据为：{metadata}")
    logger.info(f"调用了{agent_name}模型前的callback, 现在Agent共有{history_length}条历史记录,metadata数据为：{metadata}")
    #清空contents,不需要上一步的拆分topic的记录, 不能在这里清理，否则，每次调用工具都会清除记忆，白操作了
    # llm_request.contents.clear()
    # 返回 None，继续调用 LLM
    return None
def my_after_model_callback(callback_context: CallbackContext, llm_response: LlmResponse) -> Optional[LlmResponse]:
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
    logger.info(f"调用了{agent_name}模型后的callback, 这次模型回复{response_parts}条信息,metadata数据为：{metadata},回复内容是: {part_text_content}")
    #清空contents,不需要上一步的拆分topic的记录, 不能在这里清理，否则，每次调用工具都会清除记忆，白操作了
    # llm_request.contents.clear()
    # 返回 None，继续调用 LLM
    return None

# --- 1. Custom Callback Functions for PPTWriterSubAgent ---
def my_writer_before_agent_callback(callback_context: CallbackContext) -> None:
    """
    在调用LLM之前，从会话状态中获取当前幻灯片计划，并格式化LLM输入。
    """
    current_slide_index: int = callback_context.state.get("current_slide_index", 0)  # Default to 0
    slides_plan_num = callback_context.state.get("slides_plan_num")
    # 返回 None，继续调用 LLM
    return None


def my_after_agent_callback(callback_context: CallbackContext) -> None:
    """
    在LLM生成内容后，将其存储到会话状态中。供下一页ppt生成使用
    """
    model_last_output_content = callback_context._invocation_context.session.events[-1]
    response_parts = model_last_output_content.content.parts
    part_texts =[]
    for one_part in response_parts:
        part_text = one_part.text
        if part_text is not None:
            part_texts.append(part_text)
    part_text_content = "\n".join(part_texts)
    # 获取或初始化存储所有生成幻灯片内容的列表
    all_generated_slides_content: List[str] = callback_context.state.get("generated_slides_content", [])
    all_generated_slides_content.append(part_text_content)

    # 更新会话状态
    callback_context.state["generated_slides_content"] = all_generated_slides_content
    print(f"--- Stored content for slide {callback_context.state.get('current_slide_index', 0) + 1} ---")


class PPTWriterSubAgent(LlmAgent):
    def __init__(self, **kwargs):
        super().__init__(
            name="PPTWriterSubAgent",
            model=create_model(model=PPT_WRITER_AGENT_CONFIG["model"], provider=PPT_WRITER_AGENT_CONFIG["provider"]),
            description="根据每一页的幻灯片slide的json结构，丰富幻灯片的slide的内容",
            instruction=self._get_dynamic_instruction,
            before_agent_callback=my_writer_before_agent_callback,
            after_agent_callback=my_after_agent_callback,
            before_model_callback=my_before_model_callback,
            after_model_callback=my_after_model_callback,
            **kwargs
        )

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        slides_plan_num: int = ctx.session.state.get("slides_plan_num")
        current_slide_index: int = ctx.session.state.get("current_slide_index", 0)
        # 清空历史记录，防止历史记录进行干扰
        ctx.session.events = []
        if current_slide_index == 0:
            # 在第一个子Agent返回前返回 XML 开头
            yield Event(
                author=self.name,
                content=types.Content(parts=[types.Part(text="""```xml
<PRESENTATION>
""")]),
            )
        # 调用父类逻辑（最终结果）
        async for event in super()._run_async_impl(ctx):
            print(f"{self.name} 收到事件：{event}")
            logger.info(f"{self.name} 收到事件：{event}")
            yield event
        if current_slide_index == slides_plan_num - 1:
            # 在最后一个子Agent返回后返回 XML 结尾
            yield Event(
                author=self.name,
                content=types.Content(parts=[types.Part(text="""
</PRESENTATION>```""")]),
            )

    def _get_dynamic_instruction(self, ctx: InvocationContext) -> str:
        """动态整合所有研究发现并生成指令"""
        # 当前正在生成第几页的ppt
        current_slide_index: int = ctx.state.get("current_slide_index", 0)
        # 获取大纲
        outline_json: list = ctx.state.get("outline_json")
        # 获取要生成的ppt的这一页的schema大纲
        current_slide_schema = outline_json[current_slide_index]
        # 这页ppt的类型
        current_slide_type = current_slide_schema.get("type")
        print(f"当前要生成第{current_slide_index}页的ppt， 类型为：{current_slide_type}， 具体内容为：{current_slide_schema}")
        # 根据不同的类型，形成不同的prompt
        slide_prompt = prompt.prompt_mapper[current_slide_type]
        prompt_instruction = prompt.PREFIX_PAGE_PROMPT + slide_prompt.format(input_slide_data=current_slide_schema)
        print(f"第{current_slide_index}页的prompt是：{prompt_instruction}")
        return prompt_instruction

def my_super_before_agent_callback(callback_context: CallbackContext):
    """
    在Loop Agent调用之前，进行数据处理
    :param callback_context:
    :return:
    """
    # print(callback_context)
    # 初始化重试次数记录
    if "rewrite_retry_count_map" not in callback_context.state:
        callback_context.state["rewrite_retry_count_map"] = {}
    return None

# --- 4. PPTGeneratorLoopAgent ---
ppt_generator_loop_agent = LoopAgent(
    name="PPTGeneratorLoopAgent",
    max_iterations=100,  # 设置一个足够大的最大迭代次数，以防万一。主要依赖ConditionAgent停止。
    sub_agents=[
        PPTWriterSubAgent(),  # 首先生成当前页的内容
    ],
    before_agent_callback=my_super_before_agent_callback,
)
