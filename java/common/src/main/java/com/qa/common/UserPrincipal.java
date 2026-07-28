package com.qa.common;

public class UserPrincipal {

    private final Long userId;
    private final String username;
    private final String role;
    private final String department;

    public UserPrincipal(Long userId, String username, String role, String department) {
        this.userId = userId;
        this.username = username;
        this.role = role;
        this.department = department;
    }

    public Long getUserId() { return userId; }
    public String getUsername() { return username; }
    public String getRole() { return role; }
    public String getDepartment() { return department; }

    public boolean isAdmin() { return "ROLE_ADMIN".equals(role); }
    public boolean isHr() { return "ROLE_HR".equals(role); }
    public boolean isLeader() { return "ROLE_LEADER".equals(role); }
    public boolean isEmployee() { return "ROLE_EMPLOYEE".equals(role); }
    public boolean canManageAllDocuments() { return isAdmin() || isHr(); }
}
