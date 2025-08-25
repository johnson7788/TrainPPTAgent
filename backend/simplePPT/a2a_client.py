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
                'messageId': request_id,
                'metadata': {"language": "中文"}
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
    prompt = """# 2025科技前沿动态

## 人工智能新突破
### 大语言模型的进化
- 多模态大模型实现文本、图像、音频的深度融合理解
- 参数效率优化，降低训练成本的同时提升性能
- 自主推理和规划能力增强，接近人类思维方式

### 生成式AI的商业应用
- 内容创作行业全面变革，自动化生成高质量文章、视频和音乐
- 药物研发周期缩短，AI辅助设计新分子结构
- 工业设计领域实现快速原型迭代和优化

### AI与脑科学的交叉研究
- 脑机接口技术取得重大突破，实现更高精度的思维解码
- 神经形态芯片模仿人脑结构，大幅提升能效比
- AI辅助脑疾病诊断和治疗，实现精准医疗

### 量子算法与应用
- 量子化学模拟加速新材料和药物发现
- 量子优化算法解决物流、金融等领域的复杂问题
- 量子机器学习算法处理高维度数据更高效

### 量子生态系统建设
- 主要科技公司建立量子计算研究中心
- 量子编程语言和开发工具链日趋成熟
- 量子教育和人才培养体系逐步完善
- 量子产业联盟形成，推动标准化和商业化
- 政府加大量子技术投入，制定发展战略和政策

### 精准医疗与个性化治疗
- 基于基因组学的个性化治疗方案普及
- 循环肿瘤DNA技术实现癌症早期筛查和监测
- 微生物组研究揭示肠道健康与疾病的关系
- 基因编辑细胞疗法在免疫治疗领域取得突破

## 新能源与可持续发展
### 清洁能源技术革新
- 钙钛矿太阳能电池效率突破30%，成本持续下降
- 核聚变能源实验取得突破，能量增益比显著提高
- 氢燃料电池技术实现商业化，续航里程大幅提升
- 海上浮式风电场建设加速，拓展清洁能源空间

## 通信技术与连接未来
### 6G网络与卫星互联网
- 6G网络原型展示，传输速率达到1Tbps
- 太赫兹通信技术实现高速数据传输
- 低轨道卫星互联网实现全球无缝覆盖
- 空天地一体化网络构建，支持万物互联
- 量子通信卫星网络实现全球安全通信

### 智能制造系统
- 数字孪生工厂实现全流程模拟和优化
- 自适应制造系统能够根据需求调整生产流程
- 人工智能驱动的质量控制实现零缺陷生产
- 供应链智能优化降低库存和物流成本
- 可持续制造技术减少能源消耗和废弃物产生"""
    asyncio.run(httpx_client())
