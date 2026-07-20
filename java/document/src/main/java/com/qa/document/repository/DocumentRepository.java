package com.qa.document.repository;

import com.qa.document.entity.DocDocument;
import org.springframework.data.jpa.repository.JpaRepository;

public interface DocumentRepository extends JpaRepository<DocDocument, Long> {
}
