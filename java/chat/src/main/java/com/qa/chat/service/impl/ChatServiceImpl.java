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

        // Normalize: ensure history is never null (Pydantic rejects null)
        if (request.getHistory() == null) {
            request.setHistory(java.util.Collections.emptyList());
        }

        return webClient.post()
                .uri("/api/agent/chat/stream")
                .header("X-API-Key", apiKey)
                .header("X-User-Id", userId)
                .header("X-User-Role", role)
                .header("X-User-Department", department != null ? department : "全部")
                .header("X-Conversation-Id", String.valueOf(conversationId))
                .bodyValue(request)
                .retrieve()
                .bodyToFlux(ChatResponse.class)
                .timeout(Duration.ofSeconds(180))
                .doOnNext(event -> {
                    switch (event.getType()) {
                        case "answer":
                            if (event.getContent() != null) answerBuffer.append(event.getContent());
                            break;
                        case "citation":
                            captureCitation(citationList, event);
                            break;
                        case "summary":
                            if (event.getContent() != null) {
                                conversationRepository.findById(conversationId).ifPresent(c -> {
                                    c.setSummary(event.getContent());
                                    conversationRepository.save(c);
                                });
                            }
                            break;
                        case "token_usage":
                            captureTokenUsage(auditLog, event);
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
                    String errorDetail = extractErrorDetail(e);
                    log.error("Chat stream error: {}", errorDetail, e);
                    updateAuditLog(auditLog, answerBuffer.toString(), startTime, errorDetail);
                    if (answerBuffer.length() > 0) {
                        saveAssistantMessage(conversationId, answerBuffer.toString(), citationList, agentStepList);
                    }
                })
                .onErrorResume(e -> {
                    String cause = extractErrorDetail(e);
                    return Flux.just(ChatResponse.builder()
                            .type("error")
                            .content("AI服务暂时不可用，请稍后重试。错误详情: " + cause)
                            .build());
                });
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

    private void captureTokenUsage(AuditLog auditLog, ChatResponse event) {
        if (event.getData() instanceof Map) {
            @SuppressWarnings("unchecked")
            Map<String, Object> usage = (Map<String, Object>) event.getData();
            try {
                auditLog.setTokenUsage(objectMapper.writeValueAsString(usage));
            } catch (JsonProcessingException e) {
                log.warn("Failed to serialize tokenUsage", e);
            }
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
        updateAuditLog(auditLog, answer, startTime, null);
    }

    private void updateAuditLog(AuditLog auditLog, String answer, long startTime, String errorMessage) {
        try {
            int responseTime = (int) (System.currentTimeMillis() - startTime);
            auditLog.setAnswer(answer.isEmpty() ? null : answer);
            auditLog.setResponseTime(responseTime);
            if (errorMessage != null) {
                auditLog.setErrorMessage(errorMessage);
            }
            auditLogService.save(auditLog);
            log.info("Audit log updated: responseTime={}ms, answerLen={}, error={}", responseTime, answer.length(),
                    errorMessage != null ? errorMessage.substring(0, Math.min(100, errorMessage.length())) : "none");
            if (responseTime > 5000) {
                log.warn("SLOW_QUERY | responseTime={}ms | question='{}' | userId={}",
                        responseTime, auditLog.getQuestion(), auditLog.getUserId());
            }
        } catch (Exception e) {
            log.error("Failed to update audit log", e);
        }
    }

    private String extractErrorDetail(Throwable e) {
        if (e == null) return "未知错误";
        String msg = e.getMessage();
        if (msg != null && !msg.isEmpty()) return msg;
        Throwable cause = e.getCause();
        if (cause != null && cause.getMessage() != null) return cause.getMessage();
        return e.getClass().getSimpleName();
    }
}
