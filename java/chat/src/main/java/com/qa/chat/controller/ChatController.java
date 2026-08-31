package com.qa.chat.controller;

import com.qa.common.UserPrincipal;
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
        // /api/chat/stream 已 permitAll（兼容 SSE 异步分发），此处显式校验登录态：
        // 匿名/无效 token 的 details 不是 UserPrincipal，直接返回错误事件而非 500。
        if (auth == null || !(auth.getDetails() instanceof UserPrincipal)
                || auth.getAuthorities() == null || auth.getAuthorities().isEmpty()) {
            return Flux.just(ChatResponse.builder()
                    .type("error")
                    .content("未登录或登录已过期，请重新登录")
                    .build());
        }
        UserPrincipal principal = (UserPrincipal) auth.getDetails();
        String role = auth.getAuthorities().iterator().next().getAuthority();

        return chatService.chatStream(request, String.valueOf(principal.getUserId()),
                role, principal.getDepartment());
    }
}
