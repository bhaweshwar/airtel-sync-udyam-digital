package com.udhyam.digital.catalogue.config;

import com.udhyam.digital.catalogue.infrastructure.CsvCatalogueLoader;
import com.udhyam.digital.catalogue.infrastructure.ProductCatalogue;
import java.nio.file.Path;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class CatalogueConfiguration {
    @Bean
    ProductCatalogue productCatalogue(@Value("${app.catalogue.path:data/source/dataset/product_catalogue.csv}") String cataloguePath) {
        return new CsvCatalogueLoader().load(Path.of(cataloguePath));
    }
}
