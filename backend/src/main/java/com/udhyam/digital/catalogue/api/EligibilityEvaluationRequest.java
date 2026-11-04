package com.udhyam.digital.catalogue.api;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;

public record EligibilityEvaluationRequest(@Valid @NotNull BusinessProfileRequest businessProfile) { }
