package com.qa.audit;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.ComponentScan;
import org.springframework.context.annotation.FilterType;

@SpringBootApplication
@ComponentScan(basePackages = "com.qa",
    excludeFilters = {
        @ComponentScan.Filter(type = FilterType.REGEX,
            pattern = "com\\.qa\\.(auth|document|chat)\\..*")
    })
public class AuditApplication {
    public static void main(String[] args) {
        SpringApplication.run(AuditApplication.class, args);
    }
}
