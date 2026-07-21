package com.qa.chat.dto;

public class ChatResponse {
    private String type;   // thinking / answer / citation / done / error
    private String content;
    private Object data;

    public ChatResponse() {
    }

    public ChatResponse(String type, String content, Object data) {
        this.type = type;
        this.content = content;
        this.data = data;
    }

    public String getType() {
        return type;
    }

    public void setType(String type) {
        this.type = type;
    }

    public String getContent() {
        return content;
    }

    public void setContent(String content) {
        this.content = content;
    }

    public Object getData() {
        return data;
    }

    public void setData(Object data) {
        this.data = data;
    }

    // --- Builder ---

    public static Builder builder() {
        return new Builder();
    }

    public static class Builder {
        private String type;
        private String content;
        private Object data;

        public Builder type(String type) {
            this.type = type;
            return this;
        }

        public Builder content(String content) {
            this.content = content;
            return this;
        }

        public Builder data(Object data) {
            this.data = data;
            return this;
        }

        public ChatResponse build() {
            return new ChatResponse(type, content, data);
        }
    }
}
