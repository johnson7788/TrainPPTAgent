# 文件: /Users/admin/git/TrainPPTAgent/backend/slide_agent/slide_agent/sub_agents/ppt_writer/agent.py
import json
import logging
from typing import Dict, List, Any, AsyncGenerator, Optional, Union, Tuple
from google.genai import types
from google.adk.agents.llm_agent import LlmAgent  # Renamed Agent to LlmAgent for clarity/convention
from google.adk.agents import LoopAgent, BaseAgent  # Import LoopAgent and BaseAgent
from google.adk.events import Event, EventActions
from google.adk.agents.invocation_context import InvocationContext
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmRequest, LlmResponse
from .tools import SearchImage, DocumentSearch
from ...config import PPT_WRITER_AGENT_CONFIG, PPT_CHECKER_AGENT_CONFIG
from ...create_model import create_model
from . import prompt
from .utils import only_json, validate_slide

logger = logging.getLogger(__name__)



# ================== 通用回调 ==================
def my_before_model_callback(callback_context: CallbackContext, llm_request: LlmRequest) -> Optional[LlmResponse]:
    agent_name = callback_context.agent_name
    history_length = len(llm_request.contents)
    metadata = callback_context.state.get("metadata")
    print(f"调用了{agent_name}模型前的callback, 现在Agent共有{history_length}条历史记录,metadata数据为：{metadata}")
    logger.info(f"调用了{agent_name}模型前的callback, 现在Agent共有{history_length}条历史记录,metadata数据为：{metadata}")
    return None


def my_after_model_callback(callback_context: CallbackContext, llm_response: LlmResponse) -> Optional[LlmResponse]:
    """
    这里仅记录原始文本；真正的 JSON 解析与校验放到 agent 的 after_agent_callback 里做（能拿到 schema）。
    """
    agent_name = callback_context.agent_name
    response_parts = llm_response.content.parts
    part_texts = []
    for one_part in response_parts:
        part_text = getattr(one_part, "text", None)
        if part_text is not None:
            part_texts.append(part_text)
    part_text_content = "\n".join(part_texts)
    metadata = callback_context.state.get("metadata")
    print(f"调用了{agent_name}模型后的callback, 这次模型回复{response_parts}条信息,metadata数据为：{metadata},回复内容是: {part_text_content}")
    logger.info(f"调用了{agent_name}模型后的callback, 这次模型回复{response_parts}条信息,metadata数据为：{metadata},回复内容是: {part_text_content}")
    # 暂存在 state，供 after_agent_callback 使用
    callback_context.state["_last_raw_text_reply"] = part_text_content
    return None


# --- 1. Custom Callback Functions for PPTWriterSubAgent ---
def my_writer_before_agent_callback(callback_context: CallbackContext) -> None:
    """
    在调用LLM之前，从会话状态中获取当前幻灯片计划，并格式化LLM输入。
    """
    # 初始化当前页的重试计数
    retry_map: Dict[int, int] = callback_context.state.get("rewrite_retry_count_map", {})
    cur_idx: int = callback_context.state.get("current_slide_index", 0)
    retry_map[cur_idx] = 0
    callback_context.state["rewrite_retry_count_map"] = retry_map
    # 本轮开始前清理上轮临时值
    callback_context.state["_last_raw_text_reply"] = None
    callback_context.state["_last_slide_json"] =  None
    callback_context.state["_last_slide_valid"] = None
    callback_context.state["_last_slide_missing_keys"] = None
    return None


def my_after_agent_callback(callback_context: CallbackContext) -> None:
    """
    在LLM生成内容后：解析 -> 校验 -> 决定是否重试（规则判断，不用大模型）。
    仅当通过校验时，才写入 generated_slides_content。
    """
    state = callback_context.state
    cur_idx: int = state.get("current_slide_index", 0)
    outline_json: List[Dict[str, Any]] = state.get("outline_json") or []
    current_slide_schema: Dict[str, Any] = outline_json[cur_idx] if 0 <= cur_idx < len(outline_json) else {}

    raw_text = state.get("_last_raw_text_reply") or ""
    data = only_json(raw_text)

    is_valid = False
    missing_keys: List[str] = []
    if data is not None:
        is_valid, missing_keys = validate_slide(data, current_slide_schema)

    state["_last_slide_json"] = data
    state["_last_slide_valid"] = is_valid
    state["_last_slide_missing_keys"] = missing_keys

    if not is_valid:
        # 增加重试计数
        retry_map: Dict[int, int] = state.get("rewrite_retry_count_map", {})
        retry_map[cur_idx] = retry_map.get(cur_idx, 0) + 1
        state["rewrite_retry_count_map"] = retry_map
        state["retry_current_slide"] = True

        logger.warning(
            f"[PPTWriterSubAgent] 第{cur_idx}页校验失败，将重试。原因："
            + ("非JSON" if data is None else f"缺少字段 {missing_keys}")
        )
        print(
            f"[PPTWriterSubAgent] 第{cur_idx}页校验失败，将重试。原因："
            + ("非JSON" if data is None else f"缺少字段 {missing_keys}")
        )
        # 不写入 generated_slides_content，等待重试
        return

    # 校验通过：写入结果
    all_generated_slides_content: List[Any] = state.get("generated_slides_content", [])
    # 存 dict（结构化），便于后续使用；如需文本也可存 raw_text
    all_generated_slides_content.append(data)
    state["generated_slides_content"] = all_generated_slides_content
    state["retry_current_slide"] = False
    print(f"--- Stored VALID JSON for slide {cur_idx + 1} ---")


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
            tools=[SearchImage, DocumentSearch],  # 注册SearchImage工具
            **kwargs
        )

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        slides_plan_num: int = ctx.session.state.get("slides_plan_num")
        current_slide_index: int = ctx.session.state.get("current_slide_index", 0)
        max_retries: int = int(ctx.session.state.get("writer_max_retries", 3))

        # 清空历史记录，防止历史记录进行干扰
        ctx.session.events = []
        if current_slide_index == 0:
            print(f"正在生成第{current_slide_index}页幻灯片...")

        # 调用父类逻辑（最终结果）
        async for event in super()._run_async_impl(ctx):
            logger.info(f"{self.name} 收到事件：{event}")
            yield event

        # 根据 after_agent_callback 的校验结果决定是否重试
        state = ctx.session.state
        retry_map: Dict[int, int] = state.get("rewrite_retry_count_map", {})
        should_retry: bool = bool(state.get("retry_current_slide"))
        retry_times = int(retry_map.get(current_slide_index, 0))

        if should_retry and retry_times < max_retries:
            # 不前进 index，不结束 loop，本次迭代结束后 LoopAgent 会再次调用本子代理
            print(f"[PPTWriterSubAgent] 第{current_slide_index}页触发规则重试，第{retry_times}/{max_retries}次。")
            logger.info(f"[PPTWriterSubAgent] slide {current_slide_index} retry {retry_times}/{max_retries}.")
            # 可在 state 中放入“纠错提醒”提示模型严格输出 json + 必含字段（不用调用额外大模型判断）
            # 这里不修改 instruction，只依赖你现有 prompt 中的 JSON 要求；若需更强约束，可在 state 放标志位让 prompt 里引用
            yield Event(author=self.name, actions=EventActions())  # 正常结束本轮，让 LoopAgent 继续
            return

        if should_retry and retry_times >= max_retries:
            # 达到最大重试，记录并跳过此页
            print(f"[PPTWriterSubAgent] 第{current_slide_index}页达到最大重试次数({max_retries})，跳过此页。")
            logger.warning(f"[PPTWriterSubAgent] slide {current_slide_index} reached max retries, skip.")
            # 标记为失败页（可选）
            failed_pages: List[int] = state.get("failed_pages", [])
            failed_pages.append(current_slide_index)
            state["failed_pages"] = failed_pages
            state["retry_current_slide"] = False  # 避免死循环

        # 若为最后一页且已完成/跳过，触发升级结束
        if current_slide_index == slides_plan_num - 1:
            print(f"生成第{current_slide_index}页幻灯片完成...")
            yield Event(author=self.name, actions=EventActions(escalate=True))

        # 只有当未处于“需要重试”状态时才推进索引
        if not state.get("retry_current_slide"):
            ctx.session.state["current_slide_index"] = current_slide_index + 1

    def _get_dynamic_instruction(self, ctx: InvocationContext) -> str:
        """动态整合所有研究发现并生成指令"""
        current_slide_index: int = ctx.state.get("current_slide_index", 0)
        outline_json: list = ctx.state.get("outline_json")
        current_slide_schema = outline_json[current_slide_index]
        current_slide_type = current_slide_schema.get("type")
        print(f"当前要生成第{current_slide_index}页的ppt， 类型为：{current_slide_type}， 具体内容为：{current_slide_schema}")
        slide_prompt = prompt.prompt_mapper[current_slide_type]

        # 若上一轮失败，附加更强约束提醒（规则引导，不调用判断模型）
        retry_map: Dict[int, int] = ctx.state.get("rewrite_retry_count_map", {}) or {}
        retried = int(retry_map.get(current_slide_index, 0))
        extra_rule_tip = ""
        if retried > 0:
            must_keys = ", ".join(list(current_slide_schema.keys()))
            extra_rule_tip = (
                f"\n\n[严格输出要求-第{retried}次重试提示]\n"
                f"- 必须输出 **纯 JSON 对象**，不得包含额外文本。\n"
                f"- JSON 顶层必须为字典（object）。\n"
                f"- 顶层 key 至少包含以下字段（可多不可少）：[{must_keys}]。\n"
                f"- 字段缺失将被判定为失败并继续重试。\n"
            )

        prompt_instruction = (
            prompt.PREFIX_PAGE_PROMPT
            + slide_prompt.format(input_slide_data=current_slide_schema)
            + extra_rule_tip
        )
        print(f"第{current_slide_index}页的prompt是：{prompt_instruction}")
        return prompt_instruction


def my_super_before_agent_callback(callback_context: CallbackContext):
    """
    在Loop Agent调用之前，进行数据处理
    """
    if "rewrite_retry_count_map" not in callback_context.state:
        callback_context.state["rewrite_retry_count_map"] = {}
    # 提供默认最大重试次数，亦可通过外部 state 覆盖 writer_max_retries
    callback_context.state["writer_max_retries"] = 5
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
