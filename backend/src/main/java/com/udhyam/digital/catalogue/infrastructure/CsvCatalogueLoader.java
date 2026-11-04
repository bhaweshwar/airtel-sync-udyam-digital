package com.udhyam.digital.catalogue.infrastructure;

import com.udhyam.digital.catalogue.domain.BusinessSegment;
import com.udhyam.digital.catalogue.domain.Product;
import com.udhyam.digital.catalogue.domain.ProductCategory;
import com.udhyam.digital.catalogue.domain.ProductUnit;
import java.io.IOException;
import java.io.Reader;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.regex.Pattern;

/** Loads and validates the complete RFC-4180-style source catalogue. */
public final class CsvCatalogueLoader {
    private static final List<String> REQUIRED_HEADERS = List.of(
            "product_id", "category", "product_name", "description", "unit",
            "price_min_inr_per_month", "price_max_inr_per_month", "one_time_setup_inr",
            "min_contract_months", "available_city_tiers", "min_employees", "min_sites",
            "requires_gstin", "requires_one_of", "typical_install_days", "target_segments");
    private static final Pattern PRODUCT_ID = Pattern.compile("P\\d{2}");

    public ProductCatalogue load(Path path) {
        Path resolved = resolve(path);
        if (!Files.isRegularFile(resolved)) throw new CatalogueLoadException("Catalogue file not found: " + path.toAbsolutePath());
        try (Reader reader = Files.newBufferedReader(resolved, StandardCharsets.UTF_8)) {
            return new ProductCatalogue(loadProducts(reader));
        } catch (IOException e) {
            throw new CatalogueLoadException("Could not read catalogue file " + resolved + ": " + e.getMessage(), e);
        }
    }

    public List<Product> loadProducts(Reader reader) {
        List<CsvRecord> records;
        try {
            records = parseCsv(reader);
        } catch (IOException e) {
            throw new CatalogueLoadException("Could not read catalogue: " + e.getMessage(), e);
        }
        if (records.isEmpty()) throw new CatalogueLoadException("Catalogue is empty; expected header row 1");
        CsvRecord headerRecord = records.get(0);
        List<String> headerValues = headerRecord.values().stream().map(String::trim).toList();
        if (!headerValues.isEmpty() && headerValues.get(0).startsWith("\uFEFF")) {
            List<String> mutable = new ArrayList<>(headerValues);
            mutable.set(0, mutable.get(0).substring(1));
            headerValues = List.copyOf(mutable);
        }
        final List<String> headers = headerValues;
        Set<String> duplicates = new HashSet<>();
        Set<String> seen = new HashSet<>();
        for (String header : headers) if (!seen.add(header)) duplicates.add(header);
        if (!duplicates.isEmpty()) throw error(1, "duplicate headers " + duplicates);
        List<String> missing = REQUIRED_HEADERS.stream().filter(required -> !headers.contains(required)).toList();
        if (!missing.isEmpty()) throw error(1, "missing required headers " + missing);

        Map<String, Integer> positions = new HashMap<>();
        for (int i = 0; i < headers.size(); i++) positions.put(headers.get(i), i);
        List<Product> products = new ArrayList<>();
        Map<String, Integer> productRows = new LinkedHashMap<>();
        Map<String, Integer> sourceRows = new HashMap<>();
        for (int recordIndex = 1; recordIndex < records.size(); recordIndex++) {
            CsvRecord record = records.get(recordIndex);
            if (record.values().stream().allMatch(String::isBlank)) continue;
            if (record.values().size() != headers.size()) {
                throw error(record.line(), "expected " + headers.size() + " columns but found " + record.values().size());
            }
            Map<String, String> row = new HashMap<>();
            for (int i = 0; i < headers.size(); i++) row.put(headers.get(i), record.values().get(i).trim());
            String id = required(row, "product_id", record.line()).toUpperCase();
            if (!PRODUCT_ID.matcher(id).matches()) throw error(record.line(), "invalid product_id '" + id + "' (expected P followed by two digits)");
            if (productRows.putIfAbsent(id, record.line()) != null) {
                throw error(record.line(), "duplicate product_id " + id + " (first seen at row " + productRows.get(id) + ")");
            }
            try {
                BigDecimal minimum = decimal(row, "price_min_inr_per_month", record.line());
                BigDecimal maximum = decimal(row, "price_max_inr_per_month", record.line());
                BigDecimal setup = decimal(row, "one_time_setup_inr", record.line());
                if (minimum.signum() < 0 || maximum.signum() < 0 || setup.signum() < 0) throw error(record.line(), "prices and setup fee must be nonnegative");
                if (minimum.compareTo(maximum) > 0) throw error(record.line(), "monthly minimum exceeds monthly maximum for " + id);
                int contract = integer(row, "min_contract_months", record.line());
                int employees = integer(row, "min_employees", record.line());
                int sites = integer(row, "min_sites", record.line());
                int installDays = integer(row, "typical_install_days", record.line());
                if (contract <= 0) throw error(record.line(), "min_contract_months must be positive");
                if (employees < 0) throw error(record.line(), "min_employees cannot be negative");
                if (sites < 1) throw error(record.line(), "min_sites must be at least 1");
                if (installDays <= 0) throw error(record.line(), "typical_install_days must be positive");
                boolean requiresGstin = switch (required(row, "requires_gstin", record.line()).toUpperCase()) {
                    case "Y" -> true;
                    case "N" -> false;
                    default -> throw error(record.line(), "requires_gstin must be Y or N");
                };
                Product product = new Product(id,
                        ProductCategory.fromCatalogue(required(row, "category", record.line())),
                        required(row, "product_name", record.line()), row.get("description"),
                        ProductUnit.fromCatalogue(required(row, "unit", record.line())), minimum, maximum, setup,
                        contract, integerSet(required(row, "available_city_tiers", record.line()), record.line(), "available_city_tiers", true),
                        employees, sites, requiresGstin,
                        tokenSet(row.get("requires_one_of"), record.line(), "requires_one_of", "|", true),
                        installDays, segmentSet(required(row, "target_segments", record.line()), record.line()));
                products.add(product);
                sourceRows.put(id, record.line());
            } catch (CatalogueLoadException e) {
                throw e;
            } catch (RuntimeException e) {
                throw new CatalogueLoadException("Catalogue row " + record.line() + ": " + e.getMessage(), e);
            }
        }
        if (products.isEmpty()) throw new CatalogueLoadException("Catalogue contains no product rows");
        validateDependencies(products, sourceRows);
        return List.copyOf(products);
    }

    private static void validateDependencies(List<Product> products, Map<String, Integer> rows) {
        Map<String, Product> byId = new HashMap<>();
        products.forEach(product -> byId.put(product.productId(), product));
        for (Product product : products) for (String dependency : product.dependencyAlternatives()) {
            if (!byId.containsKey(dependency)) throw error(rows.get(product.productId()), "unknown dependency " + dependency + " referenced by " + product.productId());
        }
        Set<String> visiting = new HashSet<>();
        Set<String> visited = new HashSet<>();
        for (Product product : products) visit(product.productId(), byId, visiting, visited, rows);
    }

    private static void visit(String id, Map<String, Product> byId, Set<String> visiting, Set<String> visited, Map<String, Integer> rows) {
        if (visited.contains(id)) return;
        if (!visiting.add(id)) throw error(rows.get(id), "dependency cycle detected at " + id);
        for (String dependency : byId.get(id).dependencyAlternatives()) visit(dependency, byId, visiting, visited, rows);
        visiting.remove(id);
        visited.add(id);
    }

    private static String required(Map<String, String> row, String key, int line) {
        String value = row.get(key);
        if (value == null || value.isBlank()) throw error(line, "required value '" + key + "' is blank");
        return value.trim();
    }

    private static BigDecimal decimal(Map<String, String> row, String key, int line) {
        String value = required(row, key, line);
        try { return new BigDecimal(value); }
        catch (NumberFormatException e) { throw error(line, "invalid decimal in " + key + ": '" + value + "'"); }
    }

    private static int integer(Map<String, String> row, String key, int line) {
        String value = required(row, key, line);
        try { return Integer.parseInt(value); }
        catch (NumberFormatException e) { throw error(line, "invalid integer in " + key + ": '" + value + "'"); }
    }

    private static Set<Integer> integerSet(String value, int line, String field, boolean semicolon) {
        String delimiter = semicolon ? ";" : "|";
        Set<Integer> result = new HashSet<>();
        for (String token : value.split(delimiter, -1)) {
            String part = token.trim();
            if (part.isEmpty()) throw error(line, "malformed " + field + ": empty value");
            try {
                int parsed = Integer.parseInt(part);
                if (parsed < 1) throw new NumberFormatException();
                result.add(parsed);
            } catch (NumberFormatException e) { throw error(line, "invalid positive integer '" + part + "' in " + field); }
        }
        return Set.copyOf(result);
    }

    private static Set<String> tokenSet(String value, int line, String field, String delimiter, boolean allowEmpty) {
        if (value == null || value.isBlank()) return allowEmpty ? Set.of() : throwError(line, field + " is required");
        Set<String> result = new HashSet<>();
        for (String token : value.split(Pattern.quote(delimiter), -1)) {
            String part = token.trim().toUpperCase();
            if (part.isEmpty() || !PRODUCT_ID.matcher(part).matches()) throw error(line, "malformed product reference '" + token + "' in " + field);
            if (!result.add(part)) throw error(line, "duplicate product reference " + part + " in " + field);
        }
        return Set.copyOf(result);
    }

    private static <T> T throwError(int line, String message) { throw error(line, message); }

    private static Set<BusinessSegment> segmentSet(String value, int line) {
        Set<BusinessSegment> result = new HashSet<>();
        for (String token : value.split(";", -1)) {
            try {
                if (token.isBlank()) throw new IllegalArgumentException("empty segment");
                if (!result.add(BusinessSegment.fromCatalogue(token))) throw new IllegalArgumentException("duplicate segment " + token);
            } catch (RuntimeException e) { throw error(line, "invalid target_segments: " + e.getMessage()); }
        }
        return Set.copyOf(result);
    }

    private static Path resolve(Path path) {
        if (path.isAbsolute()) return path.normalize();
        Path current = Path.of("").toAbsolutePath().normalize();
        while (current != null) {
            Path candidate = current.resolve(path).normalize();
            if (Files.isRegularFile(candidate)) return candidate;
            current = current.getParent();
        }
        return Path.of("").toAbsolutePath().resolve(path).normalize();
    }

    private static CatalogueLoadException error(int line, String message) {
        return new CatalogueLoadException("Catalogue row " + line + ": " + message);
    }

    /** Minimal RFC-4180 parser retaining the physical line on which each record starts. */
    private static List<CsvRecord> parseCsv(Reader reader) throws IOException {
        List<CsvRecord> records = new ArrayList<>();
        List<String> values = new ArrayList<>();
        StringBuilder field = new StringBuilder();
        boolean quoted = false;
        boolean afterQuote = false;
        int line = 1;
        int recordLine = 1;
        int raw;
        while ((raw = reader.read()) != -1) {
            char c = (char) raw;
            if (quoted) {
                if (c == '"') {
                    reader.mark(1);
                    int next = reader.read();
                    if (next == '"') field.append('"');
                    else { quoted = false; afterQuote = true; if (next != -1) reader.reset(); }
                } else {
                    field.append(c);
                    if (c == '\n') line++;
                }
                continue;
            }
            if (afterQuote && c != ',' && c != '\r' && c != '\n' && !Character.isWhitespace(c)) {
                throw error(line, "unexpected character after closing quote");
            }
            if (c == '"' && field.length() == 0 && !afterQuote) { quoted = true; continue; }
            if (c == ',') {
                values.add(field.toString().trim()); field.setLength(0); afterQuote = false; continue;
            }
            if (c == '\r' || c == '\n') {
                values.add(field.toString().trim()); field.setLength(0); records.add(new CsvRecord(recordLine, List.copyOf(values)));
                values.clear(); afterQuote = false;
                if (c == '\r') { reader.mark(1); int next = reader.read(); if (next != '\n' && next != -1) reader.reset(); }
                line++; recordLine = line; continue;
            }
            if (afterQuote && Character.isWhitespace(c)) continue;
            field.append(c);
        }
        if (quoted) throw error(recordLine, "unterminated quoted field");
        if (field.length() > 0 || !values.isEmpty()) {
            values.add(field.toString().trim()); records.add(new CsvRecord(recordLine, List.copyOf(values)));
        }
        return records;
    }

    private record CsvRecord(int line, List<String> values) { }
}
