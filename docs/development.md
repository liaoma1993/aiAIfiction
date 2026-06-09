# 开发与二次开发

本文档面向想参与开发或二次开发 AI Fiction Studio 的开发者。

## 本地开发

后端：

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

前端：

```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1
```

访问：

```text
http://127.0.0.1:5173/
```

## 代码风格

### 后端

- 使用 FastAPI router 分模块组织。
- 数据访问使用 SQLAlchemy async。
- AI 任务尽量放在 `wizard.py` 或服务层。
- 复杂上下文构建放在 `services/`。
- 不要在 API handler 里写太多 prompt 拼接逻辑。

### 前端

- 页面级功能目前集中在 `frontend/src/pages`。
- API 封装优先放在 `services/projectApi.ts` 或 `services/api.ts`。
- UI 使用 Ant Design。
- 页面文字优先中文。
- 用户可见枚举尽量中文化，不暴露英文 key。

## 常用命令

后端语法检查：

```bash
cd backend
python3 -m compileall app
```

前端构建：

```bash
cd frontend
npm run build
```

## 新增 AI 任务的推荐流程

1. 在 `ai_service.py` 增加 prompt 和方法。
2. 在 `wizard.py` 增加 Request schema。
3. 编写 `_do_xxx()` 任务函数。
4. 使用 `start_task()` 包装为异步任务。
5. 前端调用接口，轮询 `/wizard/task/{task_id}`。
6. 任务结果写入数据库或返回给前端。
7. 更新任务类型中文映射。

示例结构：

```python
class MyTaskRequest(BaseModel):
    instruction: str
    apply: bool = True


async def _do_my_task(project_id: str, body: MyTaskRequest, task_id: str = "") -> dict:
    update_progress(task_id, 0.2, "正在分析")
    ai = AIService()
    result = await ai.my_task(...)
    update_progress(task_id, 1, "完成")
    return result


@router.post("/my-task")
async def my_task(project_id: str, body: MyTaskRequest, user: User = Depends(get_current_user)):
    task_id = str(uuid.uuid4())
    return {
        "task_id": start_task(
            _do_my_task(project_id, body, task_id),
            "my_task",
            project_id,
            body.model_dump(),
            task_id=task_id,
        )
    }
```

## 新增页面

1. 在 `frontend/src/pages` 新增页面。
2. 在 `frontend/src/routes/index.tsx` 注册路由。
3. 如果需要导航入口，在工作台顶部或项目页面添加链接。
4. 新增 CSS 文件，并避免影响全局样式。

## 数据迁移

当前项目启动时会先执行 `Base.metadata.create_all()` 保证新库可启动，再执行版本化 schema migration。

开发期可以这样处理：

- 小字段：在 model 中添加，并新增一个 migration 版本，保持只追加、不覆盖旧数据。
- 大变更：使用 Alembic revision，并同步确认启动迁移兼容旧库。
- 生产：升级前备份数据库；迁移不能自动重写用户正文、章节摘要、弧线或角色关系。

## 错误处理约定

后端：

- 用户输入错误：抛 `HTTPException`。
- AI 格式错误：抛清晰的 RuntimeError。
- 任务失败：写入 `GenerationTask.error_message`。

前端：

- 优先展示 `e.response.data.detail`。
- 任务失败展示任务错误。
- 对可能旧后端未加载的新接口，必要时加 404 兜底。

## UI 约定

- 面向写作工具，界面应密集但清晰。
- 不做营销式大 hero。
- 操作按钮要直接说明动作。
- 质量、状态、严重度等字段必须中文化。
- 长文本必须可换行或滚动，不能盖住字段。
- AI 任务详情不能只展示 JSON，应优先结构化展示。

## 提交 PR 前检查

```bash
cd backend
python3 -m compileall app

cd ../frontend
npm run build
```

同时手动检查：

- 登录。
- 打开工作台。
- 打开大纲页。
- 触发一个轻量 AI 任务。
- 查看任务详情。
- 查看质量仪表盘。

## 推荐贡献方向

- Prompt 可视化管理。
- PostgreSQL 迁移支持。
- 外部任务队列。
- 章节版本 diff。
- 记忆冲突检测。
- 伏笔生命周期管理。
- 图谱交互优化。
- AI 任务去重。
- 多用户协作。
- 测试覆盖。

## 安全注意

开源或部署前必须处理：

- 修改默认管理员密码。
- 修改 `JWT_SECRET_KEY`。
- 不提交 `.env`。
- 不提交真实 API Key。
- 为模型供应商 API Key 做加密存储。
- 限制 CORS。
- 增加请求频率限制。
- 增加任务消耗统计和额度控制。
