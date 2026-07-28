package com.qa.document.repository;

import com.qa.document.entity.DocDocument;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

public interface DocumentRepository extends JpaRepository<DocDocument, Long> {
    Page<DocDocument> findByDepartment(String department, Pageable pageable);
}
