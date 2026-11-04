package com.udhyam.digital.advisor.application;

import com.udhyam.digital.advisor.domain.AdvisorMessage;
import com.udhyam.digital.advisor.domain.AdvisorProfile;
import com.udhyam.digital.catalogue.api.RecommendationResponse;
import java.util.List;

/** LLM port; model output is candidate language/facts and never a commercial decision. */
public interface AdvisorModelProvider {
    ExtractionResponse extract(AdvisorProfile currentProfile, List<AdvisorMessage> recentHistory,
            String latestCustomerMessage);

    ExplanationResponse explain(AdvisorProfile profile, RecommendationResponse recommendation);

    record ExtractedFact(String field, String value, String evidence) { }
    record ExtractionResponse(String reply, List<ExtractedFact> facts, List<String> followUpFields) { }
    record ExplanationResponse(String summary, List<ProductExplanation> products) { }
    record ProductExplanation(String productId, String reason) { }
}
