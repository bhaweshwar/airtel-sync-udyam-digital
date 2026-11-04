package com.udhyam.digital.advisor.domain;

import com.udhyam.digital.catalogue.api.RecommendationResponse;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.locks.ReentrantLock;

/** Ephemeral, process-local prototype session. Each session serializes turn updates with its lock. */
public final class AdvisorConversation {
    private final String id = UUID.randomUUID().toString();
    private final ReentrantLock lock = new ReentrantLock();
    private final List<AdvisorMessage> messages = new ArrayList<>();
    private AdvisorProfile profile = AdvisorProfile.empty();
    private List<String> followUpQuestions = List.of();
    private RecommendationResponse recommendation;
    private String advisorExplanation;
    private Map<String, String> productExplanations = Map.of();
    private Instant lastAccess = Instant.now();

    public String id() { return id; }
    public ReentrantLock lock() { return lock; }
    public List<AdvisorMessage> messages() { return List.copyOf(messages); }
    public AdvisorProfile profile() { return profile; }
    public List<String> followUpQuestions() { return followUpQuestions; }
    public RecommendationResponse recommendation() { return recommendation; }
    public String advisorExplanation() { return advisorExplanation; }
    public Map<String, String> productExplanations() { return productExplanations; }
    public Instant lastAccess() { return lastAccess; }
    public void update(AdvisorProfile next, List<AdvisorMessage> nextMessages, List<String> questions,
            RecommendationResponse result, String explanation, Map<String, String> productReasons) {
        profile = next;
        messages.clear();
        messages.addAll(nextMessages);
        followUpQuestions = List.copyOf(questions);
        recommendation = result;
        advisorExplanation = explanation;
        productExplanations = Map.copyOf(productReasons);
        lastAccess = Instant.now();
    }
    public void touch() { lastAccess = Instant.now(); }
}
