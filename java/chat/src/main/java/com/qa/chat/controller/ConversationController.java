package com.qa.chat.controller;

import com.qa.chat.dto.ConversationDto;
import com.qa.chat.dto.MessageDto;
import com.qa.chat.service.ConversationService;
import com.qa.common.ApiResult;
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

    @GetMapping
    public ApiResult<List<ConversationDto>> listConversations(Authentication auth) {
        Long userId = (Long) auth.getDetails();
        List<ConversationDto> list = conversationService.listConversations(userId);
        return ApiResult.success(list);
    }

    @GetMapping("/{id}")
    public ApiResult<List<MessageDto>> getMessages(@PathVariable Long id, Authentication auth) {
        Long userId = (Long) auth.getDetails();
        List<MessageDto> messages = conversationService.getMessages(id, userId);
        return ApiResult.success(messages);
    }

    @DeleteMapping("/{id}")
    public ApiResult<Void> deleteConversation(@PathVariable Long id, Authentication auth) {
        Long userId = (Long) auth.getDetails();
        conversationService.deleteConversation(id, userId);
        return ApiResult.success(null);
    }

    @PostMapping("/messages/{id}/feedback")
    public ApiResult<Void> submitFeedback(@PathVariable Long id,
                                           @RequestBody Map<String, String> body,
                                           Authentication auth) {
        Long userId = (Long) auth.getDetails();
        String feedback = body.get("feedback");
        conversationService.submitFeedback(id, userId, feedback);
        return ApiResult.success(null);
    }
}
