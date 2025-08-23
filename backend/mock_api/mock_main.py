import asyncio
import json
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Allow CORS for the frontend development server
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
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

image_data = {
    "type": "content",
    "data": {
        "title": "暴力犯罪",
        "items": [
            {
                "title": "谋杀心理特征",
                "text": "探讨谋杀者的心理动机…",
                "images": [
                    {
                        "src": "https://www.hertz.com/content/dam/hertz/global/blog-articles/things-to-do/hertz230-things-to-do-londons-top-10-attractions/Big-Ben-Clock-Tower.jpg",
                        "alt": "不同年份的谋杀率",
                        "imageType": "itemFigure"
                    }
                ]
            }
        ]
    }
}
charts_data = {
    "type": "content",
    "data": {
        "title": "绘图信息",
        "items": [
            {
                "title": "绘图图表",
                "text": "图表…",
                "charts": [
                    {
                        "chartType": "column",
                        "data": {
                            "labels": ["2019","2020","2021","2022"],
                            "legends": ["案件数"],
                            "series": [[82, 96, 110, 104]]
                        },
                        "options": {"stack": False},
                        "themeColors": ["#4e79a7"],
                        "textColor": "#333",
                        "lineColor": "#ddd"
                    }
                ]
            }
        ]
    }
}

data_response_content = [
    {"type": "cover", "data": {"title": "2025科技前沿动态", "text": "探索人工智能、量子计算、生物技术等领域的最新突破与未来发展方向"}},
    {"type": "contents", "data": {"items": ["人工智能新突破", "量子计算商业化进程", "生物技术与医疗革新", "新能源与可持续发展", "通信技术与连接未来", "先进制造与机器人技术"]}},
    {"type": "transition", "data": {"title": "人工智能新突破", "text": "人工智能技术实现多模态融合、参数效率优化与个性化服务，推动各行业创新应用"}},
    {"type": "content", "data": {"title": "大语言模型的进化", "items": [
        {"title": "多模态融合", "text": "大语言模型已实现文本、图像、音频等多模态信息的深度融合理解，使AI系统能够更接近人类感知世界的方式，处理复杂场景下的信息整合与推理任务。"},
        {"title": "参数效率优化", "text": "通过模型架构创新与训练算法优化，新一代大语言模型显著降低了训练成本，同时保持了甚至提升了模型性能，使更多研究机构和企业能够参与AI技术研发与应用。"},
        {"title": "自主推理能力", "text": "AI系统的自主推理和规划能力显著增强，能够基于复杂环境做出更接近人类思维方式的决策，在科学研究、问题解决等领域展现出前所未有的潜力。"},
        {"title": "个性化AI助手", "text": "AI助手已实现高度个性化，能够学习用户习惯、偏好和需求，提供定制化服务，成为日常生活和工作的得力助手，显著提升个人效率与体验。"},
        {"title": "安全伦理框架", "text": "随着AI应用的普及，安全与伦理框架逐步完善，通过算法优化、数据治理和监管措施，有效减少AI系统中的偏见与滥用风险，促进技术健康发展。"}
    ]}},
    {"type": "content", "data": {"title": "生成式AI的商业应用", "items": [
        {"title": "内容创作变革", "text": "生成式AI已全面变革内容创作行业，自动化生成高质量文章、视频和音乐的能力显著提升，大幅降低了内容生产成本，提高了创作效率，为创意产业带来新的发展机遇。"},
        {"title": "药物研发加速", "text": "AI技术显著缩短了药物研发周期，通过分子结构设计与药物特性预测，加速了新药发现过程，为治疗复杂疾病提供了更多可能性，降低了研发成本与风险。"},
        {"title": "工业设计优化", "text": "在工业设计领域，生成式AI实现了快速原型迭代和优化，能够根据需求自动生成多种设计方案，并评估其可行性与性能，大幅提高了设计效率与创新性。"},
        {"title": "精准营销投放", "text": "生成式AI在营销领域实现千人千面的个性化广告投放，通过分析用户行为与偏好，精准匹配内容与目标受众，显著提升了营销效果与转化率。"},
        {"title": "自适应教育", "text": "教育领域通过AI提供自适应学习路径和智能辅导系统，根据学生能力与学习进度动态调整内容难度与教学方式，实现个性化教育，提升学习效果。"}
    ]}},
    {"type": "content", "data": {"title": "AI与脑科学的交叉研究", "items": [
        {"title": "脑机接口突破", "text": "脑机接口技术取得重大突破，实现了更高精度的思维解码，使大脑信号能够更准确地转化为控制指令，为医疗康复和人机交互开辟了新途径。"},
        {"title": "神经形态芯片", "text": "神经形态芯片模仿人脑结构与工作机制，大幅提升了能效比，在处理复杂模式识别与学习任务时展现出显著优势，为低功耗AI计算提供了新方向。"},
        {"title": "脑疾病精准医疗", "text": "AI辅助脑疾病诊断和治疗系统已实现临床应用，通过分析神经影像与脑电数据，提高了阿尔茨海默症、帕金森病等神经系统疾病的早期诊断准确性与治疗效果。"},
        {"title": "意识上传探索", "text": "意识上传与数字永生概念已从理论走向初步实验阶段，通过脑部扫描与神经网络建模，科学家们正在探索保存人类认知特征的可能性，为未来脑机融合奠定基础。"},
        {"title": "认知科学启发", "text": "认知科学研究为AI提供了新的理论框架与算法启发，而AI的发展也反过来促进了脑科学研究，形成双向促进的良性循环，推动了两个领域的共同进步。"}
    ]}},
    image_data,
    charts_data,
    {"type": "end"}
]

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

class AipptContentRequest(BaseModel):
    content: str


def parse_markdown_to_slides(markdown_text):
    slides = []
    lines = markdown_text.strip().split('\n')

    # Find title
    main_title = ""
    for line in lines:
        if line.startswith('# '):
            main_title = line[2:].strip()
            # Use a generic subtitle
            slides.append({"type": "cover", "data": {"title": main_title, "text": "A presentation generated by AI"}})
            break

    # Find sections for contents page
    sections = []
    for line in lines:
        if line.startswith('## '):
            sections.append(line[2:].strip())
    if sections:
        slides.append({"type": "contents", "data": {"items": sections}})

    # Process each section and its subsections
    current_section_title = ""
    current_subsection_title = ""
    current_items = []

    for line in lines:
        line = line.strip()
        if line.startswith('## '):
            if current_subsection_title:
                slide_items = []
                for item in current_items:
                    slide_items.append({"title": item, "text": f"Detailed content about {item}"})
                slides.append({"type": "content", "data": {"title": current_subsection_title, "items": slide_items}})
                current_items = []

            current_section_title = line[2:].strip()
            current_subsection_title = ""
            slides.append({"type": "transition", "data": {"title": current_section_title, "text": f"Exploring the topic of {current_section_title}"}})
        elif line.startswith('### '):
            if current_subsection_title:
                slide_items = []
                for item in current_items:
                    slide_items.append({"title": item, "text": f"Detailed content about {item}"})
                slides.append({"type": "content", "data": {"title": current_subsection_title, "items": slide_items}})
                current_items = []
            current_subsection_title = line[4:].strip()
        elif line.startswith('- '):
            if current_subsection_title:
                current_items.append(line[2:].strip())

    if current_subsection_title:
        slide_items = []
        for item in current_items:
            slide_items.append({"title": item, "text": f"Detailed content about {item}"})
        slides.append({"type": "content", "data": {"title": current_subsection_title, "items": slide_items}})

    slides.append({"type": "end"})
    return slides

def preset_json_to_slides(mardkown_text):
    slides = []
    for one in data_response_content:
        slides.append(one)
    return slides

async def aippt_content_streamer(markdown_content: str):
    """Parses markdown and streams slide data as JSON objects."""
    # slides = parse_markdown_to_slides(markdown_content)
    slides = preset_json_to_slides(markdown_content)
    for slide in slides:
        yield json.dumps(slide, ensure_ascii=False) + '\n'
        await asyncio.sleep(0.1)

@app.post("/tools/aippt")
async def aippt_content(request: AipptContentRequest):
    return StreamingResponse(aippt_content_streamer(request.content), media_type="application/json; charset=utf-8")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=6800)

