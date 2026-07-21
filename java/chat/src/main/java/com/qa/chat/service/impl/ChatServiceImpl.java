package com.qa.chat.service.impl;

import com.qa.chat.dto.ChatRequest;
import com.qa.chat.dto.ChatResponse;
import com.qa.chat.service.ChatService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Flux;

import java.time.Duration;

@Service
public class ChatServiceImpl implements ChatService {

    private static final Logger log = LoggerFactory.getLogger(ChatServiceImpl.class);

    private final WebClient webClient;

    @Value("${app.agent.base-url}")
    private String agentBaseUrl;

    @Value("${app.agent.api-key}")
    private String apiKey;

    public ChatServiceImpl(WebClient webClient) {
        this.webClient = webClient;
    }

    @Override
    public Flux<ChatResponse> chatStream(ChatRequest request, String userId, String role, String department) {
        return webClient.post()
                .uri("/api/agent/chat/stream")
                .header("X-API-Key", apiKey)
                .header("X-User-Id", userId)
                .header("X-User-Role", role)
                .header("X-User-Department", department != null ? department : "全部")
                .bodyValue(request)
                .retrieve()
                .bodyToFlux(ChatResponse.class)
                .timeout(Duration.ofSeconds(60))
                .onErrorResume(e -> {
                    log.error("Chat stream error", e);
                    return Flux.just(ChatResponse.builder()
                            .type("error")
                            .content("AI服务暂时不可用，请稍后重试")
                            .build());
                });
    }
}
