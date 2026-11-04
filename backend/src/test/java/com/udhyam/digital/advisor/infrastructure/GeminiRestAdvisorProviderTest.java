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
import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.ResourceAccessException;

class GeminiRestAdvisorProviderTest {
    private final ObjectMapper mapper = new ObjectMapper();

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
    void rateLimitReturnsASafeRecoverableProviderError() {
        RestClient.Builder builder = RestClient.builder().baseUrl("https://generativelanguage.googleapis.com");
        MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
        server.expect(requestTo("https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent"))
                .andRespond(withStatus(HttpStatus.TOO_MANY_REQUESTS).contentType(MediaType.APPLICATION_JSON).body("secret provider detail"));
        var provider = new GeminiRestAdvisorProvider("test-key-only", "gemini-3.8-flash", Duration.ofSeconds(2), mapper, builder.build());
        assertThatThrownBy(() -> provider.extract(AdvisorProfile.empty(), List.of(), "hello"))
                .isInstanceOf(AdvisorProviderException.class).hasMessageContaining("busy right now")
                .hasMessageNotContaining("secret provider detail");
        server.verify();
    }

    @Test
    void malformedGeminiPayloadIsRejectedWithoutPassingRawOutputThrough() {
        RestClient.Builder builder = RestClient.builder().baseUrl("https://generativelanguage.googleapis.com");
        MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
        server.expect(requestTo("https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent"))
                .andRespond(withSuccess("{\"candidates\":[{\"content\":{\"parts\":[{\"text\":\"not-json\"}]}}]}", MediaType.APPLICATION_JSON));
        var provider = new GeminiRestAdvisorProvider("test-key-only", "gemini-3.8-flash", Duration.ofSeconds(2), mapper, builder.build());
        assertThatThrownBy(() -> provider.extract(AdvisorProfile.empty(), List.of(), "hello"))
                .isInstanceOf(AdvisorProviderException.class).hasMessage("The business advisor returned an incomplete response. Please try again.");
        server.verify();
    }

    @Test
    void timeoutMapsToGatewayTimeoutWithoutExposingTransportDetails() {
        RestClient.Builder builder = RestClient.builder().baseUrl("https://generativelanguage.googleapis.com");
        MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
        server.expect(requestTo("https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent"))
                .andRespond(request -> { throw new ResourceAccessException("private transport detail"); });
        var provider = new GeminiRestAdvisorProvider("test-key-only", "gemini-3.8-flash", Duration.ofSeconds(2), mapper, builder.build());
        assertThatThrownBy(() -> provider.extract(AdvisorProfile.empty(), List.of(), "hello"))
                .isInstanceOf(AdvisorProviderException.class).hasMessageContaining("too long")
                .hasMessageNotContaining("private transport detail");
        server.verify();
    }
}
