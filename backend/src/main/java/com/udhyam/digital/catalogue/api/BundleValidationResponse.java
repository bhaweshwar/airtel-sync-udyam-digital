package com.udhyam.digital.catalogue.api;

import com.udhyam.digital.catalogue.application.BundleValidationResult;
import com.udhyam.digital.catalogue.domain.EligibilityStatus;
import java.util.List;

public record BundleValidationResponse(boolean valid, EligibilityStatus status, List<EligibilityResponse> products) {
    public static BundleValidationResponse from(BundleValidationResult result) {
        return new BundleValidationResponse(result.valid(), result.status(), result.products().stream().map(EligibilityResponse::from).toList());
    }
}
