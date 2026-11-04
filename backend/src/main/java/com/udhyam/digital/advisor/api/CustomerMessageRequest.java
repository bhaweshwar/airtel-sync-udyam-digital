package com.udhyam.digital.advisor.api;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public record CustomerMessageRequest(@NotBlank @Size(max = 2000) String message) { }
