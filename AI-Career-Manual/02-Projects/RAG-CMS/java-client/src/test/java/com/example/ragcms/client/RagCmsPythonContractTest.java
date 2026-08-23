package com.example.ragcms.client;

import org.junit.jupiter.api.Test;

import java.time.Duration;

import static org.assertj.core.api.Assertions.assertThat;
import static org.junit.jupiter.api.Assumptions.assumeTrue;

class RagCmsPythonContractTest {
    @Test
    void callsTheRealPythonRouteAndKeepsTraceableCitation() {
        String baseUrl = System.getenv("RAG_CMS_CONTRACT_BASE_URL");
        assumeTrue(baseUrl != null && !baseUrl.isBlank(),
                "Set RAG_CMS_CONTRACT_BASE_URL to run the Java-to-Python contract test");

        QuestionResponse response = new RagCmsClient(baseUrl, Duration.ofSeconds(3))
                .ask("contract-document", "发布前做什么？", 1);

        assertThat(response.getDocumentId()).isEqualTo("contract-document");
        assertThat(response.getQuestion()).isEqualTo("发布前做什么？");
        assertThat(response.getAnswer()).isEqualTo("完成回归测试。[来源 1]");
        assertThat(response.getCitations()).hasSize(1);
        Citation citation = response.getCitations().get(0);
        assertThat(citation.getReference()).isEqualTo(1);
        assertThat(citation.getChunkIndex()).isEqualTo(2);
        assertThat(citation.getStartOffset()).isEqualTo(20);
        assertThat(citation.getEndOffset()).isEqualTo(34);
        assertThat(citation.getScore()).isEqualTo(0.91);
    }
}
