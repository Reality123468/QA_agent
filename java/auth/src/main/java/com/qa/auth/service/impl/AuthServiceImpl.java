package com.qa.auth.service.impl;

import com.qa.auth.dto.LoginRequest;
import com.qa.auth.dto.LoginResponse;
import com.qa.auth.dto.RegisterRequest;
import com.qa.auth.entity.SysUser;
import com.qa.auth.repository.UserRepository;
import com.qa.auth.service.AuthService;
import com.qa.auth.util.JwtUtil;
import com.qa.common.BusinessException;
import com.qa.common.ErrorCode;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;

@Service
public class AuthServiceImpl implements AuthService {

    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;
    private final JwtUtil jwtUtil;

    public AuthServiceImpl(UserRepository userRepository,
                          PasswordEncoder passwordEncoder,
                          JwtUtil jwtUtil) {
        this.userRepository = userRepository;
        this.passwordEncoder = passwordEncoder;
        this.jwtUtil = jwtUtil;
    }

    @Override
    public LoginResponse login(LoginRequest request) {
        SysUser user = userRepository.findByUsername(request.getUsername())
                .orElseThrow(() -> new BusinessException(ErrorCode.USERNAME_OR_PASSWORD_ERROR));

        if (!passwordEncoder.matches(request.getPassword(), user.getPassword())) {
            throw new BusinessException(ErrorCode.USERNAME_OR_PASSWORD_ERROR);
        }

        String token = jwtUtil.generateToken(user.getId(), user.getUsername(), user.getRole());
        return LoginResponse.builder()
                .token(token)
                .username(user.getUsername())
                .role(user.getRole())
                .department(user.getDepartment())
                .build();
    }

    @Override
    public void register(RegisterRequest request) {
        if (userRepository.existsByUsername(request.getUsername())) {
            throw new BusinessException(ErrorCode.USERNAME_EXISTS);
        }

        SysUser user = SysUser.builder()
                .username(request.getUsername())
                .password(passwordEncoder.encode(request.getPassword()))
                .email(request.getEmail())
                .department(request.getDepartment())
                .role("ROLE_EMPLOYEE")
                .build();

        userRepository.save(user);
    }
}
