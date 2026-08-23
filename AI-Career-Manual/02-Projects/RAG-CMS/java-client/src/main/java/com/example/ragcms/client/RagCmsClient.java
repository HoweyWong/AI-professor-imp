package com.example.ragcms.client;

import org.springframework.web.reactive.function.client.ClientResponse;
import org.springframework.web.reactive.function.client.WebClient;
import org.springframework.web.reactive.function.client.WebClientRequestException;
import reactor.core.publisher.Mono;

import java.time.Duration;
import java.util.Objects;
import java.util.concurrent.TimeoutException;

public final class RagCmsClient {
    private final WebClient webClient;
    private final Duration timeout;

    public RagCmsClient(String baseUrl, Duration timeout) {
        if (baseUrl == null || baseUrl.trim().isEmpty()) {
            throw new IllegalArgumentException("baseUrl 不能为空");
        }
        this.timeout = Objects.requireNonNull(timeout, "timeout 不能为空");
        if (timeout.isZero() || timeout.isNegative()) {
            throw new IllegalArgumentException("timeout 必须大于 0");
        }
        this.webClient = WebClient.builder().baseUrl(baseUrl).build();
    }

    public QuestionResponse ask(String documentId, String question, int topK) {
        String normalizedDocumentId = requireText(documentId, "documentId 不能为空");
        String normalizedQuestion = requireText(question, "question 不能为空");
        if (topK < 1 || topK > 10) {
            throw new IllegalArgumentException("topK 必须在 1 到 10 之间");
        }

        return webClient.post()
                .uri("/v1/documents/{documentId}/questions", normalizedDocumentId)
                .bodyValue(new QuestionRequest(normalizedQuestion, topK))
                .exchangeToMono(this::mapResponse)
                .timeout(timeout)
                .onErrorMap(
                        TimeoutException.class,
                        error -> new RagCmsClientException(
                                RagCmsClientException.FailureType.TIMEOUT,
                                "RAG-CMS 请求超时",
                                null,
                                null,
                                error
                        )
                )
                .onErrorMap(
                        WebClientRequestException.class,
                        error -> new RagCmsClientException(
                                RagCmsClientException.FailureType.TRANSPORT,
                                "无法连接 RAG-CMS 服务",
                                null,
                                null,
                                error
                        )
                )
                .block();
    }

    private Mono<QuestionResponse> mapResponse(ClientResponse response) {
        int status = response.rawStatusCode();
        if (response.statusCode().is2xxSuccessful()) {
            return response.bodyToMono(QuestionResponse.class);
        }
        return response.bodyToMono(String.class)
                .defaultIfEmpty("")
                .flatMap(body -> Mono.error(httpException(status, body)));
    }

    private RagCmsClientException httpException(int status, String body) {
        RagCmsClientException.FailureType type;
        if (status == 502) {
            type = RagCmsClientException.FailureType.UPSTREAM_FAILURE;
        } else if (status == 503) {
            type = RagCmsClientException.FailureType.SERVICE_UNAVAILABLE;
        } else {
            type = RagCmsClientException.FailureType.HTTP_ERROR;
        }
        return new RagCmsClientException(type, "RAG-CMS 返回 HTTP " + status, status, body, null);
    }

    private String requireText(String value, String message) {
        if (value == null || value.trim().isEmpty()) {
            throw new IllegalArgumentException(message);
        }
        return value.trim();
    }
}
