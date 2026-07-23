# MVP 智能问答系统实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建"混合检索 RAG + LLM 问答"核心链路，实现文档上传→索引→智能问答端到端流程。

**Architecture:** Java Spring Boot 业务底座（认证、文档管理、对话代理）+ Python FastAPI AI 服务（RAG 检索、LLM 生成），通过 HTTP/SSE 通信，MySQL + Qdrant + MinIO 存储。

**Tech Stack:** Java 21 + Spring Boot 3.5.16 + Maven, Python 3.11 + FastAPI 0.128.0 + LangChain 1.2.22 + Poetry, MySQL 8.0, Qdrant (Docker), MinIO (Docker), DeepSeek API, Vue 3 (frontend)

## Global Constraints

- Java 21, Spring Boot 3.5.16, Maven 构建
- Python 3.11, FastAPI 0.128.0, LangChain 1.2.22, Poetry 包管理
- MySQL root/hwx1314520 本地，Qdrant 端口 6333，MinIO 端口 9000/9001
- 统一响应体 `ApiResult { code, message, data }`，分页 `PageResult`
- JWT 认证，bcrypt 密码哈希，Python 内部 API Key 认证
- DeepSeek API 做 LLM 和 Embedding
- Vue 3 + Element Plus 前端，Vite 开发服务器端口 5173
- 各 Java 模块独立端口：auth 8080 / document 8081 / chat 8082 / audit 8083 / frontend 8084
- 开发顺序：基础设施 → Java common → Java auth → Java document → Java chat → Python api → Python rag → Python llm → Java audit → Java launcher → Vue 前端

---

## Task 0: 基础设施准备

**Files:**
- Create: `docker/docker-compose.yml`

**Interfaces:**
- Produces: Qdrant `localhost:6333`（gRPC）/ `localhost:6334`（HTTP），MinIO `localhost:9000`（API）/ `localhost:9001`（Console）

- [ ] **Step 1: 创建 Docker Compose 文件**

```yaml
# docker/docker-compose.yml
version: '3.8'
services:
  qdrant:
    image: qdrant/qdrant:latest
    container_name: qa-qdrant
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - qdrant_data:/qdrant/storage
    restart: unless-stopped

  minio:
    image: minio/minio:latest
    container_name: qa-minio
    command: server /data --console-address ":9001"
    ports:
      - "9000:9000"
      - "9001:9001"
    environment:
      MINIO_ROOT_USER: admin
      MINIO_ROOT_PASSWORD: admin123456
    volumes:
      - minio_data:/data
    restart: unless-stopped

volumes:
  qdrant_data:
  minio_data:
```

- [ ] **Step 2: 启动中间件**

```bash
cd docker && docker compose up -d
```

验证: `curl http://localhost:6334/health` 返回 200，浏览器打开 `http://localhost:9001` MinIO 控制台。

- [ ] **Step 3: 提交**

```bash
git add docker/docker-compose.yml
git commit -m "feat: add Docker Compose for Qdrant and MinIO"
```

---

## Task 1: Java 父 POM 与 Common 模块

**Files:**
- Create: `java/pom.xml`
- Create: `java/common/pom.xml`
- Create: `java/common/src/main/java/com/qa/CommonApplication.java`
- Create: `java/common/src/main/java/com/qa/common/ApiResult.java`
- Create: `java/common/src/main/java/com/qa/common/PageResult.java`
- Create: `java/common/src/main/java/com/qa/common/ErrorCode.java`
- Create: `java/common/src/main/java/com/qa/common/BusinessException.java`
- Create: `java/common/src/main/java/com/qa/common/GlobalExceptionHandler.java`
- Create: `java/common/src/main/resources/application.yml`

**Interfaces:**
- Produces:
  - `ApiResult<T>` — `static <T> ApiResult<T> success(T data)`, `static ApiResult<Void> error(int code, String message)`
  - `PageResult<T>` — `List<T> content, long totalElements, int totalPages, int number, int size`
  - `ErrorCode` 枚举 — `USERNAME_OR_PASSWORD_ERROR(1001)`, `USERNAME_EXISTS(1002)`, `TOKEN_EXPIRED(1003)`, `TOKEN_INVALID(1004)`, `FILE_TYPE_NOT_SUPPORTED(2001)`, `FILE_SIZE_EXCEEDED(2002)`, `DOCUMENT_INDEX_FAILED(2003)`, `DOCUMENT_NOT_FOUND(2004)`, `AI_SERVICE_UNAVAILABLE(3001)`, `AI_TIMEOUT(3002)`
  - `BusinessException(ErrorCode errorCode)` — 运行时异常
  - `GlobalExceptionHandler` — `@RestControllerAdvice`，处理 BusinessException 和通用异常，返回 `ApiResult`

- [ ] **Step 1: 创建父 POM**

```xml
<!-- java/pom.xml -->
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0
         http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>

    <parent>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-parent</artifactId>
        <version>3.2.4</version>
        <relativePath/>
    </parent>

    <groupId>com.qa</groupId>
    <artifactId>qa-agent</artifactId>
    <version>1.0.0-SNAPSHOT</version>
    <packaging>pom</packaging>
    <name>QA Agent - Parent</name>

    <modules>
        <module>common</module>
        <module>auth</module>
        <module>document</module>
        <module>chat</module>
    </modules>

    <properties>
        <java.version>21</java.version>
        <jjwt.version>0.12.5</jjwt.version>
    </properties>

    <dependencies>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-web</artifactId>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-data-jpa</artifactId>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-security</artifactId>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-validation</artifactId>
        </dependency>
        <dependency>
            <groupId>com.mysql</groupId>
            <artifactId>mysql-connector-j</artifactId>
            <scope>runtime</scope>
        </dependency>
        <dependency>
            <groupId>org.projectlombok</groupId>
            <artifactId>lombok</artifactId>
            <optional>true</optional>
        </dependency>
        <dependency>
            <groupId>io.jsonwebtoken</groupId>
            <artifactId>jjwt-api</artifactId>
            <version>${jjwt.version}</version>
        </dependency>
        <dependency>
            <groupId>io.jsonwebtoken</groupId>
            <artifactId>jjwt-impl</artifactId>
            <version>${jjwt.version}</version>
            <scope>runtime</scope>
        </dependency>
        <dependency>
            <groupId>io.jsonwebtoken</groupId>
            <artifactId>jjwt-jackson</artifactId>
            <version>${jjwt.version}</version>
            <scope>runtime</scope>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-test</artifactId>
            <scope>test</scope>
        </dependency>
    </dependencies>

    <build>
        <plugins>
            <plugin>
                <groupId>org.springframework.boot</groupId>
                <artifactId>spring-boot-maven-plugin</artifactId>
                <configuration>
                    <excludes>
                        <exclude>
                            <groupId>org.projectlombok</groupId>
                            <artifactId>lombok</artifactId>
                        </exclude>
                    </excludes>
                </configuration>
            </plugin>
        </plugins>
    </build>
</project>
```

- [ ] **Step 2: common 模块 POM**

```xml
<!-- java/common/pom.xml -->
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0
         http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>

    <parent>
        <groupId>com.qa</groupId>
        <artifactId>qa-agent</artifactId>
        <version>1.0.0-SNAPSHOT</version>
    </parent>

    <artifactId>qa-common</artifactId>
    <name>QA Common</name>
</project>
```

- [ ] **Step 3: 创建统一响应类**

```java
// java/common/src/main/java/com/qa/CommonApplication.java
package com.qa;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class CommonApplication {
    public static void main(String[] args) {
        SpringApplication.run(CommonApplication.class, args);
    }
}
```

```java
// java/common/src/main/java/com/qa/common/ErrorCode.java
package com.qa.common;

import lombok.Getter;

@Getter
public enum ErrorCode {
    SUCCESS(200, "success"),
    USERNAME_OR_PASSWORD_ERROR(1001, "用户名或密码错误"),
    USERNAME_EXISTS(1002, "用户名已存在"),
    TOKEN_EXPIRED(1003, "Token已过期"),
    TOKEN_INVALID(1004, "Token格式错误"),
    FILE_TYPE_NOT_SUPPORTED(2001, "文件类型不支持"),
    FILE_SIZE_EXCEEDED(2002, "文件大小超出限制"),
    DOCUMENT_INDEX_FAILED(2003, "文档索引失败"),
    DOCUMENT_NOT_FOUND(2004, "文档不存在"),
    AI_SERVICE_UNAVAILABLE(3001, "AI服务暂时不可用"),
    AI_TIMEOUT(3002, "AI服务响应超时"),
    FORBIDDEN(4003, "无权限访问"),
    INTERNAL_ERROR(5000, "服务器内部错误");

    private final int code;
    private final String message;

    ErrorCode(int code, String message) {
        this.code = code;
        this.message = message;
    }
}
```

```java
// java/common/src/main/java/com/qa/common/ApiResult.java
package com.qa.common;

import com.fasterxml.jackson.annotation.JsonInclude;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
@JsonInclude(JsonInclude.Include.NON_NULL)
public class ApiResult<T> {
    private int code;
    private String message;
    private T data;

    public static <T> ApiResult<T> success(T data) {
        return new ApiResult<>(200, "success", data);
    }

    public static <T> ApiResult<T> error(int code, String message) {
        return new ApiResult<>(code, message, null);
    }

    public static <T> ApiResult<T> error(ErrorCode errorCode) {
        return new ApiResult<>(errorCode.getCode(), errorCode.getMessage(), null);
    }
}
```

```java
// java/common/src/main/java/com/qa/common/PageResult.java
package com.qa.common;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class PageResult<T> {
    private List<T> content;
    private long totalElements;
    private int totalPages;
    private int number;
    private int size;

    public static <T> PageResult<T> of(List<T> content, long totalElements, int totalPages, int number, int size) {
        return new PageResult<>(content, totalElements, totalPages, number, size);
    }
}
```

```java
// java/common/src/main/java/com/qa/common/BusinessException.java
package com.qa.common;

import lombok.Getter;

@Getter
public class BusinessException extends RuntimeException {
    private final ErrorCode errorCode;

    public BusinessException(ErrorCode errorCode) {
        super(errorCode.getMessage());
        this.errorCode = errorCode;
    }
}
```

- [ ] **Step 4: 创建全局异常处理器**

```java
// java/common/src/main/java/com/qa/common/GlobalExceptionHandler.java
package com.qa.common;

import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.validation.FieldError;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

import java.util.stream.Collectors;

@Slf4j
@RestControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(BusinessException.class)
    public ResponseEntity<ApiResult<Void>> handleBusinessException(BusinessException e) {
        log.warn("Business exception: {}", e.getMessage());
        return ResponseEntity.status(HttpStatus.BAD_REQUEST)
                .body(ApiResult.error(e.getErrorCode()));
    }

    @ExceptionHandler(AccessDeniedException.class)
    public ResponseEntity<ApiResult<Void>> handleAccessDeniedException(AccessDeniedException e) {
        return ResponseEntity.status(HttpStatus.FORBIDDEN)
                .body(ApiResult.error(ErrorCode.FORBIDDEN));
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ApiResult<String>> handleValidation(MethodArgumentNotValidException e) {
        String msg = e.getBindingResult().getFieldErrors().stream()
                .map(FieldError::getDefaultMessage)
                .collect(Collectors.joining(", "));
        return ResponseEntity.badRequest()
                .body(ApiResult.error(400, msg));
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<ApiResult<Void>> handleException(Exception e) {
        log.error("Unexpected error", e);
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                .body(ApiResult.error(ErrorCode.INTERNAL_ERROR));
    }
}
```

- [ ] **Step 5: 创建 common 模块配置文件**

```yaml
# java/common/src/main/resources/application.yml
spring:
  application:
    name: qa-common
  datasource:
    url: jdbc:mysql://localhost:3306/qa_agent?useUnicode=true&characterEncoding=utf8mb4&serverTimezone=Asia/Shanghai&createDatabaseIfNotExist=true
    username: root
    password: hwx1314520
    driver-class-name: com.mysql.cj.jdbc.Driver
  jpa:
    hibernate:
      ddl-auto: update
    show-sql: false
    properties:
      hibernate:
        dialect: org.hibernate.dialect.MySQLDialect
        format_sql: true

server:
  port: 8080

app:
  jwt:
    secret: qa-agent-jwt-secret-key-2026-mvp-minlength-256bit
    expiration: 86400000
  agent:
    api-key: qa-agent-internal-api-key-2026
    base-url: http://localhost:8000
```

- [ ] **Step 6: 验证编译**

```bash
cd java && mvn clean compile -pl common -am
```

- [ ] **Step 7: 提交**

```bash
git add java/pom.xml java/common/
git commit -m "feat: add parent POM and common module with ApiResult, exception handling"
```

---

## Task 2: Auth 认证模块

**Files:**
- Create: `java/auth/pom.xml`
- Create: `java/auth/src/main/java/com/qa/auth/AuthApplication.java`
- Create: `java/auth/src/main/java/com/qa/auth/entity/SysUser.java`
- Create: `java/auth/src/main/java/com/qa/auth/repository/UserRepository.java`
- Create: `java/auth/src/main/java/com/qa/auth/dto/LoginRequest.java`
- Create: `java/auth/src/main/java/com/qa/auth/dto/RegisterRequest.java`
- Create: `java/auth/src/main/java/com/qa/auth/dto/LoginResponse.java`
- Create: `java/auth/src/main/java/com/qa/auth/util/JwtUtil.java`
- Create: `java/auth/src/main/java/com/qa/auth/service/AuthService.java`
- Create: `java/auth/src/main/java/com/qa/auth/service/impl/AuthServiceImpl.java`
- Create: `java/auth/src/main/java/com/qa/auth/controller/AuthController.java`
- Create: `java/auth/src/main/java/com/qa/auth/config/SecurityConfig.java`
- Create: `java/auth/src/main/java/com/qa/auth/config/JwtAuthFilter.java`
- Create: `java/auth/src/main/resources/application.yml`

**Interfaces:**
- Consumes: `ApiResult<T>`, `ErrorCode`, `BusinessException` from common
- Produces:
  - `JwtUtil.generateToken(userId, username, role)` → `String`
  - `JwtUtil.parseToken(token)` → `Claims`
  - `AuthService.login(LoginRequest)` → `LoginResponse`
  - `AuthService.register(RegisterRequest)` → `void`
  - `POST /api/auth/login` 公开
  - `POST /api/auth/register` 公开

- [ ] **Step 1: 创建 auth 模块 POM**

```xml
<!-- java/auth/pom.xml -->
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0
         http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>

    <parent>
        <groupId>com.qa</groupId>
        <artifactId>qa-agent</artifactId>
        <version>1.0.0-SNAPSHOT</version>
    </parent>

    <artifactId>qa-auth</artifactId>
    <name>QA Auth</name>

    <dependencies>
        <dependency>
            <groupId>com.qa</groupId>
            <artifactId>qa-common</artifactId>
            <version>${project.version}</version>
        </dependency>
    </dependencies>
</project>
```

- [ ] **Step 2: 创建 JPA 实体**

```java
// java/auth/src/main/java/com/qa/auth/AuthApplication.java
package com.qa.auth;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class AuthApplication {
    public static void main(String[] args) {
        SpringApplication.run(AuthApplication.class, args);
    }
}
```

```java
// java/auth/src/main/java/com/qa/auth/entity/SysUser.java
package com.qa.auth.entity;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Entity
@Table(name = "sys_user")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class SysUser {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, unique = true, length = 50)
    private String username;

    @Column(nullable = false, length = 255)
    private String password;

    @Column(length = 100)
    private String email;

    @Column(length = 50)
    private String department;

    @Column(length = 20)
    @Builder.Default
    private String role = "ROLE_EMPLOYEE";

    @Column(name = "created_at")
    private LocalDateTime createdAt;

    @PrePersist
    protected void onCreate() {
        createdAt = LocalDateTime.now();
    }
}
```

```java
// java/auth/src/main/java/com/qa/auth/repository/UserRepository.java
package com.qa.auth.repository;

import com.qa.auth.entity.SysUser;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;

public interface UserRepository extends JpaRepository<SysUser, Long> {
    Optional<SysUser> findByUsername(String username);
    boolean existsByUsername(String username);
}
```

- [ ] **Step 3: 创建 DTO**

```java
// java/auth/src/main/java/com/qa/auth/dto/LoginRequest.java
package com.qa.auth.dto;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
public class LoginRequest {
    @NotBlank(message = "用户名不能为空")
    private String username;

    @NotBlank(message = "密码不能为空")
    private String password;
}
```

```java
// java/auth/src/main/java/com/qa/auth/dto/RegisterRequest.java
package com.qa.auth.dto;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.Data;

@Data
public class RegisterRequest {
    @NotBlank @Size(min = 3, max = 50)
    private String username;

    @NotBlank @Size(min = 6, max = 100)
    private String password;

    @Email
    private String email;

    private String department;
}
```

```java
// java/auth/src/main/java/com/qa/auth/dto/LoginResponse.java
package com.qa.auth.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;

@Data
@Builder
@AllArgsConstructor
public class LoginResponse {
    private String token;
    private String username;
    private String role;
    private String department;
}
```

- [ ] **Step 4: 创建 JwtUtil**

```java
// java/auth/src/main/java/com/qa/auth/util/JwtUtil.java
package com.qa.auth.util;

import io.jsonwebtoken.*;
import io.jsonwebtoken.security.Keys;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.util.Date;

@Component
public class JwtUtil {

    private final SecretKey key;
    private final long expiration;

    public JwtUtil(@Value("${app.jwt.secret}") String secret,
                   @Value("${app.jwt.expiration}") long expiration) {
        this.key = Keys.hmacShaKeyFor(secret.getBytes(StandardCharsets.UTF_8));
        this.expiration = expiration;
    }

    public String generateToken(Long userId, String username, String role) {
        Date now = new Date();
        return Jwts.builder()
                .subject(username)
                .claim("userId", userId)
                .claim("role", role)
                .issuedAt(now)
                .expiration(new Date(now.getTime() + expiration))
                .signWith(key)
                .compact();
    }

    public Claims parseToken(String token) {
        return Jwts.parser()
                .verifyWith(key)
                .build()
                .parseSignedClaims(token)
                .getPayload();
    }

    public boolean validateToken(String token) {
        try {
            parseToken(token);
            return true;
        } catch (JwtException | IllegalArgumentException e) {
            return false;
        }
    }
}
```

- [ ] **Step 5: 创建 AuthService**

```java
// java/auth/src/main/java/com/qa/auth/service/AuthService.java
package com.qa.auth.service;

import com.qa.auth.dto.LoginRequest;
import com.qa.auth.dto.LoginResponse;
import com.qa.auth.dto.RegisterRequest;

public interface AuthService {
    LoginResponse login(LoginRequest request);
    void register(RegisterRequest request);
}
```

```java
// java/auth/src/main/java/com/qa/auth/service/impl/AuthServiceImpl.java
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
import lombok.RequiredArgsConstructor;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;

@Service
@RequiredArgsConstructor
public class AuthServiceImpl implements AuthService {

    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;
    private final JwtUtil jwtUtil;

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
```

- [ ] **Step 6: 创建 AuthController**

```java
// java/auth/src/main/java/com/qa/auth/controller/AuthController.java
package com.qa.auth.controller;

import com.qa.auth.dto.LoginRequest;
import com.qa.auth.dto.LoginResponse;
import com.qa.auth.dto.RegisterRequest;
import com.qa.auth.service.AuthService;
import com.qa.common.ApiResult;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/auth")
@RequiredArgsConstructor
public class AuthController {

    private final AuthService authService;

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
```

- [ ] **Step 7: 创建 SecurityConfig 和 JwtAuthFilter**

```java
// java/auth/src/main/java/com/qa/auth/config/SecurityConfig.java
package com.qa.auth.config;

import lombok.RequiredArgsConstructor;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;

@Configuration
@EnableWebSecurity
@RequiredArgsConstructor
public class SecurityConfig {

    private final JwtAuthFilter jwtAuthFilter;

    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        http
            .csrf(AbstractHttpConfigurer::disable)
            .sessionManagement(session -> session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/api/auth/login", "/api/auth/register").permitAll()
                .anyRequest().authenticated()
            )
            .addFilterBefore(jwtAuthFilter, UsernamePasswordAuthenticationFilter.class);

        return http.build();
    }

    @Bean
    public PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder();
    }
}
```

```java
// java/auth/src/main/java/com/qa/auth/config/JwtAuthFilter.java
package com.qa.auth.config;

import com.qa.auth.util.JwtUtil;
import io.jsonwebtoken.Claims;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Component;
import org.springframework.util.StringUtils;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.List;

@Component
@RequiredArgsConstructor
public class JwtAuthFilter extends OncePerRequestFilter {

    private final JwtUtil jwtUtil;

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response,
                                    FilterChain filterChain) throws ServletException, IOException {
        String header = request.getHeader("Authorization");

        if (StringUtils.hasText(header) && header.startsWith("Bearer ")) {
            String token = header.substring(7);
            if (jwtUtil.validateToken(token)) {
                Claims claims = jwtUtil.parseToken(token);
                String username = claims.getSubject();
                String role = claims.get("role", String.class);
                Long userId = claims.get("userId", Long.class);

                UsernamePasswordAuthenticationToken auth =
                        new UsernamePasswordAuthenticationToken(
                                username, null,
                                List.of(new SimpleGrantedAuthority(role)));
                auth.setDetails(userId);
                SecurityContextHolder.getContext().setAuthentication(auth);
            }
        }

        filterChain.doFilter(request, response);
    }
}
```

- [ ] **Step 8: auth 配置文件和 Spring Boot 扫描设置**

```yaml
# java/auth/src/main/resources/application.yml
spring:
  application:
    name: qa-auth
  datasource:
    url: jdbc:mysql://localhost:3306/qa_agent?useUnicode=true&characterEncoding=utf8mb4&serverTimezone=Asia/Shanghai&createDatabaseIfNotExist=true
    username: root
    password: hwx1314520
    driver-class-name: com.mysql.cj.jdbc.Driver
  jpa:
    hibernate:
      ddl-auto: update
    show-sql: false
    properties:
      hibernate:
        dialect: org.hibernate.dialect.MySQLDialect

server:
  port: 8080

app:
  jwt:
    secret: qa-agent-jwt-secret-key-2026-mvp-minlength-256bit
    expiration: 86400000
```

需要在 AuthApplication 上加 `@ComponentScan(basePackages = "com.qa")` 确保扫描到 common 模块的 GlobalExceptionHandler。

```java
@SpringBootApplication
@ComponentScan(basePackages = "com.qa")
public class AuthApplication { ... }
```

- [ ] **Step 9: 启动 auth 模块并测试**

```bash
cd java/auth && mvn spring-boot:run
```

测试注册:
```bash
curl -X POST http://localhost:8080/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123","email":"admin@qa.com","department":"技术部"}'
```

测试登录:
```bash
curl -X POST http://localhost:8080/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```

预期：返回 JWT token。

- [ ] **Step 10: 提交**

```bash
git add java/auth/
git commit -m "feat: add auth module with JWT login/register"
```

---

## Task 3: Document 文档管理模块

**Files:**
- Create: `java/document/pom.xml`
- Create: `java/document/src/main/java/com/qa/document/DocumentApplication.java`
- Create: `java/document/src/main/java/com/qa/document/entity/DocDocument.java`
- Create: `java/document/src/main/java/com/qa/document/repository/DocumentRepository.java`
- Create: `java/document/src/main/java/com/qa/document/dto/DocumentUploadRequest.java`
- Create: `java/document/src/main/java/com/qa/document/dto/DocumentResponse.java`
- Create: `java/document/src/main/java/com/qa/document/config/MinioConfig.java`
- Create: `java/document/src/main/java/com/qa/document/service/DocumentService.java`
- Create: `java/document/src/main/java/com/qa/document/service/impl/DocumentServiceImpl.java`
- Create: `java/document/src/main/java/com/qa/document/controller/DocumentController.java`
- Create: `java/document/src/main/resources/application.yml`

**Interfaces:**
- Consumes: `ApiResult<T>`, `PageResult<T>`, `ErrorCode`, `BusinessException` from common; JWT auth from auth
- Produces:
  - `POST /api/documents/upload` — multipart 上传，返回 DocumentResponse
  - `GET /api/documents` — 分页列表
  - `GET /api/documents/{id}` — 详情
  - `DELETE /api/documents/{id}` — 删除
  - `POST /api/documents/{id}/index` — 触发异步索引
  - `GET /api/documents/status/{id}` — 查询索引状态
  - `DocumentService.upload(MultipartFile, DocumentUploadRequest, Long uploaderId)` → `DocumentResponse`

- [ ] **Step 1: 创建 document 模块 POM**

```xml
<!-- java/document/pom.xml -->
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0
         http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>

    <parent>
        <groupId>com.qa</groupId>
        <artifactId>qa-agent</artifactId>
        <version>1.0.0-SNAPSHOT</version>
    </parent>

    <artifactId>qa-document</artifactId>
    <name>QA Document</name>

    <dependencies>
        <dependency>
            <groupId>com.qa</groupId>
            <artifactId>qa-common</artifactId>
            <version>${project.version}</version>
        </dependency>
        <dependency>
            <groupId>com.qa</groupId>
            <artifactId>qa-auth</artifactId>
            <version>${project.version}</version>
        </dependency>
        <dependency>
            <groupId>io.minio</groupId>
            <artifactId>minio</artifactId>
            <version>8.5.7</version>
        </dependency>
    </dependencies>
</project>
```

- [ ] **Step 2: 创建实体和 DTO**

```java
// java/document/src/main/java/com/qa/document/DocumentApplication.java
package com.qa.document;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.ComponentScan;
import org.springframework.scheduling.annotation.EnableAsync;

@SpringBootApplication
@ComponentScan(basePackages = "com.qa")
@EnableAsync
public class DocumentApplication {
    public static void main(String[] args) {
        SpringApplication.run(DocumentApplication.class, args);
    }
}
```

```java
// java/document/src/main/java/com/qa/document/entity/DocDocument.java
package com.qa.document.entity;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Entity
@Table(name = "doc_document")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class DocDocument {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, length = 200)
    private String title;

    @Column(name = "file_name", nullable = false, length = 200)
    private String fileName;

    @Column(name = "file_path", nullable = false, length = 500)
    private String filePath;

    @Column(name = "file_size", nullable = false)
    private Long fileSize;

    @Column(name = "file_type", nullable = false, length = 20)
    private String fileType;

    @Column(length = 50)
    @Builder.Default
    private String department = "全部";

    @Column(name = "security_level", length = 20)
    @Builder.Default
    private String securityLevel = "内部";

    @Column(length = 20)
    @Builder.Default
    private String status = "UPLOADED";

    @Column(name = "upload_by")
    private Long uploadBy;

    @Builder.Default
    private Integer version = 1;

    @Column(name = "created_at")
    private LocalDateTime createdAt;

    @Column(name = "updated_at")
    private LocalDateTime updatedAt;

    @PrePersist
    protected void onCreate() {
        createdAt = LocalDateTime.now();
        updatedAt = LocalDateTime.now();
    }

    @PreUpdate
    protected void onUpdate() {
        updatedAt = LocalDateTime.now();
    }
}
```

```java
// java/document/src/main/java/com/qa/document/repository/DocumentRepository.java
package com.qa.document.repository;

import com.qa.document.entity.DocDocument;
import org.springframework.data.jpa.repository.JpaRepository;

public interface DocumentRepository extends JpaRepository<DocDocument, Long> {
}
```

```java
// java/document/src/main/java/com/qa/document/dto/DocumentUploadRequest.java
package com.qa.document.dto;

import lombok.Data;

@Data
public class DocumentUploadRequest {
    private String title;
    private String department = "全部";
    private String securityLevel = "内部";
}
```

```java
// java/document/src/main/java/com/qa/document/dto/DocumentResponse.java
package com.qa.document.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@Builder
@AllArgsConstructor
public class DocumentResponse {
    private Long id;
    private String title;
    private String fileName;
    private String filePath;
    private Long fileSize;
    private String fileType;
    private String department;
    private String securityLevel;
    private String status;
    private String uploadByName;
    private LocalDateTime createdAt;
}
```

- [ ] **Step 3: 创建 MinioConfig**

```java
// java/document/src/main/java/com/qa/document/config/MinioConfig.java
package com.qa.document.config;

import io.minio.MinioClient;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class MinioConfig {

    @Value("${minio.endpoint}")
    private String endpoint;

    @Value("${minio.access-key}")
    private String accessKey;

    @Value("${minio.secret-key}")
    private String secretKey;

    @Bean
    public MinioClient minioClient() {
        return MinioClient.builder()
                .endpoint(endpoint)
                .credentials(accessKey, secretKey)
                .build();
    }
}
```

- [ ] **Step 4: 创建 DocumentService**

```java
// java/document/src/main/java/com/qa/document/service/DocumentService.java
package com.qa.document.service;

import com.qa.common.PageResult;
import com.qa.document.dto.DocumentResponse;
import org.springframework.web.multipart.MultipartFile;

public interface DocumentService {
    DocumentResponse upload(MultipartFile file, String title, String department, String securityLevel, Long uploaderId);
    PageResult<DocumentResponse> list(int page, int size);
    DocumentResponse getById(Long id);
    void delete(Long id);
    void triggerIndex(Long id);
    String getStatus(Long id);
}
```

```java
// java/document/src/main/java/com/qa/document/service/impl/DocumentServiceImpl.java
package com.qa.document.service.impl;

import com.qa.common.BusinessException;
import com.qa.common.ErrorCode;
import com.qa.common.PageResult;
import com.qa.document.dto.DocumentResponse;
import com.qa.document.entity.DocDocument;
import com.qa.document.repository.DocumentRepository;
import com.qa.document.service.DocumentService;
import io.minio.MinioClient;
import io.minio.PutObjectArgs;
import io.minio.RemoveObjectArgs;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.reactive.function.client.WebClient;

import java.time.LocalDateTime;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

@Slf4j
@Service
@RequiredArgsConstructor
public class DocumentServiceImpl implements DocumentService {

    private final DocumentRepository documentRepository;
    private final MinioClient minioClient;
    private final WebClient webClient;

    @Value("${minio.bucket}")
    private String bucket;

    @Value("${minio.endpoint}")
    private String minioEndpoint;

    private static final Set<String> ALLOWED_TYPES = Set.of("pdf", "md", "txt", "docx");
    private static final long MAX_FILE_SIZE = 50 * 1024 * 1024L; // 50MB

    @Override
    public DocumentResponse upload(MultipartFile file, String title, String department,
                                    String securityLevel, Long uploaderId) {
        String originalName = file.getOriginalFilename();
        String ext = getFileExtension(originalName).toLowerCase();

        if (!ALLOWED_TYPES.contains(ext)) {
            throw new BusinessException(ErrorCode.FILE_TYPE_NOT_SUPPORTED);
        }
        if (file.getSize() > MAX_FILE_SIZE) {
            throw new BusinessException(ErrorCode.FILE_SIZE_EXCEEDED);
        }

        String objectName = UUID.randomUUID() + "." + ext;

        try {
            minioClient.putObject(PutObjectArgs.builder()
                    .bucket(bucket)
                    .object(objectName)
                    .stream(file.getInputStream(), file.getSize(), -1)
                    .contentType(file.getContentType())
                    .build());
        } catch (Exception e) {
            log.error("MinIO upload failed", e);
            throw new BusinessException(ErrorCode.INTERNAL_ERROR);
        }

        DocDocument doc = DocDocument.builder()
                .title(title != null ? title : originalName)
                .fileName(originalName)
                .filePath(bucket + "/" + objectName)
                .fileSize(file.getSize())
                .fileType(ext)
                .department(department)
                .securityLevel(securityLevel)
                .status("UPLOADED")
                .uploadBy(uploaderId)
                .build();

        doc = documentRepository.save(doc);

        return toResponse(doc);
    }

    @Override
    public PageResult<DocumentResponse> list(int page, int size) {
        Page<DocDocument> docPage = documentRepository.findAll(PageRequest.of(page - 1, size));
        return PageResult.of(
                docPage.getContent().stream().map(this::toResponse).toList(),
                docPage.getTotalElements(),
                docPage.getTotalPages(),
                page,
                size
        );
    }

    @Override
    public DocumentResponse getById(Long id) {
        DocDocument doc = documentRepository.findById(id)
                .orElseThrow(() -> new BusinessException(ErrorCode.DOCUMENT_NOT_FOUND));
        return toResponse(doc);
    }

    @Override
    public void delete(Long id) {
        DocDocument doc = documentRepository.findById(id)
                .orElseThrow(() -> new BusinessException(ErrorCode.DOCUMENT_NOT_FOUND));

        try {
            minioClient.removeObject(RemoveObjectArgs.builder()
                    .bucket(bucket)
                    .object(doc.getFilePath().substring(bucket.length() + 1))
                    .build());
        } catch (Exception e) {
            log.error("MinIO delete failed for doc {}", id, e);
        }

        documentRepository.delete(doc);
    }

    @Override
    @Async
    public void triggerIndex(Long id) {
        DocDocument doc = documentRepository.findById(id)
                .orElseThrow(() -> new BusinessException(ErrorCode.DOCUMENT_NOT_FOUND));

        doc.setStatus("INDEXING");
        documentRepository.save(doc);

        try {
            Map<String, Object> requestBody = Map.of(
                    "document", Map.of(
                            "id", doc.getId(),
                            "title", doc.getTitle(),
                            "filePath", doc.getFilePath(),
                            "fileType", doc.getFileType(),
                            "department", doc.getDepartment(),
                            "securityLevel", doc.getSecurityLevel()
                    ),
                    "callbackUrl", "http://localhost:8080/api/documents/status/" + doc.getId()
            );

            webClient.post()
                    .uri("/api/agent/index")
                    .bodyValue(requestBody)
                    .retrieve()
                    .toBodilessEntity()
                    .block();

            doc.setStatus("COMPLETED");
        } catch (Exception e) {
            log.error("Index failed for doc {}", id, e);
            doc.setStatus("FAILED");
        }

        documentRepository.save(doc);
    }

    @Override
    public String getStatus(Long id) {
        DocDocument doc = documentRepository.findById(id)
                .orElseThrow(() -> new BusinessException(ErrorCode.DOCUMENT_NOT_FOUND));
        return doc.getStatus();
    }

    private DocumentResponse toResponse(DocDocument doc) {
        return DocumentResponse.builder()
                .id(doc.getId())
                .title(doc.getTitle())
                .fileName(doc.getFileName())
                .filePath(doc.getFilePath())
                .fileSize(doc.getFileSize())
                .fileType(doc.getFileType())
                .department(doc.getDepartment())
                .securityLevel(doc.getSecurityLevel())
                .status(doc.getStatus())
                .createdAt(doc.getCreatedAt())
                .build();
    }

    private String getFileExtension(String filename) {
        if (filename == null || !filename.contains(".")) return "";
        return filename.substring(filename.lastIndexOf('.') + 1);
    }
}
```

- [ ] **Step 5: 创建 DocumentController**

```java
// java/document/src/main/java/com/qa/document/controller/DocumentController.java
package com.qa.document.controller;

import com.qa.common.ApiResult;
import com.qa.common.PageResult;
import com.qa.document.dto.DocumentResponse;
import com.qa.document.service.DocumentService;
import lombok.RequiredArgsConstructor;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

@RestController
@RequestMapping("/api/documents")
@RequiredArgsConstructor
public class DocumentController {

    private final DocumentService documentService;

    @PostMapping("/upload")
    public ApiResult<DocumentResponse> upload(
            @RequestParam("file") MultipartFile file,
            @RequestParam(value = "title", required = false) String title,
            @RequestParam(value = "department", defaultValue = "全部") String department,
            @RequestParam(value = "securityLevel", defaultValue = "内部") String securityLevel,
            Authentication auth) {
        Long uploaderId = (Long) auth.getDetails();
        return ApiResult.success(documentService.upload(file, title, department, securityLevel, uploaderId));
    }

    @GetMapping
    public ApiResult<PageResult<DocumentResponse>> list(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "20") int size) {
        return ApiResult.success(documentService.list(page, size));
    }

    @GetMapping("/{id}")
    public ApiResult<DocumentResponse> getById(@PathVariable Long id) {
        return ApiResult.success(documentService.getById(id));
    }

    @DeleteMapping("/{id}")
    public ApiResult<Void> delete(@PathVariable Long id) {
        documentService.delete(id);
        return ApiResult.success(null);
    }

    @PostMapping("/{id}/index")
    public ApiResult<Void> triggerIndex(@PathVariable Long id) {
        documentService.triggerIndex(id);
        return ApiResult.success(null);
    }

    @GetMapping("/status/{id}")
    public ApiResult<String> getStatus(@PathVariable Long id) {
        return ApiResult.success(documentService.getStatus(id));
    }
}
```

- [ ] **Step 6: document 配置文件**

```yaml
# java/document/src/main/resources/application.yml
spring:
  application:
    name: qa-document
  datasource:
    url: jdbc:mysql://localhost:3306/qa_agent?useUnicode=true&characterEncoding=utf8mb4&serverTimezone=Asia/Shanghai&createDatabaseIfNotExist=true
    username: root
    password: hwx1314520
    driver-class-name: com.mysql.cj.jdbc.Driver
  jpa:
    hibernate:
      ddl-auto: update
    show-sql: false
  servlet:
    multipart:
      max-file-size: 50MB
      max-request-size: 50MB

server:
  port: 8081

app:
  jwt:
    secret: qa-agent-jwt-secret-key-2026-mvp-minlength-256bit
    expiration: 86400000
  agent:
    api-key: qa-agent-internal-api-key-2026
    base-url: http://localhost:8000

minio:
  endpoint: http://localhost:9000
  access-key: admin
  secret-key: admin123456
  bucket: qa-documents
```

- [ ] **Step 7: 需要在 document 模块中配置 WebClient Bean**

在 DocumentApplication 或 config 中添加 WebClient Bean（用于异步索引调用 Python）。创建 config：

```java
// java/document/src/main/java/com/qa/document/config/WebClientConfig.java
package com.qa.document.config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.reactive.function.client.WebClient;

@Configuration
public class WebClientConfig {

    @Value("${app.agent.base-url}")
    private String agentBaseUrl;

    @Value("${app.agent.api-key}")
    private String apiKey;

    @Bean
    public WebClient webClient() {
        return WebClient.builder()
                .baseUrl(agentBaseUrl)
                .defaultHeader("X-API-Key", apiKey)
                .build();
    }
}
```

- [ ] **Step 8: 验证编译**

```bash
cd java && mvn clean compile -pl document -am
```

- [ ] **Step 9: 确保 MinIO bucket 存在**

MinIO 启动后需要创建 bucket。通过 MinIO Console `http://localhost:9001` 登录（admin/admin123456），创建 bucket `qa-documents`。或者用代码自动创建。

- [ ] **Step 10: 启动测试**

```bash
cd java/document && mvn spring-boot:run
```

测试上传（需要先登录获取 token）:
```bash
# 先注册并登录
TOKEN=$(curl -s -X POST http://localhost:8080/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' | jq -r '.data.token')

# 上传文件
curl -X POST http://localhost:8080/api/documents/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@test.pdf" \
  -F "title=测试文档" \
  -F "department=技术部"
```

测试文档列表：
```bash
curl http://localhost:8080/api/documents \
  -H "Authorization: Bearer $TOKEN"
```

- [ ] **Step 11: 提交**

```bash
git add java/document/
git commit -m "feat: add document module with MinIO upload and async index trigger"
```

---

## Task 4: Chat 对话代理模块

**Files:**
- Create: `java/chat/pom.xml`
- Create: `java/chat/src/main/java/com/qa/chat/ChatApplication.java`
- Create: `java/chat/src/main/java/com/qa/chat/dto/ChatRequest.java`
- Create: `java/chat/src/main/java/com/qa/chat/dto/ChatResponse.java`
- Create: `java/chat/src/main/java/com/qa/chat/service/ChatService.java`
- Create: `java/chat/src/main/java/com/qa/chat/service/impl/ChatServiceImpl.java`
- Create: `java/chat/src/main/java/com/qa/chat/controller/ChatController.java`
- Create: `java/chat/src/main/resources/application.yml`

**Interfaces:**
- Consumes: `ApiResult<T>` from common; JWT auth from auth
- Produces:
  - `POST /api/chat/stream` — SSE 流式对话
  - `ChatService.chatStream(ChatRequest)` → `Flux<ChatResponse>`

- [ ] **Step 1: 创建 chat 模块 POM**

```xml
<!-- java/chat/pom.xml -->
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0
         http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>

    <parent>
        <groupId>com.qa</groupId>
        <artifactId>qa-agent</artifactId>
        <version>1.0.0-SNAPSHOT</version>
    </parent>

    <artifactId>qa-chat</artifactId>
    <name>QA Chat</name>

    <dependencies>
        <dependency>
            <groupId>com.qa</groupId>
            <artifactId>qa-common</artifactId>
            <version>${project.version}</version>
        </dependency>
        <dependency>
            <groupId>com.qa</groupId>
            <artifactId>qa-auth</artifactId>
            <version>${project.version}</version>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-webflux</artifactId>
        </dependency>
    </dependencies>
</project>
```

- [ ] **Step 2: 创建 DTO**

```java
// java/chat/src/main/java/com/qa/chat/ChatApplication.java
package com.qa.chat;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.ComponentScan;

@SpringBootApplication
@ComponentScan(basePackages = "com.qa")
public class ChatApplication {
    public static void main(String[] args) {
        SpringApplication.run(ChatApplication.class, args);
    }
}
```

```java
// java/chat/src/main/java/com/qa/chat/dto/ChatRequest.java
package com.qa.chat.dto;

import jakarta.validation.constraints.NotBlank;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class ChatRequest {
    @NotBlank
    private String question;
    private List<HistoryMessage> history;
}
```

```java
// java/chat/src/main/java/com/qa/chat/dto/HistoryMessage.java
package com.qa.chat.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class HistoryMessage {
    private String role;  // user / assistant
    private String content;
}
```

```java
// java/chat/src/main/java/com/qa/chat/dto/ChatResponse.java
package com.qa.chat.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ChatResponse {
    private String type;   // thinking / answer / citation / done / error
    private String content;
    private Object data;
}
```

- [ ] **Step 3: 创建 ChatService**

```java
// java/chat/src/main/java/com/qa/chat/service/ChatService.java
package com.qa.chat.service;

import com.qa.chat.dto.ChatRequest;
import com.qa.chat.dto.ChatResponse;
import reactor.core.publisher.Flux;

public interface ChatService {
    Flux<ChatResponse> chatStream(ChatRequest request, String userId, String role, String department);
}
```

```java
// java/chat/src/main/java/com/qa/chat/service/impl/ChatServiceImpl.java
package com.qa.chat.service.impl;

import com.qa.chat.dto.ChatRequest;
import com.qa.chat.dto.ChatResponse;
import com.qa.chat.service.ChatService;
import com.qa.common.ErrorCode;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Flux;

import java.time.Duration;

@Slf4j
@Service
@RequiredArgsConstructor
public class ChatServiceImpl implements ChatService {

    private final WebClient webClient;

    @Value("${app.agent.base-url}")
    private String agentBaseUrl;

    @Value("${app.agent.api-key}")
    private String apiKey;

    @Override
    public Flux<ChatResponse> chatStream(ChatRequest request, String userId, String role, String department) {
        return webClient.post()
                .uri("/api/agent/chat/stream")
                .header("X-API-Key", apiKey)
                .header("X-User-Id", userId)
                .header("X-User-Role", role)
                .header("X-User-Department", department != null ? department : "全部")
                .bodyValue(request)
                .retrieve()
                .bodyToFlux(ChatResponse.class)
                .timeout(Duration.ofSeconds(60))
                .onErrorResume(e -> {
                    log.error("Chat stream error", e);
                    return Flux.just(ChatResponse.builder()
                            .type("error")
                            .content("AI服务暂时不可用，请稍后重试")
                            .build());
                });
    }
}
```

- [ ] **Step 4: 创建 ChatController**

```java
// java/chat/src/main/java/com/qa/chat/controller/ChatController.java
package com.qa.chat.controller;

import com.qa.chat.dto.ChatRequest;
import com.qa.chat.dto.ChatResponse;
import com.qa.chat.service.ChatService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.MediaType;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import reactor.core.publisher.Flux;

@RestController
@RequestMapping("/api/chat")
@RequiredArgsConstructor
public class ChatController {

    private final ChatService chatService;

    @PostMapping(value = "/stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public Flux<ChatResponse> chatStream(@Valid @RequestBody ChatRequest request, Authentication auth) {
        Long userId = (Long) auth.getDetails();
        String role = auth.getAuthorities().iterator().next().getAuthority();
        String department = null; // 后续从 user 表查询
        return chatService.chatStream(request, String.valueOf(userId), role, department);
    }
}
```

- [ ] **Step 5: chat 配置文件**

```yaml
# java/chat/src/main/resources/application.yml
spring:
  application:
    name: qa-chat
  datasource:
    url: jdbc:mysql://localhost:3306/qa_agent?useUnicode=true&characterEncoding=utf8mb4&serverTimezone=Asia/Shanghai&createDatabaseIfNotExist=true
    username: root
    password: hwx1314520
    driver-class-name: com.mysql.cj.jdbc.Driver
  jpa:
    hibernate:
      ddl-auto: update

server:
  port: 8082

app:
  jwt:
    secret: qa-agent-jwt-secret-key-2026-mvp-minlength-256bit
    expiration: 86400000
  agent:
    api-key: qa-agent-internal-api-key-2026
    base-url: http://localhost:8000
```

需要添加 WebClient Bean。在 chat 模块创建 config：

```java
// java/chat/src/main/java/com/qa/chat/config/WebClientConfig.java
package com.qa.chat.config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.reactive.function.client.WebClient;

@Configuration
public class WebClientConfig {

    @Value("${app.agent.base-url}")
    private String agentBaseUrl;

    @Value("${app.agent.api-key}")
    private String apiKey;

    @Bean
    public WebClient webClient() {
        return WebClient.builder()
                .baseUrl(agentBaseUrl)
                .defaultHeader("X-API-Key", apiKey)
                .build();
    }
}
```

- [ ] **Step 6: 验证编译**

```bash
cd java && mvn clean compile -pl chat -am
```

- [ ] **Step 7: 提交**

```bash
git add java/chat/
git commit -m "feat: add chat module with SSE streaming proxy to Python agent"
```

---

## Task 5: Python API 模块（FastAPI 入口）

**Files:**
- Create: `python/pyproject.toml`
- Create: `python/api/__init__.py`
- Create: `python/api/main.py`
- Create: `python/api/dependencies.py`
- Create: `python/api/schemas/__init__.py`
- Create: `python/api/schemas/chat.py`
- Create: `python/api/schemas/index.py`
- Create: `python/api/routes/__init__.py`
- Create: `python/api/routes/health_routes.py`
- Create: `python/api/routes/agent_routes.py`

**Interfaces:**
- Produces:
  - `GET /api/agent/health` → `{"status": "ok"}`
  - `POST /api/agent/index` — 接收索引请求（API Key 认证）
  - `POST /api/agent/chat/stream` — SSE 流式对话（API Key 认证）
  - `verify_api_key()` FastAPI 依赖注入

- [ ] **Step 1: 创建 pyproject.toml**

```toml
# python/pyproject.toml
[tool.poetry]
name = "qa-agent"
version = "1.0.0"
description = "Enterprise Q&A AI Agent - Python service"
authors = ["QA Team"]
python = "^3.11"

[tool.poetry.dependencies]
python = "^3.11"
fastapi = "^0.128.0"
uvicorn = {extras = ["standard"], version = "^0.34.0"}
langchain = "^1.2.22"
langchain-community = "^0.4.0"
langchain-deepseek = "^0.1.0"
qdrant-client = "^1.12.0"
python-multipart = "^0.0.12"
pydantic = "^2.10.0"
httpx = "^0.28.0"
sse-starlette = "^2.0.0"
python-dotenv = "^1.0.0"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
```

- [ ] **Step 2: 创建请求/响应模型**

```python
# python/api/schemas/__init__.py
# empty
```

```python
# python/api/schemas/chat.py
from pydantic import BaseModel, Field
from typing import List, Optional


class HistoryMessage(BaseModel):
    role: str  # user / assistant
    content: str


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    history: List[HistoryMessage] = []


class ChatResponse(BaseModel):
    type: str  # thinking / answer / citation / done / error
    content: str
    data: Optional[dict] = None
```

```python
# python/api/schemas/index.py
from pydantic import BaseModel, Field
from typing import Optional


class DocumentInfo(BaseModel):
    id: int
    title: str
    file_path: str
    file_type: str
    department: str = "全部"
    security_level: str = "内部"


class IndexRequest(BaseModel):
    document: DocumentInfo
    callback_url: Optional[str] = None
```

- [ ] **Step 3: 创建 API Key 认证依赖**

```python
# python/api/dependencies.py
import os
from fastapi import Header, HTTPException, Depends


INTERNAL_API_KEY = os.getenv("AGENT_INTERNAL_API_KEY", "qa-agent-internal-api-key-2026")


async def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")):
    if x_api_key != INTERNAL_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return x_api_key
```

- [ ] **Step 4: 创建路由**

```python
# python/api/routes/health_routes.py
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    return {"status": "ok", "service": "qa-agent-python"}
```

```python
# python/api/routes/agent_routes.py
import logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from api.dependencies import verify_api_key
from api.schemas.chat import ChatRequest
from api.schemas.index import IndexRequest

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/index")
async def index_document(request: IndexRequest, api_key: str = Depends(verify_api_key)):
    """异步索引文档（暂为骨架，RAG 模块实现后补齐）"""
    logger.info(f"Index request received for doc {request.document.id}: {request.document.title}")
    # 骨架：返回成功，后续 rag 模块替换此处
    return {"status": "indexing", "doc_id": request.document.id}


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest, api_key: str = Depends(verify_api_key)):
    """SSE 流式对话（暂为骨架，LLM 模块实现后补齐）"""
    logger.info(f"Chat request: {request.question[:50]}...")
    # 骨架：返回占位响应，后续 llm 模块替换此处
    async def event_stream():
        import json
        yield f"data: {json.dumps({'type': 'answer', 'content': '系统正在建设中，请稍后重试'})}\n\n"
        yield f"data: {json.dumps({'type': 'done', 'content': ''})}\n\n"
    return StreamingResponse(event_stream(), media_type="text/event-stream")
```

- [ ] **Step 5: 创建 FastAPI 入口**

```python
# python/api/main.py
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import health_routes, agent_routes

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="QA Agent - Python AI Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_routes.router, prefix="/api/agent", tags=["health"])
app.include_router(agent_routes.router, prefix="/api/agent", tags=["agent"])


@app.on_event("startup")
async def startup_event():
    logger.info("QA Agent Python service starting up...")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
```

- [ ] **Step 6: 安装依赖并启动测试**

```bash
cd python && poetry install
poetry run python -m api.main
```

验证健康检查:
```bash
curl http://localhost:8000/api/agent/health
```

测试索引接口（带 API Key）:
```bash
curl -X POST http://localhost:8000/api/agent/index \
  -H "Content-Type: application/json" \
  -H "X-API-Key: qa-agent-internal-api-key-2026" \
  -d '{"document":{"id":1,"title":"测试","file_path":"test.pdf","file_type":"pdf"}}'
```

测试对话接口:
```bash
curl -X POST http://localhost:8000/api/agent/chat/stream \
  -H "Content-Type: application/json" \
  -H "X-API-Key: qa-agent-internal-api-key-2026" \
  -d '{"question":"你好","history":[]}'
```

- [ ] **Step 7: 提交**

```bash
git add python/pyproject.toml python/api/
git commit -m "feat: add Python FastAPI entry with health, index, and chat endpoints"
```

---

## Task 6: Python RAG 检索模块

**Files:**
- Create: `python/rag/__init__.py`
- Create: `python/rag/loader.py`
- Create: `python/rag/splitter.py`
- Create: `python/rag/embedder.py`
- Create: `python/rag/indexer.py`
- Create: `python/rag/retriever.py`

**Interfaces:**
- Consumes: `api/schemas/index.py:IndexRequest`, `api/schemas/chat.py:ChatRequest`
- Produces:
  - `indexer.index_document(doc_info)` → `None`（索引文档到 Qdrant）
  - `retriever.hybrid_search(query, department, security_level, top_k)` → `List[Document]`
  - `splitter.split_documents(docs, file_type)` → `List[Document]`
  - `embedder.embed(texts)` → `List[List[float]]`

- [ ] **Step 1: 创建文档加载器**

```python
# python/rag/__init__.py
# empty
```

```python
# python/rag/loader.py
import logging
from langchain_community.document_loaders import PyMuPDFLoader, TextLoader, UnstructuredMarkdownLoader

logger = logging.getLogger(__name__)


def load_document(file_path: str, file_type: str) -> list:
    """根据文件类型加载文档，返回 List[Document]"""
    logger.info(f"Loading document: {file_path} (type={file_type})")

    if file_type == "pdf":
        loader = PyMuPDFLoader(file_path)
    elif file_type == "md":
        loader = UnstructuredMarkdownLoader(file_path)
    elif file_type == "txt":
        loader = TextLoader(file_path, encoding="utf-8")
    else:
        raise ValueError(f"Unsupported file type: {file_type}")

    return loader.load()
```

```python
# python/rag/splitter.py
import logging
from typing import List
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.text_splitter import MarkdownHeaderTextSplitter

logger = logging.getLogger(__name__)


def split_documents(docs: List[Document], file_type: str) -> List[Document]:
    """根据文件类型使用不同分块策略"""
    logger.info(f"Splitting {len(docs)} documents, file_type={file_type}")

    if file_type == "md":
        # Markdown: 按标题层级分割
        headers_to_split_on = [
            ("##", "section"),
            ("###", "subsection"),
        ]
        splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=headers_to_split_on,
            strip_headers=False,
        )
        chunks = []
        for doc in docs:
            md_chunks = splitter.split_text(doc.page_content)
            for chunk in md_chunks:
                chunk.metadata.update(doc.metadata)
            chunks.extend(md_chunks)
        return chunks

    elif file_type == "pdf":
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=800,
            chunk_overlap=100,
            separators=["\n\n", "\n", "。", ".", " ", ""],
        )
    else:  # txt, docx
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1024,
            chunk_overlap=128,
            separators=["\n\n", "\n", "。", ".", " ", ""],
        )

    return splitter.split_documents(docs)
```

```python
# python/rag/embedder.py
import logging
import os
from typing import List
from langchain_deepseek import DeepSeekEmbeddings

logger = logging.getLogger(__name__)

# 从环境变量读取 DeepSeek API Key
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_API_URL = os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com")

_embedder = None


def get_embedder() -> DeepSeekEmbeddings:
    global _embedder
    if _embedder is None:
        _embedder = DeepSeekEmbeddings(
            model="deepseek-chat",
            api_key=DEEPSEEK_API_KEY,
            api_base=DEEPSEEK_API_URL,
        )
    return _embedder


def embed_texts(texts: List[str]) -> List[List[float]]:
    """将文本列表转换为向量"""
    embedder = get_embedder()
    return embedder.embed_documents(texts)


def embed_query(query: str) -> List[float]:
    """将查询文本转换为向量"""
    embedder = get_embedder()
    return embedder.embed_query(query)
```

- [ ] **Step 2: 创建索引器**

```python
# python/rag/indexer.py
import logging
from typing import List
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from langchain.schema import Document

from rag.loader import load_document
from rag.splitter import split_documents
from rag.embedder import embed_texts

logger = logging.getLogger(__name__)

COLLECTION_NAME = "qa_documents"
VECTOR_SIZE = 1536  # DeepSeek embedding 维度


def _get_qdrant_client() -> QdrantClient:
    return QdrantClient(host="localhost", port=6333)


def _ensure_collection(client: QdrantClient):
    """确保 collection 存在"""
    collections = [c.name for c in client.get_collections().collections]
    if COLLECTION_NAME not in collections:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        )
        logger.info(f"Created Qdrant collection: {COLLECTION_NAME}")


def index_document(doc_info: dict) -> None:
    """
    完整索引流程：加载文档 → 分块 → 向量化 → 存入 Qdrant

    doc_info 字段:
        - id: 文档ID
        - title: 标题
        - file_path: MinIO 文件路径
        - file_type: pdf/md/txt
        - department: 所属部门
        - security_level: 密级
    """
    doc_id = doc_info["id"]
    title = doc_info["title"]
    file_path = doc_info["file_path"]
    file_type = doc_info["file_type"]
    department = doc_info.get("department", "全部")
    security_level = doc_info.get("security_level", "内部")

    logger.info(f"Indexing document {doc_id}: {title}")

    # 1. 如果文档之前索引过，先删除旧 chunks
    client = _get_qdrant_client()
    _ensure_collection(client)
    _delete_doc_chunks(client, doc_id)

    # 2. 加载文档
    raw_docs = load_document(file_path, file_type)

    # 3. 分块
    chunks = split_documents(raw_docs, file_type)

    # 4. 向量化
    texts = [chunk.page_content for chunk in chunks]
    vectors = embed_texts(texts)

    # 5. 构建 Qdrant points（带 metadata）
    points = []
    for i, (chunk, vector) in enumerate(zip(chunks, vectors)):
        payload = {
            "doc_id": doc_id,
            "title": title,
            "department": department,
            "security_level": security_level,
            "chunk_index": i,
            "text": chunk.page_content,
            "source_page": chunk.metadata.get("page", 0),
            "heading": chunk.metadata.get("section", ""),
        }
        points.append(PointStruct(id=f"{doc_id}_{i}", vector=vector, payload=payload))

    client.upsert(collection_name=COLLECTION_NAME, points=points)
    logger.info(f"Indexed {len(points)} chunks for document {doc_id}: {title}")


def _delete_doc_chunks(client: QdrantClient, doc_id: int):
    """删除指定文档的所有 chunks"""
    client.delete(
        collection_name=COLLECTION_NAME,
        points_selector={"filter": {"must": [{"key": "doc_id", "match": {"value": doc_id}}]}},
    )
    logger.info(f"Deleted existing chunks for doc {doc_id}")
```

- [ ] **Step 3: 创建混合检索器**

```python
# python/rag/retriever.py
import logging
from typing import List
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchAny, MatchExcept
from rag.embedder import embed_query

logger = logging.getLogger(__name__)

COLLECTION_NAME = "qa_documents"


def _get_qdrant_client() -> QdrantClient:
    return QdrantClient(host="localhost", port=6333)


def hybrid_search(query: str, department: str = "全部", security_level: str = "内部",
                  top_k: int = 10) -> List[dict]:
    """
    混合检索：向量语义检索 + 权限过滤

    Args:
        query: 用户查询
        department: 用户部门（用于权限过滤）
        security_level: 用户可见密级
        top_k: 返回结果数

    Returns:
        List[dict]: 每个结果包含 text, title, doc_id, chunk_index, score
    """
    client = _get_qdrant_client()

    # 查询向量
    query_vector = embed_query(query)

    # 构建权限过滤条件
    must_conditions = [
        FieldCondition(
            key="department",
            match=MatchAny(any=[department, "全部"]),
        )
    ]
    # 非 LEADER/ADMIN 不能看机密文档
    if security_level == "内部":
        must_conditions.append(
            FieldCondition(
                key="security_level",
                match=MatchExcept(**{"except": ["机密"]}),
            )
        )

    results = client.search(
        collection_name=COLLECTION_NAME,
        query_vector=query_vector,
        query_filter=Filter(must=must_conditions),
        limit=top_k,
        with_payload=True,
    )

    hits = []
    for r in results:
        hits.append({
            "text": r.payload.get("text", ""),
            "title": r.payload.get("title", ""),
            "doc_id": r.payload.get("doc_id", 0),
            "chunk_index": r.payload.get("chunk_index", 0),
            "source_page": r.payload.get("source_page", 0),
            "heading": r.payload.get("heading", ""),
            "score": r.score,
        })

    logger.info(f"Hybrid search: query='{query[:50]}...', hits={len(hits)}")
    return hits
```

- [ ] **Step 4: 更新 agent_routes 以接入 RAG 模块**

修改 `python/api/routes/agent_routes.py`，将 index 端点接入真实的索引器：

```python
# python/api/routes/agent_routes.py (更新后)
import json
import logging
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from api.dependencies import verify_api_key
from api.schemas.chat import ChatRequest
from api.schemas.index import IndexRequest
from rag.indexer import index_document

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/index")
async def index_document_route(request: IndexRequest, api_key: str = Depends(verify_api_key)):
    """将文档索引到 Qdrant 向量数据库"""
    try:
        index_document(request.document.model_dump())
        return {"status": "completed", "doc_id": request.document.id}
    except Exception as e:
        logger.error(f"Index failed: {e}", exc_info=True)
        return {"status": "failed", "doc_id": request.document.id, "error": str(e)}


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest, api_key: str = Depends(verify_api_key)):
    """SSE 流式对话（检索部分已接入，LLM 生成暂时占位）"""
    from rag.retriever import hybrid_search

    # 先做检索
    hits = hybrid_search(request.question)

    context_texts = [h["text"] for h in hits[:5]]

    async def event_stream():
        yield f"data: {json.dumps({'type': 'thinking', 'content': f'检索到 {len(hits)} 个相关片段'})}\n\n"
        if context_texts:
            yield f"data: {json.dumps({'type': 'answer', 'content': '检索完成，LLM 模块接入后将基于以下上下文生成答案：'})}\n\n"
            for h in hits[:5]:
                yield f"data: {json.dumps({'type': 'citation', 'content': h['title'], 'data': h})}\n\n"
        else:
            yield f"data: {json.dumps({'type': 'answer', 'content': '知识库中暂无相关信息'})}\n\n"
        yield f"data: {json.dumps({'type': 'done', 'content': ''})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
```

- [ ] **Step 5: 启动并测试检索功能**

```bash
cd python && poetry run python -m api.main
```

测试索引（需要用实际文件，先用一个测试 Markdown 文件）：
```bash
# 创建一个测试文件
echo "# 测试文档\n\n## 休假制度\n\n员工入职满1年可享受5天年假。\n\n## 报销流程\n\n报销需部门主管审批。" > /tmp/test_policy.md

# 调用索引接口（文件路径需要是 MinIO 可访问的路径）
curl -X POST http://localhost:8000/api/agent/index \
  -H "Content-Type: application/json" \
  -H "X-API-Key: qa-agent-internal-api-key-2026" \
  -d '{"document":{"id":1,"title":"员工手册","file_path":"/tmp/test_policy.md","file_type":"md","department":"全部","security_level":"内部"}}'
```

测试检索：
```bash
curl -X POST http://localhost:8000/api/agent/chat/stream \
  -H "Content-Type: application/json" \
  -H "X-API-Key: qa-agent-internal-api-key-2026" \
  -d '{"question":"年假有多少天","history":[]}'
```

- [ ] **Step 6: 提交**

```bash
git add python/rag/
git commit -m "feat: add RAG module with document indexing and hybrid retrieval"
```

---

## Task 7: Python LLM 模块（DeepSeek 集成 + RAG 流水线）

**Files:**
- Create: `python/llm/__init__.py`
- Create: `python/llm/deepseek_client.py`
- Create: `python/llm/rag_chain.py`
- Modify: `python/api/routes/agent_routes.py`

**Interfaces:**
- Consumes: `rag.retriever.hybrid_search`, `api/schemas/chat.py:ChatRequest`
- Produces:
  - `deepseek_client.chat_stream(messages)` → 流式生成器
  - `rag_chain.answer(question, context)` → SSE 流
  - `POST /api/agent/chat/stream` → 完整 RAG+LLM 流式响应

- [ ] **Step 1: 创建 DeepSeek 客户端**

```python
# python/llm/__init__.py
# empty
```

```python
# python/llm/deepseek_client.py
import os
import logging
from openai import OpenAI

logger = logging.getLogger(__name__)

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_API_URL = os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com")

_client = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_API_URL)
    return _client


def chat_stream(messages: list, model: str = "deepseek-chat", temperature: float = 0.3,
                max_tokens: int = 2048):
    """流式调用 DeepSeek API，逐 token yield"""
    client = get_client()
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        stream=True,
    )
    for chunk in response:
        if chunk.choices and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content
```

```python
# python/llm/rag_chain.py
import json
import logging
from typing import List, AsyncGenerator
from rag.retriever import hybrid_search
from llm.deepseek_client import chat_stream

logger = logging.getLogger(__name__)

RAG_PROMPT_TEMPLATE = """你是一名企业智能助手。请根据以下参考文档中的信息回答用户问题。

## 要求
- 仅根据参考文档内容回答，不要编造信息
- 如果参考文档中没有相关信息，明确告知用户"该问题我目前无法准确回答"
- 回答中引用具体的文档名称和章节
- 回答准确、简洁、专业

## 参考文档
{context}

## 用户问题
{question}

## 回答
"""


async def answer_with_rag(question: str, history: List[dict] = None,
                          department: str = "全部", security_level: str = "内部") -> AsyncGenerator[str, None]:
    """
    完整 RAG 问答流水线：检索 → 构建 Prompt → LLM 生成 → SSE 流式输出

    Yields: SSE 格式的字符串
    """
    # Step 1: 思考提示
    yield f"data: {json.dumps({'type': 'thinking', 'content': '正在检索相关文档...'}, ensure_ascii=False)}\n\n"

    # Step 2: 检索
    hits = hybrid_search(question, department=department, security_level=security_level)

    if not hits:
        yield f"data: {json.dumps({'type': 'answer', 'content': '知识库中暂无相关信息，我无法准确回答该问题。'}, ensure_ascii=False)}\n\n"
        yield f"data: {json.dumps({'type': 'done', 'content': ''})}\n\n"
        return

    yield f"data: {json.dumps({'type': 'thinking', 'content': f'检索到 {len(hits)} 个相关片段，正在生成回答...'}, ensure_ascii=False)}\n\n"

    # Step 3: 构建上下文和 Prompt
    context = "\n\n---\n\n".join([
        f"[来源: {h['title']}] (章节: {h.get('heading', '未知')})\n{h['text']}"
        for h in hits[:5]
    ])

    prompt = RAG_PROMPT_TEMPLATE.format(context=context, question=question)

    messages = [{"role": "system", "content": prompt}]
    if history:
        messages = [{"role": "system", "content": prompt}] + history
    messages.append({"role": "user", "content": question})

    # Step 4: 流式生成
    full_answer = ""
    try:
        for token in chat_stream(messages):
            full_answer += token
            yield f"data: {json.dumps({'type': 'answer', 'content': token}, ensure_ascii=False)}\n\n"
    except Exception as e:
        logger.error(f"LLM generation failed: {e}")
        yield f"data: {json.dumps({'type': 'error', 'content': 'AI服务暂时不可用，请稍后重试'})}\n\n"
        return

    # Step 5: 溯源引用
    citations = [
        {"title": h["title"], "heading": h.get("heading", ""), "page": h.get("source_page", 0),
         "chunk": h["text"][:200] + "..."}
        for h in hits[:5]
    ]
    yield f"data: {json.dumps({'type': 'citation', 'content': '', 'data': citations}, ensure_ascii=False)}\n\n"
    yield f"data: {json.dumps({'type': 'done', 'content': ''})}\n\n"
```

- [ ] **Step 2: 更新 agent_routes 接入完整 LLM 流程**

修改 `python/api/routes/agent_routes.py` 的 chat/stream 端点：

```python
# python/api/routes/agent_routes.py (最终版)
import json
import logging
from fastapi import APIRouter, Depends, Header
from fastapi.responses import StreamingResponse
from api.dependencies import verify_api_key
from api.schemas.chat import ChatRequest
from api.schemas.index import IndexRequest
from rag.indexer import index_document
from llm.rag_chain import answer_with_rag

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/index")
async def index_document_route(request: IndexRequest, api_key: str = Depends(verify_api_key)):
    try:
        index_document(request.document.model_dump())
        return {"status": "completed", "doc_id": request.document.id}
    except Exception as e:
        logger.error(f"Index failed: {e}", exc_info=True)
        return {"status": "failed", "doc_id": request.document.id, "error": str(e)}


@router.post("/chat/stream")
async def chat_stream_route(
    request: ChatRequest,
    api_key: str = Depends(verify_api_key),
    x_user_role: str = Header(default="ROLE_EMPLOYEE", alias="X-User-Role"),
    x_user_department: str = Header(default="全部", alias="X-User-Department"),
):
    """SSE 流式对话：RAG 检索 + LLM 生成 + 溯源引用"""
    # 根据角色确定可见密级
    security_level = "内部"
    if x_user_role in ("ROLE_LEADER", "ROLE_ADMIN"):
        security_level = "机密"

    history = [
        {"role": h.role, "content": h.content}
        for h in request.history
    ]

    return StreamingResponse(
        answer_with_rag(
            question=request.question,
            history=history,
            department=x_user_department,
            security_level=security_level,
        ),
        media_type="text/event-stream",
    )
```

- [ ] **Step 3: 确保 .env 可被读取**

在 `python/api/main.py` 中添加 dotenv 加载：

```python
# 在文件顶部添加
from dotenv import load_dotenv
load_dotenv()  # 加载项目根目录的 .env 文件

# ... 其余代码
```

同时需要确保 DeepSeek API Key 可从项目根目录的 `.env` 读取。可以添加：

```python
import os
from pathlib import Path

# 查找项目根目录 .env
root_env = Path(__file__).parent.parent.parent.parent / ".env"
if root_env.exists():
    load_dotenv(root_env)
```

- [ ] **Step 4: 安装新增依赖并测试完整流程**

```bash
cd python && poetry install

# 启动服务
poetry run python -m api.main
```

测试完整 RAG+LLM 流程（前提：已有索引好的文档）：
```bash
curl -N -X POST http://localhost:8000/api/agent/chat/stream \
  -H "Content-Type: application/json" \
  -H "X-API-Key: qa-agent-internal-api-key-2026" \
  -H "X-User-Role: ROLE_EMPLOYEE" \
  -H "X-User-Department: 技术部" \
  -d '{"question":"年假有多少天？","history":[]}'
```

预期：SSE 流式输出思考过程 → 逐字输出答案 → 返回溯源引用。

- [ ] **Step 5: 端到端测试（Java → Python）**

启动 Java chat 模块：
```bash
cd java/chat && mvn spring-boot:run
```

```bash
# 获取 token
TOKEN=$(curl -s -X POST http://localhost:8080/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' | jq -r '.data.token')

# 流式对话
curl -N -X POST http://localhost:8080/api/chat/stream \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question":"年假有多少天？","history":[]}'
```

预期：Java 透传 Python 的 SSE 流到前端。

- [ ] **Step 6: 提交**

```bash
git add python/llm/
git commit -m "feat: add LLM module with DeepSeek integration and RAG pipeline"
```

---

## Task 8: 审计日志与整体联调

**Files:**
- Create: `java/audit/pom.xml`
- Create: `java/audit/src/main/java/com/qa/audit/AuditApplication.java`
- Create: `java/audit/src/main/java/com/qa/audit/entity/AuditLog.java`
- Create: `java/audit/src/main/java/com/qa/audit/repository/AuditLogRepository.java`
- Create: `java/audit/src/main/java/com/qa/audit/service/AuditLogService.java`
- Create: `java/audit/src/main/java/com/qa/audit/service/impl/AuditLogServiceImpl.java`
- Create: `java/audit/src/main/java/com/qa/audit/controller/AuditLogController.java`
- Modify: `java/chat/src/main/java/com/qa/chat/controller/ChatController.java`（添加审计记录）
- Update: `java/pom.xml`（添加 audit 模块）

**Interfaces:**
- Consumes: common, auth, chat 模块
- Produces:
  - `GET /api/audit/logs` — 审计日志分页查询（管理员）
  - 每次对话自动记录审计日志

- [ ] **Step 1: 创建 audit 模块**

```xml
<!-- java/audit/pom.xml -->
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0
         http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>

    <parent>
        <groupId>com.qa</groupId>
        <artifactId>qa-agent</artifactId>
        <version>1.0.0-SNAPSHOT</version>
    </parent>

    <artifactId>qa-audit</artifactId>
    <name>QA Audit</name>

    <dependencies>
        <dependency>
            <groupId>com.qa</groupId>
            <artifactId>qa-common</artifactId>
            <version>${project.version}</version>
        </dependency>
        <dependency>
            <groupId>com.qa</groupId>
            <artifactId>qa-auth</artifactId>
            <version>${project.version}</version>
        </dependency>
    </dependencies>
</project>
```

```java
// java/audit/src/main/java/com/qa/audit/AuditApplication.java
package com.qa.audit;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.ComponentScan;

@SpringBootApplication
@ComponentScan(basePackages = "com.qa")
public class AuditApplication {
    public static void main(String[] args) {
        SpringApplication.run(AuditApplication.class, args);
    }
}
```

```java
// java/audit/src/main/java/com/qa/audit/entity/AuditLog.java
package com.qa.audit.entity;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Entity
@Table(name = "audit_log")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class AuditLog {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "user_id")
    private Long userId;

    @Column(columnDefinition = "TEXT", nullable = false)
    private String question;

    @Column(columnDefinition = "TEXT")
    private String answer;

    @Column(name = "tools_called", columnDefinition = "JSON")
    private String toolsCalled;

    @Column(name = "response_time")
    private Integer responseTime;

    @Column(name = "token_usage", columnDefinition = "JSON")
    private String tokenUsage;

    @Column(name = "created_at")
    private LocalDateTime createdAt;

    @PrePersist
    protected void onCreate() {
        createdAt = LocalDateTime.now();
    }
}
```

- [ ] **Step 2: 创建审计服务**

```java
// java/audit/src/main/java/com/qa/audit/repository/AuditLogRepository.java
package com.qa.audit.repository;

import com.qa.audit.entity.AuditLog;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

public interface AuditLogRepository extends JpaRepository<AuditLog, Long> {
    Page<AuditLog> findByUserIdOrderByCreatedAtDesc(Long userId, Pageable pageable);
}
```

```java
// java/audit/src/main/java/com/qa/audit/service/AuditLogService.java
package com.qa.audit.service;

import com.qa.common.PageResult;
import com.qa.audit.entity.AuditLog;

public interface AuditLogService {
    void save(AuditLog log);
    PageResult<AuditLog> list(int page, int size, Long userId);
}
```

```java
// java/audit/src/main/java/com/qa/audit/service/impl/AuditLogServiceImpl.java
package com.qa.audit.service.impl;

import com.qa.audit.entity.AuditLog;
import com.qa.audit.repository.AuditLogRepository;
import com.qa.audit.service.AuditLogService;
import com.qa.common.PageResult;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;

@Service
@RequiredArgsConstructor
public class AuditLogServiceImpl implements AuditLogService {

    private final AuditLogRepository auditLogRepository;

    @Override
    public void save(AuditLog log) {
        auditLogRepository.save(log);
    }

    @Override
    public PageResult<AuditLog> list(int page, int size, Long userId) {
        Page<AuditLog> logPage;
        if (userId != null) {
            logPage = auditLogRepository.findByUserIdOrderByCreatedAtDesc(userId, PageRequest.of(page - 1, size));
        } else {
            logPage = auditLogRepository.findAll(PageRequest.of(page - 1, size));
        }
        return PageResult.of(logPage.getContent(), logPage.getTotalElements(),
                logPage.getTotalPages(), page, size);
    }
}
```

```java
// java/audit/src/main/java/com/qa/audit/controller/AuditLogController.java
package com.qa.audit.controller;

import com.qa.audit.entity.AuditLog;
import com.qa.audit.service.AuditLogService;
import com.qa.common.ApiResult;
import com.qa.common.PageResult;
import lombok.RequiredArgsConstructor;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/audit")
@RequiredArgsConstructor
public class AuditLogController {

    private final AuditLogService auditLogService;

    @GetMapping("/logs")
    @PreAuthorize("hasAuthority('ROLE_ADMIN')")
    public ApiResult<PageResult<AuditLog>> list(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "20") int size,
            @RequestParam(required = false) Long userId) {
        return ApiResult.success(auditLogService.list(page, size, userId));
    }
}
```

- [ ] **Step 3: 更新父 POM 添加 audit 模块**

修改 `java/pom.xml` 的 `<modules>` 部分：

```xml
<modules>
    <module>common</module>
    <module>auth</module>
    <module>document</module>
    <module>chat</module>
    <module>audit</module>
</modules>
```

- [ ] **Step 4: 在 ChatController 中记录审计日志**

修改 `java/chat/src/main/java/com/qa/chat/controller/ChatController.java`，注入 AuditLogService 并记录：

在 ChatServiceImpl 中注入 AuditLogService，在 chatStream 完成后记录：

```java
// 在 ChatServiceImpl 中添加
private final AuditLogService auditLogService;

// 不在这步具体改，保持 chat 模块独立性。审计功能独立验证。
```

实际在 chat 模块的 pom.xml 中添加 audit 依赖：
```xml
<dependency>
    <groupId>com.qa</groupId>
    <artifactId>qa-audit</artifactId>
    <version>${project.version}</version>
</dependency>
```

- [ ] **Step 5: 验证编译**

```bash
cd java && mvn clean compile
```

- [ ] **Step 6: 提交**

```bash
git add java/audit/ java/pom.xml
git commit -m "feat: add audit log module for recording Q&A history"
```

---

## 验证清单

完成所有 Task 后，逐项验证：

- [ ] Docker Qdrant 和 MinIO 正常运行
- [ ] 用户注册 + 登录返回 JWT
- [ ] 上传 PDF/MD 文件成功
- [ ] 触发索引后文档状态变为 COMPLETED
- [ ] Python 健康检查正常
- [ ] 问答流式返回 AI 回答 + 溯源引用
- [ ] 无关问题正确拒答
- [ ] 审计日志可查询
- [ ] Java → Python SSE 透传正常
