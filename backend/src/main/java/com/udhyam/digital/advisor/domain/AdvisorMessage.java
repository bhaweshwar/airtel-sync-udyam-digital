package com.udhyam.digital.advisor.domain;

import java.time.Instant;

public record AdvisorMessage(String role, String content, Instant createdAt) { }
