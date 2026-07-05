# Embodied Visual Search

基于 AI2-THOR 的在线交互版具身视觉搜索 Agent。系统提供机器人第一视角 `robot view`、第三方房间观察视角 `room view`、手动控制、room view 点选目标生成参考图，以及基于 OpenAI-compatible `/chat/completions` 的多模态 LLM 自动搜索链路。

## 核心功能

* 场景选择与加载，支持按房间类型切换 AI2-THOR 场景。
* `robot view` 显示机器人当前第一视角观察。
* `room view` 显示第三方房间观察视角，支持鼠标悬停 inspect、拖拽 / QE 旋转观察、点击物体选择目标。
* 点击 room view 物体后自动聚焦，并生成 target reference image 作为视觉目标参考。
* 手动动作控制，前后端动作空间保持一致，支持移动、旋转、视角调整和基础结束动作。
* Agent 自动搜索。
* OpenAI-compatible 模型配置：`base_url`、`api_key`、`model`、`temperature`、`max_tokens`、`timeout`、`vision_enabled`。
* 搜索记忆与轨迹记录，包含 `checked`、`ruled_out`、`avoid`、`recent_clues`、last feedback、recent trajectory，以及每步 thought / action / result / memory_update / robot_view。

## 目录结构

```text
backend/    FastAPI 后端、AI2-THOR 环境封装、Agent、动作执行、schema
frontend/   React + Vite 前端页面与 API 封装
data/       运行生成的数据目录，包括轨迹、观察截图、目标截图
```

## 环境配置

### 后端依赖

推荐在 Linux 图形环境中运行后端。当前已验证环境为 `WSL2 + Ubuntu 24.04`。

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 前端依赖

```bash
cd frontend
npm install
```

## AI2-THOR 运行环境

当前后端使用 AI2-THOR `Linux64` 平台，需要可用的图形显示环境，例如 WSLg 或 X Server。

当前已验证的图形环境变量如下：

```bash
export AI2THOR_PLATFORM=Linux64
export AI2THOR_X_DISPLAY=:0
export AI2THOR_FORCE_GLCORE=1
export DISPLAY=:0
export GALLIUM_DRIVER=d3d12
export MESA_D3D12_DEFAULT_ADAPTER_NAME='NVIDIA'
```

项目默认启动脚本已内置上述环境变量。若运行环境不同，可根据本机图形配置调整相关变量。

## OpenAI-compatible API 配置

模型设置通过前端页面保存到本地配置文件。接口需兼容 OpenAI 风格 `/chat/completions`。

当 `vision_enabled=true` 时，后端会向模型发送当前 `robot view`。如果已选择目标，还会附带 target reference image。

## 启动方式

### 后端启动

推荐使用仓库根目录下的启动脚本：

```bash
cd /path/to/embodied-visual-search
bash start_backend.sh
```

`start_backend.sh` 会完成以下操作：

* 激活虚拟环境
* 设置 AI2-THOR 图形环境变量
* 调用 `backend/launch_backend.py`
* 启动 `backend.app:app`

也可以手动执行等价命令：

```bash
cd /path/to/embodied-visual-search
source .venv/bin/activate

export AI2THOR_PLATFORM=Linux64
export AI2THOR_X_DISPLAY=:0
export AI2THOR_FORCE_GLCORE=1
export DISPLAY=:0
export GALLIUM_DRIVER=d3d12
export MESA_D3D12_DEFAULT_ADAPTER_NAME='NVIDIA'

python backend/launch_backend.py
```

### 前端启动

```bash
cd frontend
npm run dev
```

## 访问地址

* 前端默认地址：`http://127.0.0.1:5173`
* 后端默认端口：`8000`

如果前端和后端不在同一个网络上下文中，需要根据实际环境调整代理或 `VITE_API_BASE_URL` / `VITE_BACKEND_PROXY_TARGET`。

## 使用流程

1. 启动后端。
2. 启动前端。
3. 在前端选择房间类型和场景，加载 AI2-THOR 场景。
4. 在模型设置面板填写 OpenAI-compatible 配置并保存。
5. 通过 `room view` 观察环境，可悬停查看物体信息、拖拽调整视角。
6. 点击 `room view` 中的目标物体，系统会聚焦并生成 target reference image。
7. 输入任务指令，启动 Agent 自动搜索，或使用手动动作控制机器人。
8. 在主页面和轨迹页面查看每一步 thought、action、feedback、memory update 与 robot view。

## 注意事项

* 后端启动脚本对应当前已验证的 Linux 图形环境配置。
* 如果修改 `backend.app:app` 下的业务逻辑、路由、Agent 或环境封装，`start_backend.sh` 通常无需调整。
* 如果修改后端入口、虚拟环境路径或 AI2-THOR 图形环境变量，需要同步更新 `start_backend.sh` 和 `backend/launch_backend.py`。
* `vision_enabled` 开启时，会向模型发送当前 `robot view`；若已选择目标，也会发送 target reference image。
* Agent 只基于当前第一视角图像、可见物体 refs、搜索记忆和轨迹反馈决策，不直接使用隐藏对象信息。
* target reference image 仅作为视觉参考，不是可直接操作的 object ref。
* 交互动作只能作用于当前可见对象 refs。
* `data/observations/`、`data/targets/`、`data/trajectories/` 为运行生成目录，首次运行后会自动创建或更新。
