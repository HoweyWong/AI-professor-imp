package com.example.ragcms.client;

public final class RagCmsClientException extends RuntimeException {
    public enum FailureType {
        UPSTREAM_FAILURE,
        SERVICE_UNAVAILABLE,
        TIMEOUT,
        TRANSPORT,
        HTTP_ERROR
    }

    private final FailureType failureType;
    private final Integer statusCode;
    private final String responseBody;

    public RagCmsClientException(
            FailureType failureType,
            String message,
            Integer statusCode,
            String responseBody,
            Throwable cause
    ) {
        super(message, cause);
        this.failureType = failureType;
        this.statusCode = statusCode;
        this.responseBody = responseBody;
    }

    public FailureType getFailureType() {
        return failureType;
    }

    public Integer getStatusCode() {
        return statusCode;
    }

    public String getResponseBody() {
        return responseBody;
    }
}
