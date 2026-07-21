package com.qa.chat.controller;

import com.qa.chat.dto.ChatRequest;
import com.qa.chat.dto.ChatResponse;
import com.qa.chat.service.ChatService;
import jakarta.validation.Valid;
import org.springframework.http.MediaType;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import reactor.core.publisher.Flux;

@RestController
@RequestMapping("/api/chat")
public class ChatController {

    private final ChatService chatService;

    public ChatController(ChatService chatService) {
        this.chatService = chatService;
    }

    @PostMapping(value = "/stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public Flux<ChatResponse> chatStream(@Valid @RequestBody ChatRequest request, Authentication auth) {
        Long userId = (Long) auth.getDetails();
        String role = auth.getAuthorities().iterator().next().getAuthority();
        String department = null; // 后续从 user 表查询
        return chatService.chatStream(request, String.valueOf(userId), role, department);
    }
}
