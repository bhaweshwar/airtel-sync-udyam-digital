package com.udhyam.digital.catalogue.application;

import java.math.BigDecimal;

public record PriceLine(String productId, String productName, String unit, int quantity,
        BigDecimal monthlyMinimum, BigDecimal monthlyMaximum, BigDecimal defaultUnitMonthlyPrice,
        BigDecimal extendedMonthlyMinimum, BigDecimal extendedMonthlyMaximum,
        BigDecimal extendedDefaultMonthly, BigDecimal oneTimeSetupFee,
        String setupFeeBasis) { }
