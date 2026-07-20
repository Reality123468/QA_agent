package com.qa.document.config;

import io.minio.BucketExistsArgs;
import io.minio.MakeBucketArgs;
import io.minio.MinioClient;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.CommandLineRunner;
import org.springframework.stereotype.Component;

@Component
public class BucketInitializer implements CommandLineRunner {

    private static final Logger log = LoggerFactory.getLogger(BucketInitializer.class);

    private final MinioClient minioClient;

    @Value("${minio.bucket}")
    private String bucket;

    public BucketInitializer(MinioClient minioClient) {
        this.minioClient = minioClient;
    }

    @Override
    public void run(String... args) throws Exception {
        boolean exists = minioClient.bucketExists(BucketExistsArgs.builder().bucket(bucket).build());
        if (!exists) {
            minioClient.makeBucket(MakeBucketArgs.builder().bucket(bucket).build());
            log.info("MinIO bucket '{}' created successfully", bucket);
        } else {
            log.info("MinIO bucket '{}' already exists", bucket);
        }
    }
}
