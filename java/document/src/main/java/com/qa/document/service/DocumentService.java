package com.qa.document.service;

import com.qa.common.PageResult;
import com.qa.document.dto.DocumentResponse;
import org.springframework.web.multipart.MultipartFile;

public interface DocumentService {
    DocumentResponse upload(MultipartFile file, String title, String department, String securityLevel, Long uploaderId);
    PageResult<DocumentResponse> list(int page, int size);
    DocumentResponse getById(Long id);
    void delete(Long id);
    void triggerIndex(Long id);
    String getStatus(Long id);
}
