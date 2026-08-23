package com.example.ragcms.client;

import com.fasterxml.jackson.annotation.JsonProperty;

public final class QuestionRequest {
    private final String question;
    private final int topK;

    public QuestionRequest(String question, int topK) {
        this.question = question;
        this.topK = topK;
    }

    public String getQuestion() {
        return question;
    }

    @JsonProperty("top_k")
    public int getTopK() {
        return topK;
    }
}
