package com.udhyam.digital.catalogue.infrastructure;

import com.udhyam.digital.catalogue.domain.Product;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.function.Function;
import java.util.stream.Collectors;

public final class ProductCatalogue {
    private final Map<String, Product> products;

    public ProductCatalogue(List<Product> products) {
        this.products = products.stream().collect(Collectors.toUnmodifiableMap(Product::productId, Function.identity()));
        if (this.products.isEmpty()) throw new IllegalArgumentException("Catalogue must contain at least one product");
    }

    public List<Product> all() { return products.values().stream().sorted((a, b) -> a.productId().compareTo(b.productId())).toList(); }
    public Optional<Product> find(String productId) { return Optional.ofNullable(products.get(productId.toUpperCase())); }
    public boolean contains(String productId) { return products.containsKey(productId.toUpperCase()); }
    public int size() { return products.size(); }
}
