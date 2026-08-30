# Java 调用 Python AI 服务｜接口契约与故障边界｜2026-08-30

## 业务背景

RAG-CMS 的问答能力由 Python 提供，现有 Java 业务系统需要获得答案及其依据，并在失败时判断问题位于 Java、Python 还是外部 Embedding/LLM。

## 原有问题

- Java 没有稳定的请求、回答和引用 DTO；
- 只返回答案会丢失证据追溯能力；
- 所有异常若统一成“调用失败”，无法选择正确排查路径；
- Java 自建假服务只能验证自己的预期 JSON，不能发现真实 Python 契约漂移。

## 核心约束

- Java 11、Spring Boot 2.7.18；
- Python `top_k` 约束为 `1..10`；
- 答案必须携带文档、Chunk、源路径、字符偏移和分数；
- 当前不引入网关、服务注册、重试或熔断；
- 未获授权前不向外部模型发送数据；
- Docker 缺失，不与本次 Java 集成并行补齐。

## 解决方案

```text
Java QuestionRequest
→ WebClient POST /v1/documents/{documentId}/questions
→ FastAPI 参数校验
→ Embedding → Top-K 检索 → LLM
→ answer + citations
→ Java QuestionResponse / Citation

失败分支：
无 HTTP 响应 → TRANSPORT
超过 Java 截止时间 → TIMEOUT
Python 能力/配置不可用 → 503 SERVICE_UNAVAILABLE
Python 外部依赖失败 → 502 UPSTREAM_FAILURE
```

实现分两层验证：

1. Java 随机端口假服务验证请求 JSON、DTO 与 502/503/超时/传输映射；
2. Java 通过真实 HTTP 调用 FastAPI 路由，Python 的 Embedding、检索、LLM 使用明确本地替身，验证跨语言契约而不访问外部服务。

## 关键取舍

1. **保留完整引用，而非只返回答案。** 增加 DTO 字段维护成本，换取审计、故障定位和质量评测能力。
2. **先分层测试，再接真实模型。** 不能一次证明生产链路，但能先排除 Java HTTP/JSON 与 Python 路由契约问题，缩小真实联调失败面。
3. **显式错误分类，而非统一异常。** 业务层多处理几个 FailureType，换取可操作的恢复与告警语义。
4. **使用同步 `block()` 完成最小闭环。** 对当前调用示例简单直接；若进入响应式服务链路，必须改为非阻塞返回，不能照搬。

## 风险与限制

- 本地替身结果不能证明真实模型、向量、网络配置或数据授权正确；
- Java 总体超时尚未拆成连接、响应、Embedding 和 LLM 的分段预算；
- 没有接口版本字段，破坏性变更依赖契约测试发现；
- 引用字段完整不等于引用忠实，仍需 RAG 四层评测；
- 502/503 的语义需要 Python 与 Java 长期共同维护。

## 可迁移经验

- 跨语言 AI 接口要同时设计成功数据、证据数据和失败语义；
- 假服务测试负责可控故障，真实路由契约测试负责发现服务间漂移；
- 排查从最外层可观察事实开始：是否收到 HTTP、状态码、原始 JSON、DTO 映射，再进入模型质量；
- “测试通过”的结论必须带边界，不能把契约验证扩大为真实模型验收。

## 对 RAG-CMS 的启发

下一步先补 Week 4 验收和知识沉淀。接真实模型时复用现有 Java 客户端与故障分类，只替换已明确标注的 Python 本地替身，并在数据授权、配置、网络都确认后运行少量真实问题。若契约变化，必须同步更新 Python、Java、README 和跨语言测试。

## 可验证行动

- Java 五项假服务测试保持通过；
- `RagCmsPythonContractTest` 穿过真实 FastAPI 路由并断言完整引用；
- `top_k=11` 返回 422，证明服务端边界仍生效；
- 真实模型调用另立验收记录，不复用本地替身结论。
