# Docker｜RAG-CMS 镜像、配置、数据与健康边界｜2026-08-30

## 所属主线

AI 应用架构

## 核心结论

容器化不是把整个开发目录打包，而是划分四个生命周期：镜像保存应用和依赖，环境变量承载运行配置，挂载目录保存运行数据，健康检查只描述被检查的服务能力。

## 问题背景

RAG-CMS 本地运行依赖 Python、模型配置和 `data/` 文件。若密钥或数据进入镜像，会造成泄露和生命周期混乱；若只看容器进程为 `running`，又可能在应用尚未就绪时接收流量。

## 输入、处理与输出

```text
app/ + requirements.txt → Python 3.9 镜像
镜像 + 运行时模型变量 + ./data:/app/data
→ Uvicorn 容器
→ /health = API 进程健康
→ /questions = 还依赖 Embedding、检索和 LLM
```

## 关键机制

- `.dockerignore` 排除 `.env`、`.venv` 和 `data/`；
- Compose 在运行时注入配置；
- Bind mount 让数据独立于容器生命周期；
- `HEALTHCHECK` 访问容器内 `/health`；
- `docker compose up --wait` 等到健康条件成立。

## 项目中的实际数据链路

```text
Dockerfile → Buildx → rag-cms-rag-cms-api 镜像
→ Compose 启动并映射 8000:8000
→ GET /health 返回 200
→ 上传测试文档到 /app/data/documents
→ 宿主机 ./data/documents 出现同一文件
→ 强制重建容器
→ metadata.json 哈希保持一致
```

## 适用条件

- 单机开发与最小部署验证；
- 文件数据规模和并发仍适合本地目录；
- 配置能通过环境变量安全注入。

## 限制与风险

- `/health` 只证明 API 进程，不证明模型就绪或回答质量；
- Bind mount 不提供数据库事务、一致性或备份；
- 文件哈希证明字节未变，不证明元数据语义正确；
- 以 root 用户运行和基础镜像安全更新尚未专项加固；
- Colima 是本地开发运行时，不等同生产部署平台。

## 参数实验与结论

- 容器从 `health: starting` 到 `healthy`：立即请求曾失败，应等待健康条件；
- 强制重建容器：挂载文件哈希不变，数据独立于容器；
- 移除模型变量：容器仍健康，问答返回 503，证明进程健康与模型能力是不同层次。

## 一个失败案例

重建容器后看到 `running` 就立即访问，得到空响应。改用 Compose `--wait` 后稳定成功。根因是把进程创建完成误当成应用就绪。

## 与 Java / Spring 的对照

Dockerfile 类似固定 JRE、JAR 和启动命令；环境变量类似外部化配置；健康检查类似 Spring Actuator 的 liveness。边界是当前 `/health` 没有 readiness 依赖检查，也不应把外部模型短暂故障直接等同于进程死亡。

## 对当前项目的启发

保留轻量 `/health`，在需要流量治理时再明确区分 liveness 与 readiness；真实模型验证继续遵守数据授权前置条件，不通过容器环境变量自动扩大权限。

## 可验证行动

执行 `docker compose up --build -d --wait`，上传固定文本并重建容器，比较挂载文件哈希；再以无模型变量容器验证问答 503。

## 我能否脱离代码讲清楚

- 为什么需要它：让运行环境可重复，同时分离制品、配置和数据；
- 输入和输出：源码生成镜像，运行配置和数据挂载后提供 API；
- 失败时先检查：Docker 状态、health 状态、端口，再查模型配置；
- 仍未理解的问题：生产环境如何设计独立的 readiness 和安全的密钥管理。

## 参考材料

- `02-Projects/RAG-CMS/Dockerfile`
- `02-Projects/RAG-CMS/compose.yaml`
- `05-Weekly-Reviews/2026-08-30-docker-project-session.md`
