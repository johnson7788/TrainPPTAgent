# 🚀 TrainPPTAgent 生产环境部署指南

## ✨ 新增功能

### 📋 统一ENV管理
- **统一配置文件**: 根目录下的 `.env` 文件管理所有服务配置
- **配置模板**: `env_template` 提供完整的配置说明
- **智能读取**: 各服务自动读取统一配置，支持命令行参数覆盖

### 🎯 一键生产部署
- **自动构建**: 自动执行前端 `npm run build`
- **依赖管理**: 自动安装前后端依赖
- **服务启动**: 一键启动所有后端服务和前端静态服务
- **进程监控**: 自动监控服务状态，异常时重启

## 🚀 快速开始

### 1. 配置环境变量

```bash
# 复制配置模板
cp env_template .env

# 编辑配置文件，填入你的API密钥
nano .env
```

**必须配置的重要项**:
```bash
# 选择你要使用的模型供应商
MODEL_PROVIDER=deepseek
LLM_MODEL=deepseek-chat

# 填入对应的API密钥
DEEPSEEK_API_KEY=your_actual_api_key_here
```

### 2. 一键启动生产环境

```bash
# 生产模式启动（推荐）
python start_production.py
```

**功能特性**:
- ✅ 自动检查环境依赖
- ✅ 自动安装项目依赖
- ✅ 自动构建前端项目
- ✅ 自动启动所有服务
- ✅ 端口冲突检测和清理
- ✅ 进程监控和日志管理

### 3. 访问应用

生产环境启动后：
- **前端界面**: http://your-server-ip:5173
- **主API**: http://your-server-ip:6800
- **大纲服务**: http://your-server-ip:10001
- **内容生成**: http://your-server-ip:10011

## 📁 项目结构更新

```
TrainPPTAgent/
├── .env                      # 🆕 统一环境配置
├── .env.template            # 🆕 配置模板
├── start_production.py     # 🆕 生产环境启动脚本
├── logs/                   # 🆕 统一日志目录
│   ├── production.log      # 主日志
│   ├── main_api.log       # 各服务日志
│   ├── outline.log
│   └── content.log
├── backend/
│   ├── start_backend.py   # 原开发模式启动脚本
│   └── ...
└── frontend/
    ├── dist/              # 构建后的静态文件
    └── ...
```

## ⚙️ 配置说明

### 服务器配置
```bash
# 生产/开发模式
PRODUCTION=true

# 服务绑定地址
HOST=0.0.0.0

# 各服务端口
MAIN_API_PORT=6800
OUTLINE_API_PORT=10001
CONTENT_API_PORT=10011
FRONTEND_PORT=5173
```

### AI模型配置
```bash
# 模型供应商选择
MODEL_PROVIDER=deepseek  # google, openai, deepseek, claude, ali

# 对应模型
LLM_MODEL=deepseek-chat

# API密钥（根据选择的供应商填写对应密钥）
DEEPSEEK_API_KEY=your_key
GOOGLE_API_KEY=your_key
OPENAI_API_KEY=your_key
CLAUDE_API_KEY=your_key
ALI_API_KEY=your_key
```

### 流式响应配置
```bash
# 大纲服务流式响应（推荐开启）
OUTLINE_STREAMING=true

# 内容生成流式响应（推荐关闭，避免JSON解析问题）
CONTENT_STREAMING=false
```

## 🔧 高级功能

### 开发模式 vs 生产模式

**开发模式**（原方式）:
```bash
# 后端开发启动
cd backend
python start_backend.py

# 前端开发启动
cd frontend
npm run dev
```

**生产模式**（新方式）:
```bash
# 一键生产部署
python start_production.py
```

### 日志管理

生产环境自动生成日志：
- `logs/production.log`: 主启动日志
- `logs/main_api.log`: 主API服务日志
- `logs/outline.log`: 大纲生成服务日志
- `logs/content.log`: 内容生成服务日志

### 进程管理

生产脚本提供完整的进程管理：
- **自动监控**: 监控服务状态，异常时记录日志
- **优雅停止**: Ctrl+C 优雅停止所有服务
- **端口清理**: 自动检测并清理端口冲突
- **资源回收**: 确保所有进程正确释放资源

## 🔒 生产环境建议

### 安全配置
1. **API密钥**: 妥善保管 `.env` 文件，不要提交到代码仓库
2. **端口安全**: 生产环境建议使用防火墙限制端口访问
3. **反向代理**: 建议使用Nginx等反向代理服务器

### 性能优化
1. **工作进程**: 根据CPU核心数调整 `WORKERS` 参数
2. **并发连接**: 根据服务器配置调整 `MAX_CONNECTIONS`
3. **超时设置**: 根据实际需求调整 `REQUEST_TIMEOUT`

### 监控告警
1. **日志监控**: 定期检查 `logs/` 目录下的日志文件
2. **服务状态**: 使用 `systemd` 等服务管理器进一步增强稳定性
3. **资源监控**: 监控CPU、内存、磁盘使用情况

## ❓ 常见问题

### 1. 端口被占用
```bash
# 自动处理：启动脚本会自动检测并询问是否清理
# 手动处理：
netstat -tulpn | grep :6800
sudo kill -9 <PID>
```

### 2. 前端构建失败
```bash
# 检查Node.js版本
node --version  # 需要 v16+

# 手动构建
cd frontend
npm install
npm run build
```

### 3. API密钥配置
```bash
# 确保在 .env 文件中配置了正确的密钥
# 检查MODEL_PROVIDER对应的密钥是否已填写
cat .env | grep API_KEY
```

### 4. 服务启动失败
```bash
# 查看详细日志
tail -f logs/production.log
tail -f logs/main_api.log
```

## 🎉 升级优势

相比原来的部署方式，新的生产部署具有以下优势：

1. **🔧 配置统一**: 一个文件管理所有配置，避免重复配置
2. **🚀 一键部署**: 单个命令完成完整部署流程
3. **📊 监控完善**: 统一日志和进程监控
4. **🔒 生产就绪**: 适合生产环境的配置和优化
5. **🛠 易于维护**: 清晰的目录结构和日志管理

立即体验新的生产部署方式！