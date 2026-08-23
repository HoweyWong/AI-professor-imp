package com.example.ragcms.client;

import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.concurrent.atomic.AtomicReference;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class RagCmsClientTest {
    private HttpServer server;

    @AfterEach
    void stopServer() {
        if (server != null) {
            server.stop(0);
            server = null;
        }
    }

    @Test
    void mapsAnswerAndTraceableCitation() throws Exception {
        AtomicReference<String> requestBody = new AtomicReference<>();
        startServer(exchange -> {
            requestBody.set(new String(exchange.getRequestBody().readAllBytes(), StandardCharsets.UTF_8));
            respond(exchange, 200, "{" +
                    "\"document_id\":\"document-1\"," +
                    "\"question\":\"发布前做什么？\"," +
                    "\"answer\":\"完成回归测试。[来源 1]\"," +
                    "\"citations\":[{" +
                    "\"reference\":1,\"document_id\":\"document-1\",\"chunk_index\":2," +
                    "\"source_path\":\"document-1/source.md\",\"start_offset\":20," +
                    "\"end_offset\":34,\"score\":0.91}]}" );
        });

        QuestionResponse response = client(Duration.ofSeconds(1))
                .ask("document-1", " 发布前做什么？ ", 3);

        assertThat(response.getAnswer()).contains("[来源 1]");
        assertThat(response.getCitations()).hasSize(1);
        assertThat(response.getCitations().get(0).getChunkIndex()).isEqualTo(2);
        assertThat(response.getCitations().get(0).getStartOffset()).isEqualTo(20);
        assertThat(requestBody.get()).contains("\"question\":\"发布前做什么？\"");
        assertThat(requestBody.get()).contains("\"top_k\":3");
    }

    @Test
    void distinguishesUpstreamFailureAndServiceUnavailable() throws Exception {
        startServer(exchange -> respond(exchange, 503, "模型服务未配置"));

        assertThatThrownBy(() -> client(Duration.ofSeconds(1)).ask("document-1", "问题", 3))
                .isInstanceOfSatisfying(RagCmsClientException.class, error -> {
                    assertThat(error.getFailureType())
                            .isEqualTo(RagCmsClientException.FailureType.SERVICE_UNAVAILABLE);
                    assertThat(error.getStatusCode()).isEqualTo(503);
                    assertThat(error.getResponseBody()).contains("模型服务未配置");
                });

        stopServer();
        startServer(exchange -> respond(exchange, 502, "模型服务调用失败"));

        assertThatThrownBy(() -> client(Duration.ofSeconds(1)).ask("document-1", "问题", 3))
                .isInstanceOfSatisfying(RagCmsClientException.class, error ->
                        assertThat(error.getFailureType())
                                .isEqualTo(RagCmsClientException.FailureType.UPSTREAM_FAILURE));
    }

    @Test
    void mapsSlowResponseToTimeout() throws Exception {
        startServer(exchange -> {
            try {
                Thread.sleep(200);
                respond(exchange, 200, "{}");
            } catch (InterruptedException interrupted) {
                Thread.currentThread().interrupt();
            }
        });

        assertThatThrownBy(() -> client(Duration.ofMillis(30)).ask("document-1", "问题", 3))
                .isInstanceOfSatisfying(RagCmsClientException.class, error ->
                        assertThat(error.getFailureType())
                                .isEqualTo(RagCmsClientException.FailureType.TIMEOUT));
    }

    @Test
    void rejectsInvalidArgumentsBeforeSendingRequest() {
        RagCmsClient client = new RagCmsClient("http://127.0.0.1:1", Duration.ofSeconds(1));

        assertThatThrownBy(() -> client.ask(" ", "问题", 3))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> client.ask("document-1", " ", 3))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> client.ask("document-1", "问题", 11))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void mapsConnectionFailureToTransport() throws Exception {
        startServer(exchange -> respond(exchange, 200, "{}"));
        int closedPort = server.getAddress().getPort();
        stopServer();
        RagCmsClient client = new RagCmsClient(
                "http://127.0.0.1:" + closedPort,
                Duration.ofSeconds(1)
        );

        assertThatThrownBy(() -> client.ask("document-1", "问题", 3))
                .isInstanceOfSatisfying(RagCmsClientException.class, error ->
                        assertThat(error.getFailureType())
                                .isEqualTo(RagCmsClientException.FailureType.TRANSPORT));
    }

    private RagCmsClient client(Duration timeout) {
        return new RagCmsClient("http://127.0.0.1:" + server.getAddress().getPort(), timeout);
    }

    private void startServer(Handler handler) throws IOException {
        server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        server.createContext("/v1/documents/document-1/questions", exchange -> handler.handle(exchange));
        server.start();
    }

    private static void respond(HttpExchange exchange, int status, String body) throws IOException {
        byte[] bytes = body.getBytes(StandardCharsets.UTF_8);
        exchange.getResponseHeaders().set("Content-Type", "application/json; charset=utf-8");
        exchange.sendResponseHeaders(status, bytes.length);
        exchange.getResponseBody().write(bytes);
        exchange.close();
    }

    @FunctionalInterface
    private interface Handler {
        void handle(HttpExchange exchange) throws IOException;
    }
}
