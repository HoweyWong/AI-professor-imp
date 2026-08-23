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
