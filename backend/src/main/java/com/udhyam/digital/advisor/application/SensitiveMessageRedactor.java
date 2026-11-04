package com.udhyam.digital.advisor.application;

import java.util.List;
import java.util.regex.Pattern;
import org.springframework.stereotype.Component;

/** Drops common Indian government/financial identifiers before any conversation is retained or sent to Gemini. */
@Component
public class SensitiveMessageRedactor {
    private static final List<Pattern> IDENTIFIERS = List.of(
            Pattern.compile("(?i)\\b(my name is|owner name is|my address is|account number is)\\s+[^,.;\\n]{2,80}"),
            Pattern.compile("(?i)\\b(passport|passport no\\.?|document id)\\s*(?:is|:|=)?\\s*[A-Z0-9-]{6,20}\\b"),
            Pattern.compile("(?i)\\b(password|passcode|PIN)\\s*(?:is|:|=)\\s*[^\\s,;]+"),
            Pattern.compile("\\bUDYAM-[A-Z]{2}-\\d{2}-\\d{7}\\b"),
            Pattern.compile("(?i)\\b[A-Z]{5}[0-9]{4}[A-Z]\\b"),
            Pattern.compile("(?i)\\b[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]\\b"),
            Pattern.compile("(?<!\\d)(?:\\d[ -]?){12}(?!\\d)"),
            Pattern.compile("(?<!\\d)(?:\\d[ -]?){9,18}(?!\\d)"),
            Pattern.compile("(?<!\\d)(?:\\+91[ -]?)?[6-9]\\d{9}(?!\\d)"),
            Pattern.compile("(?i)\\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\\.[A-Z]{2,}\\b"));

    public String redact(String text) {
        String result = text;
        for (Pattern pattern : IDENTIFIERS) result = pattern.matcher(result).replaceAll("[removed]");
        return result.trim();
    }
}
