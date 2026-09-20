# 高校体育教师 AI 教学智能体

面向高校体育教师的单机网页端 AI 教学辅助平台（无学生端），覆盖「课前备课 → 课中教学 → 课后分析」完整闭环。

- 后端：Python 3.10+ / Flask + Flask-SQLAlchemy
- 数据库：SQLite（`data/app.db`）
- 前端：HTML + CSS + 轻量 JS（Jinja2 模板）+ ECharts
- AI：DeepSeek（文字 `deepseek-chat`，视觉 `deepseek-v4-flash-vision-exp`）

## 快速启动

双击项目根目录 `start.bat`，浏览器自动打开 `http://127.0.0.1:5000`。
默认账号：`admin` / `admin123`。

## 目录结构

```
├── app.py               # 入口 + 应用工厂 + 轻量迁移
├── config.py            # 配置（上传目录、帧目录等）
├── models.py            # SQLAlchemy 数据表
├── routes/              # 蓝图（auth/home/workbench/classroom/lesson_prep/modules/api/rag/admin）
├── services/            # AI 调用、体测评分、视频抽帧、视觉分析、姿态分析
├── templates/           # Jinja2 页面
├── static/              # 样式 / JS / ECharts / 上传文件
├── data/                # SQLite 数据库与临时数据
├── docs/                # 需求、技术、设计、数据库等文档
└── 开发日志/            # 每日开发日志与滚动待办
```

## AI 动作识别：MediaPipe 部署方案

「AI 动作识别」使用 MediaPipe 提取人体 33 个关键点、计算关节角度与力矩、绘制 2D 骨骼，并结合视觉模型生成文字诊断。

- `mediapipe` 用于姿态分析（骨骼关键点、关节角度、力矩估算）。
- 未安装 `mediapipe` 时，自动回退为纯文字诊断（无骨骼/关节参数），不影响文字诊断功能。

> 关键冲突：`mediapipe` 依赖 `opencv-contrib-python`，安装时会卸载替换项目现有的 `opencv-python-headless`，且运行中的 Flask 进程会锁住 `cv2.pyd` 导致 `[WinError 5] 拒绝访问`。

### 方案一：本地开发（单机调试，推荐个人使用）

1. 关闭 Flask 与所有 Python 进程（关闭 `start.bat` 窗口，确保没有 `python` 进程占用 `cv2.pyd`）。
2. 执行安装并接受 opencv 包替换：
   ```bash
   pip install mediapipe
   ```
3. 重新双击 `start.bat` 启动，进入「AI 动作识别」选择「基础模式（MediaPipe）」即可自动生效，无需改代码。

> 注意：此方案只适合本地调试。`mediapipe` 替换了 `opencv-python-headless` 后，如后续需要纯 headless 环境，需手动重新安装 `opencv-python-headless`。

### 方案二：生产部署（独立微服务，规避包冲突）

为规避 `mediapipe` 与 `opencv-python-headless` 的包冲突和文件占用，推荐把姿态分析拆成独立微服务：

1. 新建独立虚拟环境，单独安装 `mediapipe` + `opencv-python`：
   ```bash
   python -m venv pose_venv
   pose_venv\Scripts\activate
   pip install flask mediapipe opencv-python numpy
   ```
2. 在该微服务中暴露 HTTP 接口（例如 `POST /pose/analyze`，接收视频文件，返回 33 关键点、关节角度、力矩）。
3. 主 Flask 项目**保持 `opencv-python-headless` 不变**，把 `services/pose_analysis.py` 里的 `analyze_pose` 改为调用该微服务接口（HTTP 请求），返回 JSON 后照常入库。

这样主项目不引入 `mediapipe` 依赖，两个环境完全隔离，互不影响。

## 环境检测

后端提供 `GET /action/mediapipe-status` 接口，返回 MediaPipe 是否已安装；未安装时前端提示「仅文字诊断」，不影响文字诊断功能。

## 其他模块

教案生成/修订、体质健康分析、班级-运动项目配置、教学进度导入、备课成果管理等模块均已实现，详见 `docs/` 目录与 `开发日志/`。

## 二期规划

- 后续可扩展接入 **OpenCap 3D 生物力学分析**（依赖 `app.opencap.ai` 云端 API 与账号凭证），提供真实 3D 骨骼、生物力学关节角度与关节力矩，用于专项评估、科研场景。
