package com.udhyam.digital.common.api;

import com.udhyam.digital.catalogue.api.EligibilityResponse;
import java.util.List;

public record ApiErrorResponse(String code, String message, List<EligibilityResponse> details) {
    public ApiErrorResponse { details = details == null ? List.of() : List.copyOf(details); }
}
