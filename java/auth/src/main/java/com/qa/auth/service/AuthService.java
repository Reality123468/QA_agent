package com.qa.auth.service;

import com.qa.auth.dto.LoginRequest;
import com.qa.auth.dto.LoginResponse;
import com.qa.auth.dto.RegisterRequest;

public interface AuthService {
    LoginResponse login(LoginRequest request);
    void register(RegisterRequest request);
}
