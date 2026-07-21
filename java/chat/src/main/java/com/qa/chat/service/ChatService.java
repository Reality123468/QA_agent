package com.qa.chat.service;

import com.qa.chat.dto.ChatRequest;
import com.qa.chat.dto.ChatResponse;
import reactor.core.publisher.Flux;

public interface ChatService {
    Flux<ChatResponse> chatStream(ChatRequest request, String userId, String role, String department);
}
