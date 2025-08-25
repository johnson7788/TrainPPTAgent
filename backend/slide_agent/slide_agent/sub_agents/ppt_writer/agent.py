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

    research_outputs_content: str = callback_context.state.get("research_outputs_content")
    if not research_outputs_content:
        raise ValueError("research_outputs_content is missing in session state. Please ensure research_outputs_content ran successfully.")
    # 所有研究Agent的图片的内容输出结果进行拼接

    formatted_slide_outline = f"Page {current_slide_index + 1}"

    print(f"--- 正在生成第{current_slide_index + 1}页PPT ---")
    logger.info(f"--- 正在生成第{current_slide_index + 1}页PPT ---")
    page_num = f"{current_slide_index + 1}/{slides_plan_num}"
    # 第一页的prompt和后面ppt的页的prompt是不一样的，因为后面页的prompt需要继续前一页的继续生成
    # 构建LLM请求的contents
    callback_context.state["research_doc"] = research_outputs_content
    callback_context.state["page_num"] = page_num

    rewrite_reason = callback_context.state.get("rewrite_reason")
    if rewrite_reason:
        print(f"[PPTWriterSubAgent] 上一轮校验失败，收到重写建议: {rewrite_reason}")
        callback_context.state["other_suggestion"] = f"⚠️ 上一轮审核未通过，请特别注意以下问题：" + rewrite_reason
        callback_context.state["rewrite_reason"] = "" # 清空重写原因，防止下次重复使用
    else:
        callback_context.state["other_suggestion"] = ""

    # 第一页和其它页只有历史记录和页码不一样
    if current_slide_index == 0:
        # 用于初始化prompt
        callback_context.state["history_slides_xml"] = ""
    else:
        all_generated_slides_content: List[str] = callback_context.state.get("generated_slides_content", [])
        history_slides_xml = "\n\n".join(all_generated_slides_content)
        callback_context.state["history_slides_xml"] = history_slides_xml
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

# --- 2. PPTWriterSubAgent (The Worker Agent) ---
# 这个代理负责根据单页大纲生成XML内容
ppt_writer_sub_agent = PPTWriterSubAgent(
    model=create_model(model=PPT_WRITER_AGENT_CONFIG["model"], provider=PPT_WRITER_AGENT_CONFIG["provider"]),
    name="PPTWriterSubAgent",
    description="根据每一页的幻灯片slide的json结构，丰富幻灯片的slide的内容",
    instruction=prompt.XML_PPT_AGENT_NEXT_PAGE_PROMPT,
    before_agent_callback=my_writer_before_agent_callback,
    after_agent_callback=my_after_agent_callback,
    before_model_callback=my_before_model_callback,
    after_model_callback=my_after_model_callback,
    tools=[SearchImage]
)

## PPT检查Agent
class PPTCheckerAgent(LlmAgent):
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        current_slide_index: int = ctx.session.state.get("current_slide_index", 0)
        generated_slides_content: List[str] = ctx.session.state.get("generated_slides_content", [])
        rewrite_retry_count_map: Dict[int, int] = ctx.session.state.get("rewrite_retry_count_map", {})

        if current_slide_index >= len(generated_slides_content):
            print(f"[PPTCheckerAgent] 没有找到当前页内容 index={current_slide_index}")
            yield Event(author=self.name, actions=EventActions())
            return

        current_slide = generated_slides_content[current_slide_index]
        history_slides = "\n\n".join(generated_slides_content[:current_slide_index])
        ctx.session.events = []
        ctx.session.state["slide_to_check"] = current_slide
        ctx.session.state["history_slides"] = history_slides  #用于ppt的生成结果的检查
        async for event in super()._run_async_impl(ctx):
            print(f"{self.name} 检查结果事件：{event}")
            result = event.content.parts[0].text.strip()

            if "需要重写" in result:
                retry_count = rewrite_retry_count_map.get(current_slide_index, 0)
                if retry_count < 3:
                    ctx.session.state["rewrite_reason"] = result
                    print(f"[PPTCheckerAgent] 第 {retry_count + 1} 次尝试重写 slide {current_slide_index + 1}")
                    ctx.session.state["generated_slides_content"].pop()
                    if current_slide_index == 0:
                        # 第一次初始化，如果为-1，那么
                        ctx.session.state["current_slide_index"] = -1
                    else:
                        ctx.session.state["current_slide_index"] = current_slide_index - 1
                    rewrite_retry_count_map[current_slide_index] = retry_count + 1
                    ctx.session.state["rewrite_retry_count_map"] = rewrite_retry_count_map
                else:
                    print(f"[PPTCheckerAgent] 第 {retry_count} 次重写失败，已达最大次数，跳过当前页")
                    yield Event(author=self.name, content=types.Content(parts=[types.Part(text="写失败，已达最大次数，跳过当前页检查，使用最后一次生成的结果")]))

            yield event


ppt_checker_agent = PPTCheckerAgent(
    model=create_model(model=PPT_CHECKER_AGENT_CONFIG["model"], provider=PPT_CHECKER_AGENT_CONFIG["provider"]),
    name="PPTCheckerAgent",
    description="检查幻灯片内容是否合格",
    instruction=prompt.CHECKER_AGENT_PROMPT,
)



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

# --- 3. SlideLoopConditionAgent (The Condition Checker) ---
# 这个代理负责更新当前幻灯片索引，并决定是否继续循环
class SlideLoopConditionAgent(BaseAgent):
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        slides_plan_num: int = ctx.session.state.get("slides_plan_num")
        current_slide_index: int = ctx.session.state.get("current_slide_index", 0)

        if not slides_plan_num:
            # 如果没有 slides_plan，则直接结束循环 (可能在前面步骤出错), 幻灯片的生成计划是必须的
            print("No slides_plan_num found. Terminating loop.")
            logger.info("No slides_plan_num found. Terminating loop.")
            yield Event(author=self.name, actions=EventActions(escalate=True))
            return

        # 检查是否所有幻灯片都已处理
        if current_slide_index >= slides_plan_num - 1:
            print(f"--- All {slides_plan_num} slides processed. Terminating loop. ---")
            logger.info(f"--- All {slides_plan_num} slides processed. Terminating loop. ---")
            yield Event(author=self.name, actions=EventActions(escalate=True))  # 提升事件，停止循环
        else:
            # 如果还有未处理的幻灯片，则更新索引并继续
            new_slide_index = current_slide_index + 1
            ctx.session.state["current_slide_index"] = new_slide_index
            print(f"--- 开始生成第 {new_slide_index + 1} / {slides_plan_num} 幻灯片---")
            logger.info(f"--- 开始生成第 {new_slide_index + 1} / {slides_plan_num} 幻灯片---")
            yield Event(author=self.name, actions=EventActions())  # 不提升事件，继续循环

# --- 4. PPTGeneratorLoopAgent ---
ppt_generator_loop_agent = LoopAgent(
    name="PPTGeneratorLoopAgent",
    max_iterations=100,  # 设置一个足够大的最大迭代次数，以防万一。主要依赖ConditionAgent停止。
    sub_agents=[
        ppt_writer_sub_agent,  # 首先生成当前页的内容
        ppt_checker_agent,
        SlideLoopConditionAgent(name="SlideCounter"),  # 然后检查并更新索引，决定是否继续
    ],
    before_agent_callback=my_super_before_agent_callback,
)
