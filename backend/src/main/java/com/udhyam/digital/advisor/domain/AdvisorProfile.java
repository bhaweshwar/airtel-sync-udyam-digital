package com.udhyam.digital.advisor.domain;

import com.udhyam.digital.catalogue.domain.BusinessNeed;
import com.udhyam.digital.catalogue.domain.BusinessProfile;
import com.udhyam.digital.catalogue.domain.BusinessSegment;
import com.udhyam.digital.catalogue.domain.GstinVerificationStatus;
import java.util.LinkedHashSet;
import java.util.Collections;
import java.util.Set;

/** Customer-stated discovery fields. A null field remains unknown; GSTIN status is never registry-verified here. */
public record AdvisorProfile(
        BusinessSegment segment, String businessType, Integer employeeCount, Integer siteCount,
        String city, Integer cityTier, String state, GstinVerificationStatus gstinStatus,
        Set<BusinessNeed> currentRequirements, String industryActivity) {

    public AdvisorProfile {
        currentRequirements = currentRequirements == null ? Set.of() : Set.copyOf(currentRequirements);
    }

    public static AdvisorProfile empty() {
        return new AdvisorProfile(null, null, null, null, null, null, null,
                null, Set.of(), null);
    }

    public AdvisorProfile withNeed(BusinessNeed need) {
        var needs = new LinkedHashSet<>(currentRequirements);
        needs.add(need);
        return new AdvisorProfile(segment, businessType, employeeCount, siteCount, city, cityTier,
                state, gstinStatus, needs, industryActivity);
    }

    public boolean ready() {
        return segment != null && businessType != null && employeeCount != null && siteCount != null
                && city != null && cityTier != null && state != null && !currentRequirements.isEmpty();
    }

    public Set<String> missingFields() {
        var missing = new LinkedHashSet<String>();
        if (segment == null || businessType == null) missing.add("BUSINESS_TYPE");
        if (employeeCount == null) missing.add("EMPLOYEE_COUNT");
        if (siteCount == null) missing.add("SITE_COUNT");
        if (city == null || state == null || cityTier == null) missing.add("LOCATION");
        if (currentRequirements.isEmpty()) missing.add("BUSINESS_NEEDS");
        return Collections.unmodifiableSet(missing);
    }

    public BusinessProfile toRecommendationProfile() {
        if (!ready()) throw new IllegalStateException("The business profile is incomplete.");
        // A conversational statement is not a registry result. Keep GST-gated offers ineligible until a later verified flow.
        return new BusinessProfile(segment, businessType, employeeCount, siteCount, city, cityTier,
                state, GstinVerificationStatus.NOT_PROVIDED, currentRequirements, industryActivity);
    }
}
