package com.udhyam.digital.catalogue.domain;

import java.math.BigDecimal;
import java.util.Set;

public record Product(
        String productId,
        ProductCategory category,
        String name,
        String description,
        ProductUnit unit,
        BigDecimal monthlyMinimum,
        BigDecimal monthlyMaximum,
        BigDecimal setupFee,
        int minimumContractMonths,
        Set<Integer> availableCityTiers,
        int minimumEmployees,
        int minimumSites,
        boolean requiresGstin,
        Set<String> dependencyAlternatives,
        int typicalInstallDays,
        Set<BusinessSegment> targetSegments) {

    public Product {
        productId = required(productId, "productId").toUpperCase();
        category = required(category, "category");
        name = required(name, "name");
        description = description == null ? "" : description.trim();
        unit = required(unit, "unit");
        monthlyMinimum = required(monthlyMinimum, "monthlyMinimum");
        monthlyMaximum = required(monthlyMaximum, "monthlyMaximum");
        setupFee = required(setupFee, "setupFee");
        availableCityTiers = Set.copyOf(availableCityTiers);
        dependencyAlternatives = Set.copyOf(dependencyAlternatives);
        targetSegments = Set.copyOf(targetSegments);
    }

    private static String required(String value, String name) {
        if (value == null || value.isBlank()) throw new IllegalArgumentException(name + " is required");
        return value.trim();
    }

    private static <T> T required(T value, String name) {
        if (value == null) throw new IllegalArgumentException(name + " is required");
        return value;
    }
}
