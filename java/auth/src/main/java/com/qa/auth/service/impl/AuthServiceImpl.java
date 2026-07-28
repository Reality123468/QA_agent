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

        String token = jwtUtil.generateToken(user.getId(), user.getUsername(), user.getRole(), user.getDepartment());
        return LoginResponse.builder()
                .token(token)
                .username(user.getUsername())
                .role(user.getRole())
                .department(user.getDepartment())
                .position(user.getPosition())
                .build();
    }

    @Override
    public void register(RegisterRequest request) {
        if (userRepository.existsByUsername(request.getUsername())) {
            throw new BusinessException(ErrorCode.USERNAME_EXISTS);
        }

        String role = mapPositionToRole(request.getPosition());
        SysUser user = SysUser.builder()
                .username(request.getUsername())
                .password(passwordEncoder.encode(request.getPassword()))
                .email(request.getEmail())
                .department(request.getDepartment())
                .role(role)
                .position(request.getPosition())
                .build();

        userRepository.save(user);
    }

    private String mapPositionToRole(String position) {
        if (position == null) return "ROLE_EMPLOYEE";
        return switch (position) {
            case "部门经理" -> "ROLE_ADMIN";
            case "部门主管" -> "ROLE_LEADER";
            case "人事专员" -> "ROLE_HR";
            default -> "ROLE_EMPLOYEE";
        };
    }
}
