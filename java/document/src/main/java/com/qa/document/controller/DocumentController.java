package com.qa.document.controller;

import com.qa.common.ApiResult;
import com.qa.common.BusinessException;
import com.qa.common.ErrorCode;
import com.qa.common.PageResult;
import com.qa.common.UserPrincipal;
import com.qa.document.dto.DocumentResponse;
import com.qa.document.service.DocumentService;
import com.qa.document.ws.IndexProgressHandler;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.util.Map;

@RestController
@RequestMapping("/api/documents")
@PreAuthorize("!hasAuthority('ROLE_EMPLOYEE')")
public class DocumentController {

    private final DocumentService documentService;
    private final IndexProgressHandler progressHandler;

    public DocumentController(DocumentService documentService, IndexProgressHandler progressHandler) {
        this.documentService = documentService;
        this.progressHandler = progressHandler;
    }

    private UserPrincipal getUser(Authentication auth) {
        return (UserPrincipal) auth.getDetails();
    }

    @PostMapping("/upload")
    public ApiResult<DocumentResponse> upload(
            @RequestParam("file") MultipartFile file,
            @RequestParam(value = "title", required = false) String title,
            @RequestParam(value = "department", defaultValue = "全部") String department,
            @RequestParam(value = "securityLevel", defaultValue = "内部") String securityLevel,
            Authentication auth) {
        UserPrincipal user = getUser(auth);
        return ApiResult.success(documentService.upload(file, title, department, securityLevel, user.getUserId()));
    }

    @GetMapping
    public ApiResult<PageResult<DocumentResponse>> list(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "20") int size,
            Authentication auth) {
        UserPrincipal user = getUser(auth);
        return ApiResult.success(documentService.list(page, size, user));
    }

    @GetMapping("/{id}")
    public ApiResult<DocumentResponse> getById(@PathVariable Long id) {
        return ApiResult.success(documentService.getById(id));
    }

    @DeleteMapping("/{id}")
    public ApiResult<Void> delete(@PathVariable Long id, Authentication auth) {
        UserPrincipal user = getUser(auth);
        documentService.delete(id, user);
        return ApiResult.success(null);
    }

    @PostMapping("/{id}/index")
    public ApiResult<Void> triggerIndex(@PathVariable Long id, Authentication auth) {
        UserPrincipal user = getUser(auth);
        documentService.triggerIndex(id, user);
        return ApiResult.success(null);
    }

    @GetMapping("/status/{id}")
    public ApiResult<String> getStatus(@PathVariable Long id) {
        return ApiResult.success(documentService.getStatus(id));
    }

    @PostMapping("/index-progress/{docId}")
    @PreAuthorize("permitAll()")
    public ApiResult<Void> reportProgress(@PathVariable Long docId, @RequestBody Map<String, Object> body) {
        String status = (String) body.getOrDefault("status", "INDEXING");
        String message = (String) body.getOrDefault("message", "");
        progressHandler.broadcastProgress(docId, status, message);
        return ApiResult.success(null);
    }
}
