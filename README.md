# Mythos AI

**Textbook-Grounded Learning Platform for Classical Greek and Roman Mythology**

基于《Classical Mythology》(Morford, Lenardon, Sham · Oxford University Press) 教材的 AI 辅助教学系统。

---

## 🌐 在线地址

| 前端 | 后端 API |
|------|----------|
| https://lanhui18115-than.github.io/mythos-ai/output/index.html | https://mythos-ai-o8kd.onrender.com |

---

## 📸 界面预览

| 首页 | 学习中心 |
|:---:|:---:|
| ![首页](screenshots/home.png) | ![学习中心](screenshots/learning_center_1.png) |

| 角色索引 | 家族树 |
|:---:|:---:|
| ![角色索引](screenshots/character_index_1.png) | ![家族树](screenshots/family_tree_1.png) |

| 知识测验 | 填字游戏 |
|:---:|:---:|
| ![知识测验](screenshots/quiz.png) | ![填字游戏](screenshots/crossword.png) |

| 艺术品识别 | AI Tutor |
|:---:|:---:|
| ![艺术品识别](screenshots/artwork_quiz_1.png) | ![AI Tutor](screenshots/ai_tutor.png) |

---

## 🎯 教育目标

面向英语语言文学本科生的神话学辅助教学平台，结合：

- 教材阅读
- AI 助教导学
- 知识图谱检索
- 互动测验
- 填字游戏
- 艺术品识别
- 神话角色探索

**核心原则：Textbook First, AI Second.** 所有知识来源于教材，AI 仅用于组织和呈现。

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────┐
│  Layer 4: AI Tutor                                  │
│  RAG 检索 + DeepSeek API → 自然语言回答（含出处）      │
├─────────────────────────────────────────────────────┤
│  Layer 3: 学习层                                     │
│  测验 · 填字 · 艺术品识别 · 家族树 · 角色索引 · 学习中心 │
├─────────────────────────────────────────────────────┤
│  Layer 2: 知识图谱                                   │
│  1010 角色 · 402 神话 · 390 地点 · 433 概念 · 206 艺术品 │
│  3340 条关系 · 每一条关系均回溯教材章节页码             │
├─────────────────────────────────────────────────────┤
│  Layer 1: 教材原文                                   │
│  Classical Mythology · 11th Edition · Oxford UP      │
└─────────────────────────────────────────────────────┘
```

---

## ✨ 功能模块

| 页面 | 说明 |
|------|------|
| **🏠 首页** | 导航入口，全局统计（1010 角色，3340 关系） |
| **📚 学习中心** | 24 章章节阅读 + PDF 内嵌阅读器 + 章节测验 |
| **📖 角色索引** | 搜索/筛选 1010 个角色，含希腊名/罗马名/称号/家族关系/神话摘要 |
| **🌳 家族树** | 交互式可视化图谱，支持搜索+分类浏览 |
| **📝 知识测验** | 选择题/判断题/匹配题/简答题，每题标注教材出处 |
| **🧩 填字游戏** | 自动生成网格，键盘导航，检查答案 |
| **🎨 艺术品识别** | 基于教材 206 件艺术品的识别与匹配 |
| **🤖 AI Tutor** | 浮动聊天组件，RAG 检索 + DeepSeek API，支持中英文双语查询 |

---

## 🛠️ 技术栈

| 层 | 技术 |
|----|------|
| 前端 | 原生 HTML/CSS/JS（无框架依赖） |
| 数据 | 知识图谱 JSON + 静态索引 |
| 可视化 | vis-network（家族树） |
| 后端 | Python Flask + Gunicorn |
| AI | DeepSeek API（OpenAI 兼容接口） |
| 部署 | GitHub Pages（前端）+ Render（后端） |

---

## 🚀 本地运行

### 前提条件

```
Python 3.10+
```

### 安装依赖

```bash
pip install -r scripts/requirements.txt
```

### 启动 AI Tutor 后端（可选）

```bash
py -3 scripts/ai_tutor_server.py
```

后端默认运行在 http://localhost:5800。如果不启动，AI Tutor 自动降级为纯前端本地搜索模式。

### 重新生成学习活动

```bash
py -3 scripts/14_build_tutor_index.py    # AI Tutor 索引
py -3 scripts/12_character_index.py      # 角色索引
py -3 scripts/13_learning_center.py      # 学习中心
py -3 scripts/04_family_tree.py          # 家族树
py -3 scripts/05_quiz_generator.py       # 测验
py -3 scripts/06_crossword_generator.py  # 填字游戏
py -3 scripts/07_artwork_quiz.py         # 艺术品测验
```

然后直接用浏览器打开 `output/index.html`。

---

## 📁 项目结构

```
MYTH PROJECT/
├── output/              # 生成的 HTML 页面（可直接打开）
│   ├── index.html       # 首页
│   ├── learning_center.html
│   ├── character_index.html
│   ├── family_tree.html
│   ├── quiz.html
│   ├── crossword.html
│   ├── artwork_quiz.html
│   └── ai_tutor_widget.js
├── data/                # 知识图谱与索引
│   ├── knowledge_graph.json    # 主知识图谱（2441 实体，3340 关系）
│   ├── ai_tutor_index.json     # AI Tutor 搜索索引
│   └── char_index_data.js      # 角色索引数据
├── scripts/             # 构建脚本（50 个 Python 脚本）
│   ├── ai_tutor_server.py      # AI Tutor 后端（RAG + LLM）
│   └── requirements.txt
├── textbook/            # 教材 PDF（版权文件，不纳入版本控制）
├── .env                 # API Key 配置（不纳入版本控制）
└── README.md
```

---

## 📚 知识来源

Morford, M., Lenardon, R. J., & Sham, M. *Classical Mythology* (11th Edition). Oxford University Press.

所有知识点分三级：
- **Level 1 — Explicit**：教材明确陈述
- **Level 2 — Implicit**：教材可合理推导
- **Level 3 — Supplementary**：仅作为可选拓展，不混入核心知识库

---

## 📄 许可证

仅供教育用途。
