package com.qa.chat.dto;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

public class MessageDto {

    private Long id;
    private String role;
    private String content;
    private List<Map<String, Object>> citations;
    private List<Map<String, Object>> agentSteps;
    private String feedback;
    private LocalDateTime timestamp;

    public MessageDto() {}

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public String getRole() { return role; }
    public void setRole(String role) { this.role = role; }
    public String getContent() { return content; }
    public void setContent(String content) { this.content = content; }
    public List<Map<String, Object>> getCitations() { return citations; }
    public void setCitations(List<Map<String, Object>> citations) { this.citations = citations; }
    public List<Map<String, Object>> getAgentSteps() { return agentSteps; }
    public void setAgentSteps(List<Map<String, Object>> agentSteps) { this.agentSteps = agentSteps; }
    public String getFeedback() { return feedback; }
    public void setFeedback(String feedback) { this.feedback = feedback; }
    public LocalDateTime getTimestamp() { return timestamp; }
    public void setTimestamp(LocalDateTime timestamp) { this.timestamp = timestamp; }
}
