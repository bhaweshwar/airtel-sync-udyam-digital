package com.udhyam.digital.catalogue.application;

import static org.assertj.core.api.Assertions.assertThat;

import com.udhyam.digital.catalogue.domain.BusinessProfile;
import com.udhyam.digital.catalogue.domain.BusinessSegment;
import com.udhyam.digital.catalogue.domain.EligibilityReasonCode;
import com.udhyam.digital.catalogue.domain.EligibilityStatus;
import com.udhyam.digital.catalogue.domain.GstinVerificationStatus;
import com.udhyam.digital.catalogue.domain.Product;
import com.udhyam.digital.catalogue.domain.ProductCategory;
import com.udhyam.digital.catalogue.domain.ProductSelection;
import com.udhyam.digital.catalogue.domain.ProductUnit;
import com.udhyam.digital.catalogue.infrastructure.ProductCatalogue;
import java.math.BigDecimal;
import java.util.List;
import java.util.Set;
import org.junit.jupiter.api.Test;

class EligibilityAndBundleTest {
    private final ProductEligibilityEvaluator evaluator = new ProductEligibilityEvaluator();
    private final Product p01 = product("P01", 1, 1, false, Set.of(), Set.of(BusinessSegment.PROFESSIONAL_OFFICES, BusinessSegment.MICRO_RETAIL_AND_SERVICES));
    private final Product p02 = product("P02", 1, 1, false, Set.of(), Set.of(BusinessSegment.PROFESSIONAL_OFFICES, BusinessSegment.SMALL_MULTI_SITE_BUSINESSES));
    private final Product p03 = product("P03", 5, 1, true, Set.of(), Set.of(BusinessSegment.PROFESSIONAL_OFFICES, BusinessSegment.SMALL_MANUFACTURERS));
    private final Product p09 = product("P09", 1, 1, false, Set.of("P01", "P02", "P03"), Set.of(BusinessSegment.PROFESSIONAL_OFFICES));
    private final Product p22 = product("P22", 1, 1, false, Set.of("P01", "P02"), Set.of(BusinessSegment.PROFESSIONAL_OFFICES));
    private final ProductCatalogue catalogue = new ProductCatalogue(List.of(p01, p02, p03, p09, p22));
    private final BundleValidator bundleValidator = new BundleValidator(catalogue, evaluator);

    @Test
    void appliesEligibilityBoundariesAndMultipleReasons() {
        var result = evaluator.evaluate(p03, profile(BusinessSegment.MICRO_RETAIL_AND_SERVICES, 4, 1, 2, GstinVerificationStatus.NOT_PROVIDED));
        assertThat(result.status()).isEqualTo(EligibilityStatus.INELIGIBLE);
        assertThat(result.issues()).extracting(issue -> issue.code()).contains(
                EligibilityReasonCode.CITY_TIER_UNSUPPORTED,
                EligibilityReasonCode.INSUFFICIENT_EMPLOYEES,
                EligibilityReasonCode.GSTIN_REQUIRED,
                EligibilityReasonCode.SEGMENT_NOT_SUPPORTED);
    }

    @Test
    void employeeAndSiteMinimumBoundariesAreInclusive() {
        Product multi = product("P10", 10, 3, true, Set.of(), Set.of(BusinessSegment.SMALL_MULTI_SITE_BUSINESSES));
        var atBoundary = evaluator.evaluate(multi, profile(BusinessSegment.SMALL_MULTI_SITE_BUSINESSES, 10, 3, 1, GstinVerificationStatus.ACTIVE));
        var belowBoundary = evaluator.evaluate(multi, profile(BusinessSegment.SMALL_MULTI_SITE_BUSINESSES, 9, 2, 1, GstinVerificationStatus.ACTIVE));
        assertThat(atBoundary.status()).isEqualTo(EligibilityStatus.ELIGIBLE);
        assertThat(belowBoundary.issues()).extracting(issue -> issue.code()).contains(
                EligibilityReasonCode.INSUFFICIENT_EMPLOYEES, EligibilityReasonCode.INSUFFICIENT_SITES);
    }

    @Test
    void gstinStatusPolicyDistinguishesHardFailureAndManualReview() {
        assertThat(evaluator.evaluate(p03, profile(BusinessSegment.PROFESSIONAL_OFFICES, 5, 1, 1, GstinVerificationStatus.ACTIVE)).status()).isEqualTo(EligibilityStatus.ELIGIBLE);
        assertThat(evaluator.evaluate(p03, profile(BusinessSegment.PROFESSIONAL_OFFICES, 5, 1, 1, GstinVerificationStatus.CANCELLED)).status()).isEqualTo(EligibilityStatus.INELIGIBLE);
        assertThat(evaluator.evaluate(p03, profile(BusinessSegment.PROFESSIONAL_OFFICES, 5, 1, 1, GstinVerificationStatus.SUSPENDED)).status()).isEqualTo(EligibilityStatus.MANUAL_REVIEW);
        assertThat(evaluator.evaluate(p03, profile(BusinessSegment.PROFESSIONAL_OFFICES, 5, 1, 1, GstinVerificationStatus.NOT_FOUND)).status()).isEqualTo(EligibilityStatus.MANUAL_REVIEW);
        assertThat(evaluator.evaluate(p03, profile(BusinessSegment.PROFESSIONAL_OFFICES, 5, 1, 1, GstinVerificationStatus.LOOKUP_FAILED)).status()).isEqualTo(EligibilityStatus.MANUAL_REVIEW);
        assertThat(evaluator.evaluate(p03, profile(BusinessSegment.PROFESSIONAL_OFFICES, 5, 1, 1, GstinVerificationStatus.NOT_PROVIDED)).issues())
                .extracting(issue -> issue.code()).contains(EligibilityReasonCode.GSTIN_REQUIRED);
    }

    @Test
    void requiresOneOfFailsWithoutDependencyAndAcceptsEitherAlternative() {
        var missing = bundleValidator.validate(profile(BusinessSegment.PROFESSIONAL_OFFICES, 5, 1, 1, GstinVerificationStatus.ACTIVE), List.of(new ProductSelection("P09", 1)));
        var firstAlternative = bundleValidator.validate(profile(BusinessSegment.PROFESSIONAL_OFFICES, 5, 1, 1, GstinVerificationStatus.ACTIVE), List.of(new ProductSelection("P09", 1), new ProductSelection("P01", 1)));
        var secondAlternative = bundleValidator.validate(profile(BusinessSegment.PROFESSIONAL_OFFICES, 5, 1, 1, GstinVerificationStatus.ACTIVE), List.of(new ProductSelection("P09", 1), new ProductSelection("P02", 1)));
        assertThat(missing.valid()).isFalse();
        assertThat(missing.products().getFirst().issues()).extracting(issue -> issue.code()).contains(EligibilityReasonCode.DEPENDENCY_NOT_SATISFIED);
        assertThat(firstAlternative.valid()).isTrue();
        assertThat(secondAlternative.valid()).isTrue();
    }

    @Test
    void ineligibleSelectedDependencyCannotSatisfyAnOrRule() {
        var result = bundleValidator.validate(profile(BusinessSegment.PROFESSIONAL_OFFICES, 5, 1, 1, GstinVerificationStatus.CANCELLED),
                List.of(new ProductSelection("P09", 1), new ProductSelection("P03", 1)));
        assertThat(result.valid()).isFalse();
        assertThat(result.products().stream().filter(item -> item.productId().equals("P09")).findFirst().orElseThrow().issues())
                .extracting(issue -> issue.code()).contains(EligibilityReasonCode.DEPENDENCY_NOT_SATISFIED);
    }

    @Test
    void suspendedDependencyRoutesBundleToManualReview() {
        var result = bundleValidator.validate(profile(BusinessSegment.PROFESSIONAL_OFFICES, 5, 1, 1, GstinVerificationStatus.SUSPENDED),
                List.of(new ProductSelection("P09", 1), new ProductSelection("P03", 1)));
        assertThat(result.status()).isEqualTo(EligibilityStatus.MANUAL_REVIEW);
    }

    @Test
    void rejectsDuplicateSelectionsAndNonsensicalProfileValues() {
        org.assertj.core.api.Assertions.assertThatThrownBy(() -> bundleValidator.validate(profile(BusinessSegment.PROFESSIONAL_OFFICES, 2, 1, 1, GstinVerificationStatus.ACTIVE),
                List.of(new ProductSelection("P01", 1), new ProductSelection("p01", 2)))).isInstanceOf(IllegalArgumentException.class);
        org.assertj.core.api.Assertions.assertThatThrownBy(() -> profile(BusinessSegment.PROFESSIONAL_OFFICES, -1, 1, 1, GstinVerificationStatus.ACTIVE))
                .isInstanceOf(IllegalArgumentException.class);
        org.assertj.core.api.Assertions.assertThatThrownBy(() -> profile(BusinessSegment.PROFESSIONAL_OFFICES, 1, 0, 1, GstinVerificationStatus.ACTIVE))
                .isInstanceOf(IllegalArgumentException.class);
    }

    private static BusinessProfile profile(BusinessSegment segment, int employees, int sites, int tier, GstinVerificationStatus gstin) {
        return new BusinessProfile(segment, "Test business", employees, sites, "Pune", tier, "Maharashtra", gstin, Set.of(), "Services");
    }

    private static Product product(String id, int minimumEmployees, int minimumSites, boolean gstin,
            Set<String> dependencies, Set<BusinessSegment> segments) {
        return new Product(id, ProductCategory.CONNECTIVITY, "Product " + id, "Synthetic test product", ProductUnit.PER_SITE,
                new BigDecimal("100.00"), new BigDecimal("200.00"), new BigDecimal("50.00"), 12,
                Set.of(1), minimumEmployees, minimumSites, gstin, dependencies, 5, segments);
    }
}
