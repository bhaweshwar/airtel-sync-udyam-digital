package com.udhyam.digital.catalogue.application;

import com.udhyam.digital.catalogue.domain.BusinessProfile;
import com.udhyam.digital.catalogue.domain.Product;
import com.udhyam.digital.catalogue.domain.ProductSelection;
import com.udhyam.digital.catalogue.infrastructure.ProductCatalogue;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.List;
import org.springframework.stereotype.Service;

@Service
public class PricingService {
    private static final int MONEY_SCALE = 2;
    private static final RoundingMode ROUNDING = RoundingMode.HALF_UP;
    private final ProductCatalogue catalogue;
    private final BundleValidator bundleValidator;

    public PricingService(ProductCatalogue catalogue, BundleValidator bundleValidator) {
        this.catalogue = catalogue;
        this.bundleValidator = bundleValidator;
    }

    public BundlePrice calculate(BusinessProfile profile, List<ProductSelection> selections) {
        BundleValidationResult validation = bundleValidator.validate(profile, selections);
        if (!validation.valid()) throw new BundleValidationException(validation);
        List<PriceLine> lines = selections.stream().map(selection -> line(catalogue.find(selection.productId()).orElseThrow(), selection.quantity())).toList();
        BigDecimal minimum = sum(lines.stream().map(PriceLine::extendedMonthlyMinimum).toList());
        BigDecimal maximum = sum(lines.stream().map(PriceLine::extendedMonthlyMaximum).toList());
        BigDecimal defaultPrice = sum(lines.stream().map(PriceLine::extendedDefaultMonthly).toList());
        BigDecimal setup = sum(lines.stream().map(PriceLine::oneTimeSetupFee).toList());
        int contract = selections.stream().mapToInt(selection -> catalogue.find(selection.productId()).orElseThrow().minimumContractMonths()).max().orElseThrow();
        int installationDays = selections.stream().mapToInt(selection -> catalogue.find(selection.productId()).orElseThrow().typicalInstallDays()).max().orElseThrow();
        return new BundlePrice(lines, minimum, maximum, defaultPrice, setup, contract, installationDays,
                "Maximum selected product duration; catalogue defines no sequential installation dependency.");
    }

    private static PriceLine line(Product product, int quantity) {
        BigDecimal midpoint = product.monthlyMinimum().add(product.monthlyMaximum())
                .divide(BigDecimal.valueOf(2), MONEY_SCALE, ROUNDING);
        return new PriceLine(product.productId(), product.name(), product.unit().catalogueValue(), quantity,
                money(product.monthlyMinimum()), money(product.monthlyMaximum()), money(midpoint),
                money(product.monthlyMinimum().multiply(BigDecimal.valueOf(quantity))),
                money(product.monthlyMaximum().multiply(BigDecimal.valueOf(quantity))),
                money(midpoint.multiply(BigDecimal.valueOf(quantity))),
                money(product.setupFee()), "Once per selected product line; catalogue has no per-unit setup basis.");
    }

    private static BigDecimal sum(List<BigDecimal> values) {
        return money(values.stream().reduce(BigDecimal.ZERO, BigDecimal::add));
    }

    private static BigDecimal money(BigDecimal amount) { return amount.setScale(MONEY_SCALE, ROUNDING); }
}
