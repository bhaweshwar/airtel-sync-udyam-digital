package com.udhyam.digital.advisor.infrastructure;

import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.content;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.header;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.method;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withStatus;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withSuccess;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.udhyam.digital.advisor.application.AdvisorProviderException;
import com.udhyam.digital.advisor.domain.AdvisorMessage;
import com.udhyam.digital.advisor.domain.AdvisorProfile;
import java.time.Duration;
import java.net.ConnectException;
import java.net.SocketTimeoutException;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.springframework.boot.test.system.CapturedOutput;
import org.springframework.boot.test.system.OutputCaptureExtension;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.ResourceAccessException;

@ExtendWith(OutputCaptureExtension.class)
class GeminiRestAdvisorProviderTest {
    private final ObjectMapper mapper = new ObjectMapper();
    private static final String SUCCESS_RESPONSE = """
            {"candidates":[{"content":{"parts":[{"text":"{\\"facts\\":[],\\"reply\\":\\"Thanks for sharing.\\",\\"followUpFields\\":[\\"BUSINESS_TYPE\\"]}"}]}}]}
            """;

    @Test
    void missingGeminiKeyFailsRecoverablyWithoutSendingARequest() {
        var provider = new GeminiRestAdvisorProvider("", "gemini-3.8-flash", Duration.ofSeconds(1), mapper);
        assertThatThrownBy(() -> provider.extract(AdvisorProfile.empty(), List.of(), "hello"))
                .isInstanceOf(AdvisorProviderException.class)
                .hasMessageContaining("GEMINI_API_KEY");
    }

    @Test
    void invalidModelNameIsRejectedBeforeAnyProviderRequest() {
        var provider = new GeminiRestAdvisorProvider("test-only-not-a-real-key", "https://bad.example/route", Duration.ofSeconds(1), mapper);
        assertThatThrownBy(() -> provider.extract(AdvisorProfile.empty(), List.of(new AdvisorMessage("user", "hello", java.time.Instant.now())), "hello"))
                .isInstanceOf(AdvisorProviderException.class)
                .hasMessageContaining("GEMINI_MODEL");
    }

    @Test
    void usesDocumentedGeminiEndpointAndStructuredJsonWithoutPuttingKeyInBody() {
        RestClient.Builder builder = RestClient.builder().baseUrl("https://generativelanguage.googleapis.com");
        MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
        server.expect(requestTo("https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent"))
                .andExpect(method(HttpMethod.POST)).andExpect(header("x-goog-api-key", "test-key-only"))
                .andExpect(content().string(org.hamcrest.Matchers.not(org.hamcrest.Matchers.containsString("test-key-only"))))
                .andExpect(content().string(org.hamcrest.Matchers.containsString("responseSchema")))
                .andRespond(withSuccess("""
                        {"candidates":[{"content":{"parts":[{"text":"{\\"facts\\":[],\\"reply\\":\\"Thanks for sharing.\\",\\"followUpFields\\":[\\"BUSINESS_TYPE\\"]}"}]}}]}
                        """, MediaType.APPLICATION_JSON));
        var provider = new GeminiRestAdvisorProvider("test-key-only", "gemini-3.8-flash", Duration.ofSeconds(2), mapper, builder.build());
        var response = provider.extract(AdvisorProfile.empty(), List.of(new AdvisorMessage("user", "hello", java.time.Instant.now())), "hello");
        assertThat(response.reply()).isEqualTo("Thanks for sharing.");
        assertThat(response.followUpFields()).containsExactly("BUSINESS_TYPE");
        server.verify();
    }

    @Test
    void rateLimitReturnsASafeRecoverableProviderErrorAndLogsOnlyStatus(CapturedOutput output) {
        RestClient.Builder builder = RestClient.builder().baseUrl("https://generativelanguage.googleapis.com");
        MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
        server.expect(requestTo("https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent"))
                .andRespond(withStatus(HttpStatus.TOO_MANY_REQUESTS).contentType(MediaType.APPLICATION_JSON).body("secret provider detail"));
        var provider = new GeminiRestAdvisorProvider("test-key-only", "gemini-3.8-flash", Duration.ofSeconds(2), mapper, builder.build());
        assertThatThrownBy(() -> provider.extract(AdvisorProfile.empty(), List.of(), "hello"))
                .isInstanceOf(AdvisorProviderException.class).hasMessageContaining("busy right now")
                .hasMessageNotContaining("secret provider detail");
        assertThat(output).contains("upstreamStatus=429", "Gemini upstream HTTP failure")
                .doesNotContain("secret provider detail", "test-key-only");
        server.verify();
    }

    @Test
    void upstreamServerErrorLogsStatusWithoutResponseBodyOrKey(CapturedOutput output) {
        RestClient.Builder builder = RestClient.builder().baseUrl("https://generativelanguage.googleapis.com");
        MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
        server.expect(requestTo("https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent"))
                .andRespond(withStatus(HttpStatus.BAD_GATEWAY).contentType(MediaType.APPLICATION_JSON).body("private upstream payload"));
        var provider = new GeminiRestAdvisorProvider("private-test-key", "gemini-3.8-flash", Duration.ofSeconds(2), mapper, builder.build());

        assertThatThrownBy(() -> provider.extract(AdvisorProfile.empty(), List.of(), "hello"))
                .isInstanceOf(AdvisorProviderException.class)
                .hasMessage("The business advisor is temporarily unavailable. Please try again.");
        assertThat(output).contains("upstreamStatus=502", "exceptionType=")
                .doesNotContain("private upstream payload", "private-test-key");
        server.verify();
    }

    @Test
    void retries503AndSucceedsOnTheNextAttempt(CapturedOutput output) {
        RestClient.Builder builder = RestClient.builder().baseUrl("https://generativelanguage.googleapis.com");
        MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
        String uri = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent";
        server.expect(requestTo(uri)).andRespond(withStatus(HttpStatus.SERVICE_UNAVAILABLE).body("private upstream detail"));
        server.expect(requestTo(uri)).andRespond(withSuccess(SUCCESS_RESPONSE, MediaType.APPLICATION_JSON));
        var provider = new GeminiRestAdvisorProvider("private-test-key", "gemini-3.8-flash", Duration.ofSeconds(2), mapper, builder.build());

        var response = provider.extract(AdvisorProfile.empty(), List.of(), "hello");

        assertThat(response.reply()).isEqualTo("Thanks for sharing.");
        assertThat(output).contains("category=upstream_503", "retry=1/2", "backoffMs=200")
                .doesNotContain("private upstream detail", "private-test-key");
        server.verify();
    }

    @Test
    void stopsAfterTwoAdditional503Attempts(CapturedOutput output) {
        RestClient.Builder builder = RestClient.builder().baseUrl("https://generativelanguage.googleapis.com");
        MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
        String uri = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent";
        for (int i = 0; i < 3; i++) {
            server.expect(requestTo(uri)).andRespond(withStatus(HttpStatus.SERVICE_UNAVAILABLE).body("private upstream detail"));
        }
        var provider = new GeminiRestAdvisorProvider("private-test-key", "gemini-3.8-flash", Duration.ofSeconds(2), mapper, builder.build());

        assertThatThrownBy(() -> provider.extract(AdvisorProfile.empty(), List.of(), "hello"))
                .isInstanceOf(AdvisorProviderException.class)
                .hasMessage("The business advisor is temporarily unavailable. Please try again.");
        assertThat(output).contains("retry=1/2", "retry=2/2", "upstreamStatus=503")
                .doesNotContain("private upstream detail", "private-test-key", "retry=3/");
        server.verify();
    }

    @Test
    void doesNotRetryPermanentClientErrors(CapturedOutput output) {
        RestClient.Builder builder = RestClient.builder().baseUrl("https://generativelanguage.googleapis.com");
        MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
        server.expect(requestTo("https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent"))
                .andRespond(withStatus(HttpStatus.BAD_REQUEST).body("private invalid request detail"));
        var provider = new GeminiRestAdvisorProvider("private-test-key", "gemini-3.8-flash", Duration.ofSeconds(2), mapper, builder.build());

        assertThatThrownBy(() -> provider.extract(AdvisorProfile.empty(), List.of(), "hello"))
                .isInstanceOf(AdvisorProviderException.class)
                .hasMessage("The business advisor could not use the configured Gemini model. Check the backend configuration and try again.");
        assertThat(output).contains("upstreamStatus=400")
                .doesNotContain("Gemini transient failure", "private invalid request detail", "private-test-key");
        server.verify();
    }

    @Test
    void runtimeFailureLogsExceptionTypeButNotMessageOrKey(CapturedOutput output) {
        RestClient.Builder builder = RestClient.builder().baseUrl("https://generativelanguage.googleapis.com");
        MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
        server.expect(requestTo("https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent"))
                .andRespond(request -> { throw new IllegalStateException("private runtime detail"); });
        var provider = new GeminiRestAdvisorProvider("private-test-key", "gemini-3.8-flash", Duration.ofSeconds(2), mapper, builder.build());

        assertThatThrownBy(() -> provider.extract(AdvisorProfile.empty(), List.of(), "hello"))
                .isInstanceOf(AdvisorProviderException.class)
                .hasMessage("The business advisor is temporarily unavailable. Please try again.");
        assertThat(output).contains("Gemini runtime failure", "exceptionType=IllegalStateException")
                .doesNotContain("private runtime detail", "private-test-key");
        server.verify();
    }

    @Test
    void doesNotRetryRestClientExceptionWithUnclassifiedCause(CapturedOutput output) {
        RestClient.Builder builder = RestClient.builder().baseUrl("https://generativelanguage.googleapis.com");
        MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
        server.expect(requestTo("https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent"))
                .andRespond(request -> { throw new RestClientException("private client detail", new IllegalArgumentException("private parse detail")); });
        var provider = new GeminiRestAdvisorProvider("private-test-key", "gemini-3.8-flash", Duration.ofSeconds(2), mapper, builder.build());

        assertThatThrownBy(() -> provider.extract(AdvisorProfile.empty(), List.of(), "hello"))
                .isInstanceOf(AdvisorProviderException.class)
                .hasMessage("The business advisor is temporarily unavailable. Please try again.");
        assertThat(output).contains("Gemini REST client failure", "category=non_transient", "underlyingExceptionType=IllegalArgumentException")
                .doesNotContain("Gemini transient failure", "private client detail", "private parse detail", "private-test-key");
        server.verify();
    }

    @Test
    void malformedGeminiPayloadIsRejectedAndLogsSafeParsingDiagnostic(CapturedOutput output) {
        RestClient.Builder builder = RestClient.builder().baseUrl("https://generativelanguage.googleapis.com");
        MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
        server.expect(requestTo("https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent"))
                .andRespond(withSuccess("{\"candidates\":[{\"content\":{\"parts\":[{\"text\":\"not-json\"}]}}]}", MediaType.APPLICATION_JSON));
        var provider = new GeminiRestAdvisorProvider("test-key-only", "gemini-3.8-flash", Duration.ofSeconds(2), mapper, builder.build());
        assertThatThrownBy(() -> provider.extract(AdvisorProfile.empty(), List.of(), "hello"))
                .isInstanceOf(AdvisorProviderException.class).hasMessage("The business advisor returned an incomplete response. Please try again.");
        assertThat(output).contains("Gemini response parsing failed", "InvalidResponse")
                .doesNotContain("not-json", "test-key-only");
        server.verify();
    }

    @Test
    void retriesTimeoutAndSucceedsWithoutExposingTransportDetails(CapturedOutput output) {
        RestClient.Builder builder = RestClient.builder().baseUrl("https://generativelanguage.googleapis.com");
        MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
        String uri = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent";
        server.expect(requestTo(uri))
                .andRespond(request -> { throw new ResourceAccessException("private transport detail", new SocketTimeoutException("private timeout detail")); });
        server.expect(requestTo(uri)).andRespond(withSuccess(SUCCESS_RESPONSE, MediaType.APPLICATION_JSON));
        var provider = new GeminiRestAdvisorProvider("test-key-only", "gemini-3.8-flash", Duration.ofSeconds(2), mapper, builder.build());
        assertThat(provider.extract(AdvisorProfile.empty(), List.of(), "hello").reply()).isEqualTo("Thanks for sharing.");
        assertThat(output).contains("Gemini transient failure", "category=timeout", "retry=1/2", "causeType=SocketTimeoutException")
                .doesNotContain("private transport detail", "private timeout detail", "test-key-only");
        server.verify();
    }

    @Test
    void restClientExceptionWithConnectionCauseIsRetriedAndCauseTypeIsLoggedSafely(CapturedOutput output) {
        RestClient.Builder builder = RestClient.builder().baseUrl("https://generativelanguage.googleapis.com");
        MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
        String uri = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent";
        server.expect(requestTo(uri))
                .andRespond(request -> { throw new RestClientException("private connection detail", new ConnectException("private socket detail")); });
        server.expect(requestTo(uri)).andRespond(withSuccess(SUCCESS_RESPONSE, MediaType.APPLICATION_JSON));
        var provider = new GeminiRestAdvisorProvider("private-test-key", "gemini-3.8-flash", Duration.ofSeconds(2), mapper, builder.build());

        assertThat(provider.extract(AdvisorProfile.empty(), List.of(), "hello").reply()).isEqualTo("Thanks for sharing.");
        assertThat(output).contains("Gemini transient failure", "category=connection_failure", "causeType=ConnectException")
                .doesNotContain("private connection detail", "private socket detail", "private-test-key");
        server.verify();
    }
}
