package com.qa.auth.controller;

import com.qa.auth.dto.LoginRequest;
import com.qa.auth.dto.LoginResponse;
import com.qa.auth.dto.RegisterRequest;
import com.qa.auth.service.AuthService;
import com.qa.common.ApiResult;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/auth")
public class AuthController {

    private final AuthService authService;

    public AuthController(AuthService authService) {
        this.authService = authService;
    }

    @PostMapping("/login")
    public ApiResult<LoginResponse> login(@Valid @RequestBody LoginRequest request) {
        return ApiResult.success(authService.login(request));
    }

    @PostMapping("/register")
    public ApiResult<Void> register(@Valid @RequestBody RegisterRequest request) {
        authService.register(request);
        return ApiResult.success(null);
    }
}
