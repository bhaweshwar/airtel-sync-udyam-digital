package com.udhyam.digital.catalogue;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;
import static org.assertj.core.api.Assertions.assertThat;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.udhyam.digital.catalogue.application.RecommendationService;
import com.udhyam.digital.catalogue.api.RecommendationResponse;
import com.udhyam.digital.catalogue.domain.BusinessNeed;
import com.udhyam.digital.catalogue.domain.BusinessProfile;
import com.udhyam.digital.catalogue.domain.BusinessSegment;
import com.udhyam.digital.catalogue.domain.GstinVerificationStatus;
import com.udhyam.digital.catalogue.infrastructure.ProductCatalogue;
import java.util.List;
import java.util.Set;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

@SpringBootTest
@AutoConfigureMockMvc
class RecommendationAndApiIntegrationTest {
    @Autowired private ProductCatalogue catalogue;
    @Autowired private RecommendationService recommendationService;
    @Autowired private MockMvc mockMvc;
    @Autowired private ObjectMapper objectMapper;

    @Test
    void loadsAndExposesAllTwentyFiveLocalCatalogueProducts() throws Exception {
        assertThat(catalogue.size()).isEqualTo(25);
        mockMvc.perform(get("/api/v1/catalogue/products"))
                .andExpect(status().isOk()).andExpect(jsonPath("$.length()").value(25))
                .andExpect(jsonPath("$[0].productId").value("P01"));
    }

    @Test
    void returnsSegmentSpecificValidDeterministicBundles() {
        List<BusinessProfile> profiles = List.of(
                profile(BusinessSegment.MICRO_RETAIL_AND_SERVICES, 3, 1, 2, GstinVerificationStatus.ACTIVE, Set.of(BusinessNeed.POS_BILLING)),
                profile(BusinessSegment.PROFESSIONAL_OFFICES, 5, 1, 1, GstinVerificationStatus.ACTIVE, Set.of(BusinessNeed.CLOUD_PRODUCTIVITY)),
                profile(BusinessSegment.SMALL_MULTI_SITE_BUSINESSES, 12, 3, 1, GstinVerificationStatus.ACTIVE, Set.of(BusinessNeed.MULTI_SITE_MANAGEMENT)),
                profile(BusinessSegment.SMALL_MANUFACTURERS, 25, 2, 1, GstinVerificationStatus.ACTIVE, Set.of(BusinessNeed.MACHINE_MONITORING, BusinessNeed.FLEET_TRACKING)));
        for (BusinessProfile profile : profiles) {
            RecommendationResponse first = recommendationService.recommend(profile);
            RecommendationResponse second = recommendationService.recommend(profile);
            assertThat(first.recommendations()).isNotEmpty();
            assertThat(first).isEqualTo(second);
            assertThat(first.recommendations()).allSatisfy(bundle -> {
                assertThat(bundle.eligibility().valid()).isTrue();
                assertThat(bundle.selections()).isNotEmpty();
            });
        }
        assertThat(recommendationService.recommend(profiles.get(2)).recommendations().getFirst().selections())
                .extracting(selection -> selection.productId()).contains("P02", "P09", "P10");
    }

    @Test
    void returnsClearEmptyRecommendationWhenNothingIsEligible() {
        var result = recommendationService.recommend(profile(BusinessSegment.MICRO_RETAIL_AND_SERVICES, 1, 1, 99,
                GstinVerificationStatus.NOT_PROVIDED, Set.of()));
        assertThat(result.recommendations()).isEmpty();
        assertThat(result.excludedProducts()).hasSize(25);
        assertThat(result.summary()).contains("No immediately purchasable");
    }

    @Test
    void recommendationEndpointAcceptsProfileAndReturnsProductsAndPricing() throws Exception {
        mockMvc.perform(post("/api/v1/recommendations").contentType(MediaType.APPLICATION_JSON).content(profileJson("PROFESSIONAL_OFFICES", "ACTIVE")))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.recommendations[0].selections[0].productId").value("P02"))
                .andExpect(jsonPath("$.recommendations[0].pricing.defaultMonthlyPrice").exists());
    }

    @Test
    void catalogueAndEligibilityEndpointsReturnDtosAndNotFoundErrors() throws Exception {
        mockMvc.perform(get("/api/v1/catalogue/products/P09"))
                .andExpect(status().isOk()).andExpect(jsonPath("$.dependencyAlternatives").isArray());
        mockMvc.perform(get("/api/v1/catalogue/products/P99"))
                .andExpect(status().isNotFound()).andExpect(jsonPath("$.code").value("NOT_FOUND"));
        mockMvc.perform(post("/api/v1/catalogue/eligibility/evaluate").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"businessProfile\":" + profileJson("MICRO_RETAIL_AND_SERVICES", "NOT_PROVIDED") + "}"))
                .andExpect(status().isOk()).andExpect(jsonPath("$.length()").value(25));
    }

    @Test
    void validatesBundleDependenciesAndBlocksPricingForInvalidBundle() throws Exception {
        String request = bundleJson("PROFESSIONAL_OFFICES", "ACTIVE", "P09", 1);
        mockMvc.perform(post("/api/v1/catalogue/bundles/validate").contentType(MediaType.APPLICATION_JSON).content(request))
                .andExpect(status().isOk()).andExpect(jsonPath("$.valid").value(false))
                .andExpect(jsonPath("$.products[0].issues[0].code").value("DEPENDENCY_NOT_SATISFIED"));
        mockMvc.perform(post("/api/v1/catalogue/pricing/calculate").contentType(MediaType.APPLICATION_JSON).content(request))
                .andExpect(status().isUnprocessableEntity()).andExpect(jsonPath("$.code").value("BUNDLE_NOT_PURCHASABLE"));
    }

    @Test
    void pricingEndpointIgnoresClientPriceAndUsesCatalogueMidpoint() throws Exception {
        String request = "{\"businessProfile\":" + profileJson("PROFESSIONAL_OFFICES", "ACTIVE")
                + ",\"selections\":[{\"productId\":\"P01\",\"quantity\":2,\"unitPrice\":0}]}";
        mockMvc.perform(post("/api/v1/catalogue/pricing/calculate").contentType(MediaType.APPLICATION_JSON).content(request))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.defaultMonthlyPrice").value(2198.0))
                .andExpect(jsonPath("$.oneTimeSetupTotal").value(0.0));
    }

    @Test
    void validatesNonsensicalRequestFields() throws Exception {
        String request = profileJson("PROFESSIONAL_OFFICES", "ACTIVE").replace("\"siteCount\":1", "\"siteCount\":0");
        mockMvc.perform(post("/api/v1/recommendations").contentType(MediaType.APPLICATION_JSON).content(request))
                .andExpect(status().isBadRequest()).andExpect(jsonPath("$.code").value("INVALID_REQUEST"));
    }

    private String profileJson(String segment, String gstinStatus) throws Exception {
        return objectMapper.writeValueAsString(new ProfileBody(segment, "Synthetic business", 10, 1, "Pune", 1,
                "Maharashtra", gstinStatus, List.of(), "Services"));
    }

    private String bundleJson(String segment, String gstinStatus, String productId, int quantity) throws Exception {
        return "{\"businessProfile\":" + profileJson(segment, gstinStatus) + ",\"selections\":[{\"productId\":\"" + productId + "\",\"quantity\":" + quantity + "}]}";
    }

    private static BusinessProfile profile(BusinessSegment segment, int employees, int sites, int tier,
            GstinVerificationStatus status, Set<BusinessNeed> needs) {
        return new BusinessProfile(segment, "Synthetic test business", employees, sites, "Pune", tier, "Maharashtra", status, needs, "Test activity");
    }

    private record ProfileBody(String segment, String businessType, int employeeCount, int siteCount, String city,
            int cityTier, String state, String gstinStatus, List<String> currentRequirements, String industryActivity) { }
}
