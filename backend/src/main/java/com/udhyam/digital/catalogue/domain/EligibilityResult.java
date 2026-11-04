package com.udhyam.digital.catalogue.domain;

import java.util.List;

public record EligibilityResult(String productId, EligibilityStatus status, List<EligibilityIssue> issues) {
    public EligibilityResult {
        issues = List.copyOf(issues);
    }
    public boolean immediatelyPurchasable() { return status == EligibilityStatus.ELIGIBLE; }
}
