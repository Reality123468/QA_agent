package com.qa.chat.config;

import com.qa.auth.config.JwtAuthFilter;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.annotation.Order;
import org.springframework.security.config.annotation.method.configuration.EnableMethodSecurity;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;

/**
 * chat 模块安全配置。
 *
 * 背景：chat 模块的 @ComponentScan 排除了 com.qa.auth.*，但 auth 模块的
 * SecurityConfig 仍会被加载（anyRequest 链）。SSE（/api/chat/stream）使用 Tomcat
 * 异步分发，异步线程没有 SecurityContext，anyRequest().authenticated() 会在异步
 * 分发时抛 403 中断流式响应，导致"能上传文档但无法得到回答"。
 *
 * 本配置：
 *  - securityMatcher("/api/chat/**") 限定 chat 接口，避免与 auth 的 anyRequest 链冲突；
 *  - @Order(-1) 保证本链先于 auth 链匹配；
 *  - 禁用 CSRF（stream 为 POST + SSE 长连接，CSRF token 会阻塞浏览器端）；
 *  - /api/chat/stream permitAll：SSE 异步分发不再被 AuthorizationFilter 拦截，
 *    登录态由 JwtAuthFilter 设置、控制器显式校验；
 *  - 其余 chat 接口仍要求认证。
 */
@Configuration
@EnableWebSecurity
@EnableMethodSecurity
public class ChatSecurityConfig {

    private final JwtAuthFilter jwtAuthFilter;

    public ChatSecurityConfig(JwtAuthFilter jwtAuthFilter) {
        this.jwtAuthFilter = jwtAuthFilter;
    }

    @Bean
    @Order(-1)
    public SecurityFilterChain chatSecurityFilterChain(HttpSecurity http) throws Exception {
        http
            .securityMatcher("/api/chat/**")
            .csrf(AbstractHttpConfigurer::disable)
            .sessionManagement(session -> session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/api/chat/stream").permitAll()
                .anyRequest().authenticated())
            .addFilterBefore(jwtAuthFilter, UsernamePasswordAuthenticationFilter.class);
        return http.build();
    }
}
