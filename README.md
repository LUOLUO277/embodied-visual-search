# embodied-visual-search 仓库说明

这个 README 不是使用教程，而是给你快速看懂仓库结构用的“文件地图”。
当前项目是一个基于 AI2-THOR 的具身视觉搜索原型，整体链路是：

- 前端加载场景、展示机器人视角/房间视角、配置模型参数。
- 后端维护 AI2-THOR 环境、Agent 状态、轨迹记录。
- LLM Agent 按 `观察 -> 思考 -> 高层动作 -> 执行反馈 -> 下一轮提示词` 的方式循环。

---

## 一、仓库根目录

### `README.md`
当前这份说明文档。用于解释仓库目录和各个文件的职责。

### `requirements.txt`
后端 Python 依赖列表，主要包含：
- `fastapi` / `uvicorn`：后端 API 服务
- `ai2thor`：具身环境
- `pillow`：图像处理与保存
- `pydantic`：请求/响应数据模型
- `python-dotenv`：环境变量加载

### `start_backend.sh`
后端启动脚本，通常用于本地快速启动服务。

---

## 二、`backend/` 后端主目录

`backend/` 是整个服务端核心，负责环境控制、Agent 推理闭环、动作执行、API 暴露和状态存储。

### 1. `backend/__init__.py`
把 `backend` 标记为 Python 包，本身没有业务逻辑。

### 2. `backend/app.py`
FastAPI 应用入口。
作用：
- 创建 `FastAPI` 实例
- 配置 CORS
- 注册各类路由：环境、Agent、相机、模型设置
- 提供 `/health` 健康检查接口

### 3. `backend/launch_backend.py`
后端启动辅助入口。一般用于更方便地本地拉起服务。

---

## 三、`backend/actions/` 动作执行层

这一层负责把 LLM 输出的“高层动作”翻译成 AI2-THOR 的具体执行逻辑。
这是本仓库里 Agent 行为最关键的一层。

### `backend/actions/__init__.py`
包初始化文件，无核心逻辑。

### `backend/actions/action_space.py`
定义动作集合。
主要作用：
- 定义手动控制动作枚举
- 定义 Agent 允许输出的高层动作列表，例如：
  - `observe`
  - `move forward`
  - `navigate to`
  - `pickup`
  - `put in`
  - `toggle`
  - `open`
  - `close`
  - `end`

### `backend/actions/base_action.py`
对 AI2-THOR 原子动作做一层薄封装。
主要作用：
- 封装 `MoveAhead`、`RotateLeft`、`RotateRight`
- 封装 `TeleportFull`
- 封装 `PickupObject`、`PutObject`
- 封装 `OpenObject`、`CloseObject`
- 封装 `ToggleObjectOn/Off`
- 封装 `Done`

这个文件相当于“底层动作 API 适配层”。

### `backend/actions/object_resolver.py`
对象解析器。
主要作用：
- 从当前 `metadata['objects']` 建立对象索引
- 支持按以下几种方式解析目标对象：
  - `objectType`，例如 `Drawer`
  - 编号名，例 `Drawer_1`
  - `objectId: xxx`
- 生成 `legal_navigations`
- 生成 `legal_interactions`
- 汇总当前元数据摘要

这个文件解决的是“LLM 说要去哪个对象/操作哪个对象”的对象落地问题。

### `backend/actions/action_adapter.py`
高层动作执行主入口。
主要作用：
- 接收 `HighLevelAction`
- 规范化动作名
- 分发到 `navigate to`、`observe`、`pickup`、`put in`、`open`、`close`、`toggle` 等具体逻辑
- 返回统一的 `AgentActionResult`
- 在每次动作执行后附带：
  - 是否成功
  - 选中的对象 ID / 类型
  - 错误信息
  - 合法导航列表
  - 合法交互列表
  - 图像路径
  - 元数据摘要

如果要查 Agent 为什么做出某个动作、动作为什么失败，这个文件是第一重点。

---

## 四、`backend/agents/` Agent 层

这一层负责“怎么让模型思考并驱动动作循环”。

### `backend/agents/__init__.py`
包初始化文件。

### `backend/agents/base_agent.py`
Agent 抽象基类。
定义 Agent 通用接口，便于以后扩展不同类型的 Agent。

### `backend/agents/dummy_agent.py`
简单占位 Agent。
通常用于调试或保留最小实现，不是当前主链路核心。

### `backend/agents/llm_embodied_agent.py`
当前主用 Agent。
主要作用：
- 从环境中读观察结果
- 组织 prompt 输入
- 调用 OpenAI-compatible 模型接口
- 解析模型 JSON 输出
- 执行高层动作
- 记录轨迹
- 把错误和反馈喂回下一轮 prompt

这是“LLM 决策主循环”的核心文件。

---

## 五、`backend/api/` API 路由层

这一层负责把后端能力通过 HTTP 暴露给前端。

### `backend/api/__init__.py`
包初始化文件。

### `backend/api/routes_env.py`
环境相关 API。
主要负责：
- 加载场景
- 获取当前 observation
- 执行手动控制动作

### `backend/api/routes_agent.py`
Agent 相关 API。
主要负责：
- 重置 Agent
- 单步执行 Agent
- 连续运行 Agent
- 获取 Agent 状态
- 停止 Agent
- 返回轨迹历史

### `backend/api/routes_camera.py`
房间视角相机 API。
主要负责：
- orbit 房间视角
- inspect 房间视角某个像素对应的物体

### `backend/api/routes_settings.py`
模型设置 API。
主要负责：
- 获取模型配置
- 保存模型配置
- 测试模型连接

---

## 六、`backend/envs/` 环境封装层

这一层负责和 AI2-THOR 直接交互。

### `backend/envs/__init__.py`
包初始化文件。

### `backend/envs/thor_env.py`
AI2-THOR 环境主封装。
主要作用：
- 初始化 Controller
- 重置/加载场景
- 执行控制器动作
- 获取机器人视角和房间视角
- 保存 observe 图像
- 管理第三人称房间相机
- 查找对象 metadata
- 读取可见物体和库存物体
- 可选读取 `backend/data/agent_positions.json` 里的预设传送位姿

这是“所有环境交互”的核心文件。

### `backend/envs/scene_registry.py`
场景注册表。
主要用于维护房间类型、场景编号等静态映射，方便前端选择场景。

### `backend/envs/frame_utils.py`
图像工具函数。
主要作用：
- 把 AI2-THOR 返回的 numpy 图像帧转成 base64 PNG 字符串

---

## 七、`backend/llm/` 模型调用与提示词层

这一层只负责模型输入输出，不直接碰环境执行。

### `backend/llm/__init__.py`
包初始化文件。

### `backend/llm/model_settings.py`
模型配置存储层。
主要负责：
- 加载模型配置
- 保存模型配置
- 管理默认值

### `backend/llm/openai_compatible_client.py`
OpenAI-compatible 接口客户端。
主要负责：
- 按 OpenAI 风格请求聊天模型
- 支持视觉输入
- 返回模型原始文本输出

### `backend/llm/output_parser.py`
模型输出解析器。
主要负责：
- 从模型返回文本中提取 JSON
- 解析 `thought` 和 `action`
- 在解析失败时构造标准错误结果

### `backend/llm/prompt_builder.py`
提示词构造器。
主要负责：
- 组织 system prompt
- 组织 user payload
- 把当前观察、历史轨迹、合法动作、错误反馈、库存等打包给模型

如果你要改 prompt 结构，这个文件就是入口。

---

## 八、`backend/memory/` 运行时状态与轨迹

这一层负责保存 Agent 运行过程中的“短期记忆”。

### `backend/memory/__init__.py`
包初始化文件。

### `backend/memory/search_state.py`
Agent 搜索状态。
主要记录：
- 当前任务指令
- 目标对象
- 最大步数
- 当前步数
- 是否 active / running / done / stopped
- 上一步错误
- 上一步反馈
- 已访问目标
- 已见过的对象 ID

### `backend/memory/trajectory.py`
轨迹存储。
主要负责：
- 记录每一步的 thought / action / result / raw output
- 记录可见物体、持有物体、Agent pose、robot view
- 持久化最新轨迹到 `data/trajectories/latest_trajectory.json`

---

## 九、`backend/schemas/` 数据模型层

这一层统一定义前后端交互以及后端内部使用的数据结构。

### `backend/schemas/__init__.py`
包初始化文件。

### `backend/schemas/action_schema.py`
动作相关 schema。
主要定义：
- `ActionRequest`
- `HighLevelAction`
- 高层动作名及其 normalize 规则

### `backend/schemas/agent_schema.py`
Agent 相关 schema。
主要定义：
- `AgentThought`
- `AgentResetRequest`
- `AgentStepRequest`
- `AgentRunRequest`
- `AgentActionResult`
- `TrajectoryItem`
- `AgentStepResponse`
- `AgentStateResponse`

### `backend/schemas/env_schema.py`
环境 observation 与相机相关 schema。
主要定义：
- 场景加载请求
- `AgentPose`
- `VisibleObject`
- `EnvMetadata`
- `ObservationResponse`
- 房间视角 inspect/orbit 请求与返回结构

### `backend/schemas/model_settings_schema.py`
模型配置 schema。
主要定义：
- 模型设置请求/响应结构
- 连接测试返回结构

---

## 十、`backend/scripts/` 后端辅助脚本

### `backend/scripts/check_ai2thor_runtime.py`
检查 AI2-THOR 运行环境是否可用。
一般在正式启动前先用它验证图形环境和依赖状态。

---

## 十一、`frontend/` 前端主目录

前端基于 React + Vite，负责场景控制、图像展示、模型配置和轨迹可视化。

### 1. `frontend/package.json`
前端项目依赖和脚本定义。
例如 `npm run dev`、`npm run build`。

### 2. `frontend/package-lock.json`
前端依赖锁定文件，保证安装版本一致。

### 3. `frontend/index.html`
Vite 前端入口 HTML。

### 4. `frontend/vite.config.ts`
Vite 构建与开发服务器配置。

### 5. `frontend/tsconfig.json`
前端 TypeScript 主配置。

### 6. `frontend/tsconfig.node.json`
Node 侧 TypeScript 配置，主要给 Vite 配置文件等使用。

---

## 十二、`frontend/src/` 前端源码

### `frontend/src/main.tsx`
前端 React 挂载入口。

### `frontend/src/App.tsx`
前端主页面。
主要负责：
- 初始化场景与 Agent 状态
- 组织各个面板
- 调用 API
- 协调场景加载、手动控制、Agent 单步/连续运行

### `frontend/src/vite-env.d.ts`
Vite 环境变量类型声明。

---

## 十三、`frontend/src/api/` 前端 API 封装

### `frontend/src/api/client.ts`
前端请求封装与类型定义。
主要作用：
- 定义前端使用的 TypeScript 类型
- 封装对后端的 fetch 请求
- 提供 `api.getScenes()`、`api.stepAgent()` 等调用函数

如果前后端接口字段不一致，通常先看这里。

---

## 十四、`frontend/src/components/` 前端组件

### `frontend/src/components/ScenePanel.tsx`
场景面板。
主要负责：
- 选择房间类型
- 选择具体场景
- 输入任务文本
- 触发加载场景

### `frontend/src/components/ModelSettingsPanel.tsx`
模型设置面板。
主要负责：
- 配置 base URL / API key / model / temperature / max tokens / timeout
- 保存设置
- 测试模型连接

### `frontend/src/components/ManualControl.tsx`
手动控制面板。
主要负责发送基础动作，例如移动、旋转、抬头、低头等。

### `frontend/src/components/AgentPanel.tsx`
Agent 控制面板。
主要负责：
- 输入任务指令
- 输入目标对象
- 设置最大步数
- 重置 Agent
- 单步运行 / 连续运行 / 停止
- 展示最新一步 thought / action / feedback

### `frontend/src/components/RobotView.tsx`
机器人第一视角图像组件。
负责显示当前机器人看到的 RGB 图。

### `frontend/src/components/RoomView.tsx`
房间视角组件。
主要负责：
- 显示第三人称房间图像
- 鼠标 hover inspect 物体
- 拖拽 orbit 房间相机

### `frontend/src/components/TrajectoryPanel.tsx`
轨迹历史面板。
主要负责展示每一步：
- 图片
- thought
- action
- action result
- selected object
- legal navigations
- legal interactions
- raw model output

---

## 十五、`frontend/src/styles/` 样式目录

### `frontend/src/styles/app.css`
前端全局样式文件。
负责页面布局、面板样式、图像区域样式、轨迹面板样式等。

---

## 十六、`scripts/` 仓库级脚本

这些脚本通常用于调试、冒烟测试或数据导入，不会自动进入默认运行流程。

### `scripts/check_ai2thor.py`
简单检查 AI2-THOR 是否可导入、是否能基本运行。

### `scripts/import_official_test_tasks.py`
把官方测试任务 JSON 转成当前仓库能使用的任务格式。
主要用于兼容官方 `test_809.json` 一类数据。

### `scripts/smoke_action_adapter.py`
动作执行层冒烟脚本。
主要用于：
- 加载真实 AI2-THOR 场景
- 顺序执行固定高层动作
- 检查 `action_adapter` 行为是否基本正常

### `scripts/smoke_agent_loop.py`
Agent 闭环冒烟脚本。
主要用于：
- 用 mock LLM 输出驱动 `/api/agent/step`
- 验证从 Agent API 到动作执行再到轨迹记录的整条链路

---

## 十七、`tests/` 测试目录

### `tests/test_action_adapter.py`
当前的单元测试文件。
主要覆盖：
- `ObjectResolver` 对 `Drawer` / `Drawer_1` / `objectId` 的解析
- `put in` 在空库存时的失败反馈
- `open` 非 openable 对象时的非法动作反馈

---

## 十八、运行时可能生成但未必已提交的目录

这些目录不是你现在 `rg --files` 里列出来的源码文件，但运行时通常会出现。

### `data/trajectories/`
保存最新轨迹 JSON。
典型文件：
- `data/trajectories/latest_trajectory.json`

### `data/observations/`
保存 `observe` 过程中的子图和拼接图。

### `backend/data/agent_positions.json`
可选文件。
如果存在，`navigate to` 会优先读取里面的预设传送位姿。
如果不存在，系统会自动 fallback，不是必需文件。

### `backend/config/model_settings.local.json`
模型设置本地持久化文件。
通常应被 git ignore，不要提交 API key。

---

## 十九、如果你要改代码，优先看哪里

### 想改 Agent 决策输入
看：
- `backend/llm/prompt_builder.py`
- `backend/agents/llm_embodied_agent.py`

### 想改动作执行逻辑
看：
- `backend/actions/action_adapter.py`
- `backend/actions/object_resolver.py`
- `backend/actions/base_action.py`
- `backend/envs/thor_env.py`

### 想改前后端接口字段
看：
- `backend/schemas/*.py`
- `backend/api/routes_*.py`
- `frontend/src/api/client.ts`

### 想改页面展示
看：
- `frontend/src/App.tsx`
- `frontend/src/components/*.tsx`
- `frontend/src/styles/app.css`

---

## 二十、最短理解路径

如果你第一次接这个仓库，建议按这个顺序阅读：

1. `frontend/src/App.tsx`
2. `frontend/src/api/client.ts`
3. `backend/app.py`
4. `backend/api/routes_agent.py`
5. `backend/agents/llm_embodied_agent.py`
6. `backend/llm/prompt_builder.py`
7. `backend/llm/output_parser.py`
8. `backend/actions/action_adapter.py`
9. `backend/actions/object_resolver.py`
10. `backend/envs/thor_env.py`
11. `backend/memory/trajectory.py`

这样基本就能看懂整个系统从前端按钮到环境动作执行的完整路径。
