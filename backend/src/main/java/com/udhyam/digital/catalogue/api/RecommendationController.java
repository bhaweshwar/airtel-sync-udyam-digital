package com.udhyam.digital.catalogue.api;

import com.udhyam.digital.catalogue.application.RecommendationService;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/recommendations")
public class RecommendationController {
    private final RecommendationService recommendationService;
    public RecommendationController(RecommendationService recommendationService) { this.recommendationService = recommendationService; }

    @PostMapping
    public RecommendationResponse recommend(@Valid @RequestBody BusinessProfileRequest request) {
        return recommendationService.recommend(request.toDomain());
    }
}
