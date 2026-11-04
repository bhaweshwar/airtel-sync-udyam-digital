package com.udhyam.digital.catalogue.application;

import com.udhyam.digital.catalogue.api.BundleValidationResponse;
import com.udhyam.digital.catalogue.api.EligibilityResponse;
import com.udhyam.digital.catalogue.api.RecommendationResponse;
import com.udhyam.digital.catalogue.domain.BusinessNeed;
import com.udhyam.digital.catalogue.domain.BusinessProfile;
import com.udhyam.digital.catalogue.domain.BusinessSegment;
import com.udhyam.digital.catalogue.domain.EligibilityResult;
import com.udhyam.digital.catalogue.domain.EligibilityStatus;
import com.udhyam.digital.catalogue.domain.Product;
import com.udhyam.digital.catalogue.domain.ProductCategory;
import com.udhyam.digital.catalogue.domain.ProductSelection;
import com.udhyam.digital.catalogue.domain.ProductUnit;
import com.udhyam.digital.catalogue.infrastructure.ProductCatalogue;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import org.springframework.stereotype.Service;

@Service
public class RecommendationService {
    private final ProductCatalogue catalogue;
    private final ProductEligibilityEvaluator evaluator;
    private final BundleValidator bundleValidator;
    private final PricingService pricingService;

    public RecommendationService(ProductCatalogue catalogue, ProductEligibilityEvaluator evaluator,
            BundleValidator bundleValidator, PricingService pricingService) {
        this.catalogue = catalogue;
        this.evaluator = evaluator;
        this.bundleValidator = bundleValidator;
        this.pricingService = pricingService;
    }

    public RecommendationResponse recommend(BusinessProfile profile) {
        List<Product> all = catalogue.all();
        Map<String, EligibilityResult> evaluations = new LinkedHashMap<>();
        all.forEach(product -> evaluations.put(product.productId(), evaluator.evaluate(product, profile)));
        LinkedHashMap<String, ProductSelection> selections = new LinkedHashMap<>();
        List<String> explanations = new ArrayList<>();

        pickCoreConnectivity(profile.segment(), evaluations).ifPresent(product -> {
            add(product, profile, selections);
            explanations.add(product.name() + " is the primary connectivity option listed for this business segment and city tier.");
        });

        switch (profile.segment()) {
            case MICRO_RETAIL_AND_SERVICES -> addRecommended("P19", "Cloud POS & Billing supports counter billing and inventory for a retail/service business.", profile, evaluations, selections, explanations);
            case PROFESSIONAL_OFFICES -> addRecommended("P16", "Cloud Email & Office Suite supports business email and document collaboration.", profile, evaluations, selections, explanations);
            case SMALL_MULTI_SITE_BUSINESSES -> {
                addRecommended("P09", "Backup Failover adds a secondary link where an eligible primary connection is selected.", profile, evaluations, selections, explanations);
                addRecommended("P10", "Managed SD-WAN supports centralized management for eligible multi-site businesses.", profile, evaluations, selections, explanations);
            }
            case SMALL_MANUFACTURERS -> addRecommended("P24", "Machine Monitoring IoT aligns with the manufacturing activity segment.", profile, evaluations, selections, explanations);
        }

        for (BusinessNeed need : profile.currentRequirements().stream().sorted().toList()) {
            switch (need) {
                case RELIABLE_INTERNET -> { /* Primary connectivity is already selected above. */ }
                case BUSINESS_MOBILITY -> addRecommended("P07", "Business Postpaid provides business mobile lines.", profile, evaluations, selections, explanations);
                case CUSTOMER_MESSAGING -> addFirstEligible(List.of("P15", "P14"), "Customer messaging requirement is matched by the first eligible catalogue messaging product.", profile, evaluations, selections, explanations);
                case CLOUD_PRODUCTIVITY -> addFirstEligible(List.of("P16", "P17", "P18"), "Cloud productivity requirement is matched by the first eligible catalogue product.", profile, evaluations, selections, explanations);
                case SECURITY -> {
                    addRecommended("P20", "Endpoint Security addresses device protection.", profile, evaluations, selections, explanations);
                    addRecommended("P22", "Secure Wi-Fi adds a guest network where an eligible internet dependency is in this bundle.", profile, evaluations, selections, explanations);
                }
                case POS_BILLING -> addRecommended("P19", "Cloud POS & Billing addresses the requested counter billing need.", profile, evaluations, selections, explanations);
                case CCTV -> addRecommended("P23", "Cloud CCTV addresses the requested camera monitoring need when a qualifying connection is selected.", profile, evaluations, selections, explanations);
                case MULTI_SITE_MANAGEMENT -> {
                    addRecommended("P10", "Managed SD-WAN addresses central management for eligible multi-site businesses.", profile, evaluations, selections, explanations);
                    addRecommended("P09", "Backup Failover addresses continuity for an eligible primary connection.", profile, evaluations, selections, explanations);
                }
                case MACHINE_MONITORING -> addRecommended("P24", "Machine Monitoring IoT addresses machine uptime and energy monitoring.", profile, evaluations, selections, explanations);
                case FLEET_TRACKING -> addRecommended("P25", "Fleet Tracker addresses vehicle location monitoring.", profile, evaluations, selections, explanations);
            }
        }

        List<RecommendationResponse.BundleRecommendation> recommendations = new ArrayList<>();
        if (!selections.isEmpty()) {
            List<ProductSelection> chosen = List.copyOf(selections.values());
            BundleValidationResult validation = bundleValidator.validate(profile, chosen);
            if (validation.valid()) {
                String bundleName = profile.segment().name().replace('_', ' ') + " digital essentials";
                recommendations.add(new RecommendationResponse.BundleRecommendation(bundleName, chosen,
                        BundleValidationResponse.from(validation), pricingService.calculate(profile, chosen), explanations));
            }
        }
        List<EligibilityResponse> exclusions = all.stream().map(product -> evaluations.get(product.productId()))
                .filter(result -> result.status() != EligibilityStatus.ELIGIBLE).map(EligibilityResponse::from).toList();
        String summary = recommendations.isEmpty()
                ? "No immediately purchasable catalogue bundle matches this profile. Review excluded products and requirements."
                : "A deterministic bundle was assembled from eligible catalogue products; all prices and rules were evaluated by the server.";
        return new RecommendationResponse(summary, recommendations, exclusions);
    }

    private Optional<Product> pickCoreConnectivity(BusinessSegment segment, Map<String, EligibilityResult> evaluations) {
        List<String> preferred = switch (segment) {
            case MICRO_RETAIL_AND_SERVICES -> List.of("P01", "P04", "P07");
            case PROFESSIONAL_OFFICES -> List.of("P02", "P01", "P04", "P07");
            case SMALL_MULTI_SITE_BUSINESSES -> List.of("P02", "P01", "P07");
            case SMALL_MANUFACTURERS -> List.of("P05", "P03", "P06", "P07");
        };
        return preferred.stream().map(catalogue::find).flatMap(Optional::stream)
                .filter(product -> product.category() == ProductCategory.CONNECTIVITY)
                .filter(product -> evaluations.get(product.productId()).status() == EligibilityStatus.ELIGIBLE)
                .findFirst();
    }

    private void addFirstEligible(List<String> ids, String reason, BusinessProfile profile,
            Map<String, EligibilityResult> evaluations, Map<String, ProductSelection> selections, List<String> explanations) {
        ids.stream().map(catalogue::find).flatMap(Optional::stream)
                .filter(product -> evaluations.get(product.productId()).status() == EligibilityStatus.ELIGIBLE)
                .filter(product -> dependenciesCurrentlySatisfied(product, selections))
                .findFirst().ifPresent(product -> addWithReason(product, reason, profile, selections, explanations));
    }

    private void addRecommended(String id, String reason, BusinessProfile profile,
            Map<String, EligibilityResult> evaluations, Map<String, ProductSelection> selections, List<String> explanations) {
        catalogue.find(id).filter(product -> evaluations.get(id).status() == EligibilityStatus.ELIGIBLE)
                .filter(product -> dependenciesCurrentlySatisfied(product, selections))
                .ifPresent(product -> addWithReason(product, reason, profile, selections, explanations));
    }

    private void addWithReason(Product product, String reason, BusinessProfile profile,
            Map<String, ProductSelection> selections, List<String> explanations) {
        add(product, profile, selections);
        explanations.add(reason);
    }

    private static void add(Product product, BusinessProfile profile, Map<String, ProductSelection> selections) {
        int quantity = product.unit() == ProductUnit.PER_SITE ? profile.siteCount() : 1;
        selections.putIfAbsent(product.productId(), new ProductSelection(product.productId(), quantity));
    }

    private static boolean dependenciesCurrentlySatisfied(Product product, Map<String, ProductSelection> selections) {
        return product.dependencyAlternatives().isEmpty() || product.dependencyAlternatives().stream().anyMatch(selections::containsKey);
    }
}
