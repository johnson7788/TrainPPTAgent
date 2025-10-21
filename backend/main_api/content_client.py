from copy import deepcopy
import json
import logging
import time
import asyncio
from typing import Any
from uuid import uuid4

import httpx
from a2a.client import A2ACardResolver, A2AClient
from a2a.types import (
    AgentCard,
    MessageSendParams,
    SendStreamingMessageRequest,
)

PUBLIC_AGENT_CARD_PATH = '/.well-known/agent.json'
EXTENDED_AGENT_CARD_PATH = '/agent/authenticatedExtendedCard'


class A2AContentClientWrapper:
    def __init__(self, session_id: str, agent_url: str):
        self.session_id = session_id
        self.agent_url = agent_url
        self.logger = logging.getLogger(__name__)
        self.agent_card = None
        self.client: A2AClient | None = None
        # 应该根据第一次回答，获取这个task_id并赋值
        self.task_id = None

    async def _get_agent_card(self, resolver: A2ACardResolver) -> AgentCard:
        """
        获取 AgentCard（支持扩展卡优先，否则用 public 卡）
        """
        self.logger.info(f'尝试获取 Agent Card: {self.agent_url}{PUBLIC_AGENT_CARD_PATH}')
        public_card = await resolver.get_agent_card()
        self.logger.info('成功获取 public agent card:')
        self.logger.info(public_card.model_dump_json(indent=2, exclude_none=True))

        if public_card.supportsAuthenticatedExtendedCard:
            try:
                self.logger.info('支持扩展认证卡，尝试获取...')
                auth_headers_dict = {'Authorization': 'Bearer dummy-token-for-extended-card'}
                extended_card = await resolver.get_agent_card(
                    relative_card_path=EXTENDED_AGENT_CARD_PATH,
                    http_kwargs={'headers': auth_headers_dict},
                )
                self.logger.info('成功获取扩展认证 agent card:')
                self.logger.info(extended_card.model_dump_json(indent=2, exclude_none=True))
                return extended_card
            except Exception as e:
                self.logger.warning(f'获取扩展卡失败: {e}', exc_info=True)

        self.logger.info('使用 public agent card。')
        return public_card

    async def setup(self) -> None:
        async with httpx.AsyncClient(timeout=60.0) as httpx_client:
            resolver = A2ACardResolver(httpx_client=httpx_client, base_url=self.agent_url)
            try:
                agent_card = await self._get_agent_card(resolver)
                self.agent_card = agent_card
            except Exception as e:
                self.logger.error(f'获取 AgentCard 失败: {e}', exc_info=True)
                raise RuntimeError('无法获取 agent card，无法继续运行。') from e
    async def generate(self, user_question: str, metadata={}) -> None:
        """
        user_question: 用户问题
        history： 历史对话消息
        user_id:  用户的id
        执行一次对话流程
        """
        if self.agent_card is None:
            await self.setup()
        logging.basicConfig(level=logging.INFO)
        async with httpx.AsyncClient(timeout=360.0) as httpx_client:
            self.client = A2AClient(httpx_client=httpx_client, agent_card=self.agent_card)
            self.logger.info('A2AClient 初始化完成。')

            # === 多轮对话 示例 ===
            self.logger.info("开始进行对话...")
            message_data: dict[str, Any] = {
                'message': {
                    'role': 'user',
                    'parts': [{'kind': 'text', 'text': user_question}],
                    'messageId': uuid4().hex,
                    'metadata': metadata,
                    'contextId': self.session_id,
                },
            }

            # === 流式响应 ===
            print("=== 流式响应开始 ===")
            streaming_request = SendStreamingMessageRequest(
                id=str(uuid4()),
                params=MessageSendParams(**message_data)
            )
            stream_response = self.client.send_message_streaming(streaming_request)
            # 表示工具完成了调用，可以返回metada信息了
            async for chunk in stream_response:
                # self.logger.info(f"输出的chunk内容: {chunk}")
                chunk_data = chunk.model_dump(mode='json', exclude_none=True)
                if "error" in chunk_data:
                    self.logger.error(f"错误信息: {chunk_data['error']}")
                    print(f"错误信息: {chunk_data['error']}")
                    yield {"type": "final", "text": chunk_data['error'], "author": "system"}
                    break
                result = chunk_data["result"]
                # 判断 chunk 类型
                # 查看parts类型，分为data，text，reasoning，final，例如放入{"type": "text", "text": xxx}，最后yield返回
                if result.get("kind") == "status-update":
                    chunk_status = result["status"]
                    chunk_status_state = chunk_status.get("state")

                    if chunk_status_state == "submitted":
                        self.logger.info("任务已经触发，并提交给后端")
                        continue
                    elif chunk_status_state == "working":
                        self.logger.info("任务处理中")

                    # 尝试提取内容
                    message = chunk_status.get("message", {})
                    parts = message.get("parts", [])
                    metadata = message.get("metadata", {})
                    references = metadata.get("references", [])
                    author = metadata.get("author", "unknown")
                    if references:
                        # 返回最后的元数据给前端进行解析，主要是参考信息
                        yield {"type": "metadata", "metadata": metadata, "author": author}
                    if parts:
                        for part in parts:
                            part_kind = part["kind"]
                            # print(f"status, {part}")
                            if part_kind == "data":
                                # print(f"收到的是data内容:")
                                yield {"type": "data", "data": part["data"], "author":author}
                            else:
                                # text文本,对于图表会拆分成2条数据返回
                                # yield {"type": "text", "text": part["text"], "author": author}
                                for item in self.process_chart_part_text(part.get("text", ""), author):
                                    yield item
                                    # 关键的sleep，防止前端对chunk进行粘连，无法进行json解析
                                    await asyncio.sleep(1)
                elif result.get("kind") == "artifact-update":
                    artifact = result.get("artifact", {})
                    parts = artifact.get("parts", [])
                    metadata = artifact.get("metadata", {})
                    author = metadata.get("author", "unknown")
                    if parts:
                        for part in parts:
                            # print(f"artifact, {part}")
                            yield {"type": "artifact", "text": part.get("text", ""), "author": author}
                    if metadata:
                        # 返回最后的元数据给前端进行解析，主要是参考信息
                        yield {"type": "metadata", "metadata": metadata, "author":author}
                elif result.get("kind") == "task":
                    chunk_status = result["status"]
                    print(f"任务的状态是: {chunk_status}")
                else:
                    self.logger.warning(f"未识别的chunk类型: {result.get('kind')}")
            print(f"Agent正常处理完成，对话结束。")
            yield {"type": "final", "text": "对话结束", "author": "system"}

    def process_chart_part_text(self, part_text: str, author: str):
        """
        如果是content,并且包含chart，那么就拆分成2条
        尝试解析 part_text：
        - 如果是 JSON 且 type=content，则拆分成普通项与 chart 项；
        - 否则原样返回。

        返回一个生成器（yield 多条结果）。
        """
        if not isinstance(part_text, str):
            yield {"type": "text", "text": str(part_text), "author": author}
            return

        try:
            one = json.loads(part_text)
        except json.JSONDecodeError:
            # 不是 JSON，直接返回原始文本
            yield {"type": "text", "text": part_text, "author": author}
            return

        # 如果是 content 类型则拆分
        if isinstance(one, dict) and one.get("type") == "content":
            data = one.get("data", {})
            items = data.get("items", [])
            title = data.get("title", "")
            normal_items = []
            chart_items = []
            sibling_fields = {
                k: deepcopy(v)
                for k, v in one.items()
                if k not in ("type", "data")  # 保留同级信息，但不覆盖 type/data
            }

            for item in items:
                if item.get("kind") == "chart":
                    chart_items.append(item)
                else:
                    normal_items.append(item)

            # 普通项
            if normal_items:
                normal_item_data = {"type": "content","data": {"title": title, "items": normal_items}, **deepcopy(sibling_fields)}
                yield {
                    "type": "text",
                    "text": json.dumps(normal_item_data, ensure_ascii=False),
                    "author": author,
                    }

            # 每个 chart 单独作为一条 slide
            for chart in chart_items:
                chart_data = {"type": "content", "data": {"title": title, "items": [chart]}, **deepcopy(sibling_fields)}
                yield {
                    "type": "text",
                    "text": json.dumps(chart_data, ensure_ascii=False),
                    "author": author,
                }
        else:
            # 不是 content 类型
            yield {"type": "text", "text": part_text, "author": author}

if __name__ == '__main__':
    async def main():
        session_id = time.strftime("%Y%m%d%H%M%S", time.localtime())
        wrapper = A2AContentClientWrapper(session_id=session_id, agent_url="http://localhost:10011")
        prompt = "# 2025科技前沿动态\n## 人工智能新突破\n### 大语言模型的进化\n- 多模态大模型实现文本、图像、音频的深度融合理解\n- 参数效率优化，降低训练成本的同时提升性能\n- 自主推理和规划能力增强，接近人类思维方式\n- 个性化AI助手成为日常标配，提供定制化服务\n- AI安全与伦理框架逐步完善，减少偏见和滥用风险\n### 生成式AI的商业应用\n- 内容创作行业全面变革，自动化生成高质量文章、视频和音乐\n- 药物研发周期缩短，AI辅助设计新分子结构\n- 工业设计领域实现快速原型迭代和优化\n- 营销领域实现千人千面的个性化广告投放\n- 教育领域提供自适应学习路径和智能辅导\n### AI与脑科学的交叉研究\n- 脑机接口技术取得重大突破，实现更高精度的思维解码\n- 神经形态芯片模仿人脑结构，大幅提升能效比\n- AI辅助脑疾病诊断和治疗，实现精准医疗\n- 意识上传与数字永生概念从理论走向初步实验\n- 认知科学为AI提供新启发，反向促进脑科学研究\n## 量子计算商业化进程\n### 量子计算机硬件发展\n- 超导量子计算机实现100+量子比特稳定运行\n- 离子阱量子计算机展示更长的相干时间和更高的保真度\n- 光量子计算机在特定算法上展示量子优势\n- 量子纠错技术取得突破，为实用化铺平道路\n- 量子计算云服务成为企业研发新渠道\n### 量子算法与应用\n- 量子化学模拟加速新材料和药物发现\n- 量子优化算法解决物流、金融等领域的复杂问题\n- 量子机器学习算法处理高维度数据更高效\n- 密码学领域面临量子计算威胁，后量子密码学加速发展\n- 量子人工智能结合，解决传统AI难以处理的复杂问题\n### 量子生态系统建设\n- 主要科技公司建立量子计算研究中心\n- 量子编程语言和开发工具链日趋成熟\n- 量子教育和人才培养体系逐步完善\n- 量子产业联盟形成，推动标准化和商业化\n- 政府加大量子技术投入，制定发展战略和政策\n## 生物技术与医疗革新\n### 基因编辑技术突破\n- CRISPR-Cas9技术实现更精准的基因编辑，减少脱靶效应\n- 基因编辑治疗遗传病进入临床应用阶段\n- 体外基因编辑技术在农业领域广泛应用\n- 表观遗传编辑技术调控基因表达而不改变DNA序列\n- 基因驱动技术在消除疾病传播媒介方面取得进展\n### 精准医疗与个性化治疗\n- 基于基因组学的个性化治疗方案普及\n- 循环肿瘤DNA技术实现癌症早期筛查和监测\n- 微生物组研究揭示肠道健康与疾病的关系\n- 人工智能辅助诊断系统提高疾病预测准确性\n- 基因编辑细胞疗法在免疫治疗领域取得突破\n### 生物合成与生物制造\n- 人工设计和合成生命体成为可能\n- 生物打印技术实现器官和组织的精准制造\n- 微生物细胞工厂生产高价值化合物和药物\n- 合成生物学改造植物提高产量和抗逆性\n- 生物基材料替代传统塑料，减少环境污染\n## 新能源与可持续发展\n### 清洁能源技术革新\n- 钙钛矿太阳能电池效率突破30%，成本持续下降\n- 核聚变能源实验取得突破，能量增益比显著提高\n- 氢燃料电池技术实现商业化，续航里程大幅提升\n- 海上浮式风电场建设加速，拓展清洁能源空间\n- 地热能开发技术进步，提高利用效率\n### 能源存储与管理\n- 固态电池技术解决安全性问题，能量密度提升\n- 液流电池在大规模储能领域展现优势\n- 智能电网整合分布式能源，提高系统稳定性\n- 能源区块链实现点对点能源交易\n- 人工智能优化能源使用效率，减少浪费\n### 碳捕获与利用技术\n- 直接空气捕获(DAC)技术成本降低，实现规模化应用\n- 碳矿化技术将二氧化碳转化为建筑材料\n- 人工光合作用技术将二氧化碳转化为燃料\n- 碳中和技术成为企业减排重要手段\n- 碳交易市场机制完善，促进减排技术创新\n## 通信技术与连接未来\n### 6G网络与卫星互联网\n- 6G网络原型展示，传输速率达到1Tbps\n- 太赫兹通信技术实现高速数据传输\n- 低轨道卫星互联网实现全球无缝覆盖\n- 空天地一体化网络构建，支持万物互联\n- 量子通信卫星网络实现全球安全通信\n### 沉浸式技术演进\n- 轻量化AR眼镜实现全天候佩戴\n- 脑机接口结合VR实现更自然的交互\n- 数字孪生技术实现物理世界的精确复制\n- 全息通信技术实现真实感远程会议\n- 元宇宙社交平台成为新社交方式\n### 边缘计算与物联网\n- 边缘AI芯片实现本地化智能处理\n- 物联网安全协议升级，保障设备安全\n- 低功耗广域网技术支持大规模传感器部署\n- 工业互联网平台实现设备全生命周期管理\n- 智能城市基础设施互联互通，提升城市治理效率\n## 先进制造与机器人技术\n### 3D打印技术革新\n- 金属3D打印实现大型复杂结构一体化制造\n- 生物3D打印技术打印功能性组织和器官\n- 多材料3D打印创造具有特殊性能的复合材料\n- 纳米级3D打印实现微米级精度的复杂结构\n- 4D打印技术实现打印物的自主变形和响应\n### 工业机器人进化\n- 人机协作机器人更安全、更智能\n- 柔性机器人适应非结构化环境\n- 自主学习机器人能够适应新任务\n- 群体机器人系统实现协同作业\n- 云端赋能的机器人共享知识和经验\n### 智能制造系统\n- 数字孪生工厂实现全流程模拟和优化\n- 自适应制造系统能够根据需求调整生产流程\n- 人工智能驱动的质量控制实现零缺陷生产\n- 供应链智能优化降低库存和物流成本\n- 可持续制造技术减少能源消耗和废弃物产生"
        async for chunk_data in wrapper.generate(prompt, metadata={"search_engine": False}):
            print(chunk_data)
    asyncio.run(main())
