package com.qa.auth.dto;

public class LoginResponse {
    private String token;
    private String username;
    private String role;
    private String department;

    public LoginResponse() {
    }

    public LoginResponse(String token, String username, String role, String department) {
        this.token = token;
        this.username = username;
        this.role = role;
        this.department = department;
    }

    public String getToken() {
        return token;
    }

    public void setToken(String token) {
        this.token = token;
    }

    public String getUsername() {
        return username;
    }

    public void setUsername(String username) {
        this.username = username;
    }

    public String getRole() {
        return role;
    }

    public void setRole(String role) {
        this.role = role;
    }

    public String getDepartment() {
        return department;
    }

    public void setDepartment(String department) {
        this.department = department;
    }

    // --- Builder ---

    public static Builder builder() {
        return new Builder();
    }

    public static class Builder {
        private String token;
        private String username;
        private String role;
        private String department;

        public Builder token(String token) {
            this.token = token;
            return this;
        }

        public Builder username(String username) {
            this.username = username;
            return this;
        }

        public Builder role(String role) {
            this.role = role;
            return this;
        }

        public Builder department(String department) {
            this.department = department;
            return this;
        }

        public LoginResponse build() {
            return new LoginResponse(token, username, role, department);
        }
    }
}
