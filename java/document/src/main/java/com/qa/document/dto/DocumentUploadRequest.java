package com.qa.document.dto;

public class DocumentUploadRequest {
    private String title;
    private String department = "全部";
    private String securityLevel = "内部";

    public DocumentUploadRequest() {
    }

    public DocumentUploadRequest(String title, String department, String securityLevel) {
        this.title = title;
        this.department = department;
        this.securityLevel = securityLevel;
    }

    public String getTitle() {
        return title;
    }

    public void setTitle(String title) {
        this.title = title;
    }

    public String getDepartment() {
        return department;
    }

    public void setDepartment(String department) {
        this.department = department;
    }

    public String getSecurityLevel() {
        return securityLevel;
    }

    public void setSecurityLevel(String securityLevel) {
        this.securityLevel = securityLevel;
    }
}
