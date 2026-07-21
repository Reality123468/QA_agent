package com.qa.chat.config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.reactive.function.client.WebClient;

@Configuration
public class WebClientConfig {

    @Value("${app.agent.base-url}")
    private String agentBaseUrl;

    @Value("${app.agent.api-key}")
    private String apiKey;

    @Bean
    public WebClient webClient() {
        return WebClient.builder()
                .baseUrl(agentBaseUrl)
                .defaultHeader("X-API-Key", apiKey)
                .build();
    }
}
