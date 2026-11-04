package com.udhyam.digital.catalogue.application;

import com.udhyam.digital.catalogue.domain.BusinessProfile;
import com.udhyam.digital.catalogue.domain.EligibilityIssue;
import com.udhyam.digital.catalogue.domain.EligibilityReasonCode;
import com.udhyam.digital.catalogue.domain.EligibilityResult;
import com.udhyam.digital.catalogue.domain.EligibilityStatus;
import com.udhyam.digital.catalogue.domain.Product;
import com.udhyam.digital.catalogue.domain.ProductSelection;
import com.udhyam.digital.catalogue.infrastructure.ProductCatalogue;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import org.springframework.stereotype.Service;

@Service
public class BundleValidator {
    private final ProductCatalogue catalogue;
    private final ProductEligibilityEvaluator evaluator;

    public BundleValidator(ProductCatalogue catalogue, ProductEligibilityEvaluator evaluator) {
        this.catalogue = catalogue;
        this.evaluator = evaluator;
    }

    public BundleValidationResult validate(BusinessProfile profile, List<ProductSelection> selections) {
        if (selections == null || selections.isEmpty()) throw new IllegalArgumentException("At least one product selection is required");
        Set<String> selectedIds = new HashSet<>();
        for (ProductSelection selection : selections) {
            if (!selectedIds.add(selection.productId())) throw new IllegalArgumentException("Duplicate product selection: " + selection.productId());
        }
        Map<String, EligibilityResult> base = new HashMap<>();
        for (String id : selectedIds) {
            Product product = catalogue.find(id).orElse(null);
            base.put(id, product == null
                    ? new EligibilityResult(id, EligibilityStatus.INELIGIBLE, List.of(new EligibilityIssue(
                            EligibilityReasonCode.UNKNOWN_PRODUCT, "Product does not exist in the catalogue.", "A known product ID")))
                    : evaluator.evaluate(product, profile));
        }
        Map<String, EligibilityResult> resolved = new HashMap<>();
        for (String id : selectedIds) resolve(id, selectedIds, base, resolved, new HashSet<>());
        List<EligibilityResult> products = selections.stream().map(selection -> resolved.get(selection.productId())).toList();
        EligibilityStatus status = products.stream().anyMatch(item -> item.status() == EligibilityStatus.INELIGIBLE)
                ? EligibilityStatus.INELIGIBLE
                : products.stream().anyMatch(item -> item.status() == EligibilityStatus.MANUAL_REVIEW)
                    ? EligibilityStatus.MANUAL_REVIEW : EligibilityStatus.ELIGIBLE;
        return new BundleValidationResult(status, products);
    }

    private EligibilityResult resolve(String id, Set<String> selectedIds,
            Map<String, EligibilityResult> base, Map<String, EligibilityResult> cache, Set<String> visiting) {
        if (cache.containsKey(id)) return cache.get(id);
        if (!visiting.add(id)) throw new IllegalStateException("Dependency cycle encountered at " + id);
        EligibilityResult current = base.get(id);
        Product product = catalogue.find(id).orElse(null);
        if (product == null || current.status() != EligibilityStatus.ELIGIBLE || product.dependencyAlternatives().isEmpty()) {
            visiting.remove(id);
            cache.put(id, current);
            return current;
        }
        List<EligibilityResult> chosenAlternatives = product.dependencyAlternatives().stream()
                .filter(selectedIds::contains)
                .map(dependency -> resolve(dependency, selectedIds, base, cache, visiting)).toList();
        if (chosenAlternatives.stream().anyMatch(result -> result.status() == EligibilityStatus.ELIGIBLE)) {
            visiting.remove(id);
            cache.put(id, current);
            return current;
        }
        boolean manualDependency = chosenAlternatives.stream().anyMatch(result -> result.status() == EligibilityStatus.MANUAL_REVIEW);
        List<EligibilityIssue> issues = new ArrayList<>(current.issues());
        issues.add(new EligibilityIssue(manualDependency ? EligibilityReasonCode.DEPENDENCY_INELIGIBLE : EligibilityReasonCode.DEPENDENCY_NOT_SATISFIED,
                manualDependency ? "Selected dependency requires manual review." : "Select at least one eligible required product in this bundle.",
                "One eligible product from: " + product.dependencyAlternatives()));
        EligibilityStatus status = manualDependency ? EligibilityStatus.MANUAL_REVIEW : EligibilityStatus.INELIGIBLE;
        EligibilityResult result = new EligibilityResult(id, status, issues);
        visiting.remove(id);
        cache.put(id, result);
        return result;
    }
}
