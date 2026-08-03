<h1 align="center">补习班教务管理系统</h1>

<p align="center">
  一个面向中小型培训机构的教务管理平台，覆盖学生、教师、教室、课程排课、考勤记录与课表调整的全流程。
</p>

---

## 功能概览

- **用户认证** — 登录/注册，支持管理员与普通员工角色
- **学生管理** — 学生档案（姓名、年级、电话、备注），支持初中/高中六档
- **教师管理** — 教师档案与任教学科关联
- **教室管理** — 教室类型（大教室、小教室、自习室）与容量
- **课程管理** — 排课支持周一至周日、五个时段，自动检测教室/时间冲突
- **学生选课** — 关联学生到课程，大班小班灵活分配
- **考勤管理** — 按课程按日记录出勤/缺勤，支持考勤报表导出
- **课表调整** — 临时调课、换教室，保留原排课记录

- **成绩管理** — 记录学生在校考试和补习班小测验成绩，区分考试类型
- **数据分析** — 考勤率统计、成绩分布、分科对比、趋势图表
- **学生雷达图** — 每位学生各学科成绩+出勤率双轴雷达可视化
- **AI 智能报告** — 接入 DeepSeek API，一键生成学生个性化分析报告（含总体评价、强弱项、建议），自动保存最新报告并支持导出 PDF

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | React 19 + TypeScript + Tailwind CSS 4 + Vite 8 |
| 图标 | Lucide React |
| 后端 | Python 3.11+ / FastAPI / SQLAlchemy 2 / Pydantic |
| 数据库 | SQLite |
| 容器化 | Docker + Docker Compose |
| 打包 | PyInstaller（Windows 单文件 exe） |

## 项目结构

```
.
├── frontend/                  # React 前端源码
│   └── src/
│       ├── App.tsx            # 主应用组件
│       ├── api.ts             # API 请求封装
│       └── types.ts           # TypeScript 类型定义
├── backend/                   # Python 后端
│   ├── app/
│   │   ├── main.py            # FastAPI 入口 + 静态文件服务
│   │   ├── models.py          # SQLAlchemy 数据模型
│   │   ├── schemas.py         # Pydantic 验证模型
│   │   ├── database.py        # 数据库连接与会话
│   │   └── routers/           # API 路由
│   │       ├── auth.py        # 认证接口
│   │       ├── students.py    # 学生 CRUD
│   │       ├── teachers.py    # 教师 CRUD
│   │       ├── subjects.py    # 科目 CRUD
│   │       ├── rooms.py       # 教室 CRUD
│   │       ├── courses.py     # 课程与排课
│   │       ├── attendance.py  # 考勤记录
│   │       └── adjustments.py # 课表调整
│   ├── static/                # 前端构建产物
│   ├── launcher.py            # 启动入口（开发/Docker/exe 通用）
│   └── requirements.txt
├── data/                      # 数据库文件
├── docker-compose.yml
├── Dockerfile
├── build.bat                  # Windows 构建脚本
└── start.bat                  # Windows 启动脚本
```

## 快速开始

### 方式一：Docker（推荐）

```bash
docker compose up -d
```

访问 `http://localhost:5000`。数据持久化在 `./data` 目录。

### 方式二：Windows 本地运行

**开发模式：**

```bash
# 终端 1 — 启动后端
cd backend
pip install -r requirements.txt
python launcher.py

# 终端 2 — 启动前端开发服务器
cd frontend
npm install
npm run dev
```

**打包为 exe（生产部署）：**

```bash
# 需先安装 PyInstaller
pip install pyinstaller
build.bat
```

构建完成后运行 `start.bat` 即可启动，浏览器会自动打开。

### 方式三：纯 Python 运行

```bash
cd backend
pip install -r requirements.txt
python launcher.py
```

后端会检测端口可用性（优先 5000，自动查找 5000–5010），并自动在浏览器中打开管理页面。

## 默认账户

| 角色 | 用户名 | 密码 |
|------|--------|------|
| 管理员 | `admin` | `admin123` |

首次启动会自动创建预置数据：9 门学科、5 间教室。

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `TUTORING_HOST` | `0.0.0.0` | 监听地址 |
| `TUTORING_PORT` | `5000` | 监听端口 |
| `TUTORING_DB` | `tutoring.db` | 数据库文件路径 |
| `DOCKER_ENV` | — | Docker 环境标识（容器内自动设置） |

## API 概览

| 前缀 | 说明 |
|------|------|
| `/auth` | 登录、注册、令牌验证 |
| `/students` | 学生增删改查 |
| `/teachers` | 教师与任教学科管理 |
| `/subjects` | 学科列表 |
| `/rooms` | 教室管理 |
| `/courses` | 课程排课（含学生关联与冲突检测） |
| `/attendance` | 考勤记录与报表 |
| `/adjustments` | 课表临时调整 |

| `/scores` | 成绩记录（CRUD + 多条件筛选） |
| `/analysis` | 数据分析（考勤/成绩分析、雷达图、AI报告） |
| `/settings` | 系统设置（DeepSeek API Key 配置） |
| `/demo` | 演示数据生成 |
| `/analysis/ai-report` | AI 报告生成、最新报告读取、PDF 导出 |

## License

MIT
