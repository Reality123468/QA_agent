package com.qa.chat.service.impl;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.qa.chat.dto.ConversationDto;
import com.qa.chat.dto.MessageDto;
import com.qa.chat.entity.Conversation;
import com.qa.chat.entity.Message;
import com.qa.chat.repository.ConversationRepository;
import com.qa.chat.repository.MessageRepository;
import com.qa.chat.service.ConversationService;
import com.qa.common.BusinessException;
import com.qa.common.ErrorCode;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@Service
public class ConversationServiceImpl implements ConversationService {

    private static final Logger log = LoggerFactory.getLogger(ConversationServiceImpl.class);

    private final ConversationRepository conversationRepository;
    private final MessageRepository messageRepository;
    private final ObjectMapper objectMapper;

    public ConversationServiceImpl(ConversationRepository conversationRepository,
                                   MessageRepository messageRepository,
                                   ObjectMapper objectMapper) {
        this.conversationRepository = conversationRepository;
        this.messageRepository = messageRepository;
        this.objectMapper = objectMapper;
    }

    @Override
    public List<ConversationDto> listConversations(Long userId) {
        List<Conversation> conversations = conversationRepository.findByUserIdOrderByUpdatedAtDesc(userId);
        return conversations.stream().map(conv -> {
            List<Message> messages = messageRepository.findByConversationIdOrderByTimestampAsc(conv.getId());
            return new ConversationDto(conv.getId(), conv.getTitle(), conv.getUpdatedAt(), messages.size());
        }).collect(Collectors.toList());
    }

    @Override
    public List<MessageDto> getMessages(Long conversationId, Long userId) {
        Conversation conv = conversationRepository.findById(conversationId)
                .orElseThrow(() -> new BusinessException(ErrorCode.NOT_FOUND, "会话不存在"));

        if (!conv.getUserId().equals(userId)) {
            throw new BusinessException(ErrorCode.FORBIDDEN, "无权访问该会话");
        }

        List<Message> messages = messageRepository.findByConversationIdOrderByTimestampAsc(conversationId);
        return messages.stream().map(this::toDto).collect(Collectors.toList());
    }

    @Override
    @Transactional
    public void deleteConversation(Long conversationId, Long userId) {
        Conversation conv = conversationRepository.findById(conversationId)
                .orElseThrow(() -> new BusinessException(ErrorCode.NOT_FOUND, "会话不存在"));

        if (!conv.getUserId().equals(userId)) {
            throw new BusinessException(ErrorCode.FORBIDDEN, "无权删除该会话");
        }

        messageRepository.deleteByConversationId(conversationId);
        conversationRepository.delete(conv);
        log.info("Conversation {} deleted by user {}", conversationId, userId);
    }

    @Override
    @Transactional
    public void submitFeedback(Long messageId, Long userId, String feedback) {
        if (!"thumbs_up".equals(feedback) && !"thumbs_down".equals(feedback)) {
            throw new BusinessException(ErrorCode.FORBIDDEN, "feedback 必须为 thumbs_up 或 thumbs_down");
        }
        Message message = messageRepository.findById(messageId)
                .orElseThrow(() -> new BusinessException(ErrorCode.NOT_FOUND, "消息不存在"));

        // 验证该消息属于该用户的会话
        Conversation conv = conversationRepository.findById(message.getConversationId())
                .orElseThrow(() -> new BusinessException(ErrorCode.NOT_FOUND, "会话不存在"));
        if (!conv.getUserId().equals(userId)) {
            throw new BusinessException(ErrorCode.FORBIDDEN, "无权操作该消息");
        }

        message.setFeedback(feedback);
        messageRepository.save(message);
        log.info("Message {} feedback set to {} by user {}", messageId, feedback, userId);
    }

    private MessageDto toDto(Message msg) {
        MessageDto dto = new MessageDto();
        dto.setId(msg.getId());
        dto.setRole(msg.getRole());
        dto.setContent(msg.getContent());
        dto.setFeedback(msg.getFeedback());
        dto.setTimestamp(msg.getTimestamp());

        try {
            if (msg.getCitations() != null) {
                dto.setCitations(objectMapper.readValue(msg.getCitations(),
                        new TypeReference<List<Map<String, Object>>>() {}));
            }
            if (msg.getAgentSteps() != null) {
                dto.setAgentSteps(objectMapper.readValue(msg.getAgentSteps(),
                        new TypeReference<List<Map<String, Object>>>() {}));
            }
        } catch (Exception e) {
            log.warn("Failed to parse citations/agentSteps for message {}", msg.getId(), e);
        }

        return dto;
    }
}
