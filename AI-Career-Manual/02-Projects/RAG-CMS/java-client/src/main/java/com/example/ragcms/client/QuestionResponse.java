package com.example.ragcms.client;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.ArrayList;
import java.util.List;

public final class QuestionResponse {
    private String documentId;
    private String question;
    private String answer;
    private List<Citation> citations = new ArrayList<>();

    public QuestionResponse() {
    }

    @JsonProperty("document_id")
    public String getDocumentId() {
        return documentId;
    }

    @JsonProperty("document_id")
    public void setDocumentId(String documentId) {
        this.documentId = documentId;
    }

    public String getQuestion() {
        return question;
    }

    public void setQuestion(String question) {
        this.question = question;
    }

    public String getAnswer() {
        return answer;
    }

    public void setAnswer(String answer) {
        this.answer = answer;
    }

    public List<Citation> getCitations() {
        return citations;
    }

    public void setCitations(List<Citation> citations) {
        this.citations = citations;
    }
}
