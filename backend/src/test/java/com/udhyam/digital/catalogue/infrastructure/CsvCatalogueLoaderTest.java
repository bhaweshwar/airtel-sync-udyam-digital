package com.udhyam.digital.catalogue.infrastructure;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.io.StringReader;
import java.util.List;
import org.junit.jupiter.api.Test;

class CsvCatalogueLoaderTest {
    private final CsvCatalogueLoader loader = new CsvCatalogueLoader();

    @Test
    void loadsAllTwentyFiveProductsFromActualCatalogue() {
        ProductCatalogue catalogue = loader.load(java.nio.file.Path.of("data/source/dataset/product_catalogue.csv"));
        assertThat(catalogue.size()).isEqualTo(25);
        assertThat(catalogue.find("P09").orElseThrow().dependencyAlternatives()).containsExactlyInAnyOrder("P01", "P02", "P03", "P05", "P06");
        assertThat(catalogue.find("P01").orElseThrow().description()).contains("100 Mbps");
    }

    @Test
    void supportsQuotedCommasAndWhitespace() {
        String csv = header() + "\nP01, Connectivity ,\"Fibre, 100\",\"Reliable, business internet\",per site,1,2,0,12,1;2,1,1,N,,5,micro";
        List<com.udhyam.digital.catalogue.domain.Product> products = loader.loadProducts(new StringReader(csv));
        assertThat(products).hasSize(1);
        assertThat(products.getFirst().name()).isEqualTo("Fibre, 100");
        assertThat(products.getFirst().description()).isEqualTo("Reliable, business internet");
    }

    @Test
    void rejectsMissingRequiredHeadersWithRowNumber() {
        assertThatThrownBy(() -> loader.loadProducts(new StringReader("product_id,product_name\nP01,One")))
                .isInstanceOf(CatalogueLoadException.class).hasMessageContaining("row 1").hasMessageContaining("missing required headers");
    }

    @Test
    void rejectsInvalidPriceRangeWithRowNumber() {
        String csv = header() + "\n" + row("P01", "1200", "1000", "", "");
        assertThatThrownBy(() -> loader.loadProducts(new StringReader(csv)))
                .isInstanceOf(CatalogueLoadException.class).hasMessageContaining("row 2").hasMessageContaining("monthly minimum exceeds");
    }

    @Test
    void rejectsDuplicateProductIds() {
        String csv = header() + "\n" + row("P01", "1", "2", "", "") + "\n" + row("P01", "1", "2", "", "");
        assertThatThrownBy(() -> loader.loadProducts(new StringReader(csv)))
                .isInstanceOf(CatalogueLoadException.class).hasMessageContaining("row 3").hasMessageContaining("duplicate product_id P01");
    }

    @Test
    void rejectsMalformedAndUnknownDependencies() {
        assertThatThrownBy(() -> loader.loadProducts(new StringReader(header() + "\n" + row("P01", "1", "2", "", "P01||P02"))))
                .isInstanceOf(CatalogueLoadException.class).hasMessageContaining("malformed product reference");
        assertThatThrownBy(() -> loader.loadProducts(new StringReader(header() + "\n" + row("P01", "1", "2", "", "P02"))))
                .isInstanceOf(CatalogueLoadException.class).hasMessageContaining("unknown dependency P02");
    }

    @Test
    void rejectsDependencyCycles() {
        String csv = header() + "\n" + row("P01", "1", "2", "", "P02") + "\n" + row("P02", "1", "2", "", "P01");
        assertThatThrownBy(() -> loader.loadProducts(new StringReader(csv)))
                .isInstanceOf(CatalogueLoadException.class).hasMessageContaining("dependency cycle");
    }

    private static String header() {
        return "product_id,category,product_name,description,unit,price_min_inr_per_month,price_max_inr_per_month,one_time_setup_inr,min_contract_months,available_city_tiers,min_employees,min_sites,requires_gstin,requires_one_of,typical_install_days,target_segments";
    }

    private static String row(String id, String minimum, String maximum, String unused, String dependencies) {
        return id + ",Connectivity,Product " + id + ",Synthetic product,per site," + minimum + "," + maximum + ",0,12,1;2,1,1,N," + dependencies + ",5,micro";
    }
}
