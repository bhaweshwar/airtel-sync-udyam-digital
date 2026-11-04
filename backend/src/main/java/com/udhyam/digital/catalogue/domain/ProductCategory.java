package com.udhyam.digital.catalogue.domain;

import java.util.Arrays;

public enum ProductCategory {
    CONNECTIVITY("Connectivity"),
    COMMUNICATION("Communication"),
    CLOUD_AND_PRODUCTIVITY("Cloud & Productivity"),
    SECURITY("Security"),
    IOT_AND_PHYSICAL("IoT & Physical");

    private final String catalogueValue;

    ProductCategory(String catalogueValue) {
        this.catalogueValue = catalogueValue;
    }

    public String catalogueValue() { return catalogueValue; }

    public static ProductCategory fromCatalogue(String value) {
        return Arrays.stream(values()).filter(item -> item.catalogueValue.equalsIgnoreCase(value.trim()))
                .findFirst().orElseThrow(() -> new IllegalArgumentException("Unknown product category: " + value));
    }
}
