package com.udhyam.digital.catalogue.domain;

import java.util.Arrays;

public enum BusinessSegment {
    MICRO_RETAIL_AND_SERVICES("micro"),
    PROFESSIONAL_OFFICES("prof"),
    SMALL_MULTI_SITE_BUSINESSES("multi"),
    SMALL_MANUFACTURERS("mfg");

    private final String catalogueCode;
    BusinessSegment(String catalogueCode) { this.catalogueCode = catalogueCode; }
    public String catalogueCode() { return catalogueCode; }

    public static BusinessSegment fromCatalogue(String code) {
        return Arrays.stream(values()).filter(value -> value.catalogueCode.equalsIgnoreCase(code.trim()))
                .findFirst().orElseThrow(() -> new IllegalArgumentException("Unknown target segment: " + code));
    }
}
