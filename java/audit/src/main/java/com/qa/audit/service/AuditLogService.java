package com.qa.audit.service;

import com.qa.audit.entity.AuditLog;
import com.qa.common.PageResult;

import java.util.List;

public interface AuditLogService {
    AuditLog save(AuditLog log);
    PageResult<AuditLog> list(int page, int size, Long userId);
    void delete(Long id);
    void deleteBatch(List<Long> ids);
}
