# 烟草分档项目 (Tobacco Grading System)

这是一个基于 Vue 3 + FastAPI 的前后端分离项目，用于烟草客户的自动分档与管理。

## 项目结构

```
trce_jxyc/
├── backend/            # 后端 Python/FastAPI 项目
│   ├── main.py         # 后端入口
│   ├── grading_utils.py # 核心分档逻辑
│   └── requirements.txt # 后端依赖
├── frontend/           # 前端 Vue 3 项目
│   ├── src/            # 前端源码
│   └── package.json    # 前端依赖
└── README.md           # 项目说明
```

## 本地开发指南

### 1. 后端 (Backend)

**环境要求**: Python 3.8+

1. 进入后端目录:
   ```bash
   cd backend
   ```

2. 安装依赖:
   ```bash
   pip install -r requirements.txt
   ```

3. 启动服务:
   ```bash
   # 在项目根目录下运行
   uvicorn backend.main:app --reload --port 8000
   ```
   API 文档地址: http://localhost:8000/docs

### 2. 前端 (Frontend)

**环境要求**: Node.js 18+

1. 进入前端目录:
   ```bash
   cd frontend
   ```

2. 安装依赖:
   ```bash
   npm install
   ```

3. 启动开发服务器:
   ```bash
   npm run dev
   ```
   访问地址: http://localhost:5173 (或终端显示的端口)

## 部署说明

请参考 `DEPLOY.md` 文件获取详细的 Linux 部署指南。
