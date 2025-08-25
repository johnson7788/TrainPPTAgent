import uuid
import httpx
import time
from a2a.client import A2AClient
import asyncio
from a2a.types import (MessageSendParams, SendMessageRequest, SendStreamingMessageRequest)

async def httpx_client():
    timeout = httpx.Timeout(30.0)  # 设置为 30 秒
    async with httpx.AsyncClient(timeout=timeout) as httpx_client:
        # 初始化客户端（确保base_url包含协议头）
        client = await A2AClient.get_client_from_agent_card_url(
            httpx_client, 'http://localhost:10011'  # 确保此处是完整 URL
        )

        # 生成唯一请求ID
        request_id = uuid.uuid4().hex
        # 构造消息参数
        send_message_payload = {
            'message': {
                'role': 'user',
                'parts': [{'type': 'text', 'text': prompt}],
                'messageId': request_id
            }
        }
        print(f"发送message信息: {send_message_payload}")
        # 流式请求的示例
        streaming_request = SendStreamingMessageRequest(
            id=request_id,
            params=MessageSendParams(**send_message_payload)  # 同样的 payload 可以用于非流式请求
        )

        stream_response = client.send_message_streaming(streaming_request)
        async for chunk in stream_response:
            print(time.time())
            print(chunk.model_dump(mode='json', exclude_none=True))

if __name__ == '__main__':
    prompt = """# 电动汽车发展概述
    - 电动汽车的定义和类型（BEV、PHEV、HEV）
    - 电动汽车发展简史：从早期尝试到现代复兴
    - 电动汽车在全球汽车市场的地位和作用

    # 电动汽车发展的驱动因素
    - 环境保护：减少尾气排放，应对气候变化
    - 能源安全：降低对石油的依赖，利用多样化能源
    - 技术进步：电池技术、电机技术、充电设施的进步
    - 政策支持：政府补贴、税收优惠、排放法规

    # 电动汽车的技术挑战
    - 电池技术：能量密度、续航里程、充电速度、安全性、寿命、成本
    - 充电基础设施：充电桩数量、分布、充电标准、充电效率
    - 电网负荷：大规模充电对电网的冲击、智能充电管理
    - 车辆成本：相对于传统燃油车的竞争力

    # 电动汽车的市场前景
    - 不同国家和地区的市场发展情况
    - 主要电动汽车制造商及其产品
    - 消费者接受度：购买意愿、使用习惯、顾虑因素
    - 未来发展趋势预测：市场规模、技术方向、商业模式

    # 电动汽车的社会影响
    - 对传统汽车产业的影响
    - 对能源产业的影响
    - 对城市交通和环境的影响
    - 对就业和社会结构的影响

    # 结论
    - 电动汽车发展机遇与挑战并存
    - 未来需要关注的重点领域
    - 对个人、企业和政府的建议"""
    asyncio.run(httpx_client())
