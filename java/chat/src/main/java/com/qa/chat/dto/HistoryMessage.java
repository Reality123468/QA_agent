package com.qa.chat.dto;

public class HistoryMessage {
    private String role;  // user / assistant
    private String content;

    public HistoryMessage() {
    }

    public HistoryMessage(String role, String content) {
        this.role = role;
        this.content = content;
    }

    public String getRole() {
        return role;
    }

    public void setRole(String role) {
        this.role = role;
    }

    public String getContent() {
        return content;
    }

    public void setContent(String content) {
        this.content = content;
    }
}
