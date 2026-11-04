package com.udhyam.digital.advisor.api;

import com.udhyam.digital.advisor.domain.AdvisorProfile;

public record AdvisorProfileResponse(AdvisorProfile profile, String gstinStatusSource,
        boolean gstinStatusVerified) { }
