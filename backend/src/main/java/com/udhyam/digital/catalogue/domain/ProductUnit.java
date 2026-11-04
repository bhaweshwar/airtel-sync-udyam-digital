package com.udhyam.digital.catalogue.domain;

import java.util.Arrays;

public enum ProductUnit {
    PER_SITE("per site"), PER_LINE("per line"), PER_IP("per IP"), PER_CHANNEL("per channel"),
    PER_NUMBER("per number"), PER_PACK("per pack"), PER_ACCOUNT("per account"), PER_USER("per user"),
    PER_COUNTER("per counter"), PER_DEVICE("per device"), PER_CAMERA("per camera"), PER_VEHICLE("per vehicle");

    private final String catalogueValue;
    ProductUnit(String catalogueValue) { this.catalogueValue = catalogueValue; }
    public String catalogueValue() { return catalogueValue; }

    public static ProductUnit fromCatalogue(String value) {
        return Arrays.stream(values()).filter(item -> item.catalogueValue.equalsIgnoreCase(value.trim()))
                .findFirst().orElseThrow(() -> new IllegalArgumentException("Unknown product unit: " + value));
    }
}
