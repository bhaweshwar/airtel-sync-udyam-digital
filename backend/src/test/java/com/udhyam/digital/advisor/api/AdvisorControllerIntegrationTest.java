package com.udhyam.digital.advisor.api;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.context.TestPropertySource;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;
import com.fasterxml.jackson.databind.ObjectMapper;

@SpringBootTest
@AutoConfigureMockMvc
@TestPropertySource(properties = "app.advisor.gemini.api-key=")
class AdvisorControllerIntegrationTest {
    @Autowired private MockMvc mvc;
    @Autowired private ObjectMapper mapper;

    @Test
    void startsAndRetrievesAnEmptySessionAndProfileWithoutAProviderKey() throws Exception {
        MvcResult started = mvc.perform(post("/api/v1/advisor/conversations").contentType(MediaType.APPLICATION_JSON).content("{}"))
                .andExpect(status().isOk()).andExpect(jsonPath("$.status").value("DISCOVERY"))
                .andExpect(jsonPath("$.messages.length()").value(0)).andExpect(jsonPath("$.gstinStatusVerified").value(false))
                .andReturn();
        String id = mapper.readTree(started.getResponse().getContentAsString()).path("conversationId").asText();
        mvc.perform(get("/api/v1/advisor/conversations/" + id + "/profile"))
                .andExpect(status().isOk()).andExpect(jsonPath("$.profile.employeeCount").doesNotExist())
                .andExpect(jsonPath("$.gstinStatusVerified").value(false));
        mvc.perform(get("/api/v1/advisor/conversations/" + id + "/recommendation"))
                .andExpect(status().isConflict()).andExpect(jsonPath("$.code").value("CONFLICT"));
    }

    @Test
    void missingProviderKeyAndEmptyInputReturnSafeRecoverableApiErrors() throws Exception {
        MvcResult started = mvc.perform(post("/api/v1/advisor/conversations").contentType(MediaType.APPLICATION_JSON).content("{}"))
                .andExpect(status().isOk()).andReturn();
        String id = mapper.readTree(started.getResponse().getContentAsString()).path("conversationId").asText();
        mvc.perform(post("/api/v1/advisor/conversations/" + id + "/messages").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"message\":\"I run a shop.\"}"))
                .andExpect(status().isServiceUnavailable())
                .andExpect(jsonPath("$.code").value("ADVISOR_API_KEY_MISSING"))
                .andExpect(jsonPath("$.message").value(org.hamcrest.Matchers.containsString("GEMINI_API_KEY")));
        mvc.perform(post("/api/v1/advisor/conversations/" + id + "/messages").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"message\":\" \"}"))
                .andExpect(status().isBadRequest());
    }
}
