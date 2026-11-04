package com.udhyam.digital.advisor.application;

import org.springframework.http.HttpStatus;

public final class AdvisorProviderException extends RuntimeException {
    private final String code;
    private final HttpStatus status;

    public AdvisorProviderException(String code, HttpStatus status, String safeMessage) {
        super(safeMessage);
        this.code = code;
        this.status = status;
    }
    public String code() { return code; }
    public HttpStatus status() { return status; }
}
