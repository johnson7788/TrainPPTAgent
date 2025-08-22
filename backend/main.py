import asyncio
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Allow CORS for the frontend development server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AipptRequest(BaseModel):
    content: str
    language: str
    model: str
    stream: bool

# The example markdown response provided by the user
markdown_response = """# 2025科技前沿动态

## 人工智能与机器学习
### 大型语言模型的突破
- GPT-6实现多模态理解与生成，文本、图像、音频无缝融合
- 多语言处理能力达到人类水平，支持100+种语言的深度理解
- 模型参数优化，训练能耗降低70%，推理速度提升3倍
- 自监督学习能力增强，减少标注数据依赖达90%
- 伦理安全框架完善，内置事实核查机制

### 通用人工智能进展
- AGI系统在有限领域实现超越专家水平的表现
- 多智能体协作系统解决复杂问题的能力显著提升
- 元学习算法实现快速适应新任务的能力
- 神经符号AI结合逻辑推理与神经网络优势
- 自主AI系统获得有限环境下的决策能力

### 人工智能伦理与治理
- 全球AI治理框架初步建立，包含跨国合作机制
- AI透明度与可解释性成为强制性要求
- 偏见检测与缓解技术成熟，减少算法歧视
- 数据隐私保护与AI应用的平衡机制形成
- AI安全研究重点关注对抗性攻击防御

## 量子计算与量子互联网
### 量子计算硬件突破
- 50+量子比特量子处理器实现稳定运行
- 量子纠错技术取得重大进展，错误率降低至10^-6
- 高温超导量子芯片实现室温量子计算原型
- 光量子计算机处理特定问题的速度提升100倍
- 量子-经典混合计算架构走向实用化

### 量子互联网发展
- 量子密钥分发网络覆盖主要城市，实现安全通信
- 量子中继器技术突破，量子态传输距离达1000公里
- 量子路由器与量子交换机标准形成
- 全球量子互联网基础设施初步规划完成
- 量子安全协议成为金融、政府通信标准

### 量子计算应用探索
- 药物分子模拟实现原子级别精确计算
- 优化算法解决物流、能源分配等复杂问题
- 人工智能加速器利用量子计算提升模型训练速度
- 金融风险分析模型计算效率提升1000倍
- 材料科学发现新型超导材料与催化剂"""

async def stream_generator():
    """A generator that yields parts of the markdown response to simulate streaming."""
    for char in markdown_response:
        yield char
        await asyncio.sleep(0.01) # Simulate network latency

@app.post("/tools/aippt_outline")
async def aippt_outline(request: AipptRequest):
    if request.stream:
        return StreamingResponse(stream_generator(), media_type="text/plain")
    else:
        return {"text": markdown_response}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=6800)
