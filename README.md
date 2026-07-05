# Embodied Visual Search

基于 AI2-THOR 的在线交互版具身视觉搜索 Agent。系统提供机器人第一视角 `robot view`、第三方房间观察视角 `room view`、手动控制、room view 点选目标生成参考图，以及基于 OpenAI-compatible `/chat/completions` 的多模态 LLM 自动搜索链路。

## 核心功能

- 场景选择与加载，支持按房间类型切换 AI2-THOR 场景。
- `robot view` 第一视角显示当前机器人观察。
- `room view` 第三方房间视角显示、鼠标悬停 inspect、拖拽/QE 旋转观察、点击物体选择目标。
- 点击 room view 物体后自动聚焦，并生成 target reference image 作为视觉目标参考。
- 手动动作控制，前后端动作空间保持一致，支持移动、旋转、视角调整和基础结束动作。
- Agent 自动搜索，保留 `/api/agent/reset`、`/api/agent/step`、`/api/agent/run`、`/api/agent/stop`、`/api/agent/state`、`/api/trajectory`。
- OpenAI-compatible 模型配置：`base_url`、`api_key`、`model`、`temperature`、`max_tokens`、`timeout`、`vision_enabled`。
- 搜索记忆与轨迹记录，保留 `checked`、`ruled_out`、`avoid`、`recent_clues`、last feedback、recent trajectory，以及每步 thought / action / result / memory_update / robot_view。

## 目录结构

```text
backend/    FastAPI 后端、AI2-THOR 环境封装、Agent、动作执行、schema
frontend/   React + Vite 前端页面与 API 封装
data/       运行生成的数据目录（轨迹、观察截图、目标截图）
scripts/    调试/检查/冒烟脚本
tests/      后端单元测试
```

## 环境配置

### 后端依赖

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 前端依赖

```bash
cd frontend
npm install
```

### AI2-THOR 运行说明

- 默认使用 `AI2THOR_PLATFORM`、`AI2THOR_X_DISPLAY`、`AI2THOR_FORCE_GLCORE` 等环境变量控制渲染方式。
- `backend/launch_backend.py` 和 `start_backend.sh` 提供了 Linux/WSL 图形环境常用默认值。
- 若 AI2-THOR 在 WSL / Linux 图形环境中异常，需要检查 `DISPLAY`、X Server、OpenGL / Mesa / 显卡渲染环境。

### OpenAI-compatible API 配置

- 模型设置通过前端页面保存到本地配置文件。
- 接口需兼容 OpenAI 风格 `/chat/completions`。
- `vision_enabled=true` 时，后端会向模型发送当前 `robot view`，若已选择目标，还会附带 target reference image。

## 启动方式

后端：

```bash
uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload
```

或：

```bash
python backend/launch_backend.py
```

前端：

```bash
cd frontend
npm run dev
```

浏览器访问：

- 前端默认地址：`http://localhost:5173`
- 后端默认地址：`http://localhost:8000`

如需前端显式指定后端地址，可设置 `VITE_API_BASE_URL`。

## 使用流程

1. 启动后端与前端。
2. 在前端选择房间类型和场景，加载 AI2-THOR 场景。
3. 在模型设置面板填写 OpenAI-compatible 配置并保存。
4. 通过 `room view` 观察环境，可悬停查看物体信息、拖拽调整视角。
5. 点击 room view 中的目标物体，系统会聚焦并生成 target reference image。
6. 输入任务指令，启动 Agent 自动搜索，或先用手动动作控制机器人。
7. 在主页面和轨迹页面查看每一步 thought、action、feedback、memory update 与 robot view。

## 注意事项

- `vision_enabled` 开启时，会向模型发送当前 `robot view`，若已选择目标，也会发送 target reference image。
- Agent 只基于当前第一视角图像、可见物体 refs、搜索记忆和轨迹反馈决策，不直接使用隐藏对象信息。
- target reference image 只是视觉参考，不是可直接操作的 object ref。
- 交互动作仍然只能对当前可见对象 refs 执行。
- `data/observations/`、`data/targets/`、`data/trajectories/` 为运行生成目录，首次运行后会自动创建或更新。
