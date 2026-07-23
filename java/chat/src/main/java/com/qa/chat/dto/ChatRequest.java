package com.qa.chat.dto;

import jakarta.validation.constraints.NotBlank;

import java.util.List;

public class ChatRequest {
    @NotBlank(message = "问题不能为空")
    private String question;
    private List<HistoryMessage> history;
    private String mode = "rag";

    public ChatRequest() {
    }

    public ChatRequest(String question, List<HistoryMessage> history, String mode) {
        this.question = question;
        this.history = history;
        this.mode = mode;
    }

    public String getQuestion() {
        return question;
    }

    public void setQuestion(String question) {
        this.question = question;
    }

    public List<HistoryMessage> getHistory() {
        return history;
    }

    public void setHistory(List<HistoryMessage> history) {
        this.history = history;
    }

    public String getMode() {
        return mode;
    }

    public void setMode(String mode) {
        this.mode = mode;
    }
}
