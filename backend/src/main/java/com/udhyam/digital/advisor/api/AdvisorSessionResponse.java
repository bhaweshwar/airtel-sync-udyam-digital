package com.udhyam.digital.advisor.api;

import com.udhyam.digital.advisor.domain.AdvisorMessage;
import com.udhyam.digital.advisor.domain.AdvisorProfile;
import com.udhyam.digital.catalogue.api.RecommendationResponse;
import java.util.List;
import java.util.Map;

public record AdvisorSessionResponse(String conversationId, List<AdvisorMessage> messages,
        AdvisorProfile profile, List<String> missingFields, List<String> followUpQuestions,
        String status, RecommendationResponse recommendation, String advisorExplanation,
        Map<String, String> productExplanations, boolean gstinStatusVerified) {
    public AdvisorSessionResponse {
        messages = List.copyOf(messages);
        missingFields = List.copyOf(missingFields);
        followUpQuestions = List.copyOf(followUpQuestions);
        productExplanations = Map.copyOf(productExplanations);
    }
}
