# AI-Career-Manual 工作约定

## 项目定位

本仓库是 AI 应用开发与架构转型工作区。当前唯一项目主线是
`AI-Career-Manual/02-Projects/RAG-CMS/`，目标是完成带来源引用的 CMS 技术文档问答最小闭环。

除非任务明确要求，不要扩展到 `week-01.md` 中“本周不做”的方向，也不要替用户勾选任务清单。

## 开始任务前

1. 阅读 `AI-Career-Manual/README.md`。
2. 涉及 RAG-CMS 时，再阅读：
   - `AI-Career-Manual/02-Projects/RAG-CMS/README.md`
   - `AI-Career-Manual/02-Projects/RAG-CMS/week-01.md`
3. 涉及学习计划或复盘时，读取 `AI-Career-Manual/05-Weekly-Reviews/` 中日期最新的相关文件。
4. 先执行 `git status --short`。工作区可能包含用户正在进行的修改；保留无关改动，不覆盖、不清理。

## 常用操作

### 检查项目与知识计划进度

```bash
./AI-Career-Manual/automation/ai-career-status.sh --no-notify
```

这是原 Kiro 手动 Hook 在 Codex 中的等价操作。用户说“检查计划”“查看进度”或“下一步做什么”时，执行该命令并结合对应计划文件给出简短结论。只有用户明确要求桌面通知时，才省略 `--no-notify`。

### 初始化与启动 RAG-CMS

```bash
cd AI-Career-Manual/02-Projects/RAG-CMS
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
./start.sh
```

不要提交 `.env`、密钥、`.venv/` 或 `data/` 中的运行数据。调用外部模型前，确认配置的服务获准处理相关文档。

## 修改原则

- 优先完成当前计划中的最小闭环，避免无关重构或引入新基础设施。
- Python 代码保持与项目当前 Python 3.9 环境兼容。
- API 行为变化应同步更新 RAG-CMS README。
- 新增功能应补充与风险相称的测试；当前仓库尚无测试套件时，至少执行语法检查和针对性接口验证。
- 复盘、知识卡和行业报告沿用各目录现有模板与中文写作风格。

## 验证与交付

修改 Python 后至少执行：

```bash
cd AI-Career-Manual/02-Projects/RAG-CMS
.venv/bin/python -m compileall -q app
```

若服务可启动且不需要真实模型密钥，再验证：

```bash
curl http://127.0.0.1:8000/health
```

交付时说明改动文件、已执行的验证和未验证项。任务完成不等于计划项自动完成；只有用户确认结果符合验收标准后，才更新任务勾选或复盘记录。
