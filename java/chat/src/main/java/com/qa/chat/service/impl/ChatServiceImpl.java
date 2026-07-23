package com.qa.chat.service.impl;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.qa.audit.entity.AuditLog;
import com.qa.audit.service.AuditLogService;
import com.qa.chat.dto.ChatRequest;
import com.qa.chat.dto.ChatResponse;
import com.qa.chat.entity.Conversation;
import com.qa.chat.entity.Message;
import com.qa.chat.repository.ConversationRepository;
import com.qa.chat.repository.MessageRepository;
import com.qa.chat.service.ChatService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Flux;

import java.time.Duration;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Service
public class ChatServiceImpl implements ChatService {

    private static final Logger log = LoggerFactory.getLogger(ChatServiceImpl.class);

    private final WebClient webClient;
    private final AuditLogService auditLogService;
    private final ConversationRepository conversationRepository;
    private final MessageRepository messageRepository;
    private final ObjectMapper objectMapper;

    @Value("${app.agent.api-key}")
    private String apiKey;

    public ChatServiceImpl(WebClient webClient, AuditLogService auditLogService,
                           ConversationRepository conversationRepository,
                           MessageRepository messageRepository,
                           ObjectMapper objectMapper) {
        this.webClient = webClient;
        this.auditLogService = auditLogService;
        this.conversationRepository = conversationRepository;
        this.messageRepository = messageRepository;
        this.objectMapper = objectMapper;
    }

    @Override
    public Flux<ChatResponse> chatStream(ChatRequest request, String userId, String role, String department) {
        long startTime = System.currentTimeMillis();
        StringBuilder answerBuffer = new StringBuilder();
        List<Map<String, Object>> citationList = new ArrayList<>();
        List<Map<String, Object>> agentStepList = new ArrayList<>();

        Long uid = Long.parseLong(userId);

        // Create or get conversation
        Conversation conv;
        if (request.getConversationId() != null) {
            conv = conversationRepository.findById(request.getConversationId()).orElse(null);
            if (conv == null || !conv.getUserId().equals(uid)) {
                conv = createConversation(uid, request.getQuestion());
            }
        } else {
            conv = createConversation(uid, request.getQuestion());
        }

        // Save user message
        Message userMsg = new Message();
        userMsg.setConversationId(conv.getId());
        userMsg.setRole("user");
        userMsg.setContent(request.getQuestion());
        messageRepository.save(userMsg);

        // Audit log
        AuditLog auditLog = AuditLog.builder()
                .userId(uid)
                .question(request.getQuestion())
                .createdAt(LocalDateTime.now())
                .build();
        auditLogService.save(auditLog);
        log.info("Audit log saved for user {}: {}", userId, request.getQuestion());

        final Long conversationId = conv.getId();

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
                .doOnNext(event -> {
                    switch (event.getType()) {
                        case "answer":
                            if (event.getContent() != null) answerBuffer.append(event.getContent());
                            break;
                        case "citation":
                            captureCitation(citationList, event);
                            break;
                        case "thought":
                        case "action":
                        case "observation":
                            captureAgentStep(agentStepList, event);
                            break;
                    }
                })
                .doOnComplete(() -> {
                    updateAuditLog(auditLog, answerBuffer.toString(), startTime);
                    saveAssistantMessage(conversationId, answerBuffer.toString(), citationList, agentStepList);
                })
                .doOnError(e -> {
                    log.error("Chat stream error", e);
                    updateAuditLog(auditLog, answerBuffer.toString(), startTime);
                    if (answerBuffer.length() > 0) {
                        saveAssistantMessage(conversationId, answerBuffer.toString(), citationList, agentStepList);
                    }
                })
                .onErrorResume(e -> Flux.just(ChatResponse.builder()
                        .type("error")
                        .content("AI服务暂时不可用，请稍后重试")
                        .build()));
    }

    private Conversation createConversation(Long userId, String question) {
        String title = question.length() > 100 ? question.substring(0, 100) + "..." : question;
        Conversation conv = new Conversation(userId, title);
        return conversationRepository.save(conv);
    }

    private void saveAssistantMessage(Long conversationId, String answer,
                                       List<Map<String, Object>> citations,
                                       List<Map<String, Object>> agentSteps) {
        try {
            Message msg = new Message();
            msg.setConversationId(conversationId);
            msg.setRole("assistant");
            msg.setContent(answer);
            msg.setCitations(citations.isEmpty() ? null : objectMapper.writeValueAsString(citations));
            msg.setAgentSteps(agentSteps.isEmpty() ? null : objectMapper.writeValueAsString(agentSteps));
            messageRepository.save(msg);

            // Touch conversation updatedAt
            conversationRepository.findById(conversationId).ifPresent(conv -> {
                conv.setUpdatedAt(LocalDateTime.now());
                conversationRepository.save(conv);
            });
        } catch (JsonProcessingException e) {
            log.error("Failed to serialize citations/agentSteps", e);
        }
    }

    private void captureCitation(List<Map<String, Object>> list, ChatResponse event) {
        if (event.getData() instanceof List) {
            for (Object item : (List<?>) event.getData()) {
                if (item instanceof Map) {
                    @SuppressWarnings("unchecked")
                    Map<String, Object> map = (Map<String, Object>) item;
                    list.add(map);
                }
            }
        } else if (event.getData() instanceof Map) {
            @SuppressWarnings("unchecked")
            Map<String, Object> map = (Map<String, Object>) event.getData();
            list.add(map);
        }
    }

    private void captureAgentStep(List<Map<String, Object>> list, ChatResponse event) {
        Map<String, Object> step = new HashMap<>();
        step.put("type", event.getType());
        step.put("content", event.getContent());
        if (event.getData() instanceof Map) {
            @SuppressWarnings("unchecked")
            Map<String, Object> data = (Map<String, Object>) event.getData();
            if (data.containsKey("tool")) step.put("tool", data.get("tool"));
            if (data.containsKey("args")) step.put("args", data.get("args"));
        }
        list.add(step);
    }

    private void updateAuditLog(AuditLog auditLog, String answer, long startTime) {
        try {
            int responseTime = (int) (System.currentTimeMillis() - startTime);
            auditLog.setAnswer(answer.isEmpty() ? null : answer);
            auditLog.setResponseTime(responseTime);
            auditLogService.save(auditLog);
            log.info("Audit log updated: responseTime={}ms, answerLen={}", responseTime, answer.length());
        } catch (Exception e) {
            log.error("Failed to update audit log", e);
        }
    }
}
