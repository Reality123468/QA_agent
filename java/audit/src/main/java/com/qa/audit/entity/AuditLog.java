package com.qa.audit.entity;

import jakarta.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "audit_log")
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

    public AuditLog() {
    }

    public AuditLog(Long id, Long userId, String question, String answer,
                    String toolsCalled, Integer responseTime, String tokenUsage,
                    LocalDateTime createdAt) {
        this.id = id;
        this.userId = userId;
        this.question = question;
        this.answer = answer;
        this.toolsCalled = toolsCalled;
        this.responseTime = responseTime;
        this.tokenUsage = tokenUsage;
        this.createdAt = createdAt;
    }

    @PrePersist
    protected void onCreate() {
        if (this.createdAt == null) {
            this.createdAt = LocalDateTime.now();
        }
    }

    // --- Getters and Setters ---

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public Long getUserId() {
        return userId;
    }

    public void setUserId(Long userId) {
        this.userId = userId;
    }

    public String getQuestion() {
        return question;
    }

    public void setQuestion(String question) {
        this.question = question;
    }

    public String getAnswer() {
        return answer;
    }

    public void setAnswer(String answer) {
        this.answer = answer;
    }

    public String getToolsCalled() {
        return toolsCalled;
    }

    public void setToolsCalled(String toolsCalled) {
        this.toolsCalled = toolsCalled;
    }

    public Integer getResponseTime() {
        return responseTime;
    }

    public void setResponseTime(Integer responseTime) {
        this.responseTime = responseTime;
    }

    public String getTokenUsage() {
        return tokenUsage;
    }

    public void setTokenUsage(String tokenUsage) {
        this.tokenUsage = tokenUsage;
    }

    public LocalDateTime getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(LocalDateTime createdAt) {
        this.createdAt = createdAt;
    }

    // --- Builder ---

    public static Builder builder() {
        return new Builder();
    }

    public static class Builder {
        private Long id;
        private Long userId;
        private String question;
        private String answer;
        private String toolsCalled;
        private Integer responseTime;
        private String tokenUsage;
        private LocalDateTime createdAt;

        public Builder id(Long id) {
            this.id = id;
            return this;
        }

        public Builder userId(Long userId) {
            this.userId = userId;
            return this;
        }

        public Builder question(String question) {
            this.question = question;
            return this;
        }

        public Builder answer(String answer) {
            this.answer = answer;
            return this;
        }

        public Builder toolsCalled(String toolsCalled) {
            this.toolsCalled = toolsCalled;
            return this;
        }

        public Builder responseTime(Integer responseTime) {
            this.responseTime = responseTime;
            return this;
        }

        public Builder tokenUsage(String tokenUsage) {
            this.tokenUsage = tokenUsage;
            return this;
        }

        public Builder createdAt(LocalDateTime createdAt) {
            this.createdAt = createdAt;
            return this;
        }

        public AuditLog build() {
            return new AuditLog(id, userId, question, answer,
                    toolsCalled, responseTime, tokenUsage, createdAt);
        }
    }
}
