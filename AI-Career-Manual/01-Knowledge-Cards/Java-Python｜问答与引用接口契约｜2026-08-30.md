# Java / Python｜问答与引用接口契约｜2026-08-30

## 所属主线

AI 应用架构

## 核心结论

RAG 问答接口的业务结果不是单独的答案字符串，而是“答案 + 可追溯引用”。Java DTO 必须保留文档、Chunk、字符偏移和分数，否则跨语言调用成功后仍无法审计答案依据。

## 问题背景

Python 已能通过 `/v1/documents/{document_id}/questions` 返回回答，但 Java 业务系统若只消费 `answer`，会丢失支撑证据，无法定位错误来自生成、检索还是展示层。

## 输入、处理与输出

```text
documentId + question + topK
→ Java QuestionRequest（question、top_k）
→ FastAPI QuestionRequest 校验
→ 检索与回答
→ answer + citations JSON
→ Java QuestionResponse + Citation
```

## 关键机制

- 请求契约：`question` 非空，`top_k` 为 `1..10`；
- 响应契约：`answer` 是回答文本，`citations` 是支撑回答的证据；
- 引用身份：`document_id + chunk_index` 指向片段；
- 原文定位：`source_path + start_offset + end_offset` 支持回查；
- 检索观察：`score` 可辅助比较，但不能独立证明引用忠实。

## 项目中的实际数据链路

```text
contract-document + “发布前做什么？” + topK=1
→ 固定检索片段 chunk=2、offset=20..34
→ “完成回归测试。[来源 1]”
→ Java Citation(reference=1, chunkIndex=2, startOffset=20, endOffset=34)
```

## 适用条件

- Java 业务服务通过 HTTP 调用 Python AI 服务；
- 下游需要展示、审计或回查答案依据；
- Python 和 Java 能共同维护版本化 JSON 契约。

## 限制与风险

- 字段映射通过不代表引用内容真实支持答案；
- `score` 的尺度取决于模型和实现，不能跨模型直接比较；
- 当前没有接口版本字段，破坏性变更仍需由契约测试保护；
- 本地替身没有验证真实模型、真实向量或数据授权。

## 参数实验与结论

- `top_k=1`：正常返回一条引用，跨语言字段保持完整；
- `top_k=11`：FastAPI 返回 422，服务端约束是最终防线；
- Python 返回字段与 Java DTO 不一致：Java 反序列化或断言失败，可暴露契约漂移。

## 一个失败案例

只使用 Java 内置假服务时，即使真实 FastAPI 改了字段名，测试也可能继续通过。必须增加穿过真实 FastAPI 路由的跨语言契约测试。

## 与 Java / Spring 的对照

DTO 类似 Controller 与 HTTP Client 之间的稳定协议；契约测试类似对真实 Controller 的集成测试。边界是：类型映射只检查结构，不替代 RAG 的相关性、充分性与忠实性评测。

## 对当前项目的启发

后续接口演进应同时修改 Python 响应、Java DTO、README 和跨语言契约测试，避免引用字段静默丢失。

## 可验证行动

运行 `RagCmsPythonContractTest`，确认答案和引用的 reference、Chunk、偏移与分数均被断言。

## 我能否脱离代码讲清楚

- 为什么需要它：避免跨系统调用丢失答案证据；
- 输入和输出：问题参数进入 Python，答案和完整引用返回 Java；
- 失败时先检查：先看 Python 原始 JSON，再看 Java DTO 映射；
- 仍未理解的问题：接口版本化在本项目达到什么规模时才值得引入。

## 参考材料

- `02-Projects/RAG-CMS/README.md`
- `05-Weekly-Reviews/2026-08-23-project-session.md`
