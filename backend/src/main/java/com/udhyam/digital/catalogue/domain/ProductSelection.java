package com.udhyam.digital.catalogue.domain;

public record ProductSelection(String productId, int quantity) {
    public ProductSelection {
        if (productId == null || productId.isBlank()) throw new IllegalArgumentException("productId is required");
        productId = productId.trim().toUpperCase();
        if (quantity < 1) throw new IllegalArgumentException("quantity must be at least 1");
    }
}
