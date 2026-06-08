# PARA 任务笔记一体化系统

基于 **PARA 方法** 统一组织你的工作与知识。内置完整的任务和笔记管理功能，可选同步 **滴答清单 (TickTick)** 与 **Flomo**，亦可完全独立使用。

## 功能特点

### 任务管理

* 直接在本地创建、编辑、删除任务，无需外部服务
* 支持优先级、截止日期、标签
* 可选同步 TickTick：从 TickTick 导入任务列表，完成状态自动同步回 TickTick

### 笔记记录

* 两种笔记入口：**自由笔记** 随时记录灵感，**完成感想** 在任务完成时沉淀经验
* 完成感想自动继承任务标签，形成统一的知识网络
* 支持编辑和删除笔记
* 可选同步 Flomo：笔记自动保存到 Flomo

### PARA 标签体系

* 四级分类：**01-Projects** / **02-Areas** / **03-Resources** / **04-Archives**
* 多级标签嵌套（如 `01-Projects/网站开发/前端`）
* 任务和笔记按 PARA 一级标签自动分栏展示

### 智能标签输入

* 标签输入框支持实时搜索已有标签
* **Tab 键** 快速选中，全程键盘操作无需鼠标

### AI 摘要

* 每日自动汇总当天完成的任务和记录的笔记
* 支持 OpenAI / Ollama 等兼容接口（可选配置）

## 技术栈

|层|技术|
|-|-|
|后端|Python 3.12 + FastAPI|
|前端|HTML + Alpine.js + Tailwind CSS|
|数据库|SQLite + SQLAlchemy (异步)|
|任务同步|TickTick V2 Session API（可选）|
|笔记同步|Flomo Pro 专属记录 API（可选）|

## 快速开始

### 1\. 克隆项目

```bash
git clone https://github.com/yutuotuo84/para-tracker.git
cd para-tracker
```

### 2\. 安装依赖

```bash
pip install -r requirements.txt
```

### 3\. 配置环境变量

复制 `.env.example` 为 `.env`，按需填写：

```bash
cp .env.example .env
```

```ini
# ─── TickTick 同步（可选） ───
# 留空则不启用 TickTick 同步，任务完全在本地管理
TICKTICK\_USERNAME=your\_email@example.com
TICKTICK\_PASSWORD=your\_password

# ─── Flomo 同步（可选） ───
# 留空则不启用 Flomo 同步，笔记仅保存在本地数据库
# 在 Flomo 网页版 → 设置 → 专属记录 API 中获取
FLOMO\_API\_URL=https://flomoapp.com/iwh/xxxxx/xxxxx/

# ─── AI 摘要（可选） ───
# 不配置则使用模板生成
AI\_API\_KEY=sk-your-key
AI\_API\_BASE=https://api.openai.com/v1
AI\_MODEL=gpt-3.5-turbo

# TickTick 同步间隔（秒，默认 300）
SYNC\_INTERVAL=300
```

### 4\. 启动服务

**Windows：**

```bash
start.bat
```

**手动启动：**

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 5\. 访问应用

打开浏览器访问 [http://localhost:8000](http://localhost:8000)

## 使用指南

### 首次使用

1. 启动后直接开始使用，所有数据存储在本地
2. 如需 TickTick 同步，进入 **设置** 页面填写账号密码
3. 如需 Flomo 同步，在 **设置** 页面填入专属记录 API 地址

### 任务操作

* **查看任务**：任务页面按 PARA 分类分栏展示
* **创建任务**：点击"新建任务"，填写标题、优先级、截止日期、标签
* **完成任务**：点击任务左侧的复选框，弹出笔记框记录完成感想
* **编辑任务**：点击任务右侧的编辑按钮
* **删除任务**：点击任务右侧的删除按钮

### 笔记操作

* **自由笔记**：在笔记页面点击"写笔记"，选择标签，撰写内容
* **完成感想**：完成任务时自动弹出，继承任务标签
* **编辑笔记**：点击笔记右侧的编辑按钮，可修改内容和标签
* **删除笔记**：点击笔记右侧的删除按钮

### 标签输入技巧

在任务、笔记的标签输入框中：

1. 输入任意字符搜索已有标签
2. 使用 **↑/↓** 方向键切换候选
3. 按 **Tab** 键快速选中
4. 选中后自动填入输入框

### PARA 标签管理

* 在 PARA 页面查看完整的标签树
* **一级标签**（01/02/03/04）不可编辑和删除
* **子标签** 支持修改名称和删除

## 项目结构

```
para-tracker/
├── main.py                  # FastAPI 应用入口
├── models.py                # SQLAlchemy 数据模型
├── database.py              # 数据库连接与会话管理
├── requirements.txt         # Python 依赖
├── .env.example             # 环境变量模板
├── start.bat                # Windows 启动脚本
│
├── services/
│   ├── ticktick\_service.py  # TickTick API 集成
│   ├── flomo\_service.py     # Flomo API 集成
│   ├── para\_service.py      # PARA 标签管理
│   └── summary\_service.py   # 每日总结生成
│
├── routers/
│   ├── tasks.py             # 任务 API
│   ├── memos.py             # 笔记 API
│   ├── para.py              # PARA 标签 API
│   ├── summary.py           # 每日总结 API
│   └── auth.py              # 认证 \& 同步 API
│
├── static/
│   ├── index.html           # 主页面 (Alpine.js)
│   ├── app.js               # 前端逻辑
│   └── styles.css           # 样式
│
└── data/
    └── para\_tracker.db      # SQLite 数据库（自动生成）
```

## API 概览

|方法|路径|说明|
|-|-|-|
|GET|`/api/tasks`|获取任务列表|
|POST|`/api/tasks`|创建任务|
|PUT|`/api/tasks/{id}`|编辑任务|
|DELETE|`/api/tasks/{id}`|删除任务|
|POST|`/api/tasks/{id}/toggle`|切换任务完成状态|
|GET|`/api/memos`|获取笔记列表|
|POST|`/api/memos`|创建笔记|
|POST|`/api/memos/from-task`|创建任务完成笔记|
|PUT|`/api/memos/{id}`|编辑笔记|
|DELETE|`/api/memos/{id}`|删除笔记|
|GET|`/api/para/tags`|获取 PARA 标签树|
|POST|`/api/para/tags`|创建标签|
|PUT|`/api/para/tags/{id}`|编辑标签|
|DELETE|`/api/para/tags/{id}`|删除标签|
|GET|`/api/summary/today`|获取今日总结|
|POST|`/api/summary/generate`|生成 AI 总结|

## License

MIT

