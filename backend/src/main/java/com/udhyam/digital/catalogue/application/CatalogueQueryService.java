package com.udhyam.digital.catalogue.application;

import com.udhyam.digital.catalogue.domain.BusinessProfile;
import com.udhyam.digital.catalogue.domain.EligibilityResult;
import com.udhyam.digital.catalogue.infrastructure.ProductCatalogue;
import java.util.List;
import org.springframework.stereotype.Service;

@Service
public class CatalogueQueryService {
    private final ProductCatalogue catalogue;
    private final ProductEligibilityEvaluator evaluator;

    public CatalogueQueryService(ProductCatalogue catalogue, ProductEligibilityEvaluator evaluator) {
        this.catalogue = catalogue;
        this.evaluator = evaluator;
    }

    public List<EligibilityResult> evaluateAll(BusinessProfile profile) {
        return catalogue.all().stream().map(product -> evaluator.evaluate(product, profile)).toList();
    }
}
