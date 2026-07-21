package com.qa.audit.service;

import com.qa.audit.entity.AuditLog;
import com.qa.common.PageResult;

public interface AuditLogService {
    AuditLog save(AuditLog log);
    PageResult<AuditLog> list(int page, int size, Long userId);
}
