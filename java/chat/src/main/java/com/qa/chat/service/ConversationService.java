package com.qa.chat.service;

import com.qa.chat.dto.ConversationDto;
import com.qa.chat.dto.MessageDto;

import java.util.List;

public interface ConversationService {
    List<ConversationDto> listConversations(Long userId);
    List<MessageDto> getMessages(Long conversationId, Long userId);
    void deleteConversation(Long conversationId, Long userId);
}
