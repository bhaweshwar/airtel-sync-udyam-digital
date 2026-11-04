package com.udhyam.digital.advisor.application;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.udhyam.digital.advisor.domain.AdvisorProfile;
import com.udhyam.digital.catalogue.api.RecommendationResponse;
import com.udhyam.digital.catalogue.domain.ProductSelection;
import com.udhyam.digital.catalogue.domain.BusinessNeed;
import com.udhyam.digital.catalogue.domain.BusinessSegment;
import com.udhyam.digital.catalogue.application.RecommendationService;
import java.util.List;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

class AdvisorSessionServiceTest {
    private AdvisorModelProvider provider;
    private RecommendationService recommendationService;
    private AdvisorSessionService sessions;

    @BeforeEach
    void setUp() {
        provider = mock(AdvisorModelProvider.class);
        recommendationService = mock(RecommendationService.class);
        sessions = new AdvisorSessionService(provider, recommendationService, new SensitiveMessageRedactor());
    }

    @Test
    void missingFactsRemainUnknownAndGenerateOnlyRelevantFollowups() {
        when(provider.extract(any(), any(), eq("I run a bakery."))).thenReturn(
                new AdvisorModelProvider.ExtractionResponse("Thanks for sharing that.",
                        List.of(fact("BUSINESS_TYPE", "Bakery", "bakery")), List.of("EMPLOYEE_COUNT", "SITE_COUNT")));
        var response = sessions.send(sessions.start(null).conversationId(), "I run a bakery.");
        assertThat(response.profile().businessType()).isEqualTo("Bakery");
        assertThat(response.profile().employeeCount()).isNull();
        assertThat(response.missingFields()).contains("EMPLOYEE_COUNT", "LOCATION", "BUSINESS_NEEDS");
        assertThat(response.followUpQuestions()).containsExactly("How many people work in the business?", "How many business locations should we consider?");
        assertThat(response.status()).isEqualTo("DISCOVERY");
        verify(recommendationService, never()).recommend(any());
    }

    @Test
    void laterTurnUsesConversationHistoryAndPreservesExistingFactsUnlessCorrected() {
        String id = sessions.start(null).conversationId();
        when(provider.extract(any(), any(), eq("I employ 4 people."))).thenReturn(
                new AdvisorModelProvider.ExtractionResponse("Understood.", List.of(fact("EMPLOYEE_COUNT", "4", "4 people")), List.of()));
        sessions.send(id, "I employ 4 people.");
        when(provider.extract(any(), any(), eq("I have 8 people now."))).thenReturn(
                new AdvisorModelProvider.ExtractionResponse("Thanks.", List.of(fact("EMPLOYEE_COUNT", "8", "8 people")), List.of()));
        var conflict = sessions.send(id, "I have 8 people now.");
        assertThat(conflict.profile().employeeCount()).isEqualTo(4);
        assertThat(conflict.followUpQuestions()).singleElement().asString().contains("different employee count");
        verify(provider).extract(any(), any(), eq("I have 8 people now."));

        when(provider.extract(any(), any(), eq("Correction: we have 8 people."))).thenReturn(
                new AdvisorModelProvider.ExtractionResponse("Got it.", List.of(fact("EMPLOYEE_COUNT", "8", "8 people")), List.of()));
        var corrected = sessions.send(id, "Correction: we have 8 people.");
        assertThat(corrected.profile().employeeCount()).isEqualTo(8);
        assertThat(corrected.messages()).hasSize(6);
    }

    @Test
    void identifiersAreRedactedBeforeProviderAndSessionHistory() {
        String id = sessions.start(null).conversationId();
        String message = "My PAN is ABCDE1234F and I run a shop.";
        when(provider.extract(any(), any(), any())).thenReturn(new AdvisorModelProvider.ExtractionResponse(
                "I can help with your shop.", List.of(), List.of("BUSINESS_TYPE")));
        var result = sessions.send(id, message);
        verify(provider).extract(any(), any(), eq("My PAN is [removed] and I run a shop."));
        assertThat(result.messages().getFirst().content()).doesNotContain("ABCDE1234F").contains("[removed]");
    }

    @Test
    void identifierOnlyMessageIsRejectedBeforeProviderInvocation() {
        String id = sessions.start(null).conversationId();
        org.assertj.core.api.Assertions.assertThatThrownBy(() -> sessions.send(id, "ABCDE1234F"))
                .isInstanceOf(org.springframework.web.server.ResponseStatusException.class);
        verify(provider, never()).extract(any(), any(), any());
    }

    @Test
    void extractionEvidenceMustBePresentInTheLatestCustomerTurn() {
        String id = sessions.start(null).conversationId();
        when(provider.extract(any(), any(), any())).thenReturn(new AdvisorModelProvider.ExtractionResponse(
                "Please tell me more.", List.of(fact("CITY", "Mumbai", "Delhi")), List.of("LOCATION")));
        var response = sessions.send(id, "I run a studio.");
        assertThat(response.profile().city()).isNull();
    }

    @Test
    void numericProfileFactsRequireMatchingFieldContextInQuotedEvidence() {
        String id = sessions.start(null).conversationId();
        when(provider.extract(any(), any(), any())).thenReturn(new AdvisorModelProvider.ExtractionResponse(
                "Tell me more.", List.of(fact("EMPLOYEE_COUNT", "4", "4"), fact("CITY_TIER", "2", "tier two")), List.of()));
        var response = sessions.send(id, "I am based in Jaipur. My shop is on the second tier floor.");
        assertThat(response.profile().employeeCount()).isNull();
        assertThat(response.profile().cityTier()).isNull();
    }

    @Test
    void activeGstinIsNotAcceptedFromAnUnrelatedEvidenceQuote() {
        String id = sessions.start(null).conversationId();
        when(provider.extract(any(), any(), any())).thenReturn(new AdvisorModelProvider.ExtractionResponse(
                "Thanks.", List.of(fact("GSTIN_STATUS", "ACTIVE", "I have a GSTIN")), List.of()));
        var response = sessions.send(id, "I have a GSTIN.");
        assertThat(response.profile().gstinStatus()).isNull();
        assertThat(response.gstinStatusVerified()).isFalse();
    }

    @Test
    void selfReportedActiveGstinNeverBecomesVerifiedCatalogueEligibility() {
        String id = sessions.start(null).conversationId();
        when(provider.extract(any(), any(), any())).thenReturn(new AdvisorModelProvider.ExtractionResponse(
                "Thanks.", List.of(fact("GSTIN_STATUS", "ACTIVE", "my GSTIN is active")), List.of()));
        var response = sessions.send(id, "My GSTIN is active.");
        assertThat(response.profile().gstinStatus().name()).isEqualTo("ACTIVE");
        var complete = new AdvisorProfile(BusinessSegment.MICRO_RETAIL_AND_SERVICES, "Bakery", 4, 1, "Jaipur", 1,
                "Rajasthan", response.profile().gstinStatus(), java.util.Set.of(BusinessNeed.RELIABLE_INTERNET), null);
        assertThat(complete.toRecommendationProfile().gstinStatus().name()).isEqualTo("NOT_PROVIDED");
        assertThat(response.gstinStatusVerified()).isFalse();
    }

    @Test
    void catalogueResultIsReturnedWithoutProviderControlOverTheResult() {
        String id = sessions.start(null).conversationId();
        var engineResult = new RecommendationResponse("Engine result", List.of(), List.of());
        when(recommendationService.recommend(any())).thenReturn(engineResult);
        when(provider.extract(any(), any(), any())).thenReturn(new AdvisorModelProvider.ExtractionResponse(
                "Thanks.", completeFacts(), List.of()));
        when(provider.explain(any(), eq(engineResult))).thenReturn(new AdvisorModelProvider.ExplanationResponse("Here is a fit for your needs.", List.of()));
        var response = sessions.send(id, "I run a bakery in Jaipur, Rajasthan, 4 employees, 1 location, tier 2, needing reliable internet.");
        assertThat(response.recommendation()).isSameAs(engineResult);
        assertThat(response.status()).isEqualTo("RECOMMENDATION_READY");
        assertThat(response.advisorExplanation()).isEqualTo("Here is a fit for your needs.");
        assertThat(response.gstinStatusVerified()).isFalse();
    }

    @Test
    void explanationCannotIntroduceUnselectedProductIdsOrPriceClaims() {
        String id = sessions.start(null).conversationId();
        var bundle = new RecommendationResponse.BundleRecommendation("engine bundle", List.of(new ProductSelection("P01", 1)),
                null, null, List.of("Engine-provided reason."));
        var engineResult = new RecommendationResponse("Engine result", List.of(bundle), List.of());
        when(recommendationService.recommend(any())).thenReturn(engineResult);
        when(provider.extract(any(), any(), any())).thenReturn(new AdvisorModelProvider.ExtractionResponse("Thanks.", completeFacts(), List.of()));
        when(provider.explain(any(), eq(engineResult))).thenReturn(new AdvisorModelProvider.ExplanationResponse(
                "This bundle suits your stated priorities.", List.of(new AdvisorModelProvider.ProductExplanation("P25", "A vehicle tracker helps."),
                        new AdvisorModelProvider.ProductExplanation("P01", "It costs ₹999 per month."))));
        var response = sessions.send(id, "I run a bakery in Jaipur, Rajasthan, 4 employees, 1 location, tier 2, needing reliable internet.");
        assertThat(response.recommendation()).isSameAs(engineResult);
        assertThat(response.productExplanations()).isEmpty();
        assertThat(response.advisorExplanation()).doesNotContain("₹", "999", "P25");
        assertThat(sessions.get(id).advisorExplanation()).isEqualTo(response.advisorExplanation());
    }

    @Test
    void unsafeGeneratedSummaryFailsInsteadOfReturningARecommendationAsAiExplained() {
        String id = sessions.start(null).conversationId();
        var engineResult = new RecommendationResponse("Engine result", List.of(), List.of());
        when(recommendationService.recommend(any())).thenReturn(engineResult);
        when(provider.extract(any(), any(), any())).thenReturn(new AdvisorModelProvider.ExtractionResponse("Thanks.", completeFacts(), List.of()));
        when(provider.explain(any(), eq(engineResult))).thenReturn(new AdvisorModelProvider.ExplanationResponse("Your price is ₹999.", List.of()));
        org.assertj.core.api.Assertions.assertThatThrownBy(() -> sessions.send(id,
                "I run a bakery in Jaipur, Rajasthan, 4 employees, 1 location, tier 2, needing reliable internet."))
                .isInstanceOf(AdvisorProviderException.class).hasMessageContaining("incomplete response");
        assertThat(sessions.get(id).messages()).isEmpty();
    }

    private static List<AdvisorModelProvider.ExtractedFact> completeFacts() {
        return List.of(fact("SEGMENT", "MICRO_RETAIL_AND_SERVICES", "bakery"),
                fact("BUSINESS_TYPE", "Bakery", "bakery"), fact("EMPLOYEE_COUNT", "4", "4 employees"),
                fact("SITE_COUNT", "1", "1 location"), fact("CITY", "Jaipur", "Jaipur"),
                fact("STATE", "Rajasthan", "Rajasthan"), fact("CITY_TIER", "2", "tier 2"),
                fact("NEED", "RELIABLE_INTERNET", "reliable internet"));
    }

    private static AdvisorModelProvider.ExtractedFact fact(String field, String value, String evidence) {
        return new AdvisorModelProvider.ExtractedFact(field, value, evidence);
    }
}
