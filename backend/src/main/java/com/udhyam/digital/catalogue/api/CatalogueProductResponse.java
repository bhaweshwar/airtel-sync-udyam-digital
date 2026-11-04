package com.udhyam.digital.catalogue.api;

import com.udhyam.digital.catalogue.domain.Product;
import java.math.BigDecimal;
import java.util.Set;

public record CatalogueProductResponse(String productId, String category, String productName, String description,
        String unit, BigDecimal monthlyMinimum, BigDecimal monthlyMaximum, BigDecimal oneTimeSetupFee,
        int minimumContractMonths, Set<Integer> availableCityTiers, int minimumEmployees, int minimumSites,
        boolean requiresGstin, Set<String> dependencyAlternatives, int typicalInstallDays, Set<String> targetSegments) {
    public static CatalogueProductResponse from(Product product) {
        return new CatalogueProductResponse(product.productId(), product.category().catalogueValue(), product.name(),
                product.description(), product.unit().catalogueValue(), product.monthlyMinimum(), product.monthlyMaximum(),
                product.setupFee(), product.minimumContractMonths(), product.availableCityTiers(), product.minimumEmployees(),
                product.minimumSites(), product.requiresGstin(), product.dependencyAlternatives(), product.typicalInstallDays(),
                product.targetSegments().stream().map(segment -> segment.catalogueCode()).collect(java.util.stream.Collectors.toUnmodifiableSet()));
    }
}
