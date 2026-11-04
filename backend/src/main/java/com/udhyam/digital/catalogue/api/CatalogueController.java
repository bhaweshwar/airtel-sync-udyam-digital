package com.udhyam.digital.catalogue.api;

import com.udhyam.digital.catalogue.application.BundlePrice;
import com.udhyam.digital.catalogue.application.BundleValidationResult;
import com.udhyam.digital.catalogue.application.BundleValidator;
import com.udhyam.digital.catalogue.application.CatalogueQueryService;
import com.udhyam.digital.catalogue.application.PricingService;
import com.udhyam.digital.catalogue.domain.Product;
import com.udhyam.digital.catalogue.domain.ProductSelection;
import com.udhyam.digital.catalogue.infrastructure.ProductCatalogue;
import jakarta.validation.Valid;
import java.util.List;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

@RestController
@RequestMapping("/api/v1/catalogue")
public class CatalogueController {
    private final ProductCatalogue catalogue;
    private final CatalogueQueryService queryService;
    private final BundleValidator bundleValidator;
    private final PricingService pricingService;

    public CatalogueController(ProductCatalogue catalogue, CatalogueQueryService queryService,
            BundleValidator bundleValidator, PricingService pricingService) {
        this.catalogue = catalogue;
        this.queryService = queryService;
        this.bundleValidator = bundleValidator;
        this.pricingService = pricingService;
    }

    @GetMapping("/products")
    public List<CatalogueProductResponse> products() {
        return catalogue.all().stream().map(CatalogueProductResponse::from).toList();
    }

    @GetMapping("/products/{productId}")
    public CatalogueProductResponse product(@PathVariable String productId) {
        Product product = catalogue.find(productId).orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Product not found"));
        return CatalogueProductResponse.from(product);
    }

    @PostMapping("/eligibility/evaluate")
    public List<EligibilityResponse> evaluate(@Valid @RequestBody EligibilityEvaluationRequest request) {
        return queryService.evaluateAll(request.businessProfile().toDomain()).stream().map(EligibilityResponse::from).toList();
    }

    @PostMapping("/bundles/validate")
    public BundleValidationResponse validateBundle(@Valid @RequestBody BundleRequest request) {
        BundleValidationResult result = bundleValidator.validate(request.businessProfile().toDomain(), selections(request));
        return BundleValidationResponse.from(result);
    }

    @PostMapping("/pricing/calculate")
    public BundlePrice price(@Valid @RequestBody BundleRequest request) {
        return pricingService.calculate(request.businessProfile().toDomain(), selections(request));
    }

    private static List<ProductSelection> selections(BundleRequest request) {
        return request.selections().stream().map(ProductSelectionRequest::toDomain).toList();
    }
}
