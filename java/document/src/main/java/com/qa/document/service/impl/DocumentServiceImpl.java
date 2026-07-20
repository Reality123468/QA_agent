package com.qa.document.service.impl;

import com.qa.common.BusinessException;
import com.qa.common.ErrorCode;
import com.qa.common.PageResult;
import com.qa.document.dto.DocumentResponse;
import com.qa.document.entity.DocDocument;
import com.qa.document.repository.DocumentRepository;
import com.qa.document.service.DocumentService;
import io.minio.MinioClient;
import io.minio.PutObjectArgs;
import io.minio.RemoveObjectArgs;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.reactive.function.client.WebClient;

import java.util.Map;
import java.util.Set;
import java.util.UUID;

@Service
public class DocumentServiceImpl implements DocumentService {

    private static final Logger log = LoggerFactory.getLogger(DocumentServiceImpl.class);

    private final DocumentRepository documentRepository;
    private final MinioClient minioClient;
    private final WebClient webClient;

    @Value("${minio.bucket}")
    private String bucket;

    @Value("${minio.endpoint}")
    private String minioEndpoint;

    private static final Set<String> ALLOWED_TYPES = Set.of("pdf", "md", "txt", "docx");
    private static final long MAX_FILE_SIZE = 50 * 1024 * 1024L; // 50MB

    public DocumentServiceImpl(DocumentRepository documentRepository,
                               MinioClient minioClient,
                               WebClient webClient) {
        this.documentRepository = documentRepository;
        this.minioClient = minioClient;
        this.webClient = webClient;
    }

    @Override
    public DocumentResponse upload(MultipartFile file, String title, String department,
                                    String securityLevel, Long uploaderId) {
        String originalName = file.getOriginalFilename();
        String ext = getFileExtension(originalName).toLowerCase();

        if (!ALLOWED_TYPES.contains(ext)) {
            throw new BusinessException(ErrorCode.FILE_TYPE_NOT_SUPPORTED);
        }
        if (file.getSize() > MAX_FILE_SIZE) {
            throw new BusinessException(ErrorCode.FILE_SIZE_EXCEEDED);
        }

        String objectName = UUID.randomUUID() + "." + ext;

        try {
            minioClient.putObject(PutObjectArgs.builder()
                    .bucket(bucket)
                    .object(objectName)
                    .stream(file.getInputStream(), file.getSize(), -1)
                    .contentType(file.getContentType())
                    .build());
        } catch (Exception e) {
            log.error("MinIO upload failed", e);
            throw new BusinessException(ErrorCode.INTERNAL_ERROR);
        }

        DocDocument doc = DocDocument.builder()
                .title(title != null ? title : originalName)
                .fileName(originalName)
                .filePath(bucket + "/" + objectName)
                .fileSize(file.getSize())
                .fileType(ext)
                .department(department)
                .securityLevel(securityLevel)
                .status("UPLOADED")
                .uploadBy(uploaderId)
                .build();

        doc = documentRepository.save(doc);

        return toResponse(doc);
    }

    @Override
    public PageResult<DocumentResponse> list(int page, int size) {
        Page<DocDocument> docPage = documentRepository.findAll(PageRequest.of(page - 1, size));
        return PageResult.of(
                docPage.getContent().stream().map(this::toResponse).toList(),
                docPage.getTotalElements(),
                docPage.getTotalPages(),
                page,
                size
        );
    }

    @Override
    public DocumentResponse getById(Long id) {
        DocDocument doc = documentRepository.findById(id)
                .orElseThrow(() -> new BusinessException(ErrorCode.DOCUMENT_NOT_FOUND));
        return toResponse(doc);
    }

    @Override
    public void delete(Long id) {
        DocDocument doc = documentRepository.findById(id)
                .orElseThrow(() -> new BusinessException(ErrorCode.DOCUMENT_NOT_FOUND));

        try {
            minioClient.removeObject(RemoveObjectArgs.builder()
                    .bucket(bucket)
                    .object(doc.getFilePath().substring(bucket.length() + 1))
                    .build());
        } catch (Exception e) {
            log.error("MinIO delete failed for doc {}", id, e);
        }

        documentRepository.delete(doc);
    }

    @Override
    @Async
    public void triggerIndex(Long id) {
        DocDocument doc = documentRepository.findById(id)
                .orElseThrow(() -> new BusinessException(ErrorCode.DOCUMENT_NOT_FOUND));

        doc.setStatus("INDEXING");
        documentRepository.save(doc);

        try {
            Map<String, Object> requestBody = Map.of(
                    "document", Map.of(
                            "id", doc.getId(),
                            "title", doc.getTitle(),
                            "filePath", doc.getFilePath(),
                            "fileType", doc.getFileType(),
                            "department", doc.getDepartment(),
                            "securityLevel", doc.getSecurityLevel()
                    ),
                    "callbackUrl", "http://localhost:8080/api/documents/status/" + doc.getId()
            );

            webClient.post()
                    .uri("/api/agent/index")
                    .bodyValue(requestBody)
                    .retrieve()
                    .toBodilessEntity()
                    .block();

            doc.setStatus("COMPLETED");
        } catch (Exception e) {
            log.error("Index failed for doc {}", id, e);
            doc.setStatus("FAILED");
        }

        documentRepository.save(doc);
    }

    @Override
    public String getStatus(Long id) {
        DocDocument doc = documentRepository.findById(id)
                .orElseThrow(() -> new BusinessException(ErrorCode.DOCUMENT_NOT_FOUND));
        return doc.getStatus();
    }

    private DocumentResponse toResponse(DocDocument doc) {
        return DocumentResponse.builder()
                .id(doc.getId())
                .title(doc.getTitle())
                .fileName(doc.getFileName())
                .filePath(doc.getFilePath())
                .fileSize(doc.getFileSize())
                .fileType(doc.getFileType())
                .department(doc.getDepartment())
                .securityLevel(doc.getSecurityLevel())
                .status(doc.getStatus())
                .createdAt(doc.getCreatedAt())
                .build();
    }

    private String getFileExtension(String filename) {
        if (filename == null || !filename.contains(".")) return "";
        return filename.substring(filename.lastIndexOf('.') + 1);
    }
}
