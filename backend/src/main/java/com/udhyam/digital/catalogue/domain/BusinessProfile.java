package com.udhyam.digital.catalogue.domain;

import java.util.Set;

public record BusinessProfile(
        BusinessSegment segment,
        String businessType,
        int employeeCount,
        int siteCount,
        String city,
        int cityTier,
        String state,
        GstinVerificationStatus gstinStatus,
        Set<BusinessNeed> currentRequirements,
        String industryActivity) {

    public BusinessProfile {
        if (segment == null) throw new IllegalArgumentException("segment is required");
        if (employeeCount < 0) throw new IllegalArgumentException("employeeCount cannot be negative");
        if (siteCount < 1) throw new IllegalArgumentException("siteCount must be at least 1");
        if (cityTier < 1) throw new IllegalArgumentException("cityTier must be positive");
        if (city == null || city.isBlank()) throw new IllegalArgumentException("city is required");
        if (state == null || state.isBlank()) throw new IllegalArgumentException("state is required");
        gstinStatus = gstinStatus == null ? GstinVerificationStatus.NOT_PROVIDED : gstinStatus;
        currentRequirements = currentRequirements == null ? Set.of() : Set.copyOf(currentRequirements);
        businessType = cleanOptional(businessType);
        industryActivity = cleanOptional(industryActivity);
        city = city.trim();
        state = state.trim();
    }

    private static String cleanOptional(String value) {
        return value == null || value.isBlank() ? null : value.trim();
    }
}
