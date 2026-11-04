package com.udhyam.digital.catalogue.api;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import java.util.List;

public record BundleRequest(
        @Valid @NotNull BusinessProfileRequest businessProfile,
        @NotEmpty List<@Valid @NotNull ProductSelectionRequest> selections) { }
