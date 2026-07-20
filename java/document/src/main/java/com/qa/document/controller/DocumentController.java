package com.qa.document.controller;

import com.qa.common.ApiResult;
import com.qa.common.PageResult;
import com.qa.document.dto.DocumentResponse;
import com.qa.document.service.DocumentService;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

@RestController
@RequestMapping("/api/documents")
public class DocumentController {

    private final DocumentService documentService;

    public DocumentController(DocumentService documentService) {
        this.documentService = documentService;
    }

    @PostMapping("/upload")
    public ApiResult<DocumentResponse> upload(
            @RequestParam("file") MultipartFile file,
            @RequestParam(value = "title", required = false) String title,
            @RequestParam(value = "department", defaultValue = "全部") String department,
            @RequestParam(value = "securityLevel", defaultValue = "内部") String securityLevel,
            Authentication auth) {
        Long uploaderId = (Long) auth.getDetails();
        return ApiResult.success(documentService.upload(file, title, department, securityLevel, uploaderId));
    }

    @GetMapping
    public ApiResult<PageResult<DocumentResponse>> list(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "20") int size) {
        return ApiResult.success(documentService.list(page, size));
    }

    @GetMapping("/{id}")
    public ApiResult<DocumentResponse> getById(@PathVariable Long id) {
        return ApiResult.success(documentService.getById(id));
    }

    @DeleteMapping("/{id}")
    public ApiResult<Void> delete(@PathVariable Long id) {
        documentService.delete(id);
        return ApiResult.success(null);
    }

    @PostMapping("/{id}/index")
    public ApiResult<Void> triggerIndex(@PathVariable Long id) {
        documentService.triggerIndex(id);
        return ApiResult.success(null);
    }

    @GetMapping("/status/{id}")
    public ApiResult<String> getStatus(@PathVariable Long id) {
        return ApiResult.success(documentService.getStatus(id));
    }
}
