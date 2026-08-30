# 2026-08-23｜Week 4 第 1～3 次合并补齐记录

## 今日唯一主目标

完成 Java 调用 Python 文档问答接口的本地最小契约闭环：DTO、`WebClient`、错误映射和假服务测试。

## 实现前预测

### 它解决什么问题

Python RAG 已能返回答案和引用，但 Java 业务系统没有稳定的消费边界。若只取答案字符串，引用追溯会丢失；若把所有异常都当作“调用失败”，业务层无法区分模型未配置、上游失败、超时和网络问题。

### 输入、处理与输出

```text
documentId + question + topK
→ QuestionRequest JSON
→ WebClient POST /v1/documents/{documentId}/questions
→ HTTP 状态与 JSON 解码
→ QuestionResponse + Citation DTO
或 RagCmsClientException.FailureType
```

### 关键参数和边界

- `topK` 与 Python 接口保持 `1..10`；
- 问题与文档 ID 去除首尾空白且不得为空；
- 超时由 Java 客户端显式控制，不无限等待；
- 502、503、超时、传输失败分别映射；
- 编译目标为 Java 11，实际 Maven 运行 JDK 可以更高。

## 小步实现

### 第 1 步｜数据结构

新增 `QuestionRequest`、`QuestionResponse` 和 `Citation`。引用 DTO 保留 reference、document ID、Chunk 序号、源路径、字符偏移和相似度，避免 Java 侧只保留答案。

### 第 2 步｜核心客户端

`RagCmsClient` 使用 Spring `WebClient` 发送请求，先校验本地参数，再把成功响应解码为 DTO。错误响应进入统一异常类型，但通过 `FailureType` 保留不同故障语义。

### 第 3 步｜本地假服务

测试使用 JDK `HttpServer` 在随机本地端口返回受控响应，不依赖 Python、Embedding、LLM 或外网，因此可把失败定位在 Java HTTP/JSON 契约层。

## 真实中间数据

请求：

```json
{"question":"发布前做什么？","top_k":3}
```

核心响应字段：

```text
answer = 完成回归测试。[来源 1]
citations[0].chunkIndex = 2
citations[0].startOffset = 20
```

## 三个实验

### 实验 1｜正常路径

- 改变什么：假服务返回包含一条引用的 200 JSON；
- 观察什么：请求使用 `question`、`top_k`，Java 保留答案、Chunk 和字符偏移；
- 结论：Java/Python 最小 JSON 契约可以闭环，引用没有在调用边界丢失。

### 实验 2｜状态变化

- 改变什么：分别返回 502 和 503；
- 观察什么：映射为 `UPSTREAM_FAILURE` 与 `SERVICE_UNAVAILABLE`；
- 结论：Python 自身不可用与其外部依赖失败可以交给 Java 业务层采取不同策略。

### 实验 3｜失败案例

- 改变什么：服务响应时间超过 30 毫秒，以及连接到无监听端口；
- 观察什么：分别映射为 `TIMEOUT` 与 `TRANSPORT`；
- 结论：超时不是普通 HTTP 错误，连接失败也不应伪造成 Python 返回 503。

补充环境失败：沙箱内首次启动随机本地端口报 `Operation not permitted`；获准使用本地回环端口后测试通过，证明这是执行环境权限而非 Java 代码失败。

## 与 Spring 工程的对应

- DTO 对应 Controller/Client 之间的稳定契约；
- `RagCmsClient` 对应基础设施适配器；
- `FailureType` 对应异常翻译，防止上游 HTTP 细节直接污染业务 Service；
- 当前同步 `block()` 适合最小调用案例，但在完整响应式链路中不应阻塞事件循环。

## 验证结果

- Maven 依赖解析和源码编译：通过；
- 本地假服务测试：5 项，0 失败、0 错误；覆盖成功响应、502/503、超时、传输失败和参数校验；
- 未调用 Python 或外部模型；
- `javap -verbose` 显示 `major version: 55`，确认产物兼容 Java 11；Maven 自身运行在 JDK 20，不影响编译目标。

补充失败定位：最初使用固定端口 `1` 模拟连接拒绝时，Netty 在当前 macOS 环境将地址送入异常 DNS 路径，最终表现为超时。测试改为“申请随机本地端口 → 关闭服务 → 连接已知关闭端口”，稳定得到 `TRANSPORT`。这说明失败实验的输入也必须能代表声称的故障类型。

## 三层完成状态

- 代码完成：是，DTO、客户端、错误映射、5 项测试和 Java 11 字节码验证均通过；
- 验收完成：是，用户于 2026-08-23 确认本地契约闭环通过；
- 学习完成：是，用户能够说明答案与引用的职责、区分 502/503/超时/传输失败，并确认假服务没有调用真实模型。

## 下一项目时段

启动不调用真实外部模型的本地 Python 约定场景，让 Java 客户端完成一次 Java → Python 请求并记录真实接口输出；若 Python 必须调用外部模型，则先确认数据授权或使用明确的本地替身边界。

## 第 4 次｜Java → Python 本地契约联调

### 替身边界

新增 `tests/contract_server.py`。它保留真实 FastAPI 应用、路由、Pydantic 请求校验、Prompt 构造、引用映射和 HTTP 输出，仅将 Embedding、向量检索与回答模型替换为固定本地函数。固定的 `.invalid` 模型地址不会被访问，测试中也没有真实文档数据或密钥。

### 真实请求链路

```text
Java documentId=contract-document、question=发布前做什么？、topK=1
→ RagCmsClient / QuestionRequest
→ POST 127.0.0.1:18080/v1/documents/contract-document/questions
→ FastAPI ask_document / QuestionRequest
→ 固定 query vector [1.0, 0.0]
→ 固定 Top-1 Chunk（chunk=2、offset=20..34、score=0.91）
→ 固定模型回答“完成回归测试。[来源 1]”
→ FastAPI answer + citations JSON
→ Java QuestionResponse + Citation DTO
```

### 三个可观察实验

#### 实验 1｜Python 正常路径

- 改变什么：向真实 FastAPI 路由发送固定问题和 `top_k=1`；
- 观察什么：HTTP 200，答案含 `[来源 1]`，引用含文档、Chunk、偏移和分数；
- 结论：路由校验、Prompt 构造和引用 JSON 映射可在不访问外部服务时闭环。

#### 实验 2｜Java → Python 契约

- 改变什么：不再使用 Java 内置假服务，由 `RagCmsClient` 通过真实 HTTP 调用 FastAPI；
- 观察什么：Java 断言 document ID、问题、答案及全部关键引用字段；
- 结论：Java DTO 与当前 Python JSON 契约一致，引用没有在跨语言边界丢失。

#### 实验 3｜参数边界失败

- 改变什么：把 `top_k` 从 1 改为 11；
- 观察什么：FastAPI 在调用 Embedding、检索和模型替身前返回 HTTP 422；
- 结论：Python 的 `1..10` 约束仍是服务端最终防线，Java 的本地校验不能替代服务端校验。

### 验证结果

- Python `compileall`：通过（缓存定向到 `/tmp`，规避执行沙箱对系统缓存目录的限制）；
- Python 单元测试：25 项通过；
- Java → Python 指定契约测试：通过；
- Java 完整测试套件：通过，其中无契约服务环境变量时跨语言测试按设计跳过；
- 未调用真实 Embedding、向量数据或回答模型，未验证网络、真实配置、数据授权和真实评分结果。

### 当前三层状态

- 代码完成：是；
- 验收完成：是，用户于 2026-08-30 确认 Java → Python 约定场景通过；
- 学习完成：是，用户能按“Java 断言 → Python 原始 JSON → Python 引用/检索或 Java DTO 映射”顺序定位跨语言契约故障；
- Week 4 第 4 项：已在用户确认后勾选。
