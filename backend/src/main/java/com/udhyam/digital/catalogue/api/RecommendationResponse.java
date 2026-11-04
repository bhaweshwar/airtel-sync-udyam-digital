package com.udhyam.digital.catalogue.api;

import com.udhyam.digital.catalogue.application.BundlePrice;
import com.udhyam.digital.catalogue.application.BundleValidationResult;
import com.udhyam.digital.catalogue.domain.EligibilityResult;
import com.udhyam.digital.catalogue.domain.ProductSelection;
import java.util.List;

public record RecommendationResponse(String summary, List<BundleRecommendation> recommendations,
        List<EligibilityResponse> excludedProducts) {
    public RecommendationResponse {
        recommendations = List.copyOf(recommendations);
        excludedProducts = List.copyOf(excludedProducts);
    }
    public record BundleRecommendation(String bundleName, List<ProductSelection> selections,
            BundleValidationResponse eligibility, BundlePrice pricing, List<String> explanations) {
        public BundleRecommendation { selections = List.copyOf(selections); explanations = List.copyOf(explanations); }
    }
    public static EligibilityResponse exclusion(EligibilityResult result) { return EligibilityResponse.from(result); }
}
