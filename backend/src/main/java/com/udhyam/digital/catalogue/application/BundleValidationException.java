package com.udhyam.digital.catalogue.application;

public class BundleValidationException extends RuntimeException {
    private final BundleValidationResult result;
    public BundleValidationException(BundleValidationResult result) {
        super("Bundle is not immediately purchasable");
        this.result = result;
    }
    public BundleValidationResult result() { return result; }
}
