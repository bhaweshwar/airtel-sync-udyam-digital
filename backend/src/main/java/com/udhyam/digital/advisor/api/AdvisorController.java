package com.udhyam.digital.advisor.api;

import com.udhyam.digital.advisor.application.AdvisorSessionService;
import com.udhyam.digital.catalogue.api.RecommendationResponse;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/advisor/conversations")
public class AdvisorController {
    private final AdvisorSessionService sessions;
    public AdvisorController(AdvisorSessionService sessions) { this.sessions = sessions; }

    @PostMapping
    public AdvisorSessionResponse start(@Valid @RequestBody(required = false) StartConversationRequest request) {
        return sessions.start(request == null ? null : request.initialNeed());
    }

    @PostMapping("/{conversationId}/messages")
    public AdvisorSessionResponse send(@PathVariable String conversationId,
            @Valid @RequestBody CustomerMessageRequest request) {
        return sessions.send(conversationId, request.message());
    }

    @GetMapping("/{conversationId}")
    public AdvisorSessionResponse get(@PathVariable String conversationId) { return sessions.get(conversationId); }

    @GetMapping("/{conversationId}/profile")
    public AdvisorProfileResponse profile(@PathVariable String conversationId) {
        var profile = sessions.profile(conversationId);
        return new AdvisorProfileResponse(profile, "CUSTOMER_REPORTED_OR_NOT_PROVIDED", false);
    }

    @GetMapping("/{conversationId}/recommendation")
    public RecommendationResponse recommendation(@PathVariable String conversationId) {
        return sessions.recommendation(conversationId);
    }
}
