package com.udhyam.digital.advisor.api;

import jakarta.validation.constraints.Size;

public record StartConversationRequest(@Size(max = 60) String initialNeed) { }
