# 📚 课程主导型学习导师系统

一个基于通义千问模型的智能学习辅导系统，采用"提问-引导-讲解-答疑"的教学模式，帮助用户高效学习各类专业资格认证考试。

## ✨ 主要特性

### 🤖 智能学习辅导
- 基于通义千问模型，提供专业的学习指导
- 采用课程主导型教学流程，系统化学习体验
- 支持多轮对话和对话历史管理

### 📄 文件处理能力
- 支持多种文件格式：TXT、PDF、DOCX、DOC、MD
- 异步文件处理，支持大文件上传（最大16MB）
- 智能文本提取和内容分析

### 🎨 优秀的用户体验
- **Markdown渲染**：支持丰富的文本格式展示
- **流式响应**：实时显示AI回复，提升交互体验
- **滚动控制**：便捷的聊天记录导航功能
- **响应式设计**：适配不同屏幕尺寸

### 🔧 技术特性
- 前后端分离架构
- 异步任务处理机制
- 线程安全的对话管理
- 完善的错误处理和用户反馈

## 🚀 快速开始

### 环境要求
- Python 3.7+
- 现代浏览器（支持ES6+）

### 安装依赖
```bash
pip install -r requirements.txt
```

### 配置环境变量
复制 `.env.example` 为 `.env` 并配置您的API密钥：
```bash
cp .env.example .env
```

编辑 `.env` 文件：
```env
DASHSCOPE_API_KEY=your_api_key_here
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
MODEL_NAME=qwen-turbo
```

### 运行应用
1. 启动后端服务：
```bash
python backend_api.py
```

2. 在浏览器中打开 `learning_tutor_app.html`

## 📁 项目结构

```
code/
├── backend_api.py              # 后端API服务
├── learning_tutor_app.html     # 前端界面
├── requirements.txt            # Python依赖
├── .env.example               # 环境变量模板
├── .gitignore                 # Git忽略文件
├── README.md                  # 项目说明
├── SOLUTION_SUMMARY.md        # 技术方案总结
├── conversations.json         # 对话历史存储
└── uploads/                   # 上传文件目录
```

## 🎯 功能演示

### 1. 智能学习规划
系统会自动分析上传的学习材料，制定个性化的学习计划：

```markdown
# 📚 人力资源管理 学习导师

## 📋 学习计划
1. **基础理论知识**
2. **实务操作技能** 
3. **案例分析应用**

> 💡 每个单元都会通过"提问-引导-讲解-答疑"的方式进行深度学习
```

### 2. 结构化教学内容
AI回复支持丰富的Markdown格式：

- **标题层次**：清晰的内容结构
- **列表格式**：要点归纳和步骤说明
- **表格展示**：对比分析和总结
- **代码块**：公式和重要定义
- **引用样式**：原文内容引用

### 3. 文件上传分析
支持上传学习材料，系统会：
- 自动提取文本内容
- 异步分析处理
- 生成学习计划
- 提供互动式学习体验

## 🛠️ 技术架构

### 后端技术栈
- **Flask**：Web框架
- **OpenAI API**：通义千问模型接口
- **ThreadPoolExecutor**：异步任务处理
- **PyPDF2 & python-docx**：文件内容提取

### 前端技术栈
- **原生JavaScript**：核心交互逻辑
- **Marked.js**：Markdown解析渲染
- **Highlight.js**：代码语法高亮
- **CSS3**：响应式样式设计

### 核心功能模块
1. **对话管理**：多轮对话和历史记录
2. **文件处理**：异步上传和内容提取
3. **任务调度**：后台任务状态管理
4. **流式响应**：实时内容展示
5. **Markdown渲染**：富文本格式支持

## 📊 API接口

### 对话相关
- `POST /api/new-conversation` - 创建新对话
- `POST /api/chat` - 发送消息（支持流式响应）

### 文件处理
- `POST /api/upload` - 上传文件
- `GET /api/task/<task_id>` - 获取任务状态
- `GET /api/analyze-stream/<conversation_id>` - 流式获取分析结果

## 🔒 安全特性

- 文件类型验证和大小限制
- 安全的文件名处理
- 环境变量配置敏感信息
- 线程安全的数据操作
- CORS跨域请求控制

## 🤝 贡献指南

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📝 更新日志

### v1.0.0 (2025-01-17)
- ✨ 初始版本发布
- 🎨 集成Markdown渲染功能
- 🚀 实现异步文件处理
- 📱 添加响应式设计和滚动控制
- 🔧 完善错误处理和用户反馈

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 🙏 致谢

- [通义千问](https://tongyi.aliyun.com/) - 提供强大的AI模型支持
- [Marked.js](https://marked.js.org/) - Markdown解析库
- [Highlight.js](https://highlightjs.org/) - 代码高亮库

---

⭐ 如果这个项目对您有帮助，请给它一个星标！
