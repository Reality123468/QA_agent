package com.qa.document.dto;

import java.time.LocalDateTime;

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

    public DocumentResponse() {
    }

    public DocumentResponse(Long id, String title, String fileName, String filePath,
                            Long fileSize, String fileType, String department,
                            String securityLevel, String status, String uploadByName,
                            LocalDateTime createdAt) {
        this.id = id;
        this.title = title;
        this.fileName = fileName;
        this.filePath = filePath;
        this.fileSize = fileSize;
        this.fileType = fileType;
        this.department = department;
        this.securityLevel = securityLevel;
        this.status = status;
        this.uploadByName = uploadByName;
        this.createdAt = createdAt;
    }

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public String getTitle() {
        return title;
    }

    public void setTitle(String title) {
        this.title = title;
    }

    public String getFileName() {
        return fileName;
    }

    public void setFileName(String fileName) {
        this.fileName = fileName;
    }

    public String getFilePath() {
        return filePath;
    }

    public void setFilePath(String filePath) {
        this.filePath = filePath;
    }

    public Long getFileSize() {
        return fileSize;
    }

    public void setFileSize(Long fileSize) {
        this.fileSize = fileSize;
    }

    public String getFileType() {
        return fileType;
    }

    public void setFileType(String fileType) {
        this.fileType = fileType;
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

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public String getUploadByName() {
        return uploadByName;
    }

    public void setUploadByName(String uploadByName) {
        this.uploadByName = uploadByName;
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

        public Builder id(Long id) {
            this.id = id;
            return this;
        }

        public Builder title(String title) {
            this.title = title;
            return this;
        }

        public Builder fileName(String fileName) {
            this.fileName = fileName;
            return this;
        }

        public Builder filePath(String filePath) {
            this.filePath = filePath;
            return this;
        }

        public Builder fileSize(Long fileSize) {
            this.fileSize = fileSize;
            return this;
        }

        public Builder fileType(String fileType) {
            this.fileType = fileType;
            return this;
        }

        public Builder department(String department) {
            this.department = department;
            return this;
        }

        public Builder securityLevel(String securityLevel) {
            this.securityLevel = securityLevel;
            return this;
        }

        public Builder status(String status) {
            this.status = status;
            return this;
        }

        public Builder uploadByName(String uploadByName) {
            this.uploadByName = uploadByName;
            return this;
        }

        public Builder createdAt(LocalDateTime createdAt) {
            this.createdAt = createdAt;
            return this;
        }

        public DocumentResponse build() {
            return new DocumentResponse(id, title, fileName, filePath, fileSize,
                    fileType, department, securityLevel, status, uploadByName, createdAt);
        }
    }
}
