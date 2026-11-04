package com.udhyam.digital.catalogue.application;

import com.udhyam.digital.catalogue.domain.BusinessProfile;
import com.udhyam.digital.catalogue.domain.EligibilityIssue;
import com.udhyam.digital.catalogue.domain.EligibilityReasonCode;
import com.udhyam.digital.catalogue.domain.EligibilityResult;
import com.udhyam.digital.catalogue.domain.EligibilityStatus;
import com.udhyam.digital.catalogue.domain.GstinVerificationStatus;
import com.udhyam.digital.catalogue.domain.Product;
import java.util.ArrayList;
import java.util.List;
import org.springframework.stereotype.Service;

@Service
public class ProductEligibilityEvaluator {
    public EligibilityResult evaluate(Product product, BusinessProfile profile) {
        List<EligibilityIssue> issues = new ArrayList<>();
        if (!product.availableCityTiers().contains(profile.cityTier())) {
            issues.add(new EligibilityIssue(EligibilityReasonCode.CITY_TIER_UNSUPPORTED,
                    "Product is not available in city tier " + profile.cityTier() + ".", "An available city tier: " + product.availableCityTiers()));
        }
        if (profile.employeeCount() < product.minimumEmployees()) {
            issues.add(new EligibilityIssue(EligibilityReasonCode.INSUFFICIENT_EMPLOYEES,
                    "Business has fewer employees than this product requires.", "At least " + product.minimumEmployees() + " employees"));
        }
        if (profile.siteCount() < product.minimumSites()) {
            issues.add(new EligibilityIssue(EligibilityReasonCode.INSUFFICIENT_SITES,
                    "Business has fewer sites than this product requires.", "At least " + product.minimumSites() + " sites"));
        }
        if (!product.targetSegments().contains(profile.segment())) {
            issues.add(new EligibilityIssue(EligibilityReasonCode.SEGMENT_NOT_SUPPORTED,
                    "This product is not listed for the selected business segment.", "One of the catalogue target segments: " + product.targetSegments()));
        }
        if (product.requiresGstin()) addGstinIssue(profile.gstinStatus(), issues);
        EligibilityStatus status = resolveStatus(issues);
        return new EligibilityResult(product.productId(), status, issues);
    }

    private static void addGstinIssue(GstinVerificationStatus status, List<EligibilityIssue> issues) {
        switch (status) {
            case ACTIVE -> { }
            case CANCELLED -> issues.add(new EligibilityIssue(EligibilityReasonCode.GSTIN_CANCELLED,
                    "A Cancelled GSTIN cannot be used for this product.", "An Active GSTIN"));
            case SUSPENDED -> issues.add(new EligibilityIssue(EligibilityReasonCode.GSTIN_SUSPENDED,
                    "The GSTIN is Suspended and needs manual review.", "Manual review of GSTIN status"));
            case NOT_FOUND -> issues.add(new EligibilityIssue(EligibilityReasonCode.GSTIN_NOT_FOUND,
                    "The GSTIN was not found in the mock registry and needs manual review.", "Confirm registry details manually"));
            case LOOKUP_FAILED -> issues.add(new EligibilityIssue(EligibilityReasonCode.GSTIN_LOOKUP_FAILED,
                    "GSTIN lookup failed; eligibility cannot be confirmed.", "Retry or review registry lookup"));
            case NOT_PROVIDED -> issues.add(new EligibilityIssue(EligibilityReasonCode.GSTIN_REQUIRED,
                    "This product requires an Active GSTIN.", "Provide and verify an Active GSTIN"));
        }
    }

    public static EligibilityStatus resolveStatus(List<EligibilityIssue> issues) {
        if (issues.stream().anyMatch(issue -> switch (issue.code()) {
            case GSTIN_SUSPENDED, GSTIN_NOT_FOUND, GSTIN_LOOKUP_FAILED -> true;
            default -> false;
        })) {
            if (issues.stream().anyMatch(issue -> switch (issue.code()) {
                case CITY_TIER_UNSUPPORTED, INSUFFICIENT_EMPLOYEES, INSUFFICIENT_SITES,
                        GSTIN_REQUIRED, GSTIN_CANCELLED, SEGMENT_NOT_SUPPORTED,
                        DEPENDENCY_NOT_SATISFIED, UNKNOWN_PRODUCT -> true;
                default -> false;
            })) return EligibilityStatus.INELIGIBLE;
            return EligibilityStatus.MANUAL_REVIEW;
        }
        return issues.isEmpty() ? EligibilityStatus.ELIGIBLE : EligibilityStatus.INELIGIBLE;
    }
}
