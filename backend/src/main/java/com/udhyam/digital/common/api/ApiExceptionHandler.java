package com.udhyam.digital.common.api;

import com.udhyam.digital.catalogue.api.EligibilityResponse;
import com.udhyam.digital.catalogue.application.BundleValidationException;
import jakarta.validation.ConstraintViolationException;
import java.util.List;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.server.ResponseStatusException;

@RestControllerAdvice
public class ApiExceptionHandler {
    @ExceptionHandler(BundleValidationException.class)
    ResponseEntity<ApiErrorResponse> bundleNotPurchasable(BundleValidationException exception) {
        List<EligibilityResponse> details = exception.result().products().stream().map(EligibilityResponse::from).toList();
        return ResponseEntity.unprocessableEntity().body(new ApiErrorResponse("BUNDLE_NOT_PURCHASABLE", exception.getMessage(), details));
    }

    @ExceptionHandler({IllegalArgumentException.class, MethodArgumentNotValidException.class, ConstraintViolationException.class, HttpMessageNotReadableException.class})
    ResponseEntity<ApiErrorResponse> badRequest(Exception exception) {
        String message = exception instanceof MethodArgumentNotValidException invalid
                ? invalid.getBindingResult().getFieldErrors().stream().map(error -> error.getField() + ": " + error.getDefaultMessage()).distinct().reduce((a, b) -> a + "; " + b).orElse("Request validation failed")
                : exception instanceof HttpMessageNotReadableException ? "Request body is malformed or contains an unsupported enum value."
                : exception.getMessage();
        return ResponseEntity.badRequest().body(new ApiErrorResponse("INVALID_REQUEST", message, List.of()));
    }

    @ExceptionHandler(ResponseStatusException.class)
    ResponseEntity<ApiErrorResponse> status(ResponseStatusException exception) {
        HttpStatus status = HttpStatus.valueOf(exception.getStatusCode().value());
        return ResponseEntity.status(status).body(new ApiErrorResponse(status.name(), exception.getReason(), List.of()));
    }
}
