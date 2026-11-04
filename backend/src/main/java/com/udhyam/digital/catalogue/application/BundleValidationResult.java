package com.udhyam.digital.catalogue.application;

import com.udhyam.digital.catalogue.domain.EligibilityResult;
import com.udhyam.digital.catalogue.domain.EligibilityStatus;
import java.util.List;

public record BundleValidationResult(EligibilityStatus status, List<EligibilityResult> products) {
    public BundleValidationResult { products = List.copyOf(products); }
    public boolean valid() { return status == EligibilityStatus.ELIGIBLE; }
}
