package com.qa.audit.service.impl;

import com.qa.audit.entity.AuditLog;
import com.qa.audit.repository.AuditLogRepository;
import com.qa.audit.service.AuditLogService;
import com.qa.common.PageResult;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;

@Service
public class AuditLogServiceImpl implements AuditLogService {

    private static final Logger log = LoggerFactory.getLogger(AuditLogServiceImpl.class);

    private final AuditLogRepository auditLogRepository;

    public AuditLogServiceImpl(AuditLogRepository auditLogRepository) {
        this.auditLogRepository = auditLogRepository;
    }

    @Override
    public AuditLog save(AuditLog log) {
        return auditLogRepository.save(log);
    }

    @Override
    public PageResult<AuditLog> list(int page, int size, Long userId) {
        Page<AuditLog> logPage;
        if (userId != null) {
            logPage = auditLogRepository.findByUserIdOrderByCreatedAtDesc(userId, PageRequest.of(page - 1, size));
        } else {
            logPage = auditLogRepository.findAll(PageRequest.of(page - 1, size));
        }
        return PageResult.of(logPage.getContent(), logPage.getTotalElements(),
                logPage.getTotalPages(), page, size);
    }
}
