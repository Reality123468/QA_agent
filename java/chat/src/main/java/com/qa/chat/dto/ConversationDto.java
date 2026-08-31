package com.qa.chat.dto;

import java.time.LocalDateTime;

public class ConversationDto {

    private Long id;
    private String title;
    private LocalDateTime updatedAt;
    private int messageCount;
    private String summary;

    public ConversationDto() {}

    public ConversationDto(Long id, String title, LocalDateTime updatedAt, int messageCount) {
        this.id = id;
        this.title = title;
        this.updatedAt = updatedAt;
        this.messageCount = messageCount;
    }

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public String getTitle() { return title; }
    public void setTitle(String title) { this.title = title; }
    public LocalDateTime getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(LocalDateTime updatedAt) { this.updatedAt = updatedAt; }
    public int getMessageCount() { return messageCount; }
    public void setMessageCount(int messageCount) { this.messageCount = messageCount; }
    public String getSummary() { return summary; }
    public void setSummary(String summary) { this.summary = summary; }
}
