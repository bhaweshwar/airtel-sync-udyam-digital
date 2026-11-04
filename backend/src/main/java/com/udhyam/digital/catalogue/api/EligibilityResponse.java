package com.udhyam.digital.catalogue.api;

import com.udhyam.digital.catalogue.domain.EligibilityResult;
import com.udhyam.digital.catalogue.domain.EligibilityStatus;
import java.util.List;

public record EligibilityResponse(String productId, EligibilityStatus status, List<Issue> issues) {
    public static EligibilityResponse from(EligibilityResult result) {
        return new EligibilityResponse(result.productId(), result.status(), result.issues().stream()
                .map(issue -> new Issue(issue.code().name(), issue.message(), issue.requirement())).toList());
    }
    public record Issue(String code, String message, String requirement) { }
}
