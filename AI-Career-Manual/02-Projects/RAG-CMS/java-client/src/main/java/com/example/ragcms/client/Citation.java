package com.example.ragcms.client;

import com.fasterxml.jackson.annotation.JsonProperty;

public final class Citation {
    private int reference;
    private String documentId;
    private int chunkIndex;
    private String sourcePath;
    private int startOffset;
    private int endOffset;
    private double score;

    public Citation() {
    }

    public int getReference() {
        return reference;
    }

    public void setReference(int reference) {
        this.reference = reference;
    }

    @JsonProperty("document_id")
    public String getDocumentId() {
        return documentId;
    }

    @JsonProperty("document_id")
    public void setDocumentId(String documentId) {
        this.documentId = documentId;
    }

    @JsonProperty("chunk_index")
    public int getChunkIndex() {
        return chunkIndex;
    }

    @JsonProperty("chunk_index")
    public void setChunkIndex(int chunkIndex) {
        this.chunkIndex = chunkIndex;
    }

    @JsonProperty("source_path")
    public String getSourcePath() {
        return sourcePath;
    }

    @JsonProperty("source_path")
    public void setSourcePath(String sourcePath) {
        this.sourcePath = sourcePath;
    }

    @JsonProperty("start_offset")
    public int getStartOffset() {
        return startOffset;
    }

    @JsonProperty("start_offset")
    public void setStartOffset(int startOffset) {
        this.startOffset = startOffset;
    }

    @JsonProperty("end_offset")
    public int getEndOffset() {
        return endOffset;
    }

    @JsonProperty("end_offset")
    public void setEndOffset(int endOffset) {
        this.endOffset = endOffset;
    }

    public double getScore() {
        return score;
    }

    public void setScore(double score) {
        this.score = score;
    }
}
