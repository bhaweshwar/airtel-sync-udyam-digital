package com.udhyam.digital.advisor.application;

import com.udhyam.digital.advisor.api.AdvisorSessionResponse;
import com.udhyam.digital.advisor.domain.AdvisorConversation;
import com.udhyam.digital.advisor.domain.AdvisorMessage;
import com.udhyam.digital.advisor.domain.AdvisorProfile;
import com.udhyam.digital.catalogue.api.RecommendationResponse;
import com.udhyam.digital.catalogue.application.RecommendationService;
import com.udhyam.digital.catalogue.domain.BusinessNeed;
import com.udhyam.digital.catalogue.domain.BusinessSegment;
import com.udhyam.digital.catalogue.domain.GstinVerificationStatus;
import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.regex.Pattern;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

@Service
public class AdvisorSessionService {
    private static final Duration SESSION_TTL = Duration.ofHours(2);
    private static final int MAX_SESSIONS = 5000;
    private static final int MAX_MESSAGES = 24;
    private static final Pattern CORRECTION = Pattern.compile("(?i)\\b(actually|correction|i meant|change|update|instead|not \\w+[, ]+but|that's wrong|that is wrong)\\b");
    private static final List<String> FOLLOWUP_ORDER = List.of("BUSINESS_TYPE", "EMPLOYEE_COUNT", "SITE_COUNT", "LOCATION", "BUSINESS_NEEDS");
    private static final Map<String, String> QUESTIONS = Map.of(
            "BUSINESS_TYPE", "What kind of business do you run?",
            "EMPLOYEE_COUNT", "How many people work in the business?",
            "SITE_COUNT", "How many business locations should we consider?",
            "LOCATION", "Which city and state is the business based in, and do you know its city tier (1, 2 or 3)?",
            "BUSINESS_NEEDS", "What would you like help with, such as internet, business mobility, security or billing?");
    private final Map<String, AdvisorConversation> sessions = new ConcurrentHashMap<>();
    private final AdvisorModelProvider provider;
    private final RecommendationService recommendations;
    private final SensitiveMessageRedactor redactor;

    public AdvisorSessionService(AdvisorModelProvider provider, RecommendationService recommendations,
            SensitiveMessageRedactor redactor) {
        this.provider = provider;
        this.recommendations = recommendations;
        this.redactor = redactor;
    }

    public AdvisorSessionResponse start(String initialNeed) {
        evictExpired();
        if (sessions.size() >= MAX_SESSIONS) throw new AdvisorProviderException("ADVISOR_BUSY", HttpStatus.SERVICE_UNAVAILABLE,
                "The business advisor is busy. Please try again shortly.");
        AdvisorConversation conversation = new AdvisorConversation();
        AdvisorProfile profile = conversation.profile();
        if (initialNeed != null && !initialNeed.isBlank()) {
            try { profile = profile.withNeed(BusinessNeed.valueOf(initialNeed.trim())); }
            catch (IllegalArgumentException exception) { throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "The selected business need is not supported."); }
        }
        conversation.update(profile, List.of(), List.of(), null, null, Map.of());
        sessions.put(conversation.id(), conversation);
        return view(conversation);
    }

    public AdvisorSessionResponse send(String id, String rawMessage) {
        AdvisorConversation conversation = find(id);
        conversation.lock().lock();
        try {
            String message = redactor.redact(rawMessage);
            if (message.isBlank() || message.replace("[removed]", "").isBlank()) throw new ResponseStatusException(HttpStatus.BAD_REQUEST,
                    "Please send a message without personal identifiers so the advisor can help safely.");
            List<AdvisorMessage> history = new ArrayList<>(conversation.messages());
            history.add(new AdvisorMessage("user", message, Instant.now()));
            AdvisorModelProvider.ExtractionResponse extracted = provider.extract(conversation.profile(), List.copyOf(history), message);
            if (extracted == null || extracted.facts() == null || extracted.followUpFields() == null
                    || !safeExplanation(extracted.reply())) throw invalidModelOutput();
            MergeResult merged = merge(conversation.profile(), extracted.facts(), message);
            AdvisorProfile profile = merged.profile();
            List<String> questions = selectQuestions(profile, extracted.followUpFields(), merged.conflicts());
            RecommendationResponse recommendation = null;
            String explanation = null;
            Map<String, String> productExplanations = Map.of();
            String assistantMessage;
            if (profile.ready() && merged.conflicts().isEmpty()) {
                recommendation = recommendations.recommend(profile.toRecommendationProfile());
                AdvisorModelProvider.ExplanationResponse explained = provider.explain(profile, recommendation);
                if (explained == null) throw invalidModelOutput();
                explanation = explained.summary();
                if (!safeExplanation(explanation)) throw invalidModelOutput();
                assistantMessage = explanation;
                Set<String> selectedIds = recommendation.recommendations().stream()
                        .flatMap(bundle -> bundle.selections().stream()).map(selection -> selection.productId()).collect(java.util.stream.Collectors.toSet());
                HashMap<String, String> valid = new HashMap<>();
                if (explained.products() == null) throw invalidModelOutput();
                explained.products().stream().filter(item -> item != null && selectedIds.contains(item.productId()))
                        .filter(item -> safeExplanation(item.reason())).forEach(item -> valid.putIfAbsent(item.productId(), item.reason()));
                productExplanations = Map.copyOf(valid);
                history.add(new AdvisorMessage("assistant", explanation, Instant.now()));
            } else {
                assistantMessage = extracted.reply();
                if (!safeExplanation(assistantMessage)) throw invalidModelOutput();
                history.add(new AdvisorMessage("assistant", assistantMessage, Instant.now()));
            }
            history = trim(history);
            conversation.update(profile, history, questions, recommendation, assistantMessage, productExplanations);
            return view(conversation);
        } finally { conversation.lock().unlock(); }
    }

    public AdvisorSessionResponse get(String id) {
        AdvisorConversation conversation = find(id);
        conversation.lock().lock();
        try { conversation.touch(); return view(conversation); }
        finally { conversation.lock().unlock(); }
    }

    public AdvisorProfile profile(String id) { return get(id).profile(); }

    public RecommendationResponse recommendation(String id) {
        AdvisorConversation conversation = find(id);
        conversation.lock().lock();
        try {
            if (conversation.recommendation() == null) throw new ResponseStatusException(HttpStatus.CONFLICT,
                    "A recommendation is not available until the required business details are collected.");
            return conversation.recommendation();
        } finally { conversation.lock().unlock(); }
    }

    private AdvisorConversation find(String id) {
        evictExpired();
        AdvisorConversation session = sessions.get(id);
        if (session == null) throw new ResponseStatusException(HttpStatus.NOT_FOUND, "Conversation not found or expired.");
        return session;
    }

    private void evictExpired() {
        Instant cutoff = Instant.now().minus(SESSION_TTL);
        sessions.entrySet().removeIf(entry -> entry.getValue().lastAccess().isBefore(cutoff));
    }

    private static AdvisorSessionResponse view(AdvisorConversation c) {
        return new AdvisorSessionResponse(c.id(), c.messages(), c.profile(), List.copyOf(c.profile().missingFields()),
                c.followUpQuestions(), c.recommendation() == null ? "DISCOVERY" : "RECOMMENDATION_READY",
                c.recommendation(), c.advisorExplanation(), c.productExplanations(), false);
    }

    private static List<AdvisorMessage> trim(List<AdvisorMessage> messages) {
        return List.copyOf(messages.subList(Math.max(0, messages.size() - MAX_MESSAGES), messages.size()));
    }

    private static MergeResult merge(AdvisorProfile old, List<AdvisorModelProvider.ExtractedFact> facts, String latest) {
        AdvisorProfile profile = old;
        Set<String> conflicts = new LinkedHashSet<>();
        Map<String, String> updates = new HashMap<>();
        boolean explicitCorrection = CORRECTION.matcher(latest).find();
        for (AdvisorModelProvider.ExtractedFact fact : facts) {
            if (fact == null || fact.field() == null || fact.value() == null || fact.evidence() == null
                    || fact.evidence().isBlank() || !containsEvidence(latest, fact.evidence())) continue;
            String field = fact.field().toUpperCase(Locale.ROOT);
            String value = fact.value().trim();
            if (!evidenceSupportsField(field, value, fact.evidence())) continue;
            String prior = valueOf(profile, field);
            if (prior != null && !prior.equalsIgnoreCase(value) && !field.equals("NEED")) {
                if (!explicitCorrection) { conflicts.add(field); continue; }
            }
            String previous = updates.putIfAbsent(field, value);
            if (previous != null && !previous.equalsIgnoreCase(value)) { conflicts.add(field); continue; }
            try { profile = apply(profile, field, value, fact.evidence()); }
            catch (IllegalArgumentException ignored) { /* Unrecognized output is discarded, never coerced. */ }
        }
        return new MergeResult(profile, conflicts);
    }

    private static AdvisorProfile apply(AdvisorProfile p, String field, String value, String evidence) {
        return switch (field) {
            case "SEGMENT" -> new AdvisorProfile(BusinessSegment.valueOf(value), p.businessType(), p.employeeCount(), p.siteCount(), p.city(), p.cityTier(), p.state(), p.gstinStatus(), p.currentRequirements(), p.industryActivity());
            case "BUSINESS_TYPE" -> new AdvisorProfile(p.segment(), required(value, 100), p.employeeCount(), p.siteCount(), p.city(), p.cityTier(), p.state(), p.gstinStatus(), p.currentRequirements(), p.industryActivity());
            case "EMPLOYEE_COUNT" -> new AdvisorProfile(p.segment(), p.businessType(), boundedInteger(value, 0, 100000), p.siteCount(), p.city(), p.cityTier(), p.state(), p.gstinStatus(), p.currentRequirements(), p.industryActivity());
            case "SITE_COUNT" -> new AdvisorProfile(p.segment(), p.businessType(), p.employeeCount(), boundedInteger(value, 1, 10000), p.city(), p.cityTier(), p.state(), p.gstinStatus(), p.currentRequirements(), p.industryActivity());
            case "CITY" -> new AdvisorProfile(p.segment(), p.businessType(), p.employeeCount(), p.siteCount(), required(value, 80), p.cityTier(), p.state(), p.gstinStatus(), p.currentRequirements(), p.industryActivity());
            case "CITY_TIER" -> new AdvisorProfile(p.segment(), p.businessType(), p.employeeCount(), p.siteCount(), p.city(), boundedInteger(value, 1, 3), p.state(), p.gstinStatus(), p.currentRequirements(), p.industryActivity());
            case "STATE" -> new AdvisorProfile(p.segment(), p.businessType(), p.employeeCount(), p.siteCount(), p.city(), p.cityTier(), required(value, 80), p.gstinStatus(), p.currentRequirements(), p.industryActivity());
            case "GSTIN_STATUS" -> new AdvisorProfile(p.segment(), p.businessType(), p.employeeCount(), p.siteCount(), p.city(), p.cityTier(), p.state(), customerReportedStatus(value, evidence), p.currentRequirements(), p.industryActivity());
            case "NEED" -> {
                BusinessNeed need = BusinessNeed.valueOf(value);
                var needs = new LinkedHashSet<>(p.currentRequirements());
                if (Pattern.compile("(?i)\\b(no longer need|don't need|do not need|remove|not interested in)\\b").matcher(evidence).find()) needs.remove(need);
                else needs.add(need);
                yield new AdvisorProfile(p.segment(), p.businessType(), p.employeeCount(), p.siteCount(), p.city(), p.cityTier(), p.state(), p.gstinStatus(), needs, p.industryActivity());
            }
            case "INDUSTRY_ACTIVITY" -> new AdvisorProfile(p.segment(), p.businessType(), p.employeeCount(), p.siteCount(), p.city(), p.cityTier(), p.state(), p.gstinStatus(), p.currentRequirements(), required(value, 240));
            default -> p;
        };
    }

    private static GstinVerificationStatus customerReportedStatus(String value, String evidence) {
        GstinVerificationStatus status = GstinVerificationStatus.valueOf(value);
        String lower = evidence.toLowerCase(Locale.ROOT);
        if (status == GstinVerificationStatus.ACTIVE && !lower.matches("(?s).*\\b(active|currently valid)\\b.*")) throw new IllegalArgumentException();
        if (status == GstinVerificationStatus.CANCELLED && !lower.contains("cancel")) throw new IllegalArgumentException();
        if (status == GstinVerificationStatus.SUSPENDED && !lower.contains("suspend")) throw new IllegalArgumentException();
        if (status == GstinVerificationStatus.NOT_PROVIDED && !(lower.contains("don't have") || lower.contains("do not have") || lower.contains("no gstin") || lower.contains("not registered"))) throw new IllegalArgumentException();
        if (status == GstinVerificationStatus.NOT_FOUND || status == GstinVerificationStatus.LOOKUP_FAILED) throw new IllegalArgumentException();
        return status;
    }

    private static String valueOf(AdvisorProfile p, String field) {
        return switch (field) {
            case "SEGMENT" -> p.segment() == null ? null : p.segment().name();
            case "BUSINESS_TYPE" -> p.businessType(); case "EMPLOYEE_COUNT" -> p.employeeCount() == null ? null : p.employeeCount().toString();
            case "SITE_COUNT" -> p.siteCount() == null ? null : p.siteCount().toString(); case "CITY" -> p.city();
            case "CITY_TIER" -> p.cityTier() == null ? null : p.cityTier().toString(); case "STATE" -> p.state();
            case "GSTIN_STATUS" -> p.gstinStatus() == null ? null : p.gstinStatus().name();
            case "INDUSTRY_ACTIVITY" -> p.industryActivity(); default -> null;
        };
    }

    private static boolean containsEvidence(String source, String evidence) {
        return normalize(source).contains(normalize(evidence)) && evidence.length() <= 160;
    }
    private static boolean evidenceSupportsField(String field, String value, String evidence) {
        String quote = normalize(evidence);
        return switch (field) {
            case "EMPLOYEE_COUNT" -> quote.matches("(?s).*(\\b(employee|employees|staff|worker|workers|team|people)\\b).*");
            case "SITE_COUNT" -> quote.matches("(?s).*(\\b(location|locations|site|sites|branch|branches|store|stores|outlet|outlets|office|offices)\\b).*");
            case "CITY_TIER" -> quote.matches("(?s).*\\b(city )?tier\\s*(one|two|three|1|2|3)\\b.*")
                    && value.matches("[1-3]");
            case "GSTIN_STATUS" -> quote.matches("(?s).*(\\b(active|currently valid|cancelled|canceled|suspended|don't have|do not have|no gstin|not registered)\\b).*");
            case "NEED" -> needIsExplicit(value, quote);
            default -> true;
        };
    }
    private static boolean needIsExplicit(String value, String quote) {
        try {
            return switch (BusinessNeed.valueOf(value)) {
                case RELIABLE_INTERNET -> quote.matches("(?s).*(\\binternet\\b|\\bbroadband\\b|\\bwi-?fi\\b|\\bconnectivity\\b).*");
                case BUSINESS_MOBILITY -> quote.matches("(?s).*(\\bbusiness mobile\\b|\\bmobile lines?\\b|\\bphone connection\\b|\\bpostpaid\\b).*");
                case CUSTOMER_MESSAGING -> quote.matches("(?s).*(\\bmessage|\\bwhatsapp\\b|\\bsms\\b|\\btext customers\\b).*");
                case CLOUD_PRODUCTIVITY -> quote.matches("(?s).*(\\bcloud\\b|\\bemail\\b|\\boffice suite\\b|\\bfile collaboration\\b).*");
                case SECURITY -> quote.matches("(?s).*(\\bsecurity\\b|\\bsecure\\b|\\bprotect(ion)?\\b|\\bantivirus\\b).*");
                case POS_BILLING -> quote.matches("(?s).*(\\bpos\\b|\\bbilling\\b|\\binvoice|\\bpoint of sale\\b).*");
                case CCTV -> quote.matches("(?s).*(\\bcctv\\b|\\bcamera monitoring\\b|\\bsurveillance\\b).*");
                case MULTI_SITE_MANAGEMENT -> quote.matches("(?s).*(\\bmanage (my |our )?(locations|sites|branches)\\b|\\bmulti-site management\\b).*");
                case MACHINE_MONITORING -> quote.matches("(?s).*(\\bmachine monitoring\\b|\\bmonitor (my |our )?machines\\b|\\bequipment monitoring\\b).*");
                case FLEET_TRACKING -> quote.matches("(?s).*(\\bfleet tracking\\b|\\btrack (my |our )?vehicles\\b|\\bvehicle tracking\\b).*");
            };
        } catch (IllegalArgumentException exception) { return false; }
    }
    private static String normalize(String value) { return value.toLowerCase(Locale.ROOT).replaceAll("\\s+", " ").trim(); }
    private static int boundedInteger(String value, int min, int max) {
        int result = Integer.parseInt(value);
        if (result < min || result > max) throw new IllegalArgumentException();
        return result;
    }
    private static String required(String value, int max) {
        String result = value.trim();
        if (result.isBlank() || result.length() > max) throw new IllegalArgumentException();
        return result;
    }
    private static List<String> selectQuestions(AdvisorProfile profile, List<String> modelFields, Set<String> conflicts) {
        var required = new LinkedHashSet<String>(profile.missingFields());
        required.addAll(conflicts);
        Set<String> suggested = modelFields == null ? Set.of() : Set.copyOf(modelFields);
        List<String> selected = FOLLOWUP_ORDER.stream().filter(field -> required.contains(field)
                && (suggested.isEmpty() || suggested.contains(field))).limit(2).map(QUESTIONS::get).toList();
        if (selected.isEmpty() && !required.isEmpty()) selected = FOLLOWUP_ORDER.stream().filter(required::contains).limit(2).map(QUESTIONS::get).toList();
        if (!conflicts.isEmpty()) {
            List<String> conflictQuestions = conflicts.stream().limit(2).map(field -> "I have a different "
                    + field.toLowerCase(Locale.ROOT).replace('_', ' ') + " saved. What should I change it to?").toList();
            return conflictQuestions;
        }
        return selected;
    }
    private static boolean safeExplanation(String text) {
        return text != null && text.length() <= 700 && !text.matches("(?s).*(\\x{20B9}|\\bINR\\b|\\bRs\\.?\\b|\\d|\\bP\\d{2}\\b|\\b(price|cost|discount)\\b).*");
    }
    private static AdvisorProviderException invalidModelOutput() {
        return new AdvisorProviderException("ADVISOR_INVALID_RESPONSE", HttpStatus.BAD_GATEWAY,
                "The business advisor returned an incomplete response. Please try again.");
    }
    private record MergeResult(AdvisorProfile profile, Set<String> conflicts) { }
}
