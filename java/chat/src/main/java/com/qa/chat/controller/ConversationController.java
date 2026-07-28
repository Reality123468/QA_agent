package com.qa.chat.controller;

import com.qa.chat.dto.ConversationDto;
import com.qa.chat.dto.MessageDto;
import com.qa.chat.service.ConversationService;
import com.qa.common.ApiResult;
import com.qa.common.UserPrincipal;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/chat/conversations")
public class ConversationController {

    private final ConversationService conversationService;

    public ConversationController(ConversationService conversationService) {
        this.conversationService = conversationService;
    }

    private Long getUserId(Authentication auth) {
        return ((UserPrincipal) auth.getDetails()).getUserId();
    }

    @GetMapping
    public ApiResult<List<ConversationDto>> listConversations(Authentication auth) {
        List<ConversationDto> list = conversationService.listConversations(getUserId(auth));
        return ApiResult.success(list);
    }

    @GetMapping("/{id}")
    public ApiResult<List<MessageDto>> getMessages(@PathVariable Long id, Authentication auth) {
        List<MessageDto> messages = conversationService.getMessages(id, getUserId(auth));
        return ApiResult.success(messages);
    }

    @DeleteMapping("/{id}")
    public ApiResult<Void> deleteConversation(@PathVariable Long id, Authentication auth) {
        conversationService.deleteConversation(id, getUserId(auth));
        return ApiResult.success(null);
    }

    @PostMapping("/messages/{id}/feedback")
    public ApiResult<Void> submitFeedback(@PathVariable Long id,
                                           @RequestBody Map<String, String> body,
                                           Authentication auth) {
        String feedback = body.get("feedback");
        conversationService.submitFeedback(id, getUserId(auth), feedback);
        return ApiResult.success(null);
    }
}
