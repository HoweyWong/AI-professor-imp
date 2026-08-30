# 2026-08-30｜Week 5 第 1～2 次｜Docker 静态闭环

## 今日唯一主目标

在不伪造运行证据的前提下，补齐 RAG-CMS 的镜像、运行配置、持久化数据和健康检查边界，并明确实际容器验收的环境阻塞。

## 实现前预测与结论

1. `.env` 和 API Key 应运行时注入，不能写入镜像；
2. `data/` 应挂载为宿主机目录，不能随容器生命周期丢失；
3. Dockerfile 静态检查不能替代镜像构建和容器 `/health` 验收。

用户已正确回答三项边界。

## 输入、处理与输出

```text
app/ + requirements.txt
→ Docker build（待可用环境执行）
→ Python 3.9 应用镜像
+ 运行时模型环境变量
+ ./data:/app/data 挂载
→ Uvicorn 0.0.0.0:8000
→ GET /health
```

## 小步实现

### 第 1 步｜镜像边界

`Dockerfile` 使用 Python 3.9 slim，只复制依赖清单和 `app/`，以非 reload 模式启动 Uvicorn，并提供不依赖 curl 的 Python 健康检查。

### 第 2 步｜运行边界

`compose.yaml` 运行时注入模型变量，将 `./data` 挂载到 `/app/data`；`RAG_CMS_DATA_DIR` 固定为 `/app/data/documents`。

### 第 3 步｜构建上下文边界

`.dockerignore` 排除 `.env`、`.venv`、`data/`、Java 制品和测试资料，防止密钥、运行数据或无关制品进入镜像上下文。

## 三个实验

### 实验 1｜正常静态路径

- 改变什么：读取 Dockerfile 的基础镜像、数据路径和启动命令；
- 观察什么：Python 3.9、`0.0.0.0:8000`、无 `--reload`；
- 结论：制品描述符合当前生产式最小启动边界。

### 实验 2｜配置与数据边界

- 改变什么：检查 Compose 的环境注入与目录挂载；
- 观察什么：模型变量来自运行环境，`./data:/app/data`；
- 结论：配置、镜像和运行数据职责分离。

### 实验 3｜失败案例：无容器运行时

- 改变什么：检查 Docker、Podman、Colima、OrbStack、nerdctl 和 Finch；
- 观察什么：命令及常见桌面应用均不存在；
- 结论：当前只能完成代码和静态验收，不能执行 build、启动、健康检查与卷持久化实验。

## 验证结果

- 容器静态契约测试：3 项通过；
- Python 完整测试：28 项通过；
- Python `compileall`：通过；
- `git diff --check`：通过；
- Docker 实际构建/启动：未执行，环境无容器运行时。

## 与 Java / Spring 的对照

- Dockerfile 类似规定 Spring Boot 运行时 JRE、制品和启动命令；
- Compose environment 类似外部化的 `application.yml`/环境变量；
- 数据卷类似将数据库或上传目录置于进程生命周期之外；
- 类比边界：当前 Python 服务把文档和向量存在本地文件，容器化不会自动获得数据库的一致性和并发保证。

## 三层完成状态

- 代码完成：是，Dockerfile、Compose、忽略规则、README 和静态测试已完成；
- 验收完成：第 1～2 项已确认；第 3～4 项已有实际运行证据，待用户确认；
- 学习完成：静态边界理解已完成，已观察 `running` 与 `healthy` 的启动时序差异；
- Week 5 第 1～2 项：用户于 2026-08-30 确认通过并已勾选；第 3～4 项暂不勾选，等待用户确认。

## 第 3～4 次｜真实容器验收

### 安装环境

- Apple Silicon macOS 26.6.2；
- Colima 0.10.3，Docker runtime，2 CPU、4 GiB 内存、20 GiB 磁盘，未启用 Kubernetes；
- Docker CLI 29.7.2、Docker Engine 29.5.2；
- Docker Compose 5.5.0、Buildx 0.36.1。

Homebrew 安装时自动执行了清理，删除旧缓存及其判断不再需要的 Python 3.13、旧 OpenJDK 20 formula；随后需用项目 `.venv` 测试和 Java 环境检查确认无回归。

### 实验 1｜实际构建与健康检查

- 改变什么：执行 `docker compose up --build -d`；
- 观察什么：Python 3.9 镜像成功构建，容器最终为 `running healthy`，`/health` 返回 `{"status":"ok","service":"rag-cms-api"}`；
- 结论：镜像、Uvicorn、端口转发和健康检查实际闭环。

### 实验 2｜数据卷持久化

- 改变什么：上传固定无敏感文本，强制重建容器；
- 观察什么：宿主机 `metadata.json` 在重建前后 SHA-256 均为 `13d47bd99a05fa014badf040a13cf9fafc23a7c24ae95820b8b0c05c87c1d945`，重建后容器再次健康；
- 结论：`./data:/app/data` 将运行数据置于容器生命周期之外。哈希证明该文件未变化，不证明元数据语义一定正确。

### 实验 3｜未配置模型与启动时序失败

- 改变什么：启动不注入模型变量的独立容器并调用问答接口；
- 观察什么：容器健康，问答返回 HTTP 503：`Embedding 服务未配置`，未发生外部调用；
- 结论：进程健康不等于模型就绪，配置缺失边界明确。

补充失败：强制重建后容器显示 `running (health: starting)` 时立即请求得到空响应；改为 `docker compose up -d --wait --wait-timeout 30` 后，在 `healthy` 状态请求成功。应等待健康条件，不使用固定睡眠猜测就绪时间。

### 安装后回归

- Buildx 重新构建镜像并等待容器健康：通过；
- Python 3.9.6 项目虚拟环境：可用；
- Python 测试：28 项通过；
- 系统 Java 11：可用；Maven Java 测试：通过；
- Maven 仍报告使用既有 Homebrew JDK 20 路径并可运行，后续若 Homebrew 链接发生变化，应优先让 Maven 明确使用 Java 11，避免依赖已被清理的旧 Cellar 版本。
