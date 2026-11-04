package com.udhyam.digital.catalogue.api;

import com.udhyam.digital.catalogue.domain.ProductSelection;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;

public record ProductSelectionRequest(@NotBlank String productId, @Min(1) int quantity) {
    public ProductSelection toDomain() { return new ProductSelection(productId, quantity); }
}
