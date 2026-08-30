# Java / Python｜AI 服务故障边界与定位顺序｜2026-08-30

## 所属主线

AI 应用架构

## 核心结论

Java 调用 Python AI 服务时，应按“是否收到 HTTP 响应 → HTTP 状态 → Python 外部依赖 → 响应契约”分层定位；502、503、超时和传输失败不能合并为同一种异常。

## 问题背景

AI 请求同时经过 Java 客户端、网络、Python 服务、Embedding/LLM。若统一抛出“调用失败”，业务代码无法判断应修配置、等待恢复、检查端口，还是调查模型依赖。

## 输入、处理与输出

```text
Java 请求
→ 是否建立连接并收到 HTTP
→ Python 是否具备服务能力
→ Python 调用外部模型是否成功
→ Java FailureType 或 QuestionResponse
```

## 关键机制

- `TRANSPORT`：没有收到 HTTP 响应，先查进程、端口、DNS和网络；
- `TIMEOUT`：整个调用超过 Java 截止时间，需追踪各段耗时；
- `503 SERVICE_UNAVAILABLE`：Python 可达，但必要配置或能力不可用；
- `502 UPSTREAM_FAILURE`：Python 已接收请求，但外部 Embedding/LLM 失败或返回无效结果；
- `HTTP_ERROR`：其余未单独分类的 HTTP 错误。

## 项目中的实际数据链路

```text
RagCmsClient.ask
→ WebClient
→ FastAPI /questions
→ Embedding / retrieval / LLM
→ HTTP 状态或 answer + citations
→ RagCmsClientException.FailureType 或 DTO
```

## 适用条件

- 同步 Java 调用有明确总体超时；
- Python 能将自身不可用与上游失败映射为不同状态；
- 日志不泄露密钥、完整文档或无意义的大型向量。

## 限制与风险

- 当前超时是 Java 整体截止时间，不能指出具体慢在检索还是模型；
- 没有实现重试、熔断或链路追踪；
- HTTP 状态只能表达技术边界，不能证明回答质量；
- 真实服务调用前仍需确认服务归属和数据授权。

## 参数实验与结论

- 假服务返回 502/503：Java 分别映射为上游失败与服务不可用；
- 延迟超过 30 ms：映射为 `TIMEOUT`；
- 连接已关闭的随机端口：映射为 `TRANSPORT`。

## 一个失败案例

最初用固定端口 1 模拟连接拒绝，当前 macOS/Netty 环境进入异常 DNS 路径并最终表现为超时。改为“开启随机端口 → 关闭 → 连接该已知端口”后，才稳定复现传输失败。故障实验本身也必须可重复。

## 与 Java / Spring 的对照

`RagCmsClientException` 是基础设施异常到业务可理解故障类型的翻译层，类似 Spring Client 适配器。边界是：当前同步 `block()` 适合最小闭环，不应直接放入完整 WebFlux 事件循环。

## 对当前项目的启发

下一步若接真实模型，应先保持当前错误分类，再增加请求 ID 和分段耗时；不应先引入重试框架掩盖故障来源。

## 可验证行动

运行 Java 五项假服务测试，并用 Python 原始 JSON 与 Java DTO 的先后检查法定位契约断言失败。

## 我能否脱离代码讲清楚

- 为什么需要它：让不同故障进入正确的排查和恢复路径；
- 输入和输出：HTTP 调用结果被翻译成 DTO 或明确 FailureType；
- 失败时先检查：是否收到 HTTP，再看状态和原始响应；
- 仍未理解的问题：真实链路中如何分配 Java、Python 和模型各自的超时预算。

## 参考材料

- `02-Projects/RAG-CMS/java-client/`
- `05-Weekly-Reviews/2026-08-23-project-session.md`
