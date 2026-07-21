package com.qa.document;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.ComponentScan;
import org.springframework.context.annotation.FilterType;
import org.springframework.scheduling.annotation.EnableAsync;

@SpringBootApplication
@ComponentScan(basePackages = "com.qa",
    excludeFilters = {
        @ComponentScan.Filter(type = FilterType.REGEX,
            pattern = "com\\.qa\\.(auth|chat|audit)\\..*")
    })
@EnableAsync
public class DocumentApplication {
    public static void main(String[] args) {
        SpringApplication.run(DocumentApplication.class, args);
    }
}
