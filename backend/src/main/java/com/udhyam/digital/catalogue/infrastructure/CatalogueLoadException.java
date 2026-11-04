package com.udhyam.digital.catalogue.infrastructure;

public class CatalogueLoadException extends RuntimeException {
    public CatalogueLoadException(String message) { super(message); }
    public CatalogueLoadException(String message, Throwable cause) { super(message, cause); }
}
