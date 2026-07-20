package com.qa.document.entity;

import jakarta.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "doc_document")
public class DocDocument {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, length = 200)
    private String title;

    @Column(name = "file_name", nullable = false, length = 200)
    private String fileName;

    @Column(name = "file_path", nullable = false, length = 500)
    private String filePath;

    @Column(name = "file_size", nullable = false)
    private Long fileSize;

    @Column(name = "file_type", nullable = false, length = 20)
    private String fileType;

    @Column(length = 50)
    private String department = "全部";

    @Column(name = "security_level", length = 20)
    private String securityLevel = "内部";

    @Column(length = 20)
    private String status = "UPLOADED";

    @Column(name = "upload_by")
    private Long uploadBy;

    private Integer version = 1;

    @Column(name = "created_at")
    private LocalDateTime createdAt;

    @Column(name = "updated_at")
    private LocalDateTime updatedAt;

    public DocDocument() {
    }

    public DocDocument(Long id, String title, String fileName, String filePath,
                       Long fileSize, String fileType, String department,
                       String securityLevel, String status, Long uploadBy,
                       Integer version, LocalDateTime createdAt, LocalDateTime updatedAt) {
        this.id = id;
        this.title = title;
        this.fileName = fileName;
        this.filePath = filePath;
        this.fileSize = fileSize;
        this.fileType = fileType;
        this.department = department;
        this.securityLevel = securityLevel;
        this.status = status;
        this.uploadBy = uploadBy;
        this.version = version;
        this.createdAt = createdAt;
        this.updatedAt = updatedAt;
    }

    @PrePersist
    protected void onCreate() {
        createdAt = LocalDateTime.now();
        updatedAt = LocalDateTime.now();
    }

    @PreUpdate
    protected void onUpdate() {
        updatedAt = LocalDateTime.now();
    }

    // --- Getters and Setters ---

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

    public Long getUploadBy() {
        return uploadBy;
    }

    public void setUploadBy(Long uploadBy) {
        this.uploadBy = uploadBy;
    }

    public Integer getVersion() {
        return version;
    }

    public void setVersion(Integer version) {
        this.version = version;
    }

    public LocalDateTime getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(LocalDateTime createdAt) {
        this.createdAt = createdAt;
    }

    public LocalDateTime getUpdatedAt() {
        return updatedAt;
    }

    public void setUpdatedAt(LocalDateTime updatedAt) {
        this.updatedAt = updatedAt;
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
        private String department = "全部";
        private String securityLevel = "内部";
        private String status = "UPLOADED";
        private Long uploadBy;
        private Integer version = 1;
        private LocalDateTime createdAt;
        private LocalDateTime updatedAt;

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

        public Builder uploadBy(Long uploadBy) {
            this.uploadBy = uploadBy;
            return this;
        }

        public Builder version(Integer version) {
            this.version = version;
            return this;
        }

        public Builder createdAt(LocalDateTime createdAt) {
            this.createdAt = createdAt;
            return this;
        }

        public Builder updatedAt(LocalDateTime updatedAt) {
            this.updatedAt = updatedAt;
            return this;
        }

        public DocDocument build() {
            return new DocDocument(id, title, fileName, filePath, fileSize, fileType,
                    department, securityLevel, status, uploadBy, version, createdAt, updatedAt);
        }
    }
}
