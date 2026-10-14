# TrainPPTAgent

**TrainPPTAgent** 是一款基于 AI 的智能演示文稿生成工具。用户只需输入主题，系统即可自动通过微信搜索网络内容，生成结构完整、内容丰富的 PPT 大纲与逐页内容。项目采用 **前后端分离架构**：前端负责交互、大纲编辑与模板选择，后端则借助大语言模型（LLM）与强化学习（GRPO）完成内容生成与优化，使生成的 PPT 更贴合用户目标。

English：[README_EN.md](README_EN.md)

强化学习训练代码请参见另外项目：
👉 [PPT 模型训练代码](https://github.com/johnson7788/RLTrainPPT)

---

## ✨ 功能特性

* **智能大纲生成**
  输入主题后，自动生成逻辑清晰、结构合理的演示文稿大纲。

* **逐页内容生成**
  采用流式传输技术，实现 PPT 内容的实时生成与展示，提升交互体验。

* **用户已有大纲或者文件上传到知识库**
  根据知识库的内容生成PPT。

* **模板支持**
  提供多种模板供用户选择，支持内容与样式的分离式填充。

* **不同模型**
  支持各种商业模型和本地模型，参考doc/custom_model.md。

* **前后端分离架构**
  前端使用 **Vue.js + Vite + TypeScript**，后端基于 **Python (FastAPI)**，架构清晰、可扩展性强。

* **强化学习驱动**
  引入 **GRPO 强化学习方法**，优化 PPT Agent 的生成效果，使结果更符合用户需求。

---

## 🛠 技术栈

* **前端**: Vue.js, Vite, TypeScript
* **后端**: Python, Flask/FastAPI, A2A, ADK, MCP 搜索
* **AI 模型**: 大语言模型联网搜索（用于大纲与内容生成），可以自行取消联网搜索，如果不需要，找到agent.py中的tools=[]，改成空即可。

---

## 📋 项目结构

```
TrainPPTAgent/
├── backend/           # 后端代码
│   ├── mock_api/      # 模拟生成PPT
│   ├── main_api/      # 核心 API 服务
│   ├── slide_agent/   # AI Agent根据大纲撰搜索网络或者本地知识库写每页PPT
│   ├── simpleOutline/  # AI Agent 搜索并写大纲
│   ├── personaldb/     #知识库，解析各种格式的文件，用于搜索知识库生成PPT
├── frontend/          # 前端代码
│   ├── src/
│   │   ├── views/     # 页面组件（大纲、编辑等）
│   │   ├── services/  # API 调用服务
│   │   └── ...
│   └── vite.config.ts # 前端配置
└── doc/               # 项目文档
    ├── API_*.md       # API 接口文档
    ├── CHANGES.md     # 更新日志，各个文件更新了哪里
    └── ...
```

---

## 💖 赞助商

| 赞助商 | 介绍 |
| --- | --- |
| <img src="https://www.aiwts.com/vitas/vitas-logo-transparent.webp" alt="维塔斯AI聚合" width="120"> | **[维塔斯AI聚合](https://www.aiwts.com/)** 是企业级 AI 大模型 API 聚合服务：开发者只需一个 Key，即可统一调用 GPT、Claude、DeepSeek、Gemini 等 200+ 模型（文本/生图/视频），完全兼容 OpenAI 协议，无需海外账号与信用卡 |

---

## 🚀 快速开始

### 快速体验
```
# 启动前端
cd frontend
npm install
npm run dev

# 启动模拟后端
cd backend/mock_api
python mock_main.py
```

### 🎯 一键部署（推荐）

#### 新增功能：统一配置 + 一键启动

```bash
# 1. 根目录下配置环境变量
cp env_template.txt .env
修改.env # 填入你的API密钥

# 2. 一键启动生产环境
python start.py
```

**功能特性：**
- ✅ **统一配置管理** - 所有环境变量集中在各自的`.env`文件
- ✅ **自动化部署** - 依赖安装、前端构建、服务启动一键完成
- ✅ **完整监控** - 进程监控、日志管理、优雅停止
- ✅ **生产就绪** - 适合正式环境的性能和稳定性配置

**访问地址：**
- 前端界面：`http://127.0.0.1:5173`

> 📚 详细说明请参考：[生产环境部署指南](README_PRODUCTION.md)

---

### 分别启动前后端服务

#### 方法二：一键启动

使用我们提供的启动脚本，可以一键启动所有后端服务：

```bash
cd backend
pip install -r requirements.txt
python start_backend.py
```

**功能特性：**
- ✅ 自动检查Python版本和依赖
- ✅ 自动安装所需包
- ✅ 端口占用检测和清理（需要用户确认）
- ✅ 自动设置环境文件
- ✅ 多进程管理和监控

#### 方法三：手动启动

1. 进入后端目录：

   ```bash
   cd backend
   ```
2. 安装依赖：

   ```bash
   pip install -r requirements.txt
   ```
3. 启动主 API 服务（默认运行在 `http://127.0.0.1:6800`）：

   ```bash
   cd main_api
   cp env_template .env
   python main.py
   ```
4. 启动大纲生成服务（默认运行在 `http://127.0.0.1:10001`）：

   ```bash
   cd backend/simpleOutline
   cp env_template .env   #复制完成后，修改.env文件
   python main_api.py
   ```
5. 启动 PPT 内容生成服务（默认运行在 `http://127.0.0.1:10011`）：

   ```bash
   cd backend/slide_agent
   cp env_template .env  #复制完成后，修改.env文件
   python main_api.py
   ```

> **详细说明：** 请参考 [backend/启动说明.md](backend/启动说明.md)

### 前端服务

1. 进入前端目录：

   ```bash
   cd frontend
   ```
2. 安装依赖：

   ```bash
   npm install
   ```
3. 启动开发服务器（默认运行在 `http://127.0.0.1:5173`）：

   ```bash
   npm run dev
   ```

> **提示**: 前端通过 Vite 代理与后端 API 通信，具体配置请查看 `frontend/vite.config.ts`。

#### 方法四：docker compose一键部署(确保能连接docker hub网络)
需要先按照手动启动中的方法对每个后端服务的.env都进行配置，确保每个容器都使用各自的.env文件
docker compose up 

---

## 🤖 AI 生成流程

1. **输入主题** → 用户在前端输入主题
2. **生成大纲** → 调用 `/api/tools/aippt_outline`，生成 Markdown 格式的大纲
3. **生成内容** → 调用 `/api/tools/aippt`，结合模板逐页生成内容
4. **实时渲染** → 前端渲染并展示完整 PPT

---

## 📑 流程图

PPTGen：可以扩展为更多功能的Agent，例如检查质量（图表等)
```mermaid
flowchart TD
  U((用户)) --> FE[前端界面]
  FE -->|输入主题| API[后端 API]

  API -->|调用大纲服务| Outline[大纲服务]
  Outline -->|调用 Web搜索| WebSearch1[Web 搜索]
  Outline --> API

  FE -->|确认大纲| API --> PPTGen[PPT生成服务：内部循环和检查Json格式]
  PPTGen -->|调用 Web搜索| WebSearch2[Web 搜索]
  PPTGen -->|调用 配图搜索| ImgSearch[配图搜索]
  PPTGen -->|调用 搜索上传文件| DBSearch[知识库]
  PPTGen --> API

  FE -->|渲染展示 PPT| U
```

---

## 🖼 界面示意

* **大纲生成**
  ![outline.png](doc/outline.png)

* **模板选择**
  ![select_template.png](doc/select_template.png)

* **逐页生成 PPT**
  ![start_ppt_generate.png](doc/start_ppt_generate.png)

* **图表支持 PPT**
  ![图表支持.png](doc/%E5%9B%BE%E8%A1%A8%E6%94%AF%E6%8C%81.png)


---

## 📌 待办事项
* [x] 图表的支持
* [ ] 支持上传自定义 PPT 模板并自动标注

---

## 📖 文档与参考

* [更新日志](doc/CHANGES.md)
* [自定义模板说明](doc/Template.md)
* [模版制作](doc/Template.md)
* [不同的模型配置](doc/custom_model.md)
* [PPT的图片说明]doc/Image.md
---

## 📝 关于前端引用项目（本项目后端免版权，但前端部分为AGPL-3版权）：
  [https://github.com/pipipi-pikachu/PPTist](https://github.com/pipipi-pikachu/PPTist)

## 📬 联系方式

如有问题，请联系作者：
![weichat.png](doc/weichat.png)

---
