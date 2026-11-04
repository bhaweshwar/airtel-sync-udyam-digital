package com.udhyam.digital.catalogue.application;

import java.math.BigDecimal;
import java.util.List;

public record BundlePrice(List<PriceLine> lines, BigDecimal monthlyMinimum, BigDecimal monthlyMaximum,
        BigDecimal defaultMonthlyPrice, BigDecimal oneTimeSetupTotal, int minimumContractMonths,
        int typicalInstallationDays, String installationEstimateBasis) {
    public BundlePrice { lines = List.copyOf(lines); }
}
