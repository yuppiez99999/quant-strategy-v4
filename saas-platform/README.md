# QuantMatrix SaaS - 智能量化策略平台

> **融合康波周期 + 十五五规划 + 社保基金ETF追踪 + AI Hedge Fund 的新一代量化策略SaaS平台**

## 项目概述

QuantMatrix 是一个面向机构投资者的**智能量化策略SaaS平台**，核心策略引擎基于康波周期宏观分析、十五五规划政策适配、社保基金ETF追踪和19位AI投资大师分析。平台提供从宏观分析、行业配置、组合管理到风险监控的全链条量化决策支持。

## 技术栈

| 层级 | 技术 | 用途 |
|------|------|------|
| 前端 | React 19 + TypeScript + Vite | SPA应用 |
| UI框架 | Tailwind CSS + shadcn/ui (53组件) | 暗色主题界面 |
| 图表 | Recharts | 饼图/柱状图/雷达图/矩形树图 |
| 路由 | React Router v7 | 客户端路由 |
| 后端 | FastAPI (Python 3.11+) | REST API |
| 数据库 | PostgreSQL 16 + Redis 7 | 用户数据/缓存 |
| 部署 | Docker + Nginx + docker-compose | 容器化部署 |

## 功能模块

### 客户端 (React SPA)

| 页面 | 路由 | 功能 |
|------|------|------|
| 落地页 | `/` | 产品介绍、功能展示、定价方案 |
| 登录/注册 | `/login`, `/register` | 邮箱密码认证 |
| 仪表盘 | `/dashboard` | 组合总览、关键指标、康波信号、AI推荐 |
| 投资组合 | `/portfolio` | 14只标的持仓明细、风险指标、权重偏离 |
| 市场分析 | `/market` | 宏观指标、康波周期、十五五规划对齐度 |
| 康波周期 | `/kondratiev` | 四阶段定位、行业配置建议 |
| ETF资金流 | `/etf` | 24只ETF监控、矩形树图、风格轮动信号 |
| AI分析 | `/ai-analysis` | 19位AI分析师多维度信号与综合评分 |
| 宏观数据 | `/macro` | 经济指标表、雷达图、综合判断 |
| 报告中心 | `/reports` | 历史报告搜索/预览/下载 |
| 定价 | `/pricing` | 三档订阅方案（免费/专业/企业） |
| 设置 | `/settings` | 个人资料、订阅管理、通知偏好 |

### 分析引擎 (Python Quant Modules)

- **康波周期分析**：第六轮康波（AI/算力驱动）四阶段定位
- **十五五规划适配**：7大战略方向对齐度评分与权重建议
- **社保基金ETF追踪**：4大风格分类、国家队资金流向检测
- **AI Hedge Fund**：19位投资大师AI分析师（LangGraph工作流）
- **4大投资理论**：索罗斯反身性、达利欧经济机器、第一性原理、巴菲特芒格
- **时序预测**：TimesFM 2.5 / Kronos / Qwen2.5
- **期货期权扫描**：SHF/DCE/CZCE/CFFEX/INE全品种
- **风险监控**：VaR/CVaR/止损止盈/最大回撤/波动率

### 后端API (FastAPI)

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/health` | GET | 健康检查 |
| `/api/auth/register` | POST | 用户注册 |
| `/api/auth/login` | POST | 用户登录 |
| `/api/portfolio/assets` | GET | 持仓列表 |
| `/api/portfolio/summary` | GET | 组合概要 |
| `/api/portfolio/risk` | GET | 风险指标 |
| `/api/analysis/kondratiev` | GET | 康波周期分析 |
| `/api/analysis/five-year-plan` | GET | 十五五规划对齐 |
| `/api/analysis/macro` | GET | 宏观经济指标 |
| `/api/etf/flows` | GET | ETF资金流向 |
| `/api/ai/analysis/{ticker}` | GET | AI分析师报告 |
| `/api/reports` | GET | 历史报告 |
| `/api/user/profile` | GET/PUT | 用户资料 |

## 快速开始

### 前端开发

```bash
cd saas-platform
npm install
npm run dev          # 启动开发服务器 → http://localhost:5173
```

### 后端开发

```bash
cd saas-platform/backend
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

API文档：http://localhost:8000/api/docs

### Docker部署

```bash
cd saas-platform
docker-compose up -d   # 启动全部服务
```

前端：http://localhost:80
后端：http://localhost:8000

## 项目结构

```
saas-platform/
├── src/
│   ├── components/
│   │   ├── ui/              # shadcn/ui 组件 (53个)
│   │   └── layout/          # 布局组件 (Navbar, Sidebar, Footer, DashboardLayout)
│   ├── contexts/            # React Context (AuthContext)
│   ├── hooks/               # 自定义Hooks
│   ├── lib/                 # 工具函数 (utils, mock-data)
│   ├── pages/               # 12个页面组件
│   │   ├── Landing.tsx      # 落地页
│   │   ├── Login.tsx        # 登录
│   │   ├── Register.tsx     # 注册
│   │   ├── Dashboard.tsx    # 仪表盘
│   │   ├── Portfolio.tsx    # 投资组合
│   │   ├── MarketAnalysis.tsx  # 市场分析
│   │   ├── Kondratiev.tsx   # 康波周期
│   │   ├── ETFTracking.tsx  # ETF追踪
│   │   ├── AIAnalysis.tsx   # AI分析
│   │   ├── Macro.tsx        # 宏观数据
│   │   ├── Reports.tsx      # 报告中心
│   │   ├── Pricing.tsx      # 定价
│   │   └── Settings.tsx     # 设置
│   ├── types/               # TypeScript类型定义
│   ├── App.tsx              # 路由配置
│   └── main.tsx             # 入口文件
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI应用
│   │   ├── models.py        # Pydantic数据模型
│   │   └── quant_bridge.py  # 量化模块桥接
│   └── requirements.txt
├── Dockerfile               # 后端容器
├── Dockerfile.frontend      # 前端容器
├── docker-compose.yml       # 多服务编排
├── nginx.conf               # Nginx配置
├── .env.example             # 环境变量模板
└── package.json
```

## 设计系统

- **主题**：OLED暗色模式（#0d1117背景，低白光发射）
- **主色**：Blue #3B82F6（数据/图表强调）
- **辅色**：Amber #F59E0B（CTA/警告）
- **字体**：Fira Code（标题） + Fira Sans（正文）
- **效果**：玻璃态卡片、微光阴影、渐变色文字
- **图表**：Recharts专业配色，含tooltip交互

## 数据源优先级

```
Wind MCP (P0) → AKShare (P1) → Sina API (P2) → 本地缓存 (P3) → Mock数据 (P4)
```

## 定价方案

| 方案 | 价格 | 标的数 | 核心功能 |
|------|------|--------|----------|
| 免费版 | ¥0/月 | 3只 | 基础行情、日报摘要 |
| 专业版 | ¥299/月 | 50只 | 完整分析、AI参考、风险预警 |
| 企业版 | ¥2,999/月 | 无限 | 自定义策略、API接口、私有化部署 |

## 许可证

© 2026 QuantMatrix. All rights reserved.
