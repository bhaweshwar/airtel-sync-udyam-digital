package com.udhyam.digital.catalogue.api;

import com.udhyam.digital.catalogue.domain.BusinessNeed;
import com.udhyam.digital.catalogue.domain.BusinessProfile;
import com.udhyam.digital.catalogue.domain.BusinessSegment;
import com.udhyam.digital.catalogue.domain.GstinVerificationStatus;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import java.util.Set;

public record BusinessProfileRequest(
        @NotNull BusinessSegment segment,
        String businessType,
        @Min(0) int employeeCount,
        @Min(1) int siteCount,
        @NotBlank String city,
        @Min(1) int cityTier,
        @NotBlank String state,
        GstinVerificationStatus gstinStatus,
        Set<BusinessNeed> currentRequirements,
        String industryActivity) {
    public BusinessProfile toDomain() {
        return new BusinessProfile(segment, businessType, employeeCount, siteCount, city, cityTier,
                state, gstinStatus, currentRequirements, industryActivity);
    }
}
