package com.udhyam.digital.catalogue.application;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.udhyam.digital.catalogue.domain.BusinessProfile;
import com.udhyam.digital.catalogue.domain.BusinessSegment;
import com.udhyam.digital.catalogue.domain.GstinVerificationStatus;
import com.udhyam.digital.catalogue.domain.ProductSelection;
import com.udhyam.digital.catalogue.infrastructure.CsvCatalogueLoader;
import com.udhyam.digital.catalogue.infrastructure.ProductCatalogue;
import java.math.BigDecimal;
import java.nio.file.Path;
import java.util.List;
import java.util.Set;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

class PricingServiceTest {
    private ProductCatalogue catalogue;
    private PricingService pricingService;

    @BeforeEach
    void setUp() {
        catalogue = new CsvCatalogueLoader().load(Path.of("data/source/dataset/product_catalogue.csv"));
        ProductEligibilityEvaluator evaluator = new ProductEligibilityEvaluator();
        BundleValidator validator = new BundleValidator(catalogue, evaluator);
        pricingService = new PricingService(catalogue, validator);
    }

    @Test
    void calculatesMinimumMaximumAndMidpointPricesWithDecimalPrecision() {
        BundlePrice price = pricingService.calculate(profile(BusinessSegment.PROFESSIONAL_OFFICES, 5, 1), List.of(new ProductSelection("P16", 3)));
        assertThat(price.lines().getFirst().monthlyMinimum()).isEqualByComparingTo("125.00");
        assertThat(price.lines().getFirst().monthlyMaximum()).isEqualByComparingTo("150.00");
        assertThat(price.lines().getFirst().defaultUnitMonthlyPrice()).isEqualByComparingTo("137.50");
        assertThat(price.lines().getFirst().extendedDefaultMonthly()).isEqualByComparingTo("412.50");
        assertThat(price.defaultMonthlyPrice()).isEqualByComparingTo("412.50");
    }

    @Test
    void usesMidpointAndDoesNotMultiplyCatalogueSetupFeeByQuantity() {
        BundlePrice price = pricingService.calculate(profile(BusinessSegment.PROFESSIONAL_OFFICES, 5, 1),
                List.of(new ProductSelection("P01", 2), new ProductSelection("P09", 2)));
        assertThat(price.lines()).hasSize(2);
        assertThat(price.defaultMonthlyPrice()).isEqualByComparingTo("3296.00");
        assertThat(price.oneTimeSetupTotal()).isEqualByComparingTo("1500.00");
        assertThat(price.lines().get(1).oneTimeSetupFee()).isEqualByComparingTo("1500.00");
        assertThat(price.lines().get(1).setupFeeBasis()).contains("Once per selected product line");
    }

    @Test
    void usesLongestContractAndMaximumIndependentInstallationEstimate() {
        BundlePrice price = pricingService.calculate(profile(BusinessSegment.SMALL_MANUFACTURERS, 25, 2),
                List.of(new ProductSelection("P05", 2), new ProductSelection("P24", 4)));
        assertThat(price.minimumContractMonths()).isEqualTo(24);
        assertThat(price.typicalInstallationDays()).isEqualTo(21);
        assertThat(price.oneTimeSetupTotal()).isEqualByComparingTo("13000.00");
        assertThat(price.installationEstimateBasis()).contains("Maximum selected product duration");
    }

    @Test
    void refusesManualReviewAndInvalidSelectionsInsteadOfPricingThem() {
        assertThatThrownBy(() -> pricingService.calculate(profile(BusinessSegment.PROFESSIONAL_OFFICES, 5, 1, GstinVerificationStatus.SUSPENDED),
                List.of(new ProductSelection("P03", 1)))).isInstanceOf(BundleValidationException.class);
        assertThatThrownBy(() -> pricingService.calculate(profile(BusinessSegment.PROFESSIONAL_OFFICES, 5, 1), List.of(new ProductSelection("P99", 1))))
                .isInstanceOf(BundleValidationException.class);
    }

    private static BusinessProfile profile(BusinessSegment segment, int employees, int sites) {
        return profile(segment, employees, sites, GstinVerificationStatus.ACTIVE);
    }

    private static BusinessProfile profile(BusinessSegment segment, int employees, int sites, GstinVerificationStatus gstin) {
        return new BusinessProfile(segment, "Synthetic test business", employees, sites, "Pune", 1, "Maharashtra", gstin, Set.of(), "Test activity");
    }
}
